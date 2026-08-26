# file: tests/test_api_errors.py

"""Cloud-API failure surfacing: classification, framing, and the AudioWriter
wiring that turns a swallowed exception into a user-visible notification.

Before this feature an exhausted quota was invisible: streaming segments were
silently skipped, the final transcription's exception killed the timer thread
(freezing the indicator on "processing"), and the LLM correction quietly fell
back to the raw transcript. These tests pin the three notification points and
the message contract (localized, provider-named, loudly framed so the string
can never pass for dictated text).
"""

from __future__ import annotations

import queue
from types import SimpleNamespace

import httpx
import numpy as np
import openai
import pytest

from i18n import DEFAULT_LOCALE, current_locale, set_locale
from services.api_errors import (
    CloudApiError,
    classify_api_error,
    frame_alert,
    user_message,
)
from services.audio_writer import AudioWriter


@pytest.fixture(autouse=True)
def _reset_locale():
    before = current_locale()
    set_locale(DEFAULT_LOCALE)
    yield
    set_locale(before)


def _status_error(cls, status, body=None, message="boom"):
    request = httpx.Request("POST", "https://api.test/v1")
    response = httpx.Response(status, request=request)
    return cls(message, response=response, body=body)


# ---------- classification ----------

def test_insufficient_quota_is_quota_not_rate():
    """Both arrive as HTTP 429; only the error code separates "out of money"
    (user must top up) from a transient per-minute limit (just retry)."""
    exc = _status_error(
        openai.RateLimitError,
        429,
        body={"code": "insufficient_quota"},
        message="Error code: 429 - insufficient_quota",
    )
    assert classify_api_error(exc) == "quota"


def test_plain_rate_limit_is_rate():
    exc = _status_error(
        openai.RateLimitError, 429,
        body={"code": "rate_limit_exceeded"}, message="Rate limit reached",
    )
    assert classify_api_error(exc) == "rate"


def test_payment_required_is_quota():
    exc = _status_error(openai.APIStatusError, 402, body=None)
    assert classify_api_error(exc) == "quota"


@pytest.mark.parametrize("cls,status", [
    (openai.AuthenticationError, 401),
    (openai.PermissionDeniedError, 403),
])
def test_bad_key_is_auth(cls, status):
    assert classify_api_error(_status_error(cls, status, body=None)) == "auth"


def test_connection_and_timeout_are_network():
    request = httpx.Request("POST", "https://api.test/v1")
    assert classify_api_error(openai.APIConnectionError(request=request)) == "network"
    assert classify_api_error(openai.APITimeoutError(request=request)) == "network"
    # The text-ops watchdog raises a bare TimeoutError on a hung request.
    assert classify_api_error(TimeoutError("watchdog")) == "network"


def test_unrecognized_is_unknown():
    assert classify_api_error(ValueError("nope")) == "unknown"


def test_cloud_api_error_unwraps_to_the_original():
    inner = _status_error(openai.AuthenticationError, 401, body=None)
    assert classify_api_error(CloudApiError("Groq", inner)) == "auth"


# ---------- message contract ----------

def test_frame_alert_wraps_both_ends():
    """The frame is the user's cue that this is a system alert, not their own
    dictated words — it must survive on both sides of the text."""
    framed = frame_alert("hello")
    assert framed.startswith("!!! ⚠ ")
    assert framed.endswith(" ⚠ !!!")
    assert "hello" in framed


def test_user_message_is_localized_framed_and_names_the_provider():
    set_locale("ru")
    msg = user_message("transcribe", "quota", "OpenAI")
    assert msg.startswith("!!! ⚠ ") and msg.endswith(" ⚠ !!!")
    assert "OpenAI" in msg
    assert any("Ѐ" <= ch <= "ӿ" for ch in msg), "expected a Russian message"


def test_user_message_degrades_on_unknown_codes():
    """Runs inside signal handlers — bad input must render, never raise."""
    msg = user_message("no-such-context", "no-such-kind", "OpenAI")
    assert "OpenAI" in msg and msg.startswith("!!! ⚠ ")


# ---------- AudioWriter wiring ----------

class _Bridge:
    def __init__(self):
        self.statuses: list[str] = []
        self.errors: list[tuple] = []
        self.api_error = SimpleNamespace(emit=lambda *a: self.errors.append(a))

    def safe_emit_status(self, status):
        self.statuses.append(status)


def _bare_writer():
    w = AudioWriter.__new__(AudioWriter)
    w.ui_bridge = _Bridge()
    w._api_error_notified = False
    w.transcription_backend = "openai"
    return w


def test_notify_api_error_fires_once_per_session():
    w = _bare_writer()
    err = CloudApiError("Groq", TimeoutError())
    w._notify_api_error("transcribe", err)
    w._notify_api_error("transcribe", err)  # same session: suppressed
    assert w.ui_bridge.errors == [("transcribe", "network", "Groq")]
    w._api_error_notified = False  # what start_recording does on a new session
    w._notify_api_error("transcribe", err)
    assert len(w.ui_bridge.errors) == 2


def test_streaming_segment_failure_notifies_the_user():
    """A dead quota mid-dictation loses words — that must produce exactly one
    api_error emission, not a silent log line (and not one per segment)."""
    w = _bare_writer()
    w._write_transcription_wav = lambda *a, **k: None
    w.fs = 16000
    w.overlap_duration = 1
    w.segment_duration = 0  # segment boundary on the first iteration
    w.streaming = True
    w.is_recording = True
    w._session_gen = 0
    w.transcribed_segments = []
    w.audio_queue = queue.Queue()
    w.audio_queue.put(np.zeros((100, 1), dtype=np.int16))

    def _fail(path, streaming=False):
        w.streaming = False
        w.is_recording = False
        raise CloudApiError("OpenAI", _status_error(
            openai.RateLimitError, 429, body={"code": "insufficient_quota"},
            message="insufficient_quota",
        ))

    w._transcribe_audio_file = _fail
    w.streaming_transcribe(session_gen=0)

    assert w.ui_bridge.errors == [("transcribe", "quota", "OpenAI")]


def test_final_transcription_failure_resets_state_and_shows_error(monkeypatch):
    """The stuck-on-processing bug: a raising process_audio_file must not kill
    the calling thread silently — the user gets the notification, the window
    flips to "error", and the hooks come back so the next hotkey works."""
    w = _bare_writer()
    w.is_recording = True
    w.streaming = True
    w._session_gen = 3
    w.stream = SimpleNamespace(stop=lambda: None, close=lambda: None)
    w.mouse_hook = None
    w.transcription_thread = None
    w.recording_timer = None
    w.transcribed_segments = []
    w.audio_queue = queue.Queue()
    w.audio_queue.put(np.zeros((10, 1), dtype=np.int16))
    w._write_transcription_wav = lambda *a, **k: None

    def _boom(path, session_gen=None):
        raise CloudApiError("OpenAI", _status_error(
            openai.AuthenticationError, 401, body=None,
        ))
    w.process_audio_file = _boom

    rearmed = []
    w.press_and_talk = lambda: rearmed.append(True)

    w.stop_recording()

    assert w.ui_bridge.errors == [("transcribe", "auth", "OpenAI")]
    assert w.ui_bridge.statuses[-1] == "error"
    assert rearmed, "hooks must be reinstalled after a failed transcription"


def test_postprocess_failure_pastes_raw_and_notifies():
    """The graceful raw-transcript fallback stays — but now the user learns WHY
    the text arrived uncorrected."""
    w = _bare_writer()
    w.active_action = "transcribe"
    w.config = SimpleNamespace(get=lambda *a, **k: None, llm_max_tokens=4000)

    def _raise(**kwargs):
        raise TimeoutError("watchdog")
    w.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_raise))
    )

    assert w._apply_action_transform("raw words") == "raw words"
    assert w.ui_bridge.errors == [("postprocess", "network", "OpenAI")]

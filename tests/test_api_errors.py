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
    degraded_text,
    failover_message,
    failover_text,
    frame_alert,
    notice_text,
    user_message,
)
from services import audio_writer as aw
from services.audio_writer import AudioWriter
from services.gemini_transcribe import GeminiApiError


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
        self.failovers: list[tuple] = []
        self.provider_failover = SimpleNamespace(emit=lambda *a: self.failovers.append(a))
        self.quick: list[tuple] = []
        self.quick_fallback = SimpleNamespace(emit=lambda *a: self.quick.append(a))
        self.degraded: list[tuple] = []
        self.provider_degraded = SimpleNamespace(emit=lambda *a: self.degraded.append(a))

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
    w.active_action = "quick"
    values = {"DICTATION_AI_CORRECTION": "true"}
    w.config = SimpleNamespace(get=lambda k, d=None: values.get(k, d), llm_max_tokens=4000)

    def _raise(**kwargs):
        raise TimeoutError("watchdog")
    w.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_raise))
    )

    assert w._apply_action_transform("raw words") == "Raw words"
    assert w.ui_bridge.errors == [("postprocess", "network", "OpenAI")]


# ---------- failover: no longer silent ----------

def _gemini_out_of_quota():
    return GeminiApiError("429", kind="http", status=429, body="Quota exceeded for ...")


def _failover_writer():
    """Gemini primary (dead), OpenAI as the credentialed fallback."""
    w = _bare_writer()
    w.transcription_backend = "gemini"
    w.gemini_api_key = "g"
    w.client = object()
    w.groq_client = None
    w.config = SimpleNamespace(get=lambda k, d=None: "some-model")
    w._scrub_glossary_echo = lambda text: text

    def _gemini(path, model):
        raise _gemini_out_of_quota()
    w._transcribe_via_gemini = _gemini
    w._transcribe_via_cloud = lambda path, client, label, model: "hello"
    return w


def test_batch_failover_announces_the_primary_reason_once():
    """The silent failover: text arrived via OpenAI and nothing told the user
    Gemini was out of credits. Now one provider_failover carries the PRIMARY's
    reason; the sticky switch means later segments do not repeat it."""
    w = _failover_writer()
    assert w._transcribe_audio_file("x.wav") == "hello"
    assert w.ui_bridge.failovers == [("Gemini", "quota", "OpenAI")]
    assert w.transcription_backend == "openai"
    assert w._degraded_batch == ("Gemini", "OpenAI")
    assert w.ui_bridge.errors == []          # text was delivered: not an error
    w._transcribe_audio_file("x.wav")        # now served by OpenAI directly
    assert len(w.ui_bridge.failovers) == 1


def test_recording_start_reports_the_degradation_that_applies():
    quick = next(iter(aw.REALTIME_ACTIONS))
    w = _bare_writer()
    w._degraded_batch = ("Gemini", "OpenAI")

    # No live engine key: the hotkey runs on the batch chain, so its failover
    # is this recording's news.
    w.active_action, w._session_source = quick, "batch"
    w._emit_provider_degraded()
    # A healthy live session never touches the batch chain: no banner.
    w.active_action, w._session_source = quick, "realtime"
    w._emit_provider_degraded()
    # A written-off live engine is what a quick session must hear about.
    w._degraded_quick = ("ElevenLabs", "OpenAI")
    w._emit_provider_degraded()
    # Settings save / tray model pick: everything healthy again.
    w._reset_provider_health()
    w._emit_provider_degraded()

    assert w.ui_bridge.degraded == [
        ("Gemini", "OpenAI"), ("", ""), ("ElevenLabs", "OpenAI"), ("", ""),
    ]


def test_quick_engine_is_written_off_on_quota_but_not_on_network():
    w = _bare_writer()
    w.config = SimpleNamespace(get=lambda k, d=None: d)
    w.gemini_api_key, w.elevenlabs_api_key = "g", "e"

    w._note_quick_engine_failure("gemini", "Gemini", TimeoutError("blip"))
    assert w._pick_quick_engine() == "gemini"       # transient: tried again
    assert w._degraded_quick is None

    w._note_quick_engine_failure("gemini", "Gemini", _gemini_out_of_quota())
    assert w._pick_quick_engine() == "elevenlabs"   # retry cannot cure quota
    assert w._degraded_quick == ("Gemini", "ElevenLabs")

    w._reset_provider_health()                      # keys re-read on save
    assert w._pick_quick_engine() == "gemini"


def test_quick_engine_down_with_same_named_batch_provider_stays_silent():
    """ "Gemini unavailable — using Gemini" would be nonsense in the banner."""
    w = _bare_writer()
    w.config = SimpleNamespace(get=lambda k, d=None: d)
    w.gemini_api_key, w.elevenlabs_api_key = "g", None
    w.transcription_backend = "gemini"
    w._note_quick_engine_failure("gemini", "Gemini", _gemini_out_of_quota())
    assert w._pick_quick_engine() is None
    assert w._degraded_quick is None


def test_quick_fallback_names_the_provider_that_served_once_per_session():
    w = _bare_writer()
    w.transcription_backend = "openai"       # what the batch replay ran on
    w._notify_quick_fallback(_gemini_out_of_quota(), "Gemini")
    w._notify_quick_fallback(_gemini_out_of_quota(), "Gemini")
    assert w.ui_bridge.quick == [("Gemini", "quota", "OpenAI")]
    # Shares the once-per-session gate with api_error.
    w._notify_api_error("postprocess", TimeoutError(), provider="OpenAI")
    assert w.ui_bridge.errors == []


# ---------- indicator wording ----------

def test_pill_texts_are_localized_and_name_both_providers():
    set_locale("ru")
    for text in (failover_text("Gemini", "quota", "OpenAI"),
                 degraded_text("Gemini", "OpenAI")):
        assert "Gemini" in text and "OpenAI" in text
        assert any("\u0400" <= ch <= "\u04ff" for ch in text)
    assert "Gemini" in notice_text("transcribe", "auth", "Gemini")
    # The pill is not pasteable, so its text carries no frame...
    assert "!!!" not in failover_text("Gemini", "quota", "OpenAI")
    # ...the toast fallback (indicator switched off) still does.
    framed = failover_message("Gemini", "quota", "OpenAI")
    assert framed.startswith("!!! \u26a0 ") and framed.endswith(" \u26a0 !!!")

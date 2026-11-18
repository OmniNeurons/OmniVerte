# file: tests/test_key_check.py

"""The "Check" button beside each API-key field: services.key_check + the page.

The probe exists to answer one question before the user finds out mid-dictation:
does this key work, and can the account pay? It must use the same failure
classification as the dictation pipeline (so button and indicator agree), must
never raise into the UI, and the page must never show a verdict for a key other
than the one currently in the field. No test here touches the network.
"""

from __future__ import annotations

import io
import os
import urllib.error
import wave

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import httpx
import openai
import pytest

from PySide6.QtWidgets import QApplication

from services import key_check
from services.api_errors import classify_api_error
from services.gemini_transcribe import GeminiApiError


# ---------- the probe audio ----------

def test_silent_wav_is_a_valid_one_second_mono_file():
    with wave.open(io.BytesIO(key_check.silent_wav()), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 16000)
        assert w.getnframes() == 16000


# ---------- OpenAI / Groq ----------

def _status_error(cls, status, body=None, message="boom"):
    request = httpx.Request("POST", "https://api.test/v1")
    return cls(message, response=httpx.Response(status, request=request), body=body)


def _fake_openai(monkeypatch, outcome):
    """Replace openai.OpenAI; record how it was built and what it was asked."""
    seen = {}

    class _Client:
        def __init__(self, **kwargs):
            seen["init"] = kwargs
            self.audio = self
            self.transcriptions = self

        def create(self, **kwargs):
            seen["create"] = kwargs
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(openai, "OpenAI", _Client)
    return seen


def test_openai_success_is_ok_and_probes_with_the_chosen_model(monkeypatch):
    seen = _fake_openai(monkeypatch, object())
    assert key_check.check_key("openai", "sk-x", "gpt-transcribe") == "ok"
    assert seen["init"]["api_key"] == "sk-x"
    assert seen["init"]["base_url"] is None
    assert seen["init"]["max_retries"] == 0      # a retry only delays the answer
    assert seen["create"]["model"] == "gpt-transcribe"


def test_groq_goes_to_the_groq_host(monkeypatch):
    seen = _fake_openai(monkeypatch, object())
    assert key_check.check_key("groq", "gsk-x", "whisper-large-v3") == "ok"
    assert "groq.com" in seen["init"]["base_url"]


@pytest.mark.parametrize("exc, expected", [
    (_status_error(openai.AuthenticationError, 401), "auth"),
    (_status_error(openai.RateLimitError, 429, body={"code": "insufficient_quota"},
                   message="insufficient_quota"), "quota"),
    (_status_error(openai.RateLimitError, 429, body={"code": "rate_limit_exceeded"}), "rate"),
    (openai.APIConnectionError(request=httpx.Request("POST", "https://api.test/v1")), "network"),
    (ValueError("surprise"), "unknown"),
])
def test_openai_failures_use_the_pipeline_classification(monkeypatch, exc, expected):
    _fake_openai(monkeypatch, exc)
    assert key_check.check_key("openai", "sk-x", "m") == expected


# ---------- Gemini ----------

def test_gemini_success_probes_a_real_file_and_cleans_it_up(monkeypatch):
    seen = {}

    def _transcribe(api_key, path, model, timeout=None, **kw):
        seen.update(key=api_key, path=path, model=model, existed=os.path.exists(path))
        return ""

    monkeypatch.setattr(key_check.gemini_transcribe, "transcribe_file", _transcribe)
    assert key_check.check_key("gemini", "AIza-x", "gemini-3.5-transcribe") == "ok"
    assert seen["existed"] and not os.path.exists(seen["path"])
    assert (seen["key"], seen["model"]) == ("AIza-x", "gemini-3.5-transcribe")


def test_gemini_invalid_key_is_auth_although_google_answers_400():
    """Google reports a wrong key as 400 INVALID_ARGUMENT, not 401 — without
    the ErrorInfo reason it would read as "unexpected error"."""
    body = '{"error": {"code": 400, "details": [{"reason": "API_KEY_INVALID"}]}}'
    assert classify_api_error(GeminiApiError("400", kind="http", status=400, body=body)) == "auth"
    # ...while an ordinary bad request stays unknown.
    assert classify_api_error(GeminiApiError("400", kind="http", status=400, body="{}")) == "unknown"


def test_provider_overload_is_busy_not_an_unexplained_failure(monkeypatch):
    """Seen live: Gemini answered the probe with 503 "experiencing high
    demand" and the button could only say "could not check — see the log"."""
    def _raise(*a, **k):
        raise GeminiApiError("503", kind="http", status=503,
                             body='{"error": {"code": "service_unavailable"}}')
    monkeypatch.setattr(key_check.gemini_transcribe, "transcribe_file", _raise)
    assert key_check.check_key("gemini", "AIza-x", "m") == "busy"
    # Same for the OpenAI-compatible providers.
    assert classify_api_error(_status_error(openai.InternalServerError, 503)) == "busy"


def test_gemini_out_of_quota(monkeypatch):
    def _raise(*a, **k):
        raise GeminiApiError("429", kind="http", status=429, body="Quota exceeded")
    monkeypatch.setattr(key_check.gemini_transcribe, "transcribe_file", _raise)
    assert key_check.check_key("gemini", "AIza-x", "m") == "quota"


# ---------- ElevenLabs ----------

@pytest.mark.parametrize("data, expected", [
    ({"character_count": 10, "character_limit": 10000}, "ok"),
    ({"character_count": 10000, "character_limit": 10000}, "quota"),
    ({"character_count": 12000, "character_limit": 10000}, "quota"),
    ({"tier": "free"}, "ok_nobalance"),          # accepted, numbers absent
    (["not", "a", "dict"], "unknown"),
])
def test_elevenlabs_subscription_body(data, expected):
    assert key_check.classify_elevenlabs_subscription(data) == expected


@pytest.mark.parametrize("status, body, expected", [
    (401, '{"detail": {"status": "invalid_api_key"}}', "auth"),
    # A restricted key authenticates fine; it just may not read the balance.
    (401, '{"detail": {"status": "missing_permissions"}}', "ok_nobalance"),
    (402, "", "quota"),
    (429, "", "rate"),
    (503, "", "busy"),
    (418, "", "unknown"),
])
def test_elevenlabs_http_errors(status, body, expected):
    assert key_check.classify_elevenlabs_http(status, body) == expected


def test_elevenlabs_request_carries_the_key_and_reads_the_body(monkeypatch):
    seen = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"character_count": 1, "character_limit": 100}'

    def _urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["key"] = request.get_header("Xi-api-key")
        return _Resp()

    monkeypatch.setattr(key_check.urllib.request, "urlopen", _urlopen)
    assert key_check.check_key("elevenlabs", "el-key") == "ok"
    assert seen == {"url": key_check.ELEVENLABS_SUBSCRIPTION_URL, "key": "el-key"}


def test_elevenlabs_network_failure(monkeypatch):
    def _urlopen(request, timeout=None):
        raise urllib.error.URLError("no route")
    monkeypatch.setattr(key_check.urllib.request, "urlopen", _urlopen)
    assert key_check.check_key("elevenlabs", "el-key") == "network"


def test_unknown_provider_never_raises():
    assert key_check.check_key("nope", "k") == "unknown"


# ---------- the settings page ----------

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(qapp):
    from ui.settings_pages.transcription_page import TranscriptionPage

    p = TranscriptionPage()
    p.show()  # visibility is only reported once shown
    return p


@pytest.fixture
def no_threads(monkeypatch):
    """Capture the worker instead of starting it: the page's own logic is what
    is under test, and a real thread would race the assertions."""
    from ui.settings_pages import transcription_page

    started = []

    class _Thread:
        def __init__(self, target=None, **kw):
            self.target = target

        def start(self):
            started.append(self.target)

    monkeypatch.setattr(transcription_page.threading, "Thread", _Thread)
    return started


def test_every_key_field_has_a_check_button(page):
    assert set(page._check_buttons) == {"openai", "groq", "gemini", "elevenlabs"}
    assert all(not s.isVisible() for s in page._check_status.values())


def test_empty_field_asks_for_a_key_without_a_request(page, no_threads):
    page._on_check_key("openai")
    assert no_threads == []
    assert page._check_status["openai"].isVisible()
    assert page._check_status["openai"].property("tone") == "warn"


def test_check_runs_off_thread_and_shows_the_verdict(page, no_threads, monkeypatch):
    calls = []
    monkeypatch.setattr(key_check, "check_key",
                        lambda provider, key, model: calls.append((provider, key, model)) or "quota")
    page.openai_key_edit.setText("sk-typed")
    page._on_check_key("openai")

    assert not page._check_buttons["openai"].isEnabled()      # busy
    assert page._check_status["openai"].property("tone") == "muted"
    no_threads[0]()                                           # the worker body
    QApplication.processEvents()

    assert calls == [("openai", "sk-typed", page.model_combos["openai"].currentText())]
    assert page._check_buttons["openai"].isEnabled()
    assert page._check_status["openai"].property("tone") == "bad"


def test_masked_field_checks_the_stored_key(page, no_threads, monkeypatch):
    from ui.settings_pages.transcription_page import MASKED_PLACEHOLDER

    calls = []
    monkeypatch.setattr(key_check, "check_key",
                        lambda provider, key, model: calls.append(key) or "ok")
    page.groq_key_edit.setText(MASKED_PLACEHOLDER)
    page.groq_key_edit.setRealKeyFetcher(lambda: "gsk-stored")
    page._on_check_key("groq")
    no_threads[0]()
    QApplication.processEvents()
    assert calls == ["gsk-stored"]
    assert page._check_status["groq"].property("tone") == "ok"


def test_editing_the_field_voids_a_verdict_in_flight(page, no_threads, monkeypatch):
    """The old key's verdict must not land under the new text."""
    monkeypatch.setattr(key_check, "check_key", lambda provider, key, model: "ok")
    page.gemini_key_edit.setText("AIza-old")
    page._on_check_key("gemini")
    page.gemini_key_edit.textEdited.emit("AIza-new")          # user keeps typing
    assert not page._check_status["gemini"].isVisible()
    assert page._check_buttons["gemini"].isEnabled()
    no_threads[0]()                                           # late answer
    QApplication.processEvents()
    assert not page._check_status["gemini"].isVisible()


def test_elevenlabs_is_checked_without_a_model(page, no_threads, monkeypatch):
    calls = []
    monkeypatch.setattr(key_check, "check_key",
                        lambda provider, key, model: calls.append((provider, model)) or "ok_nobalance")
    page.elevenlabs_key_edit.setText("el-key")
    page._on_check_key("elevenlabs")
    no_threads[0]()
    QApplication.processEvents()
    assert calls == [("elevenlabs", None)]
    assert page._check_status["elevenlabs"].property("tone") == "warn"

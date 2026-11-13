"""Gemini 3.5 Transcribe Live client (services.gemini_live) against a fake socket."""

from __future__ import annotations

import json
import queue

import pytest
import websocket

from services import gemini_live as gl
from services.api_errors import classify_api_error
from services.gemini_transcribe import GeminiApiError


# ---------- pure helpers ----------

def test_build_setup_maps_languages_vocabulary_and_disables_server_vad():
    setup = gl.build_setup("ru", ["en", "ru", "xx"], ["OmniVerte", " ", "TraderNet"])
    assert setup["model"] == "models/gemini-3.5-transcribe-live"
    assert setup["realtimeInputConfig"] == {"automaticActivityDetection": {"disabled": True}}
    tr = setup["inputAudioTranscription"]
    assert tr["languageCodes"] == ["ru-RU", "en-US"]      # dedup, unknown dropped
    assert tr["mode"] == "VERBATIM"
    assert tr["customVocabulary"] == ["OmniVerte", "TraderNet"]


def test_build_setup_auto_detect_and_vocabulary_cap():
    setup = gl.build_setup(None, None, [f"t{i}" for i in range(150)])
    tr = setup["inputAudioTranscription"]
    assert tr["languageCodes"] == []
    assert len(tr["customVocabulary"]) == gl.MAX_VOCABULARY_TERMS


@pytest.mark.parametrize("raw, clean", [
    ("зафиксирую все три промпта, э-э, три новых стиля", "зафиксирую все три промпта, три новых стиля"),
    ("Э-э, моя учётка только на чтение.", "Моя учётка только на чтение."),
    ("подавали её под особенным, э, условием.", "подавали её под особенным, условием."),
    ("Готово, эм.", "Готово."),
    ("Ну вот, типа так, это как бы работает.", "Ну вот, типа так, это как бы работает."),
    ("Эмма и Элла, эстетика, мама.", "Эмма и Элла, эстетика, мама."),
    ("so, um, it works", "so, it works"),
    ("Äh, das ist ähm gut.", "Das ist gut."),
    ("c'est, euh, prêt", "c'est, prêt"),
    ("è, ehm, pronto", "è, pronto"),
    ("tornillo de 5 mm", "tornillo de 5 mm"),
    ("", ""),
])
def test_strip_hesitations(raw, clean):
    assert gl.strip_hesitations(raw) == clean


@pytest.mark.parametrize("code, reason, kind", [
    (1007, "API key not valid. Please pass a valid API key.", "auth"),
    (1011, "RESOURCE_EXHAUSTED: You exceeded your current quota", "quota"),
    (1008, "models/x is not found for API version v1beta", "unknown"),
])
def test_close_error_is_classified_like_batch_gemini(code, reason, kind):
    err = gl.close_error(code, reason)
    assert isinstance(err, GeminiApiError)
    assert classify_api_error(err) == kind


# ---------- session against a fake socket ----------

def _text(obj):
    return websocket.ABNF.OPCODE_TEXT, json.dumps(obj).encode()


def _close(code, reason):
    return websocket.ABNF.OPCODE_CLOSE, code.to_bytes(2, "big") + reason.encode()


class _FakeWS:
    """Scripted server: replies are queued by reacting to what the client sends."""

    def __init__(self, on_send=None):
        self.sent = []
        self.inbox = queue.Queue()
        self.on_send = on_send or (lambda ws, msg: None)
        self.closed = False

    def send(self, raw):
        msg = json.loads(raw)
        self.sent.append(msg)
        self.on_send(self, msg)

    def push(self, frame):
        self.inbox.put(frame)

    def recv_data(self, control_frame=False):
        frame = self.inbox.get(timeout=5)
        if frame is None:
            raise websocket.WebSocketConnectionClosedException("closed")
        return frame

    def settimeout(self, t):
        pass

    def close(self):
        self.closed = True
        self.inbox.put(None)


def _server(final_text="Плохо, что нет индикатора.", complete=True):
    def on_send(ws, msg):
        if "setup" in msg:
            ws.push(_text({"setupComplete": {}}))
        elif msg.get("realtimeInput", {}).get("activityEnd") is not None:
            if final_text:
                ws.push(_text({"serverContent": {"inputTranscription": {"text": final_text}}}))
            if complete:
                ws.push(_text({"serverContent": {"generationComplete": True}}))
    return _FakeWS(on_send)


def _session(ws):
    return gl.LiveSession("k", gl.build_setup("ru"), connect=lambda key: ws)


def test_session_sends_setup_activity_audio_and_returns_final():
    ws = _server()
    s = _session(ws)
    s.start()
    s.send_pcm(b"\x01\x00" * (gl.CHUNK_BYTES // 2 + 10))   # 1 full chunk + a tail
    assert s.finish() == "Плохо, что нет индикатора."
    kinds = [next(iter(m)) if "setup" in m else next(iter(m["realtimeInput"])) for m in ws.sent]
    assert kinds[0] == "setup"
    assert kinds[1] == "activityStart"
    assert kinds[-1] == "activityEnd"
    assert kinds.count("audio") == 2                      # tail flushed on finish
    audio = ws.sent[2]["realtimeInput"]["audio"]
    assert audio["mimeType"] == "audio/pcm;rate=16000"
    assert s.segments == ["Плохо, что нет индикатора."]
    assert s.used_partial is False


def test_session_joins_several_finals():
    ws = _server(final_text=None)
    orig = ws.on_send

    def on_send(w, msg):
        if msg.get("realtimeInput", {}).get("activityEnd") is not None:
            w.push(_text({"serverContent": {"inputTranscription": {"text": "Первая часть."}}}))
            w.push(_text({"serverContent": {"inputTranscription": {"text": " Вторая часть."}}}))
        orig(w, msg)
    ws.on_send = on_send
    s = _session(ws)
    s.start()
    assert s.finish() == "Первая часть. Вторая часть."


def test_finish_falls_back_to_interim_on_timeout():
    ws = _server(final_text=None, complete=False)
    orig = ws.on_send

    def on_send(w, msg):
        orig(w, msg)
        if "audio" in msg.get("realtimeInput", {}):
            w.push(_text({"serverContent": {"interimInputTranscription": {"text": "почти готово"}}}))
    ws.on_send = on_send
    s = _session(ws)
    s.start()
    s.send_pcm(b"\x00" * gl.CHUNK_BYTES)
    assert s.finish(timeout=0.3) == "почти готово"
    assert s.used_partial is True


def test_server_close_frame_raises_classified_error():
    def on_send(ws, msg):
        if "setup" in msg:
            ws.push(_close(1007, "API key not valid. Please pass a valid API key."))
    s = _session(_FakeWS(on_send))
    s.start()
    with pytest.raises(GeminiApiError) as e:
        s.finish()
    assert classify_api_error(e.value) == "auth"


def test_connect_network_failure_is_retried_once():
    calls = []
    ws = _server()

    def connect(key):
        calls.append(key)
        if len(calls) == 1:
            raise OSError("blip")
        return ws
    s = gl.LiveSession("k", gl.build_setup("ru"), connect=connect)
    s.start()
    assert s.finish() == "Плохо, что нет индикатора."
    assert len(calls) == 2


def test_connect_http_failure_is_not_retried(monkeypatch):
    calls = []

    def connect(key):
        calls.append(key)
        raise websocket.WebSocketBadStatusException("forbidden %s %s", 403, "Forbidden")
    s = gl.LiveSession("k", gl.build_setup("ru"), connect=connect)
    s.start()
    with pytest.raises(GeminiApiError) as e:
        s.finish()
    assert e.value.status == 403
    assert len(calls) == 1


def test_silent_take_ends_on_activity_end_echo_and_ignores_interim():
    """Live behaviour on silence: an interim from vocabulary bias, then only the
    ACTIVITY_END echo — no final, no generationComplete."""
    def on_send(ws, msg):
        if "setup" in msg:
            ws.push(_text({"setupComplete": {}}))
            ws.push(_text({"serverContent": {"interimInputTranscription": {"text": "'TraderNet'"}}}))
        elif msg.get("realtimeInput", {}).get("activityEnd") is not None:
            ws.push(_text({"serverContent": {}, "voiceActivity": {"type": "ACTIVITY_END"}}))
    s = _session(_FakeWS(on_send))
    s.start()
    import time
    t0 = time.monotonic()
    assert s.finish() == ""
    assert time.monotonic() - t0 < 2.0          # no FINISH_TIMEOUT wait
    assert s.used_partial is False

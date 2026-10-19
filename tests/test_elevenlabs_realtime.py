"""ElevenLabs realtime client (services.elevenlabs_realtime) against a fake socket.

No network: RealtimeSession takes a ``connect`` factory, so each test scripts
the server side — what it says after the handshake and how it answers the
final commit.
"""

from __future__ import annotations

import base64
import json
import queue
import time
import urllib.parse

import pytest
import websocket

from services import elevenlabs_realtime as er
from services.api_errors import CloudApiError, classify_api_error


class _FakeWs:
    """Socket stand-in: recv() serves a queue, send() records and may reply."""

    def __init__(self, on_commit=None, greet=True):
        self.sent: list[dict] = []
        self._inbox: queue.Queue = queue.Queue()
        self._on_commit = on_commit or (lambda ws: None)
        self.closed = False
        if greet:
            self.push({"message_type": "session_started"})

    def push(self, msg: dict) -> None:
        self._inbox.put(json.dumps(msg))

    def settimeout(self, _):
        pass

    def recv(self):
        item = self._inbox.get(timeout=5)
        if item is None:
            raise websocket.WebSocketConnectionClosedException("closed")
        return item

    def send(self, text):
        msg = json.loads(text)
        self.sent.append(msg)
        if msg.get("commit"):
            self._on_commit(self)

    def close(self):
        self.closed = True
        self._inbox.put(None)


def _session(ws) -> er.RealtimeSession:
    s = er.RealtimeSession("key", "wss://x", connect=lambda url, key: ws)
    s.start()
    return s


def _wait_committed(s: er.RealtimeSession, n: int) -> None:
    """Let the reader thread catch up before the test calls finish()."""
    deadline = time.monotonic() + 2
    while len(s._committed) < n and time.monotonic() < deadline:
        time.sleep(0.005)


def _audio(sent: list[dict]) -> bytes:
    return b"".join(base64.b64decode(m["audio_base_64"]) for m in sent)


# ---------- pure helpers ----------

def test_build_url_carries_languages_and_keyterms():
    url = er.build_url("ru", ["en", "ru", ""], ["Acme", " ", "merge request"])
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert url.startswith(er.REALTIME_URL + "?")
    assert q["model_id"] == ["scribe_v2_realtime"]
    assert q["audio_format"] == ["pcm_16000"]
    assert q["commit_strategy"] == ["vad"]
    assert q["no_verbatim"] == ["true"]             # no LLM pass to drop fillers
    assert q["language_code"] == ["ru"]
    assert q["secondary_languages"] == ["en"]       # primary + blanks dropped
    assert q["keyterms"] == ["Acme", "merge request"]


def test_build_url_without_language_is_autodetect():
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(er.build_url(None, ["en"])).query)
    assert "language_code" not in q
    assert "secondary_languages" not in q           # meaningless without a primary


def test_build_url_caps_keyterms():
    terms = [f"t{i}" for i in range(er.MAX_KEYTERMS + 50)]
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(er.build_url(keyterms=terms)).query)
    assert len(q["keyterms"]) == er.MAX_KEYTERMS


def test_audio_chunk_message_shape():
    msg = json.loads(er.audio_chunk_message(b"\x01\x02", commit=True))
    assert msg == {
        "message_type": "input_audio_chunk",
        "audio_base_64": base64.b64encode(b"\x01\x02").decode(),
        "commit": True,
        "sample_rate": 16000,
    }


# ---------- session flow ----------

def test_finish_joins_committed_segments_in_order():
    def on_commit(ws):
        ws.push({"message_type": "committed_transcript", "text": "run the tests"})

    ws = _FakeWs(on_commit=on_commit)
    s = _session(ws)
    ws.push({"message_type": "committed_transcript", "text": "open the file,"})
    _wait_committed(s, 1)
    s.send_pcm(b"\x00" * (er.CHUNK_BYTES * 2 + 10))
    assert s.finish(timeout=2) == "open the file, run the tests"
    assert ws.closed


def test_audio_is_chunked_and_tail_committed():
    ws = _FakeWs(on_commit=lambda w: w.push(
        {"message_type": "committed_transcript", "text": "ok"}))
    s = _session(ws)
    pcm = bytes(range(256)) * 30                    # 7680 bytes = 2 chunks + tail
    s.send_pcm(pcm)
    s.finish(timeout=2)
    assert all(m["message_type"] == "input_audio_chunk" for m in ws.sent)
    assert [m["commit"] for m in ws.sent] == [False, False, True]
    assert _audio(ws.sent) == pcm                   # nothing lost or reordered


def test_audio_before_session_started_is_held_then_flushed():
    ws = _FakeWs(greet=False, on_commit=lambda w: w.push(
        {"message_type": "committed_transcript", "text": "hi"}))
    s = _session(ws)
    pcm = b"\x07" * (er.CHUNK_BYTES * 3)
    s.send_pcm(pcm)
    assert ws.sent == []                            # not up yet — held
    ws.push({"message_type": "session_started"})
    assert s.finish(timeout=2) == "hi"
    assert _audio(ws.sent) == pcm


def test_finish_timeout_returns_committed_plus_last_partial():
    ws = _FakeWs()                                  # never answers the commit
    s = _session(ws)
    ws.push({"message_type": "committed_transcript", "text": "first part"})
    ws.push({"message_type": "partial_transcript", "text": "and the tail"})
    s.send_pcm(b"\x00" * 100)
    assert s.finish(timeout=0.3) == "first part and the tail"


def test_vad_commit_racing_ours_keeps_waiting_for_the_tail():
    """A commit arriving while a newer partial is pending is not the end."""
    def on_commit(ws):
        ws.push({"message_type": "committed_transcript", "text": "segment one"})
        ws.push({"message_type": "partial_transcript", "text": "segment"})
        ws.push({"message_type": "committed_transcript", "text": "segment two"})

    ws = _FakeWs(on_commit=on_commit)
    s = _session(ws)
    s.send_pcm(b"\x00" * 100)
    assert s.finish(timeout=2) == "segment one segment two"


@pytest.mark.parametrize("mtype,kind", [
    ("auth_error", "auth"),
    ("quota_exceeded", "quota"),
    ("rate_limited", "rate"),
    ("session_time_limit_exceeded", "response"),
])
def test_server_errors_raise_with_kind(mtype, kind):
    ws = _FakeWs()
    s = _session(ws)
    ws.push({"message_type": mtype, "error": "nope"})
    s.send_pcm(b"\x00" * 100)
    with pytest.raises(er.ElevenLabsApiError) as ei:
        s.finish(timeout=1)
    assert ei.value.kind == kind
    assert ei.value.code == mtype


def test_insufficient_audio_activity_is_not_a_failure():
    ws = _FakeWs()
    s = _session(ws)
    ws.push({"message_type": "committed_transcript", "text": "done"})
    ws.push({"message_type": "insufficient_audio_activity"})
    assert s.finish(timeout=0.3) == "done"


@pytest.mark.parametrize("status,kind", [(401, "auth"), (402, "quota"), (429, "rate"), (500, "response")])
def test_handshake_http_status_maps_to_kind(status, kind):
    def boom(url, key):
        raise websocket.WebSocketBadStatusException("bad", status)

    s = er.RealtimeSession("key", "wss://x", connect=boom)
    s.start()
    with pytest.raises(er.ElevenLabsApiError) as ei:
        s.finish(timeout=1)
    assert ei.value.kind == kind


def test_network_failure_on_connect():
    def boom(url, key):
        raise OSError("no route")

    s = er.RealtimeSession("key", "wss://x", connect=boom)
    s.start()
    with pytest.raises(er.ElevenLabsApiError) as ei:
        s.finish(timeout=1)
    assert ei.value.kind == "network"


def test_connection_drop_mid_session_is_network_error():
    ws = _FakeWs()
    s = _session(ws)
    ws._inbox.put(None)                             # server vanishes
    s.send_pcm(b"\x00" * 100)
    with pytest.raises(er.ElevenLabsApiError) as ei:
        s.finish(timeout=1)
    assert ei.value.kind == "network"


# ---------- classification for the UI toast ----------

@pytest.mark.parametrize("kind,expected", [
    ("auth", "auth"), ("quota", "quota"), ("rate", "rate"),
    ("network", "network"), ("response", "unknown"),
])
def test_classify_api_error(kind, expected):
    err = er.ElevenLabsApiError("x", kind=kind)
    assert classify_api_error(err) == expected
    assert classify_api_error(CloudApiError("ElevenLabs", err)) == expected


def test_long_keyterms_are_skipped_without_costing_a_slot():
    long_term = "x" * (er.MAX_KEYTERM_CHARS + 1)
    terms = [long_term] + [f"t{i}" for i in range(er.MAX_KEYTERMS)]
    sent, too_long = er.usable_keyterms(terms)
    assert too_long == [long_term]
    assert sent == [f"t{i}" for i in range(er.MAX_KEYTERMS)]
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(er.build_url(keyterms=terms)).query)
    assert long_term not in q["keyterms"]
    assert len(q["keyterms"]) == er.MAX_KEYTERMS


def test_network_failure_on_connect_is_retried_once():
    ws = _FakeWs(on_commit=lambda w: w.push(
        {"message_type": "committed_transcript", "text": "ok"}))
    calls = []

    def flaky(url, key):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("timed out")
        return ws

    s = er.RealtimeSession("key", "wss://x", connect=flaky)
    s.start()
    s.send_pcm(b"\x00" * 100)                       # buffered across the retry
    assert s.finish(timeout=2) == "ok"
    assert len(calls) == 2
    assert _audio(ws.sent) == b"\x00" * 100


def test_http_rejection_on_connect_is_not_retried():
    calls = []

    def reject(url, key):
        calls.append(1)
        raise websocket.WebSocketBadStatusException("bad", 401)

    s = er.RealtimeSession("key", "wss://x", connect=reject)
    s.start()
    with pytest.raises(er.ElevenLabsApiError):
        s.finish(timeout=1)
    assert len(calls) == 1


def test_user_message_for_realtime_fallback_says_text_still_arrived():
    from i18n import t
    from services.api_errors import user_message

    msg = user_message("realtime_fallback", "network", "ElevenLabs")
    assert t("error.realtime_fallback.title") in msg
    assert "ElevenLabs" in msg


def test_build_url_no_verbatim_can_be_switched_off():
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(er.build_url(no_verbatim=False)).query)
    assert q["no_verbatim"] == ["false"]

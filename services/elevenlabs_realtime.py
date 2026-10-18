# file: services/elevenlabs_realtime.py

"""Streaming client for ElevenLabs Scribe v2 Realtime (the "quick" hotkey).

Unlike every other backend, this one transcribes *while the user speaks*: PCM
is pushed over a WebSocket as it is captured, the server segments it on pauses
(``commit_strategy=vad``) and sends back committed text per segment. By the
time the user releases the key, most of the transcript is already final — the
stop only has to commit the short tail. That is the whole point of the quick
mode: no batch upload after the fact, no LLM pass, paste in well under a
second.

It is deliberately NOT a member of the backend priority chain: the chain is
per-file (record → WAV → transcribe), this is per-session. AudioWriter keeps a
local copy of the session's PCM and, if this client fails, replays it through
the ordinary batch chain — so a dropped socket costs latency, never the text.

``websocket-client`` (sync, thread-based) matches the app's threading model:
one reader thread per session, sends from the caller's thread under a lock.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import urllib.parse

import websocket

logger = logging.getLogger(__name__)

REALTIME_URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
MODEL_ID = "scribe_v2_realtime"
SAMPLE_RATE = 16000

# ~100 ms of 16 kHz mono int16. Small enough that the server's VAD sees speech
# promptly, large enough not to flood the socket with tiny frames.
CHUNK_BYTES = SAMPLE_RATE * 2 // 10

# keyterms rides in the URL query; cap it so a large Pro glossary cannot blow
# past URL length limits. Glossary order is priority order — keep the head.
MAX_KEYTERMS = 100

CONNECT_TIMEOUT = 10.0
# How long finish() waits for the server to answer the final commit. The short
# variant applies when nothing is pending (the last segment was already
# committed by VAD) — then the server may have nothing to say at all.
FINISH_TIMEOUT = 3.0
FINISH_TIMEOUT_IDLE = 0.8

# Server error message_type → our kind (classified for the UI in api_errors).
_ERROR_KINDS = {
    "auth_error": "auth",
    "unaccepted_terms": "auth",
    "quota_exceeded": "quota",
    "rate_limited": "rate",
    "commit_throttled": "rate",
    "queue_overflow": "rate",
    "resource_exhausted": "rate",
    "session_time_limit_exceeded": "response",
    "input_error": "response",
    "invalid_request": "response",
    "chunk_size_exceeded": "response",
    "transcriber_error": "response",
    "error": "response",
}
# Not a failure for dictation: the user simply said nothing (or stopped
# talking long enough for the server to give up). Whatever was committed stands.
_BENIGN_ERRORS = frozenset({"insufficient_audio_activity"})


class ElevenLabsApiError(RuntimeError):
    """The realtime session failed.

    ``kind`` is "auth" | "quota" | "rate" | "network" | "response";
    ``code`` is the server's message_type or the handshake HTTP status.
    """

    def __init__(self, message: str, kind: str = "network", code=None):
        super().__init__(message)
        self.kind = kind
        self.code = code


def build_url(language: str | None = None,
              secondary_languages: list[str] | None = None,
              keyterms: list[str] | None = None) -> str:
    """Session URL with query parameters (pure — unit-testable).

    ``language`` / ``secondary_languages`` are ISO 639-1 codes (the Whisper
    short codes the app already uses); empty means auto-detect.
    """
    params: list[tuple[str, str]] = [
        ("model_id", MODEL_ID),
        ("audio_format", f"pcm_{SAMPLE_RATE}"),
        ("commit_strategy", "vad"),
    ]
    if language:
        params.append(("language_code", language))
        for code in secondary_languages or []:
            if code and code != language:
                params.append(("secondary_languages", code))
    for term in (keyterms or [])[:MAX_KEYTERMS]:
        if term and term.strip():
            params.append(("keyterms", term.strip()))
    return f"{REALTIME_URL}?{urllib.parse.urlencode(params)}"


def audio_chunk_message(pcm: bytes, commit: bool = False) -> str:
    """One ``input_audio_chunk`` frame as JSON text."""
    return json.dumps({
        "message_type": "input_audio_chunk",
        "audio_base_64": base64.b64encode(pcm).decode("ascii"),
        "commit": commit,
        "sample_rate": SAMPLE_RATE,
    })


def _connect(url: str, api_key: str):
    """Open the socket; split out so tests can inject a fake."""
    return websocket.create_connection(
        url,
        timeout=CONNECT_TIMEOUT,
        header=[f"xi-api-key: {api_key}", "User-Agent: OmniVerte (Windows)"],
    )


def _handshake_error(exc: BaseException) -> ElevenLabsApiError:
    if isinstance(exc, websocket.WebSocketBadStatusException):
        status = exc.status_code
        kind = {401: "auth", 403: "auth", 402: "quota", 429: "rate"}.get(status, "response")
        return ElevenLabsApiError(f"ElevenLabs handshake HTTP {status}", kind=kind, code=status)
    return ElevenLabsApiError(f"ElevenLabs connection failed: {exc}", kind="network")


class RealtimeSession:
    """One dictation session: start() → send_pcm()* → finish() → text.

    start() returns at once; the connection is opened on the reader thread so
    the hotkey path never waits on the network. Audio sent before the server's
    ``session_started`` is held and flushed the moment it arrives.
    """

    def __init__(self, api_key: str, url: str, connect=_connect):
        self._api_key = api_key
        self._url = url
        self._connect = connect
        self._ws = None
        self._lock = threading.Lock()        # guards sends + the state below
        self._started = threading.Event()    # session_started received
        self._closed = threading.Event()     # reader thread ended
        self._committed_event = threading.Condition(self._lock)
        self._pending = bytearray()          # audio not yet sent
        self._committed: list[str] = []
        self._partial = ""
        self._error: ElevenLabsApiError | None = None
        self._closing = False                # close() requested by us
        self._reader: threading.Thread | None = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        self._reader = threading.Thread(target=self._run, name="elevenlabs-rt", daemon=True)
        self._reader.start()

    def send_pcm(self, pcm: bytes) -> None:
        """Queue captured audio; sends in ~100 ms frames once the session is up.

        Never raises — a failure is recorded and surfaced by finish().
        """
        with self._lock:
            if self._error is not None:
                return
            self._pending.extend(pcm)
            if self._started.is_set():
                self._flush_locked(final=False)

    def finish(self, timeout: float | None = None) -> str:
        """Commit the tail and return the full transcript.

        Waits for the session to come up (bounded), sends the remaining audio
        with ``commit=true`` and waits for the matching committed segment. On
        timeout it returns what it has: committed segments plus the last
        partial — the tail as the server last heard it. Raises
        ElevenLabsApiError if the session failed; the caller falls back to the
        batch chain with its own copy of the audio.
        """
        if not self._started.wait(CONNECT_TIMEOUT):
            self.close()
            with self._lock:
                err = self._error
            raise err or ElevenLabsApiError("ElevenLabs session did not start in time")

        with self._lock:
            if self._error is not None:
                err = self._error
            else:
                err = None
                if timeout is None:
                    busy = bool(self._pending) or bool(self._partial.strip())
                    timeout = FINISH_TIMEOUT if busy else FINISH_TIMEOUT_IDLE
                seen = len(self._committed)
                self._flush_locked(final=True)
                # A fresh commit with no partial left over means the server
                # has finalized everything it heard. (A VAD commit racing our
                # own one leaves the tail's partial pending — keep waiting.)
                self._committed_event.wait_for(
                    lambda: (len(self._committed) > seen and not self._partial)
                    or self._error is not None
                    or self._closed.is_set(),
                    timeout=timeout,
                )
                err = self._error
                # On timeout the last partial is the tail as last heard.
                parts = [*self._committed, self._partial]
        self.close()
        if err is not None:
            raise err
        return " ".join(p.strip() for p in parts if p and p.strip())

    def close(self) -> None:
        self._closing = True
        ws = self._ws
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    # -- internals ---------------------------------------------------------

    def _flush_locked(self, final: bool) -> None:
        """Send pending audio. Caller holds the lock."""
        try:
            while len(self._pending) >= CHUNK_BYTES:
                chunk = bytes(self._pending[:CHUNK_BYTES])
                del self._pending[:CHUNK_BYTES]
                self._ws.send(audio_chunk_message(chunk))
            if final:
                chunk = bytes(self._pending)
                self._pending.clear()
                self._ws.send(audio_chunk_message(chunk, commit=True))
        except Exception as e:
            self._fail_locked(ElevenLabsApiError(f"ElevenLabs send failed: {e}", kind="network"))

    def _fail_locked(self, err: ElevenLabsApiError) -> None:
        if self._error is None:
            self._error = err
            logger.warning(f"ElevenLabs realtime: {err}")
        self._committed_event.notify_all()

    def _run(self) -> None:
        try:
            try:
                self._ws = self._connect(self._url, self._api_key)
            except Exception as e:
                with self._lock:
                    self._fail_locked(_handshake_error(e))
                return
            # Blocking reads from here on; close() unblocks them.
            self._ws.settimeout(None)
            while True:
                try:
                    raw = self._ws.recv()
                except Exception as e:
                    with self._lock:
                        if not self._closing_expected():
                            self._fail_locked(ElevenLabsApiError(
                                f"ElevenLabs connection lost: {e}", kind="network"))
                    return
                if not raw:
                    return
                self._handle(raw)
        finally:
            with self._lock:
                self._closed.set()
                self._committed_event.notify_all()
            # Unblock a finish() still waiting for session_started.
            self._started.set()

    def _closing_expected(self) -> bool:
        """A recv error after we asked to close is not a failure."""
        return self._closing

    def _handle(self, raw) -> None:
        try:
            msg = json.loads(raw)
        except (TypeError, ValueError):
            logger.debug(f"ElevenLabs realtime: non-JSON frame ignored: {str(raw)[:120]}")
            return
        mtype = msg.get("message_type", "")
        with self._lock:
            if mtype == "session_started":
                self._started.set()
                self._flush_locked(final=False)
            elif mtype == "partial_transcript":
                self._partial = msg.get("text") or ""
                self._committed_event.notify_all()
            elif mtype == "committed_transcript":
                self._committed.append(msg.get("text") or "")
                self._partial = ""
                self._committed_event.notify_all()
            elif mtype in _BENIGN_ERRORS:
                logger.info(f"ElevenLabs realtime: {mtype}")
                self._committed_event.notify_all()
            elif mtype in _ERROR_KINDS:
                detail = msg.get("error") or msg.get("message") or ""
                self._fail_locked(ElevenLabsApiError(
                    f"ElevenLabs {mtype}: {detail}", kind=_ERROR_KINDS[mtype], code=mtype))

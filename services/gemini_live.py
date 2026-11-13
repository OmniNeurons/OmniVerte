# file: services/gemini_live.py

"""Streaming client for Gemini 3.5 Transcribe Live (the "quick" hotkey).

Same job and same contract as services.elevenlabs_realtime.RealtimeSession —
start() → send_pcm()* → finish() → text — so AudioWriter.realtime_transcribe
drives either engine. PCM is pushed over the Live API WebSocket while the user
speaks; the hotkey itself marks the turn: ``activityStart`` once the session is
up, ``activityEnd`` on release (server VAD disabled), so a thinking pause in
mid-sentence never freezes a segment. After activityEnd the server sends the
finalized ``inputTranscription`` and ``generationComplete`` — measured ~0.4 s.

Why this engine (A/B on 300 real F9 takes, blind review, 2026-11-12): ~3x
fewer meaningful errors than Scribe v2 Realtime at the same latency. VERBATIM
mode only: SMART (server-side cleanup) rewrote words and scored 2.5x worse, so
fillers are stripped locally instead (strip_hesitations).

Failures arrive as WebSocket close frames (verified live: 1007 "API key not
valid", 1008 "model … not found") and surface as GeminiApiError, classified by
services.api_errors like the batch Gemini client. AudioWriter keeps its own
copy of the audio and replays it through the batch chain on any failure.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import threading

import websocket

from services.gemini_transcribe import MAX_VOCABULARY_TERMS, GeminiApiError

logger = logging.getLogger(__name__)

LIVE_URL = ("wss://generativelanguage.googleapis.com/ws/"
            "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent")
MODEL_ID = "gemini-3.5-transcribe-live"
SAMPLE_RATE = 16000
# 100 ms of 16 kHz mono int16 — the chunk size the Live docs recommend.
CHUNK_BYTES = SAMPLE_RATE * 2 // 10

CONNECT_ATTEMPTS = 2
CONNECT_ATTEMPT_TIMEOUT = 4.0
# Bounds finish()'s wait for setupComplete (both connect attempts + setup).
CONNECT_TIMEOUT = CONNECT_ATTEMPTS * CONNECT_ATTEMPT_TIMEOUT + 2.0
# Wait for generationComplete after activityEnd. Normally ~0.4 s; on timeout
# finish() returns what it has (finals, else the last interim).
FINISH_TIMEOUT = 5.0
# The server echoes our activityEnd as voiceActivity ACTIVITY_END — after the
# final when there was speech, and as the ONLY answer to a silent take (no
# generationComplete then; verified live). On that echo finish() allows this
# much more for a straggling final, then returns finals only: an interim seen
# on silence is vocabulary bias talking ("'TraderNet'" from 2 s of zeros).
FINAL_GRACE = 0.3

# Whisper short codes (LANGUAGE_TO_WHISPER_CODE values) → the BCP-47 codes the
# Live model lists as supported. An unsupported code is rejected and would
# fail every session, so anything unmapped is simply left out (auto-detect).
LANGUAGE_CODES = {
    "en": "en-US",
    "ru": "ru-RU",
    "es": "es-US",
    "fr": "fr-FR",
    "de": "de-DE",
    "it": "it-IT",
    "zh": "cmn-Hans-CN",
    "ja": "ja-JP",
}


def build_setup(language: str | None = None,
                secondary_languages: list[str] | None = None,
                vocabulary: list[str] | None = None) -> dict:
    """The ``setup`` message body (pure — unit-testable; no API key inside).

    Server VAD is disabled: the hotkey press/release is the turn. VERBATIM is
    the server default but stated explicitly — SMART is deliberately not used.
    """
    codes: list[str] = []
    for code in [language, *(secondary_languages or [])]:
        bcp = LANGUAGE_CODES.get(code or "")
        if bcp and bcp not in codes:
            codes.append(bcp)
    transcription: dict = {"languageCodes": codes, "mode": "VERBATIM"}
    terms = [t.strip() for t in (vocabulary or []) if t and t.strip()]
    if terms:
        transcription["customVocabulary"] = terms[:MAX_VOCABULARY_TERMS]
    return {
        "model": f"models/{MODEL_ID}",
        "generationConfig": {"responseModalities": ["TEXT"]},
        "realtimeInputConfig": {"automaticActivityDetection": {"disabled": True}},
        "inputAudioTranscription": transcription,
    }


# Pure hesitation sounds only — never words that can carry meaning ("ну",
# "типа", "вот", "like"). Matches "э", "э-э", "ээ", "эм", "мм", "хм", "uh",
# "um", "erm", "hmm", with the comma/ellipsis that VERBATIM puts after them.
# Pure hesitation sounds only, never a word with a meaning ("ну", "типа",
# "eh" / "este" in Spanish, "あの" in Japanese stay). Latin "mm" is left alone:
# it is also millimetres.
_HESITATION = (r"(?:э+(?:-э+)*|эм+|м{2,}|хм+"        # ru
               r"|uh+|um+|erm+|hmm+"                 # en
               r"|äh+m*|öh+m*"                       # de
               r"|euh+"                              # fr
               r"|ehm+)")                            # it
_HESITATION_RE = re.compile(
    rf"(?<![\w-]){_HESITATION}(?![\w-])(?:\s*(?:,|\.\.\.|…))?\s*",
    re.IGNORECASE,
)


def strip_hesitations(text: str) -> str:
    """Drop hesitation sounds from a VERBATIM transcript (pure).

    The local stand-in for ElevenLabs ``no_verbatim``: "зафиксирую все три
    промпта, э-э, три новых стиля" → "зафиксирую все три промпта, три новых
    стиля". A sentence that started with one gets its capital back.
    """
    if not text:
        return text
    # A capitalized filler started its sentence: hand the capital on to the
    # word after it (marked with \x00, resolved below).
    out = _HESITATION_RE.sub(lambda m: "\x00" if m.group(0)[0].isupper() else "", text)
    out = re.sub(r"\s+([,.!?…])", r"\1", out)        # space left before punctuation
    out = re.sub(r",\s*([.!?…])", r"\1", out)         # ", ." from a trailing filler
    out = re.sub(r",(\s*,)+", ",", out)               # doubled commas
    out = re.sub(r"^[\s,]+", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = re.sub(r"\x00\s*(\w)", lambda m: m.group(1).upper(), out)
    return out.replace("\x00", "").strip()


def _connect(api_key: str):
    """Open the socket; split out so tests can inject a fake."""
    return websocket.create_connection(
        f"{LIVE_URL}?key={api_key}",
        timeout=CONNECT_ATTEMPT_TIMEOUT,
        header=["User-Agent: OmniVerte (Windows)"],
    )


def _handshake_error(exc: BaseException) -> GeminiApiError:
    if isinstance(exc, websocket.WebSocketBadStatusException):
        return GeminiApiError(f"Gemini Live handshake HTTP {exc.status_code}",
                              kind="http", status=exc.status_code)
    return GeminiApiError(f"Gemini Live connection failed: {exc}", kind="network")


def close_error(code: int | None, reason: str) -> GeminiApiError:
    """A server close frame → GeminiApiError shaped for api_errors (pure).

    The Live API reports failures only as close code + reason text, so the
    reason is mapped onto the HTTP statuses classify_api_error already reads.
    """
    low = reason.lower()
    if "api key" in low or "permission" in low or "unauthenticated" in low:
        status = 401
    elif "quota" in low or "resource_exhausted" in low or "rate" in low:
        status = 429
    else:
        status = None
    message = f"Gemini Live closed ({code}): {reason}"
    if status is None:
        return GeminiApiError(message, kind="response", body=reason)
    return GeminiApiError(message, kind="http", status=status, body=reason)


class LiveSession:
    """One dictation session: start() → send_pcm()* → finish() → text.

    start() returns at once; the connection and setup run on the reader
    thread so the hotkey path never waits on the network. Audio sent before
    ``setupComplete`` is held and flushed right after ``activityStart``.
    """

    def __init__(self, api_key: str, setup: dict, connect=_connect):
        self._api_key = api_key
        self._setup = setup
        self._connect = connect
        self._ws = None
        self._lock = threading.Lock()        # guards sends + the state below
        self._started = threading.Event()    # setupComplete received
        self._closed = threading.Event()     # reader thread ended
        self._changed = threading.Condition(self._lock)
        self._pending = bytearray()
        self._finals: list[str] = []
        self._interim = ""
        self._ended = False                  # activityEnd sent
        self._complete = False               # generationComplete after activityEnd
        self._server_ended = False           # server echoed ACTIVITY_END
        self._error: GeminiApiError | None = None
        self._closing = False
        self._reader: threading.Thread | None = None
        # True when finish() timed out and fell back to the last interim.
        self.used_partial = False

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        self._reader = threading.Thread(target=self._run, name="gemini-live", daemon=True)
        self._reader.start()

    def send_pcm(self, pcm: bytes) -> None:
        """Queue captured audio; sent in 100 ms frames once the session is up.

        Never raises — a failure is recorded and surfaced by finish().
        """
        with self._lock:
            if self._error is not None:
                return
            self._pending.extend(pcm)
            if self._started.is_set():
                self._flush_locked(final=False)

    def finish(self, timeout: float = FINISH_TIMEOUT) -> str:
        """End the turn and return the transcript.

        Raises GeminiApiError if the session failed; the caller then replays
        its own copy of the audio through the batch chain.
        """
        if not self._started.wait(CONNECT_TIMEOUT):
            self.close()
            with self._lock:
                err = self._error
            raise err or GeminiApiError("Gemini Live session did not start in time",
                                        kind="network")
        with self._lock:
            err = self._error
            if err is None:
                self._flush_locked(final=True)
                done = lambda: (self._complete or self._error is not None
                                or self._closed.is_set())
                self._changed.wait_for(lambda: done() or self._server_ended, timeout=timeout)
                if self._server_ended and not done():
                    self._changed.wait_for(done, timeout=FINAL_GRACE)
                err = self._error
                parts = list(self._finals)
                if not parts and not self._server_ended and self._interim.strip():
                    # No final in time: the tail as the server last heard it.
                    self.used_partial = True
                    parts = [self._interim]
        self.close()
        if err is not None:
            raise err
        return " ".join(" ".join(p.strip() for p in parts if p and p.strip()).split())

    @property
    def segments(self) -> list[str]:
        """Finalized transcripts as the server sent them (copy; diagnostics)."""
        with self._lock:
            return list(self._finals)

    def close(self) -> None:
        self._closing = True
        ws = self._ws
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    # -- internals ---------------------------------------------------------

    def _send_locked(self, obj: dict) -> None:
        self._ws.send(json.dumps(obj))

    def _flush_locked(self, final: bool) -> None:
        """Send pending audio (and activityEnd when final). Caller holds the lock."""
        try:
            while len(self._pending) >= CHUNK_BYTES or (final and self._pending):
                chunk = bytes(self._pending[:CHUNK_BYTES])
                del self._pending[:CHUNK_BYTES]
                self._send_locked({"realtimeInput": {"audio": {
                    "data": base64.b64encode(chunk).decode("ascii"),
                    "mimeType": f"audio/pcm;rate={SAMPLE_RATE}",
                }}})
            if final and not self._ended:
                self._ended = True
                self._send_locked({"realtimeInput": {"activityEnd": {}}})
        except Exception as e:
            self._fail_locked(GeminiApiError(f"Gemini Live send failed: {e}", kind="network"))

    def _fail_locked(self, err: GeminiApiError) -> None:
        if self._error is None:
            self._error = err
            logger.warning(f"Gemini Live: {err}")
        self._changed.notify_all()

    def _run(self) -> None:
        try:
            for attempt in range(1, CONNECT_ATTEMPTS + 1):
                try:
                    self._ws = self._connect(self._api_key)
                    break
                except Exception as e:
                    err = _handshake_error(e)
                    if err.kind != "network" or attempt == CONNECT_ATTEMPTS or self._closing:
                        with self._lock:
                            self._fail_locked(err)
                        return
                    logger.info(f"Gemini Live: connect attempt {attempt} failed ({e}), retrying")
            if self._closing:
                self.close()
                return
            with self._lock:
                try:
                    self._send_locked({"setup": self._setup})
                except Exception as e:
                    self._fail_locked(GeminiApiError(f"Gemini Live send failed: {e}",
                                                     kind="network"))
                    return
            self._ws.settimeout(None)
            while True:
                try:
                    opcode, data = self._ws.recv_data(control_frame=True)
                except Exception as e:
                    with self._lock:
                        if not self._closing:
                            self._fail_locked(GeminiApiError(
                                f"Gemini Live connection lost: {e}", kind="network"))
                    return
                if opcode == websocket.ABNF.OPCODE_CLOSE:
                    self._handle_close(data)
                    return
                if opcode in (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY):
                    self._handle(data)
        finally:
            with self._lock:
                self._closed.set()
                self._changed.notify_all()
            self._started.set()

    def _handle_close(self, data: bytes) -> None:
        code = int.from_bytes(data[:2], "big") if len(data) >= 2 else None
        reason = data[2:].decode("utf-8", errors="replace") if len(data) > 2 else ""
        with self._lock:
            # A normal close after the turn completed (or one we asked for)
            # is just the end of the session.
            if self._closing or self._complete or code in (None, 1000):
                return
            self._fail_locked(close_error(code, reason))

    def _handle(self, raw) -> None:
        try:
            msg = json.loads(raw)
        except (TypeError, ValueError):
            logger.debug(f"Gemini Live: non-JSON frame ignored: {str(raw)[:120]}")
            return
        with self._lock:
            if "setupComplete" in msg:
                logger.info("Gemini Live: session started")
                self._started.set()
                try:
                    self._send_locked({"realtimeInput": {"activityStart": {}}})
                except Exception as e:
                    self._fail_locked(GeminiApiError(f"Gemini Live send failed: {e}",
                                                     kind="network"))
                    return
                self._flush_locked(final=False)
                return
            content = msg.get("serverContent") or {}
            interim = (content.get("interimInputTranscription") or {}).get("text")
            if interim is not None:
                self._interim = interim
            final = (content.get("inputTranscription") or {}).get("text")
            if final:
                self._finals.append(final)
                self._interim = ""
            if self._ended and (content.get("generationComplete") or content.get("turnComplete")):
                self._complete = True
            if self._ended and (msg.get("voiceActivity") or {}).get("type") == "ACTIVITY_END":
                self._server_ended = True
            self._changed.notify_all()

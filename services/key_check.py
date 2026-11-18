# file: services/key_check.py

"""On-demand "is this key alive, and is there balance?" probe.

Backs the "Check" button beside each API-key field on the Transcription
settings page. One blocking call per provider, meant to run on a worker thread.

Why a real request instead of a cheap "list models" ping: OpenAI, Groq and
Gemini expose no balance endpoint for an API key, and a metadata call succeeds
on an account with zero credits. The only thing that answers "will dictation
work?" is the call dictation itself makes — so the probe transcribes one second
of silence with the model the user picked. That costs a small fraction of a
cent, and its failure is classified by the very same classify_api_error() the
dictation pipeline uses, so the button and the indicator can never disagree.

ElevenLabs is the exception: its transcription here is a realtime websocket
session (too heavy for a probe), but it does have a subscription endpoint that
reports used/allowed credits, so that is read instead.

Never touches config or the keyring — the caller hands in the key (which may
be one typed into the field and not saved yet).
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
import urllib.error
import urllib.request
import wave

from services import gemini_transcribe
from services.api_errors import classify_api_error
from services.transcription_models import GROQ_BASE_URL

logger = logging.getLogger(__name__)

PROVIDERS = ("openai", "groq", "gemini", "elevenlabs")

# Tighter than the dictation timeout: a person is watching a button.
CHECK_TIMEOUT = 15.0

ELEVENLABS_SUBSCRIPTION_URL = "https://api.elevenlabs.io/v1/user/subscription"

# Results. The first two mean "the key works"; the rest are
# classify_api_error() kinds, passed through unchanged.
OK = "ok"                      # key accepted and the account can pay for a request
OK_NO_BALANCE = "ok_nobalance" # key accepted, but it may not read the balance
RESULTS = (OK, OK_NO_BALANCE, "quota", "auth", "rate", "network", "busy", "unknown")


def silent_wav(seconds: float = 1.0, rate: int = 16000) -> bytes:
    """A mono int16 WAV of silence — the smallest request every provider accepts."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


def check_key(provider: str, api_key: str, model: str | None = None) -> str:
    """Probe one key; returns one of RESULTS. Never raises.

    ``model`` is the transcription model to probe with (ignored for
    ElevenLabs). A model the key has no access to surfaces as the provider's
    own error, which is the truth the user needs anyway.
    """
    try:
        if provider == "elevenlabs":
            return _check_elevenlabs(api_key)
        if provider == "gemini":
            _probe_gemini(api_key, model or "")
        elif provider in ("openai", "groq"):
            _probe_openai_compatible(provider, api_key, model or "")
        else:
            logger.error(f"Key check: unknown provider {provider!r}")
            return "unknown"
        return OK
    except Exception as e:
        kind = classify_api_error(e)
        # The key itself is never logged; provider error bodies do not echo it
        # in full (OpenAI masks it to the last four characters).
        logger.warning(
            f"Key check for {provider}: {kind} ({type(e).__name__}: {str(e)[:300]})"
        )
        return kind


def _probe_openai_compatible(provider: str, api_key: str, model: str) -> None:
    """OpenAI / Groq: transcribe a second of silence. Raises the SDK's error."""
    import openai  # lazy, like the rest of the settings path: keeps page import cheap

    client = openai.OpenAI(
        api_key=api_key,
        base_url=GROQ_BASE_URL if provider == "groq" else None,
        timeout=CHECK_TIMEOUT,
        # No retries: a retry would turn a rate-limit answer into a long wait
        # and tell the user nothing more.
        max_retries=0,
    )
    client.audio.transcriptions.create(
        model=model, file=("key_check.wav", silent_wav(), "audio/wav")
    )


def _probe_gemini(api_key: str, model: str) -> None:
    """Gemini: same probe through the app's own client (it takes a file path)."""
    fd, path = tempfile.mkstemp(prefix="omniverte_key_check_", suffix=".wav")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(silent_wav())
        gemini_transcribe.transcribe_file(api_key, path, model, timeout=CHECK_TIMEOUT)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _check_elevenlabs(api_key: str) -> str:
    """ElevenLabs: read the subscription (used vs allowed credits)."""
    request = urllib.request.Request(
        ELEVENLABS_SUBSCRIPTION_URL,
        headers={"xi-api-key": api_key, "User-Agent": "OmniVerte (Windows)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=CHECK_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:2000]
        except Exception:
            pass
        logger.warning(f"Key check for elevenlabs: HTTP {e.code}: {body[:300]}")
        return classify_elevenlabs_http(e.code, body)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logger.warning(f"Key check for elevenlabs: network error: {e}")
        return "network"

    try:
        data = json.loads(raw)
    except ValueError:
        return "unknown"
    return classify_elevenlabs_subscription(data)


def classify_elevenlabs_http(status: int, body: str) -> str:
    """Map a non-2xx subscription answer to a result (pure)."""
    if status == 401:
        # A restricted key is a perfectly good key that simply lacks the
        # "read user" scope: it authenticates, but the balance stays unknown.
        if "missing_permissions" in body:
            return OK_NO_BALANCE
        return "auth"
    if status == 403:
        return "auth"
    if status == 402:
        return "quota"
    if status == 429:
        return "rate"
    if status >= 500:
        return "busy"
    return "unknown"


def classify_elevenlabs_subscription(data: object) -> str:
    """Map a subscription body to "ok" / "quota" (pure).

    ``character_count`` is what the billing period has used so far and
    ``character_limit`` what the plan allows. A body without usable numbers
    still proves the key was accepted, so it degrades to "balance unknown"
    rather than to an error.
    """
    if not isinstance(data, dict):
        return "unknown"
    used, limit = data.get("character_count"), data.get("character_limit")
    if not isinstance(used, (int, float)) or not isinstance(limit, (int, float)):
        return OK_NO_BALANCE
    return "quota" if limit > 0 and used >= limit else OK

# file: services/gemini_transcribe.py

"""Minimal client for Google's Gemini Interactions API (gemini-3.5-transcribe).

Google's dedicated ASR models are NOT reachable through an OpenAI-compatible
endpoint, so the shared openai-SDK path used for OpenAI/Groq cannot serve them.
Rather than adopting the google-genai SDK for a single POST, this module talks
to the REST endpoint directly with stdlib urllib (same approach as
licensing/api_client.py) — no new dependency, nothing extra for PyInstaller to
trace.

Audio travels inline as base64 (the API caps a request at 20 MB total, which
comfortably fits our 16 kHz mono dictation WAVs — ~7 minutes per request; the
size guard below raises before the API would). The file-upload flow (Files API)
exists for bigger inputs but is deliberately not implemented: dictation
sessions are capped at 10 minutes and the streaming path sends ~20 s chunks.

The glossary's layer B maps onto the API's first-class ``custom_vocabulary``
field — a real biasing parameter, unlike the Whisper ``prompt`` hack that can
echo the term list into the transcript.
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

# The API caps a request at 20 MB total (JSON + inline files); base64 inflates
# audio by 4/3, so cap the raw WAV well below that. At 16 kHz mono int16 this
# is still ~7 minutes of audio — beyond any single streaming chunk and most
# final files. Oversize raises GeminiApiError, which the caller's cloud
# fallback chain treats like any other provider failure.
MAX_INLINE_AUDIO_BYTES = 14 * 1024 * 1024

# The API accepts up to 1000 vocabulary terms but documents best results at
# ≤100. The glossary's own Pro cap is 200; trim to the documented sweet spot,
# keeping the head — glossary term order is already priority order
# (own_names → counterparties → services).
MAX_VOCABULARY_TERMS = 100

# Whisper short-code hint (LANGUAGE_TO_WHISPER_CODE values) → BCP-47 tag for
# ``transcription_config.language_codes``. Unmapped/empty hint = omit the field
# and let the model auto-detect (a headline capability of this model).
WHISPER_HINT_TO_BCP47 = {
    "en": "en-US",
    "ru": "ru-RU",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "it": "it-IT",
    "zh": "zh-CN",
    "ja": "ja-JP",
}


class GeminiApiError(RuntimeError):
    """A Gemini API call failed.

    ``kind`` is "http" (carries ``status``/``body``), "network" (DNS/timeout/
    connection — the request may never have reached Google), or "response"
    (2xx arrived but the body was not the documented shape). Classification
    into user-facing kinds lives in services.api_errors.
    """

    def __init__(self, message: str, kind: str = "network",
                 status: int | None = None, body: str = ""):
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.body = body


def build_transcription_payload(model: str, audio_bytes: bytes,
                                language_hint: str | None = None,
                                vocabulary: list[str] | None = None) -> dict:
    """Assemble the Interactions API request body (pure — unit-testable).

    ``language_hint`` is the Whisper short code the rest of the app trades in;
    it is widened to BCP-47 here. ``mode`` is deliberately omitted: the default
    is verbatim transcription, which is what the downstream pipeline (glossary
    layer C, LLM correction) is built around — "smart" mode would rewrite the
    text before our own post-processing gets a say.
    """
    config: dict = {}
    code = WHISPER_HINT_TO_BCP47.get((language_hint or "").lower())
    if code:
        config["language_codes"] = [code]
    if vocabulary:
        config["custom_vocabulary"] = list(vocabulary)[:MAX_VOCABULARY_TERMS]
    payload: dict = {
        "model": model,
        "input": [{
            "type": "audio",
            "data": base64.b64encode(audio_bytes).decode("ascii"),
            "mime_type": "audio/wav",
        }],
    }
    if config:
        payload["generation_config"] = {"transcription_config": config}
    return payload


def extract_transcript(response: dict) -> str:
    """Pull the transcript text out of an Interactions API response.

    ``output_text`` is the documented happy path; the steps walk is a fallback
    for responses that only carry structured content. An empty transcript for
    silent audio is valid — only a body with no text-bearing shape at all
    raises.
    """
    text = response.get("output_text")
    if isinstance(text, str):
        return text
    parts: list[str] = []
    found_shape = False
    for step in response.get("steps") or []:
        for item in (step or {}).get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                found_shape = True
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
    if parts or found_shape:
        return "".join(parts)
    raise GeminiApiError(
        f"Unexpected Gemini response shape: {str(response)[:200]}",
        kind="response",
    )


def transcribe_file(api_key: str, audio_file_path: str, model: str,
                    language_hint: str | None = None,
                    vocabulary: list[str] | None = None,
                    timeout: float = 30.0) -> str:
    """Transcribe one audio file; returns the transcript text.

    Raises GeminiApiError on any failure (size, network, HTTP status, or an
    undecipherable body) — callers treat it like any other cloud-provider
    exception and fall back down the backend chain.
    """
    with open(audio_file_path, "rb") as f:
        audio_bytes = f.read()
    if len(audio_bytes) > MAX_INLINE_AUDIO_BYTES:
        raise GeminiApiError(
            f"Audio too large for inline Gemini request "
            f"({len(audio_bytes)} > {MAX_INLINE_AUDIO_BYTES} bytes)",
            kind="response",
        )

    payload = build_transcription_payload(
        model, audio_bytes, language_hint=language_hint, vocabulary=vocabulary
    )
    request = urllib.request.Request(
        INTERACTIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            # Explicit UA out of the same caution as licensing/api_client:
            # edge proxies are known to 403 bare Python-urllib.
            "User-Agent": "OmniVerte (Windows)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:2000]
        except Exception:
            pass
        raise GeminiApiError(
            f"Gemini API HTTP {e.code}: {body[:200]}",
            kind="http", status=e.code, body=body,
        ) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise GeminiApiError(f"Gemini API network error: {e}") from e

    try:
        response = json.loads(raw)
    except ValueError as e:
        raise GeminiApiError(
            f"Gemini API returned non-JSON body: {raw[:200]}",
            kind="response",
        ) from e
    return extract_transcript(response)

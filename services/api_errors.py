# file: services/api_errors.py

"""Classify cloud-API failures and render them as user-facing alert strings.

The pipeline swallows provider errors by design (a failed correction falls back
to the raw transcript; a failed segment is skipped) — but "quota exhausted" and
"key revoked" are conditions the *user* must act on, so they get surfaced via
``UIBridge.api_error`` and rendered here on the UI side, in the UI locale.

Every user-facing string produced by this module is wrapped in a loud
``!!! ⚠ … ⚠ !!!`` frame: these messages appear near the dictation flow, and the
frame is what keeps one from ever being mistaken for transcribed speech and
pasted into a chat or document unnoticed.
"""

from __future__ import annotations

try:
    import openai
except ImportError:  # pragma: no cover - openai is a hard runtime dep
    openai = None

from services.elevenlabs_realtime import ElevenLabsApiError
from services.gemini_transcribe import GeminiApiError


class CloudApiError(RuntimeError):
    """A cloud call failed; carries the provider label for the UI message.

    Raised by AudioWriter's transcription fallback loop instead of the raw
    provider exception, so the notification layer can say *which* provider is
    out of quota. ``original`` keeps the real exception for classification.
    """

    def __init__(self, provider: str, original: BaseException):
        super().__init__(str(original))
        self.provider = provider
        self.original = original


# error kind -> i18n catalog key. Keys are stored (not resolved) at module
# scope — t() runs only inside user_message(), per the i18n freeze rule.
_KIND_KEYS = {
    "quota":   "error.api.quota",
    "auth":    "error.api.auth",
    "rate":    "error.api.rate",
    "network": "error.api.network",
    "busy":    "error.api.busy",
    "unknown": "error.api.unknown",
}

_CONTEXT_KEYS = {
    "transcribe":  "error.transcribe.title",
    "postprocess": "error.postprocess.title",
}
# Quick dictation lost its live engine but the batch chain still delivered:
# not a context here — it has its own text (quick_fallback_text) because it
# names the provider that served instead.

# Body/error codes OpenAI (and Groq, same wire format) use for "no money left",
# as opposed to a transient per-minute rate limit — both arrive as HTTP 429.
_QUOTA_CODES = ("insufficient_quota", "billing_hard_limit_reached", "billing_not_active")


def classify_api_error(exc: BaseException) -> str:
    """Map an exception from a cloud call to a user-actionable kind.

    Returns one of ``"quota" | "auth" | "rate" | "network" | "busy" | "unknown"``
    ("busy" = the provider answered 5xx: overloaded or down on its side).
    Never raises — an unrecognized exception is simply "unknown".
    """
    if isinstance(exc, CloudApiError):
        exc = exc.original

    # Gemini goes through our own urllib client, not the openai SDK.
    if isinstance(exc, GeminiApiError):
        if exc.kind == "network":
            return "network"
        if exc.kind == "http":
            if exc.status in (401, 403):
                return "auth"
            if exc.status == 429:
                # Google reports both a burst rate limit and an exhausted
                # daily/billing quota as 429 RESOURCE_EXHAUSTED; "quota" in the
                # body text is what separates "wait a minute" from "go pay".
                return "quota" if "quota" in exc.body.lower() else "rate"
            if exc.status == 402:
                return "quota"
            # Google answers a wrong/deleted key with 400 INVALID_ARGUMENT,
            # not 401 — only the ErrorInfo reason tells it from a bad request.
            if exc.status == 400 and "API_KEY_INVALID" in exc.body:
                return "auth"
            # 5xx is the provider's trouble ("experiencing high demand"), not
            # the user's key or account — say so instead of "unexpected error".
            if exc.status is not None and exc.status >= 500:
                return "busy"
        return "unknown"

    # The quick-mode realtime client already classifies on the wire.
    if isinstance(exc, ElevenLabsApiError):
        return exc.kind if exc.kind in ("quota", "auth", "rate", "network") else "unknown"

    # The other two providers go through the openai SDK (Groq is OpenAI-compatible).
    if openai is not None:
        if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
            return "auth"
        if isinstance(exc, openai.RateLimitError):
            return "quota" if _mentions_quota(exc) else "rate"
        if isinstance(exc, (openai.APITimeoutError, openai.APIConnectionError)):
            return "network"
        if isinstance(exc, openai.APIStatusError):
            # 402 or a quota code on any other status is still a billing problem.
            if exc.status_code == 402 or _mentions_quota(exc):
                return "quota"
            if exc.status_code >= 500:
                return "busy"
            return "unknown"
    # The text-ops watchdog raises a bare TimeoutError on a hung request.
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return "network"
    return "unknown"


def _mentions_quota(exc: BaseException) -> bool:
    """True when the error body/code says the account is out of credits."""
    code = getattr(exc, "code", None) or ""
    if code in _QUOTA_CODES:
        return True
    text = str(exc)
    return any(marker in text for marker in _QUOTA_CODES)


def frame_alert(text: str) -> str:
    """Wrap a message in a loud symmetric frame.

    The frame — not the wording — is what signals "system alert, not your
    dictated text" at a glance, so it must survive any surface the message
    lands on (Windows toast, log, a hypothetical text field): plain ASCII
    exclamation marks plus the universally-rendered U+26A0 warning sign.
    """
    return f"!!! ⚠ {text} ⚠ !!!"


def user_message(context: str, kind: str, provider: str) -> str:
    """Localized, framed alert for one API failure.

    ``context`` — "transcribe" (no text was produced) or "postprocess" (raw
    text was pasted without correction); ``kind`` — a classify_api_error()
    result; ``provider`` — display label ("OpenAI", "Groq"). Unknown values
    degrade to the "unknown"/"transcribe" strings rather than raising: this
    runs inside signal handlers where an exception is a crash.
    """
    from i18n import t

    title = t(_CONTEXT_KEYS.get(context, _CONTEXT_KEYS["transcribe"]))
    reason = t(_KIND_KEYS.get(kind, _KIND_KEYS["unknown"]), provider=provider)
    return frame_alert(f"{title}: {reason}")


# ---- short forms for the floating indicator ----
#
# The pill (ui/rec_indicator.py) is the primary surface for these alerts: it is
# where the user is already looking while dictating, and being a click-through,
# focus-less overlay its text can never end up in the document. It is narrow,
# so it gets its own terse wording instead of the toast's full sentences. No
# frame here — the pill's yellow styling does that job; frame_alert() is added
# only by the toast fallbacks below.

_SHORT_KIND_KEYS = {
    "quota":   "indicator.alert.quota",
    "auth":    "indicator.alert.auth",
    "rate":    "indicator.alert.rate",
    "network": "indicator.alert.network",
    "busy":    "indicator.alert.busy",
    "unknown": "indicator.alert.unknown",
}


def short_reason(kind: str, provider: str) -> str:
    """Terse localized reason, e.g. "Gemini credits exhausted"."""
    from i18n import t

    return t(_SHORT_KIND_KEYS.get(kind, _SHORT_KIND_KEYS["unknown"]), provider=provider)


def notice_text(context: str, kind: str, provider: str) -> str:
    """Pill notice for one API failure: "<what happened>: <terse reason>"."""
    from i18n import t

    title = t(_CONTEXT_KEYS.get(context, _CONTEXT_KEYS["transcribe"]))
    return f"{title}: {short_reason(kind, provider)}"


def failover_text(failed: str, kind: str, fallback: str) -> str:
    """Pill notice for a failover: "<terse reason> — switched to <fallback>"."""
    from i18n import t

    return f"{short_reason(kind, failed)} — {t('indicator.failover', fallback=fallback)}"


def degraded_text(failed: str, fallback: str) -> str:
    """Pill banner while the primary stays down: "<failed> unavailable — using <fallback>"."""
    from i18n import t

    return t("indicator.degraded", provider=failed, fallback=fallback)


def quick_fallback_text(engine: str, kind: str, serving: str) -> str:
    """Pill notice for a failed live session whose audio the batch chain
    rescued: "Quick dictation transcribed via <serving>: <terse reason>"."""
    from i18n import t

    title = t("error.realtime_fallback.title", fallback=serving)
    return f"{title}: {short_reason(kind, engine)}"


def quick_fallback_message(engine: str, kind: str, serving: str) -> str:
    """Framed quick-fallback text for the tray toast (indicator switched off)."""
    return frame_alert(quick_fallback_text(engine, kind, serving))


def failover_message(failed: str, kind: str, fallback: str) -> str:
    """Framed failover text for the tray toast (indicator switched off)."""
    return frame_alert(failover_text(failed, kind, fallback))

# file: licensing/api_client.py

"""
Thin HTTP client for the license Worker (008 §5–7).

Pure transport: it turns a license key + fingerprint into a signed token and
back, and knows nothing about entitlements, keyring, or the UI — that lives in
``licensing.activation``. Built on the standard library (``urllib``) so the
client gains no new dependency.

Contract (all POST + JSON against ``LICENSE_API_URL``):
  /activate    {license_key, machine_fp, machine_label?} -> {token, token_expires_at}
  /refresh     {token, machine_fp}                        -> {token, token_expires_at}
  /deactivate  {license_key, machine_fp}                  -> (body ignored)

Failure model — every call raises **only** ``LicenseApiError`` (or returns):
  - kind="network": connection refused / DNS / timeout / malformed response.
    The caller keeps the cached token and retries later.
  - kind="http":    a non-2xx status. ``status`` and the parsed ``error`` string
    carry the server's verdict (invalid_key / license_revoked / seat_limit / …);
    ``body`` keeps the full parsed payload (e.g. seat_limit's active_machines).

Nothing else propagates: a dead or hostile server can never crash the app.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Optional

from .config import LICENSE_API_TIMEOUT, LICENSE_API_URL

logger = logging.getLogger(__name__)

# Sent on every call. Without it urllib announces itself as "Python-urllib/3.x",
# which Cloudflare's bot protection blocks outright (error 1010,
# browser_signature_banned) — the request never reaches the Worker, and the 403
# it returns has nothing to do with the license.
USER_AGENT = "OmniVerte-License-Client/1.0"

# Error strings the Worker itself sends when a license is genuinely dead (008 §7).
# Only these justify dropping a user to Free; any other 4xx is someone else's
# verdict (a WAF, a proxy, a captive portal) and must not revoke anything.
REVOKING_ERRORS = frozenset(
    {"license_revoked", "license_refunded", "license_expired", "invalid_key"}
)


def is_revoking(exc: "LicenseApiError") -> bool:
    """True only when the Worker explicitly said this license is dead."""
    return exc.kind == "http" and (exc.error or "") in REVOKING_ERRORS


class LicenseApiError(Exception):
    """Any failure of a license API call.

    kind   : "network" (unreachable/timeout/garbage) or "http" (non-2xx).
    status : HTTP status for kind="http", else None.
    error  : the server's machine-readable ``error`` field when present
             (e.g. "invalid_key", "license_revoked", "seat_limit"), else a short
             human string.
    body   : the full parsed JSON payload when there was one (else None).
    """

    def __init__(
        self,
        message: str,
        *,
        kind: str,
        status: Optional[int] = None,
        error: Optional[str] = None,
        body: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.error = error
        self.body = body


def _post(path: str, payload: dict[str, Any]) -> dict:
    """POST ``payload`` as JSON to ``LICENSE_API_URL + path``; return parsed JSON.

    Raises ``LicenseApiError`` and nothing else.
    """
    url = LICENSE_API_URL.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=LICENSE_API_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        # Non-2xx. The Worker returns a JSON body with an ``error`` field.
        parsed = _safe_json(e.read())
        err = parsed.get("error") if isinstance(parsed, dict) else None
        raise LicenseApiError(
            f"{path} -> HTTP {e.code} ({err or 'error'})",
            kind="http",
            status=e.code,
            error=err,
            body=parsed if isinstance(parsed, dict) else None,
        ) from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        # Connection refused, DNS failure, timeout, TLS error, bad URL, …
        raise LicenseApiError(
            f"{path} unreachable: {e}", kind="network"
        ) from e

    parsed = _safe_json(raw)
    if not isinstance(parsed, dict):
        raise LicenseApiError(
            f"{path}: malformed response", kind="network"
        )
    return parsed


def _safe_json(raw: bytes | None) -> Any:
    try:
        return json.loads((raw or b"").decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def activate(license_key: str, machine_fp: str, label: Optional[str] = None) -> dict:
    """POST /activate. Returns ``{token, token_expires_at}`` on success."""
    payload: dict[str, Any] = {"license_key": license_key, "machine_fp": machine_fp}
    if label:
        payload["machine_label"] = label
    return _post("/activate", payload)


def refresh(token: str, machine_fp: str) -> dict:
    """POST /refresh. Returns ``{token, token_expires_at}`` on success."""
    return _post("/refresh", {"token": token, "machine_fp": machine_fp})


def deactivate(license_key: str, machine_fp: str) -> dict:
    """POST /deactivate to free this machine's seat."""
    return _post("/deactivate", {"license_key": license_key, "machine_fp": machine_fp})

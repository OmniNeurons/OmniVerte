# file: licensing/activation.py

"""
Crash-safe orchestration between the license Worker and the local entitlement.

This is the only place the network (``api_client``) and the offline gate
(``verify``/``entitlement``/``context``) meet. Two rules hold everywhere:

  - **The app must never crash or hang because the server is down.** Every public
    function here is fully guarded; ``refresh_now`` returns a status enum instead
    of raising, and ``start_monitor`` runs off the UI thread.
  - **Fail closed, but gently.** A revoked/refunded license drops to Free on the
    next refresh; a merely *unreachable* server keeps the cached token until it
    expires on its own (~60d sliding TTL, 008 §6) — a flaky network must not
    demote a paying user.

Startup entitlement resolution (``entitlement.resolve_entitlement``) stays 100%
offline; this module only feeds fresh tokens into that cache.
"""

from __future__ import annotations

import logging
import threading
from enum import Enum
from typing import Optional

from . import api_client
from .api_client import LicenseApiError
from .config import LICENSE_API_URL, REFRESH_INTERVAL_HOURS
from .context import refresh_entitlement
from .entitlement import (
    clear_license_key,
    clear_token,
    get_license_key,
    get_token,
    store_license_key,
    store_token,
)
from .features import Entitlement
from .verify import LicenseError, verify_token

logger = logging.getLogger(__name__)


def _machine_fp() -> Optional[str]:
    try:
        from services.machine_id import machine_fp
        return machine_fp()
    except Exception:
        return None


def _api_configured() -> bool:
    """False while ``LICENSE_API_URL`` is still the build placeholder — so we
    don't fire pointless DNS lookups at REPLACE.workers.dev."""
    return "REPLACE" not in LICENSE_API_URL


class RefreshResult(str, Enum):
    RENEWED = "renewed"            # got a fresh token; entitlement re-resolved
    REVOKED = "revoked"           # license no longer valid → dropped to Free
    OFFLINE = "offline"          # server unreachable → kept cached token
    SEAT_LIMIT = "seat_limit"    # token not reissued (machine over limit) → kept
    NOT_ACTIVATED = "not_activated"  # nothing to refresh
    ERROR = "error"               # other server/transport issue → kept token


def activate_with_key(license_key: str, label: Optional[str] = None) -> Entitlement:
    """Exchange a license key for a signed token and apply it.

    Returns the new Entitlement on success. Raises:
      - ``LicenseApiError`` on any network/HTTP failure (the UI maps ``.kind`` /
        ``.error`` / ``.status`` to a message — invalid_key, seat_limit, …);
      - ``LicenseError`` if the server returned a token we can't verify (should
        never happen with a healthy Worker — treated as a hard failure, not Pro).
    """
    license_key = license_key.strip()
    if not license_key:
        raise LicenseApiError("empty license key", kind="local", error="empty_key")

    fp = _machine_fp()
    if not fp:
        raise LicenseApiError(
            "could not read this machine's fingerprint",
            kind="local",
            error="no_fingerprint",
        )

    resp = api_client.activate(license_key, fp, label)  # raises LicenseApiError
    token = (resp or {}).get("token")
    if not token:
        raise LicenseApiError("server returned no token", kind="network")

    # Reject anything we can't verify offline so we never cache garbage and only
    # ever report Pro on a token the gate will actually honor.
    verify_token(token, machine_id=fp)  # raises LicenseError on mismatch

    store_token(token)
    store_license_key(license_key)
    return refresh_entitlement()


def refresh_now() -> RefreshResult:
    """Re-validate the cached token against the Worker. Never raises."""
    try:
        token = get_token()
        if not token:
            return RefreshResult.NOT_ACTIVATED
        if not _api_configured():
            return RefreshResult.OFFLINE

        fp = _machine_fp() or ""
        try:
            resp = api_client.refresh(token, fp)
        except LicenseApiError as e:
            if e.kind == "network":
                logger.info("license refresh offline (%s) — keeping token", e)
                return RefreshResult.OFFLINE
            if api_client.is_revoking(e):
                # The Worker itself said the license is dead (license_revoked /
                # _refunded / _expired / invalid_key). This is the teeth: stop
                # being Pro. Note we demand the explicit error string — a bare
                # 4xx can come from a WAF or proxy between us and the Worker
                # (Cloudflare's error 1010, a captive portal, …) and must never
                # demote a paying user over someone else's verdict.
                logger.warning("license refresh rejected (%s) — dropping to Free", e.error)
                clear_token()
                clear_license_key()
                refresh_entitlement()
                return RefreshResult.REVOKED
            if e.status == 409:
                # seat_limit: token not reissued, but the license is still valid.
                # Keep the current token; it lapses on its own if never renewed.
                logger.warning("license refresh hit seat limit — keeping current token")
                return RefreshResult.SEAT_LIMIT
            logger.warning("license refresh error (%s) — keeping token", e)
            return RefreshResult.ERROR

        new_token = (resp or {}).get("token")
        if not new_token:
            return RefreshResult.ERROR

        try:
            verify_token(new_token, machine_id=_machine_fp())
        except LicenseError as e:
            logger.warning("refreshed token failed verification (%s) — keeping old", e)
            return RefreshResult.ERROR

        store_token(new_token)
        refresh_entitlement()
        return RefreshResult.RENEWED
    except Exception:  # last-resort guard — a monitor thread must never die
        logger.exception("unexpected error during license refresh")
        return RefreshResult.ERROR


def deactivate_local() -> None:
    """Best-effort: free this machine's seat on the server, then clear locally.

    Network failure is swallowed — the local state is always cleared so the user
    is never stuck "activated" with no way back to Free.
    """
    key = get_license_key()
    fp = _machine_fp()
    if key and fp and _api_configured():
        try:
            api_client.deactivate(key, fp)
        except Exception as e:
            logger.info("deactivate call failed (%s) — clearing locally anyway", e)
    clear_token()
    clear_license_key()
    refresh_entitlement()


# --- background monitor -------------------------------------------------------

_monitor_started = False
_stop = threading.Event()


def start_monitor(ui_bridge=None) -> None:
    """Spawn a daemon thread that re-validates the token at startup and then
    every ``REFRESH_INTERVAL_HOURS``. Idempotent and non-blocking; safe to call
    even with no token (it just no-ops and exits). A change in entitlement emits
    ``ui_bridge.entitlement_changed`` so live gates update without a restart."""
    global _monitor_started
    if _monitor_started:
        return
    if not _api_configured():
        logger.info("license API not configured — monitor disabled")
        return
    if not get_token():
        logger.info("no license token — monitor not started")
        return

    _monitor_started = True

    def _emit_changed() -> None:
        if ui_bridge is None:
            return
        try:
            ui_bridge.entitlement_changed.emit()
        except Exception:
            pass

    def _loop() -> None:
        interval = max(1.0, REFRESH_INTERVAL_HOURS) * 3600.0
        while not _stop.is_set():
            result = refresh_now()
            if result in (RefreshResult.REVOKED, RefreshResult.RENEWED):
                _emit_changed()
            if result == RefreshResult.NOT_ACTIVATED:
                break  # token cleared elsewhere; nothing left to watch
            if _stop.wait(interval):
                break

    threading.Thread(target=_loop, name="license-monitor", daemon=True).start()


def stop_monitor() -> None:
    """Signal the monitor thread to exit (used in tests / clean shutdown)."""
    _stop.set()

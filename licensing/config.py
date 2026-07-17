# file: licensing/config.py

"""
Build-time licensing constants, collected in one place.

These are *build* switches, not user settings — they never round-trip through
``config.env`` and are not editable from the UI. The single most important one
is ``PRO_SALES_OPEN``:

  - ``False`` — *waitlist mode*. Pro is visible everywhere but cannot be
    bought from inside the app; locked features and the License page route to the
    public waitlist landing page instead. Paddle only approves a live public
    product, so the payment backend comes *after* launch (roadmap Phase 3).
  - ``True`` (now) — the License page shows the real key-activation UI: paste a
    key, the app exchanges it for a signed token against ``LICENSE_API_URL``
    (Worker ``/activate`` → verify → ``store_token``). Checkout still isn't in
    the app, so "Get a license" keeps pointing at ``WAITLIST_URL`` until a store
    exists.

Testers/beta users do NOT need a key: ``OMNIVERTE_DEV_TIER=pro`` (see
``licensing/entitlement.py``) unlocks Pro locally. No in-app bypass is shipped.
"""

from __future__ import annotations

# Master mode switch. While False, the app is in waitlist mode (see module
# docstring). Flipped to True in Phase 3: the Worker is deployed and the License
# page shows the real key-activation UI.
PRO_SALES_OPEN = True

# Public landing page + waitlist anchor. Lead capture happens ONLY on the
# landing page (Phase 1C) — the app merely opens the browser here. Placeholder
# until the domain/anchor are finalised.
WAITLIST_URL = "https://omniverte.ai/#waitlist"

# Self-roll license backend (Cloudflare Worker). Set this to the deployed Worker
# origin before flipping ``PRO_SALES_OPEN``. ``licensing.api_client`` POSTs
# ``/activate``, ``/refresh`` and ``/deactivate`` against it. While it points at
# the placeholder host every call fails fast as a network error — the app stays
# offline-safe (cached token or FREE), it never crashes.
LICENSE_API_URL = "https://omniverte-license-api.omnineurons.workers.dev"

# Network timeout (seconds) for every license API call. Kept short: a slow or
# dead server must never stall the UI thread or the startup monitor.
LICENSE_API_TIMEOUT = 10.0

# How often the background monitor re-validates the token against the Worker
# (``/refresh``). The token TTL is ~60 days (008 §6), so a daily check renews it
# with enormous margin and surfaces a revoke/refund within a day.
REFRESH_INTERVAL_HOURS = 24.0

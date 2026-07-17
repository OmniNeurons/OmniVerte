# file: licensing/__init__.py

"""
Public surface of the licensing package.

Typical use:

    from licensing import resolve_entitlement, Feature

    ent = resolve_entitlement()          # once at startup
    if ent.has(Feature.GLOSSARY):
        ...
    if not ent.allows_count("style_presets", len(saved)):
        ...                              # nudge to Pro
"""

from .features import (
    UNLIMITED,
    Entitlement,
    Feature,
    Tier,
    FREE,
    TIER_FEATURES,
    TIER_LIMITS,
)
from .entitlement import (
    resolve_entitlement,
    store_token,
    clear_token,
    store_license_key,
    get_license_key,
    clear_license_key,
    get_token,
)
from .context import get_entitlement, refresh_entitlement
from .verify import verify_token, LicenseError
from .config import PRO_SALES_OPEN, WAITLIST_URL, LICENSE_API_URL
from .api_client import LicenseApiError
from .activation import (
    activate_with_key,
    refresh_now,
    deactivate_local,
    start_monitor,
    RefreshResult,
)

__all__ = [
    "PRO_SALES_OPEN",
    "WAITLIST_URL",
    "LICENSE_API_URL",
    "UNLIMITED",
    "Entitlement",
    "Feature",
    "Tier",
    "FREE",
    "TIER_FEATURES",
    "TIER_LIMITS",
    "resolve_entitlement",
    "get_entitlement",
    "refresh_entitlement",
    "store_token",
    "clear_token",
    "store_license_key",
    "get_license_key",
    "clear_license_key",
    "get_token",
    "verify_token",
    "LicenseError",
    "LicenseApiError",
    "activate_with_key",
    "refresh_now",
    "deactivate_local",
    "start_monitor",
    "RefreshResult",
]

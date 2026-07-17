# file: licensing/entitlement.py

"""
Single entry point for "what is this install allowed to do".

Resolution order (no network at read time):
    1. dev override env var      — local development only, never in a build
    2. cached signed token       — offline-verified (verify.py)
    3. FREE default              — fresh install / no/invalid token

The token (and the license key that minted it) is cached in the Windows
Credential Manager (DPAPI-protected) via keyring — the same vault the API keys
already use, so no new secret-storage plumbing. Online re-validation against the
license Worker is a SEPARATE periodic job (``licensing.activation``): it only
refreshes the cached token; the app always reads the cache here, network-free.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import keyring
import keyring.errors

from .features import FREE, Entitlement, Tier
from .verify import LicenseError, verify_token

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "OmniVerte"      # matches services.config_store.KEYRING_SERVICE
TOKEN_KEY = "LICENSE_TOKEN"
LICENSE_KEY_KEY = "LICENSE_KEY"    # the OVRT-… key that minted the token
DEV_TIER_ENV = "OMNIVERTE_DEV_TIER"  # e.g. OMNIVERTE_DEV_TIER=pro — dev machines only


def _machine_id() -> Optional[str]:
    """The salted device fingerprint embedded in the token's ``fp`` claim.
    Returns None if unavailable — in which case machine binding is simply not
    enforced."""
    try:
        from services.machine_id import machine_fp  # salted SHA-256 of MachineGuid
        return machine_fp()
    except Exception:
        return None


def store_token(token: str) -> None:
    """Persist a token after a successful activation. Caller should verify it
    first (verify_token) so we never cache garbage."""
    keyring.set_password(KEYRING_SERVICE, TOKEN_KEY, token)


def clear_token() -> None:
    """Deactivate locally (e.g. user signs out / moves machines)."""
    try:
        keyring.delete_password(KEYRING_SERVICE, TOKEN_KEY)
    except keyring.errors.PasswordDeleteError:
        pass


def store_license_key(key: str) -> None:
    """Persist the license key alongside the token — needed to refresh and to
    free the seat on deactivate."""
    keyring.set_password(KEYRING_SERVICE, LICENSE_KEY_KEY, key)


def get_license_key() -> Optional[str]:
    """The cached license key, or None if never activated."""
    return keyring.get_password(KEYRING_SERVICE, LICENSE_KEY_KEY)


def clear_license_key() -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, LICENSE_KEY_KEY)
    except keyring.errors.PasswordDeleteError:
        pass


def get_token() -> Optional[str]:
    """The cached signed token, or None."""
    return keyring.get_password(KEYRING_SERVICE, TOKEN_KEY)


def resolve_entitlement() -> Entitlement:
    """Resolve the active entitlement. Call once at startup; re-call after an
    activation/deactivation to refresh."""
    dev = os.environ.get(DEV_TIER_ENV)
    if dev:
        try:
            ent = Entitlement(Tier(dev.lower()))
            logger.warning("DEV entitlement override active: %s", ent)
            return ent
        except ValueError:
            logger.warning("ignoring invalid %s=%r", DEV_TIER_ENV, dev)

    token = keyring.get_password(KEYRING_SERVICE, TOKEN_KEY)
    if token:
        try:
            return verify_token(token, machine_id=_machine_id())
        except LicenseError as e:
            logger.warning("cached license rejected (%s) — falling back to FREE", e)

    return FREE

# file: services/machine_id.py

"""
Stable per-machine fingerprint for soft license binding.

Reads ``MachineGuid`` from
``HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography`` — a GUID Windows
generates at install time and keeps stable across reboots and app updates.

What leaves the machine is never the raw GUID: ``machine_fp()`` returns a
**salted SHA-256** of it (008 §2 "соль+хэш"). The license server only ever sees
this opaque hash — it counts activation seats by it — and the minting backend
stamps the same hash into the token (claim ``fp``), which the client compares
offline in ``licensing.verify.verify_token``. The salt is a fixed in-repo
constant: it isn't a secret (this is source-available), it only makes the value
domain-specific and reproducible.

Windows-only by design: on any other OS, or on any read error, both helpers
return ``None`` and machine binding is simply not enforced — never a crash.
"""

from __future__ import annotations

import hashlib
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Fixed, non-secret salt that scopes the fingerprint to this product. Bumping
# the suffix (``-v2``…) would re-key every fingerprint, so don't, casually — it
# would orphan existing activations.
FP_SALT = "omniverte-fp-v1"


def machine_guid() -> Optional[str]:
    """Return the registry MachineGuid, or ``None`` off-Windows / on any error."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        # KEY_WOW64_64KEY: a 32-bit Python build must read the native 64-bit
        # registry view, otherwise it lands in the WOW6432Node redirect where
        # MachineGuid does not live.
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
    except OSError as e:
        logger.warning("could not read MachineGuid: %s", e)
        return None

    value = (value or "").strip()
    return value or None


def machine_fp() -> Optional[str]:
    """Return the salted SHA-256 fingerprint sent to the license server and
    embedded in the token's ``fp`` claim, or ``None`` when the raw GUID is
    unavailable (off-Windows / read error) — in which case seat binding is
    simply not enforced."""
    guid = machine_guid()
    if not guid:
        return None
    return hashlib.sha256(f"{FP_SALT}:{guid}".encode("utf-8")).hexdigest()

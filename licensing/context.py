# file: licensing/context.py

"""
Process-wide cached access to the resolved entitlement.

`resolve_entitlement()` reads the registry / Credential Manager and verifies a
token — cheap, but not free, and the answer is stable for the life of the
process unless a license is activated/cleared. So we resolve once, cache it, and
hand the same `Entitlement` to every gate. `refresh_entitlement()` re-resolves
after an activation/deactivation or a settings reload.
"""

from __future__ import annotations

from .features import Entitlement
from .entitlement import resolve_entitlement

_cached: Entitlement | None = None


def get_entitlement() -> Entitlement:
    """Lazy, cached per process. Use everywhere a gate is checked."""
    global _cached
    if _cached is None:
        _cached = resolve_entitlement()
    return _cached


def refresh_entitlement() -> Entitlement:
    """Re-resolve after activation/deactivation or a settings reload."""
    global _cached
    _cached = resolve_entitlement()
    return _cached

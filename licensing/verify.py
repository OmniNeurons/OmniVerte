# file: licensing/verify.py

"""
Offline verification of a signed license token.

The license Worker (``/activate`` → ``/refresh``, see
``.claude/plans/008_SPEC_tz2_worker_api.md``) signs a short JWT with an Ed25519
PRIVATE key. The app verifies it with the PUBLIC key embedded below — no network,
works air-gapped, and the user's data stays put.

  Token claims (minted server-side, 008 §8):
    iss       : "omniverte-license"                   (rejects foreign issuers)
    aud       : "omniverte"                            (rejects foreign products)
    sub       : license key                            (informational here)
    tier      : "free" | "pro" | "enterprise"          (required)
    fp        : optional soft device binding (salted MachineGuid hash, 008 §2)
    exp       : token expiry (~60d sliding, 008 §6) — present on every token
    features  : optional explicit capability list      (Enterprise/custom bundles)
    limits    : optional explicit numeric caps         (Enterprise/custom bundles)

The ``fp`` claim holds the salted hash from ``services.machine_id.machine_fp``
(NOT the raw GUID) — the same value the client sends to ``/activate``.

Requires: PyJWT + cryptography  (algorithms=["EdDSA"]).
"""

from __future__ import annotations

import logging
from typing import Optional

import jwt  # PyJWT

from .features import Entitlement, Feature, Tier

logger = logging.getLogger(__name__)

# Ed25519 PUBLIC key — safe to ship in the open repo. The matching PRIVATE key
# lives ONLY on the minting backend and never touches the client or git.
# Replace with your real key before release.
LICENSE_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAhr5mg2DADeutHDFkVHsV8mCu2xMt2DotfoAVyLwfEnI=
-----END PUBLIC KEY-----"""

# Stamped into every token by the backend; rejects tokens minted for a
# different product/issuer (008 §8). Must stay in lock-step with the Worker.
LICENSE_AUDIENCE = "omniverte"
LICENSE_ISSUER = "omniverte-license"

_VALID_FEATURE_VALUES = {f.value for f in Feature}


class LicenseError(Exception):
    """Raised on any verification failure (bad signature, expiry, audience,
    machine mismatch, unknown tier). Callers fall back to FREE."""


def verify_token(token: str, *, machine_id: Optional[str] = None) -> Entitlement:
    """Verify a signed token offline and resolve it to an Entitlement.

    Raises LicenseError on any problem. PyJWT validates `exp` automatically, so
    an expired token (every token carries one, 008 §6) fails closed to FREE
    upstream once the sliding window lapses without a refresh.

    `machine_id` is the salted fingerprint from ``machine_id.machine_fp``.
    """
    try:
        claims = jwt.decode(
            token,
            LICENSE_PUBLIC_KEY,
            algorithms=["EdDSA"],
            audience=LICENSE_AUDIENCE,
            issuer=LICENSE_ISSUER,
            options={"require": ["tier"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise LicenseError("license expired") from e
    except jwt.InvalidTokenError as e:
        raise LicenseError(f"invalid license: {e}") from e

    # Soft device binding: only enforced when the token is bound AND the caller
    # supplied a fingerprint to compare. Re-activation on a new machine is a
    # backend concern (deactivate/reactivate), not a client lock.
    bound = claims.get("fp")
    if bound and machine_id and bound != machine_id:
        raise LicenseError("license bound to a different machine")

    try:
        tier = Tier(claims["tier"])
    except ValueError as e:
        # Token is newer than this build (unknown tier). Fail safe to FREE
        # upstream and tell the user to update — never crash.
        logger.warning("unknown tier %r in token", claims.get("tier"))
        raise LicenseError("unknown tier; update the app") from e

    # Variant-C hook: a verified token MAY override the static tier->bundle map.
    # Unknown feature strings are dropped (forward-compat) rather than fatal.
    # Canonical wire form is a JSON list of strings; we also tolerate an object
    # (feature -> truthy) for forward-compat with the 008 §8 sketch.
    raw_features = claims.get("features")
    if isinstance(raw_features, dict):
        raw_features = [k for k, v in raw_features.items() if v]
    features = None
    if isinstance(raw_features, list):
        features = {
            Feature(f) for f in raw_features if f in _VALID_FEATURE_VALUES
        }

    limits = claims.get("limits") if isinstance(claims.get("limits"), dict) else None

    return Entitlement(tier, features=features, limits=limits)

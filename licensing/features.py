# file: licensing/features.py

"""
The universal gating mechanism (variant B).

Code everywhere asks `entitlement.has(Feature.X)` / `entitlement.limit("y")`,
never `tier == PRO`. The tier -> capabilities mapping lives here, in one place,
so moving the Free/Pro boundary is a one-file edit and never a refactor.

This file is fully open in the public repo. The only secret in the whole scheme
is the private signing key on the backend (see verify.py for the public half).
"""

from __future__ import annotations

from enum import Enum

UNLIMITED = -1  # sentinel for numeric limits


class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"  # reserved — built on request; currently == PRO


class Feature(str, Enum):
    """Boolean capabilities. Free carries none of these; they switch on with a
    valid Pro token. Add a new Pro capability = one entry here + one membership
    in _PRO_FEATURES below."""
    GLOSSARY = "glossary"                          # profession term packs + the larger term cap
    CUSTOM_STYLE_EDITING = "custom_style_editing"  # author/edit free-text rewrite styles (Free gets templates only)
    UNLIMITED_STYLE_PRESETS = "unlimited_style_presets"
    PERSISTENT_HISTORY = "persistent_history"      # unlimited history + search
    SIGNED_UPDATES = "signed_updates"
    PRIORITY_SUPPORT = "priority_support"


_PRO_FEATURES: set[Feature] = {
    Feature.GLOSSARY,
    Feature.CUSTOM_STYLE_EDITING,
    Feature.UNLIMITED_STYLE_PRESETS,
    Feature.PERSISTENT_HISTORY,
    Feature.SIGNED_UPDATES,
    Feature.PRIORITY_SUPPORT,
}

# Tier -> boolean capabilities.
TIER_FEATURES: dict[Tier, set[Feature]] = {
    Tier.FREE: set(),
    Tier.PRO: set(_PRO_FEATURES),
    Tier.ENTERPRISE: set(_PRO_FEATURES),  # superset hook for later enterprise-only flags
}

# Tier -> numeric caps. -1 (UNLIMITED) means no cap; 0 means none.
# Free caps are deliberately a "taste": enough to feel the feature, not enough
# to live in it.
TIER_LIMITS: dict[Tier, dict[str, int]] = {
    Tier.FREE: {
        "style_presets": 1,       # one custom slot, templates only (editing is Pro)
        "history_entries": 10,    # last 10, no search
        "glossary_terms": 5,      # demo only; no profession packs
    },
    Tier.PRO: {
        "style_presets": UNLIMITED,
        "history_entries": UNLIMITED,
        # Hard practical ceiling: past ~200 terms the ASR prompt / LLM block /
        # fuzzy index degrade faster than they help, so Pro is capped too (not
        # a paywall — a quality guard). The editor never blocks input; only the
        # active set fed to the layers is capped.
        "glossary_terms": 200,
    },
    Tier.ENTERPRISE: {
        "style_presets": UNLIMITED,
        "history_entries": UNLIMITED,
        "glossary_terms": 200,    # same quality ceiling as Pro
    },
}


class Entitlement:
    """What the running app is allowed to do. Built once at startup from the
    resolved license (see entitlement.resolve_entitlement) and consulted
    everywhere through has() / limit() / allows_count()."""

    def __init__(
        self,
        tier: Tier,
        *,
        features: set[Feature] | None = None,
        limits: dict[str, int] | None = None,
    ):
        self.tier = tier
        # `features`/`limits` overrides let a verified Enterprise token carry a
        # bespoke bundle without shipping a new build (variant-C hook). For
        # Free/Pro they stay None and we use the static maps above.
        self.features = features if features is not None else set(TIER_FEATURES[tier])
        self.limits = limits if limits is not None else dict(TIER_LIMITS[tier])

    def has(self, feature: Feature) -> bool:
        return feature in self.features

    def limit(self, name: str) -> int:
        """Numeric cap for `name`. -1 == unlimited, 0 == none, missing == 0."""
        return self.limits.get(name, 0)

    def is_unlimited(self, name: str) -> bool:
        return self.limit(name) == UNLIMITED

    def allows_count(self, name: str, current: int) -> bool:
        """True if one more item may be added given the current count."""
        cap = self.limit(name)
        return cap == UNLIMITED or current < cap

    def __repr__(self) -> str:  # handy in logs
        return f"Entitlement(tier={self.tier.value}, features={len(self.features)})"


# Module-level default. No token, no network — what every fresh install runs as.
FREE = Entitlement(Tier.FREE)

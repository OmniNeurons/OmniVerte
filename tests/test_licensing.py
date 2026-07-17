"""Licensing: Free defaults, offline token verification, caps, and the glossary gate.

Test tokens are signed with a throwaway Ed25519 keypair generated here and the
public half is monkeypatched into ``licensing.verify`` — the real signing key is
never used (and never lives in the repo).
"""

from __future__ import annotations

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from licensing import (
    UNLIMITED,
    Entitlement,
    Feature,
    Tier,
    FREE,
    LicenseError,
    verify_token,
)
from licensing import verify as verify_mod
from licensing.verify import LICENSE_AUDIENCE, LICENSE_ISSUER


# ---------- signing helpers (throwaway keypair) ----------


def _keypair() -> tuple[str, str]:
    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return priv_pem, pub_pem


def _mint(priv_pem: str, **claims) -> str:
    payload = {"aud": LICENSE_AUDIENCE, "iss": LICENSE_ISSUER, "tier": "pro"}
    payload.update(claims)
    return jwt.encode(payload, priv_pem, algorithm="EdDSA")


@pytest.fixture
def signer(monkeypatch):
    """Yield a `mint(**claims)` bound to a fresh key whose public half is the
    one `verify_token` will trust for the duration of the test."""
    priv_pem, pub_pem = _keypair()
    monkeypatch.setattr(verify_mod, "LICENSE_PUBLIC_KEY", pub_pem)

    def mint(**claims) -> str:
        return _mint(priv_pem, **claims)

    return mint


# ---------- Tier.FREE defaults ----------


def test_free_has_no_features_and_default_caps():
    assert FREE.tier is Tier.FREE
    assert FREE.features == set()
    for f in Feature:
        assert not FREE.has(f)
    assert FREE.limit("history_entries") == 10
    assert FREE.limit("glossary_terms") == 5
    assert FREE.limit("style_presets") == 1


def test_unknown_limit_is_zero():
    assert FREE.limit("nope") == 0


def test_pro_glossary_cap_is_a_quality_ceiling_not_unlimited():
    # Pro/Enterprise are capped at 200 terms (past that the model degrades),
    # while history stays unlimited for paid tiers.
    assert Entitlement(Tier.PRO).limit("glossary_terms") == 200
    assert Entitlement(Tier.ENTERPRISE).limit("glossary_terms") == 200
    assert Entitlement(Tier.PRO).is_unlimited("history_entries")


def test_custom_style_editing_is_pro_only():
    assert not FREE.has(Feature.CUSTOM_STYLE_EDITING)
    assert Entitlement(Tier.PRO).has(Feature.CUSTOM_STYLE_EDITING)


# ---------- verify_token ----------


def test_valid_pro_token_resolves_to_pro(signer):
    ent = verify_token(signer(tier="pro"))
    assert ent.tier is Tier.PRO
    assert ent.has(Feature.GLOSSARY)
    assert ent.is_unlimited("history_entries")


def test_bad_signature_is_rejected(signer, monkeypatch):
    token = signer(tier="pro")
    # Swap the trusted key for an unrelated one → signature no longer verifies.
    _, other_pub = _keypair()
    monkeypatch.setattr(verify_mod, "LICENSE_PUBLIC_KEY", other_pub)
    with pytest.raises(LicenseError):
        verify_token(token)


def test_expired_token_is_rejected(signer):
    # exp far in the past — PyJWT raises ExpiredSignatureError.
    with pytest.raises(LicenseError):
        verify_token(signer(tier="pro", exp=1_000_000_000))


def test_wrong_audience_is_rejected(signer):
    with pytest.raises(LicenseError):
        verify_token(signer(tier="pro", aud="some-other-app"))


def test_wrong_issuer_is_rejected(signer):
    with pytest.raises(LicenseError):
        verify_token(signer(tier="pro", iss="some-other-issuer"))


def test_unknown_tier_is_rejected(signer):
    with pytest.raises(LicenseError):
        verify_token(signer(tier="superduper"))


def test_token_feature_and_limit_overrides(signer):
    token = signer(
        tier="enterprise",
        features=["glossary"],
        limits={"history_entries": 50, "glossary_terms": 25},
    )
    ent = verify_token(token)
    assert ent.tier is Tier.ENTERPRISE
    # Only the explicitly-listed feature is on, despite Enterprise's static map.
    assert ent.has(Feature.GLOSSARY)
    assert not ent.has(Feature.PERSISTENT_HISTORY)
    assert ent.limit("history_entries") == 50
    assert ent.limit("glossary_terms") == 25


def test_unknown_feature_strings_are_dropped_not_fatal(signer):
    ent = verify_token(signer(tier="pro", features=["glossary", "telepathy"]))
    assert ent.has(Feature.GLOSSARY)
    assert len(ent.features) == 1


def test_machine_binding_mismatch_is_rejected(signer):
    token = signer(tier="pro", fp="AAAA-1111")
    with pytest.raises(LicenseError):
        verify_token(token, machine_id="BBBB-2222")


def test_machine_binding_match_passes(signer):
    token = signer(tier="pro", fp="AAAA-1111")
    ent = verify_token(token, machine_id="AAAA-1111")
    assert ent.tier is Tier.PRO


def test_unbound_token_ignores_machine_id(signer):
    # No `fp` claim → binding not enforced even if a fingerprint is supplied.
    ent = verify_token(signer(tier="pro"), machine_id="whatever")
    assert ent.tier is Tier.PRO


def test_features_object_form_is_tolerated(signer):
    # 008 §8 sketches features as an object; verify accepts it for forward-compat.
    ent = verify_token(
        signer(tier="enterprise", features={"glossary": True, "priority_support": False})
    )
    assert ent.has(Feature.GLOSSARY)
    assert not ent.has(Feature.PRIORITY_SUPPORT)


# ---------- allows_count boundaries ----------


def test_allows_count_cap_of_one():
    ent = Entitlement(Tier.FREE)  # style_presets == 1
    assert ent.allows_count("style_presets", 0) is True
    assert ent.allows_count("style_presets", 1) is False
    assert ent.allows_count("style_presets", 2) is False


def test_allows_count_unlimited():
    ent = Entitlement(Tier.PRO)  # style_presets == UNLIMITED (-1)
    assert ent.is_unlimited("style_presets")
    assert ent.allows_count("style_presets", 0) is True
    assert ent.allows_count("style_presets", 9999) is True


def test_allows_count_missing_limit_is_zero():
    ent = Entitlement(Tier.FREE)
    assert ent.allows_count("nonexistent", 0) is False


# ---------- glossary gate ----------


def _make_glossary(tmp_path, n_terms):
    import json

    from services.glossary import Glossary

    path = tmp_path / "glossary.json"
    path.write_text(
        json.dumps({"own_names": [f"Term{i}" for i in range(n_terms)]}),
        encoding="utf-8",
    )
    return Glossary(path)


def test_glossary_free_cap_limits_active_terms(tmp_path):
    g = _make_glossary(tmp_path, 12)
    assert g.active_term_count() == 12

    g.set_active_cap(FREE.limit("glossary_terms"))  # 5
    assert len(g.all_terms()) == 5
    # asr_prompt / hotwords / llm_block all draw from the capped set.
    assert g.asr_prompt().count(",") == 4  # exactly 5 terms → 4 separators
    assert len(g.canonical_terms()) == 5


def test_glossary_pro_uses_all_terms(tmp_path):
    g = _make_glossary(tmp_path, 12)
    g.set_active_cap(None)  # Pro / no gate
    assert len(g.all_terms()) == 12


def test_glossary_cap_does_not_mutate_file(tmp_path):
    g = _make_glossary(tmp_path, 12)
    g.set_active_cap(5)
    reloaded_raw = (tmp_path / "glossary.json").read_text(encoding="utf-8")
    assert reloaded_raw.count("Term") == 12  # file untouched


def test_glossary_cap_survives_reload(tmp_path):
    g = _make_glossary(tmp_path, 12)
    g.set_active_cap(5)
    g.reload()
    assert len(g.all_terms()) == 5  # cap is preserved across reload

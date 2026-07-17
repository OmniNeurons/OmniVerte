"""Licensing network layer: machine fingerprint, the HTTP client, and the
crash-safe refresh orchestration.

No real network and no real registry: ``urllib`` and the keyring/verify helpers
are monkeypatched so these are pure unit tests of the transport + state machine.
"""

from __future__ import annotations

import io
import urllib.error

import pytest

from licensing import api_client
from licensing.api_client import LicenseApiError
from licensing import activation
from licensing.activation import RefreshResult
from licensing.features import Entitlement, Tier


# ---------- machine_fp ----------


def test_machine_fp_is_deterministic_salted_hash(monkeypatch):
    from services import machine_id

    monkeypatch.setattr(machine_id, "machine_guid", lambda: "GUID-123")
    a = machine_id.machine_fp()
    b = machine_id.machine_fp()
    assert a == b                 # stable
    assert len(a) == 64           # sha256 hex
    assert a != "GUID-123"        # never the raw GUID


def test_machine_fp_none_without_guid(monkeypatch):
    from services import machine_id

    monkeypatch.setattr(machine_id, "machine_guid", lambda: None)
    assert machine_id.machine_fp() is None


# ---------- api_client ----------


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def test_activate_parses_token(monkeypatch):
    monkeypatch.setattr(
        api_client.urllib.request,
        "urlopen",
        lambda req, timeout=None: _FakeResp(b'{"token":"T","token_expires_at":42}'),
    )
    out = api_client.activate("OVRT-1", "fp", "laptop")
    assert out["token"] == "T"
    assert out["token_expires_at"] == 42


def test_http_error_maps_to_http_kind_with_body(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 409, "Conflict", {},
            io.BytesIO(b'{"error":"seat_limit","active_machines":[1,2]}'),
        )

    monkeypatch.setattr(api_client.urllib.request, "urlopen", boom)
    with pytest.raises(LicenseApiError) as ei:
        api_client.activate("k", "fp")
    e = ei.value
    assert e.kind == "http"
    assert e.status == 409
    assert e.error == "seat_limit"
    assert e.body["active_machines"] == [1, 2]


def test_network_error_maps_to_network_kind(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(api_client.urllib.request, "urlopen", boom)
    with pytest.raises(LicenseApiError) as ei:
        api_client.refresh("tok", "fp")
    assert ei.value.kind == "network"


def test_malformed_response_is_network_kind(monkeypatch):
    monkeypatch.setattr(
        api_client.urllib.request,
        "urlopen",
        lambda req, timeout=None: _FakeResp(b"not json"),
    )
    with pytest.raises(LicenseApiError) as ei:
        api_client.refresh("tok", "fp")
    assert ei.value.kind == "network"


# ---------- refresh_now state machine ----------


@pytest.fixture
def wired(monkeypatch):
    """Make refresh_now think it is configured and activated, with stubbable
    storage + verify. Returns a dict tracking which storage calls fired."""
    calls = {"stored": [], "cleared": False}

    monkeypatch.setattr(activation, "_api_configured", lambda: True)
    monkeypatch.setattr(activation, "_machine_fp", lambda: "fp")
    monkeypatch.setattr(activation, "get_token", lambda: "oldtoken")
    monkeypatch.setattr(activation, "store_token", lambda t: calls["stored"].append(t))
    monkeypatch.setattr(activation, "refresh_entitlement", lambda: Entitlement(Tier.PRO))
    monkeypatch.setattr(activation, "verify_token", lambda t, machine_id=None: Entitlement(Tier.PRO))

    def _clear():
        calls["cleared"] = True

    monkeypatch.setattr(activation, "clear_token", _clear)
    monkeypatch.setattr(activation, "clear_license_key", lambda: None)
    return calls


def test_refresh_renews_and_stores_new_token(monkeypatch, wired):
    monkeypatch.setattr(activation.api_client, "refresh", lambda t, fp: {"token": "newtoken"})
    assert activation.refresh_now() is RefreshResult.RENEWED
    assert wired["stored"] == ["newtoken"]
    assert wired["cleared"] is False


def test_refresh_403_drops_to_free(monkeypatch, wired):
    def boom(t, fp):
        raise LicenseApiError("revoked", kind="http", status=403, error="license_revoked")

    monkeypatch.setattr(activation.api_client, "refresh", boom)
    assert activation.refresh_now() is RefreshResult.REVOKED
    assert wired["cleared"] is True
    assert wired["stored"] == []


def test_refresh_waf_403_keeps_token(monkeypatch, wired):
    # Cloudflare (or any proxy) can answer 403 before the request ever reaches
    # the Worker — no ``error`` of ours in the body. That is not a verdict on the
    # license, so a paying user must keep Pro.
    def boom(t, fp):
        raise LicenseApiError(
            "blocked", kind="http", status=403, error=None,
            body={"error_code": 1010, "error_name": "browser_signature_banned"},
        )

    monkeypatch.setattr(activation.api_client, "refresh", boom)
    assert activation.refresh_now() is RefreshResult.ERROR
    assert wired["cleared"] is False
    assert wired["stored"] == []


def test_refresh_network_keeps_token(monkeypatch, wired):
    def boom(t, fp):
        raise LicenseApiError("down", kind="network")

    monkeypatch.setattr(activation.api_client, "refresh", boom)
    assert activation.refresh_now() is RefreshResult.OFFLINE
    assert wired["cleared"] is False
    assert wired["stored"] == []


def test_refresh_seat_limit_keeps_token(monkeypatch, wired):
    def boom(t, fp):
        raise LicenseApiError("seat", kind="http", status=409, error="seat_limit")

    monkeypatch.setattr(activation.api_client, "refresh", boom)
    assert activation.refresh_now() is RefreshResult.SEAT_LIMIT
    assert wired["cleared"] is False


def test_refresh_not_activated(monkeypatch):
    monkeypatch.setattr(activation, "_api_configured", lambda: True)
    monkeypatch.setattr(activation, "get_token", lambda: None)
    assert activation.refresh_now() is RefreshResult.NOT_ACTIVATED


def test_refresh_offline_when_api_not_configured(monkeypatch):
    monkeypatch.setattr(activation, "get_token", lambda: "tok")
    monkeypatch.setattr(activation, "_api_configured", lambda: False)
    assert activation.refresh_now() is RefreshResult.OFFLINE

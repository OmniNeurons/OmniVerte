"""HistoryDialog: Free shows the locked form, Pro filters the encrypted store."""

from __future__ import annotations

from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication

import licensing
from licensing import Entitlement, Tier
from services.history_store import HistoryStore
from ui.history_dialog import HistoryDialog
from ui.history_manager import HistoryManager


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _manager(tmp_path, monkeypatch, tier):
    monkeypatch.setattr(licensing, "get_entitlement", lambda: Entitlement(tier))
    return HistoryManager(store_factory=lambda: HistoryStore(tmp_path / "history.db"))


def test_free_opens_with_filters_locked_and_session_entries(qapp, tmp_path, monkeypatch):
    h = _manager(tmp_path, monkeypatch, Tier.FREE)
    h.add("first take")
    h.add("second take")
    d = HistoryDialog(h)
    assert not d.pro_banner.isHidden()
    for w in (d.search_edit, d.kind_combo, d.period_combo, d.volume):
        assert not w.isEnabled()
    assert d.clear_btn.isEnabled()  # wiping works on every tier
    assert d.list.count() == 2
    assert "second take" in d.list.item(0).text()  # newest first
    d.close()


def test_pro_search_filters_the_store(qapp, tmp_path, monkeypatch):
    h = _manager(tmp_path, monkeypatch, Tier.PRO)
    h.add("договор Acme")
    h.add("something else")
    d = HistoryDialog(h)
    assert d.pro_banner.isHidden()
    assert d.search_edit.isEnabled()
    assert d.list.count() == 2
    d.search_edit.setText("acme")
    d.reload()
    assert d.list.count() == 1
    assert "Acme" in d.list.item(0).text()
    d.close()


def test_clear_from_dialog_empties_the_list(qapp, tmp_path, monkeypatch):
    h = _manager(tmp_path, monkeypatch, Tier.PRO)
    h.add("x")
    d = HistoryDialog(h)
    h.clear()  # the confirm box is the only thing _on_clear adds
    assert d.list.count() == 0
    assert not d.empty_label.isHidden()
    d.close()


def test_activating_an_entry_loads_it_once_and_closes_cleanly(qapp, tmp_path, monkeypatch, recwarn):
    h = _manager(tmp_path, monkeypatch, Tier.PRO)
    h.add("pick me")
    d = HistoryDialog(h)
    chosen = []
    d.entry_chosen.connect(chosen.append)
    d.list.itemActivated.emit(d.list.item(0))
    d.done(0)  # a second close must not warn about the disconnect
    assert [e.text for e in chosen] == ["pick me"]
    assert not [w for w in recwarn if "disconnect" in str(w.message)]

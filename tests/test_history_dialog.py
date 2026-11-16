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


def test_nice_ticks_round_up_past_the_busiest_day():
    from ui.history_dialog import nice_ticks
    assert nice_ticks(1500) == [0, 500, 1000, 1500]
    assert nice_ticks(1600) == [0, 500, 1000, 1500, 2000]
    assert nice_ticks(9) == [0, 5, 10]
    assert nice_ticks(0) == [0, 1]
    assert nice_ticks(73_000)[-1] >= 73_000


def test_compact_axis_labels():
    from ui.history_dialog import _fmt_compact
    assert [_fmt_compact(n) for n in (0, 950, 1000, 1500, 12_000, 1_200_000)] == [
        "0", "950", "1k", "1.5k", "12k", "1.2M",
    ]


def test_date_axis_marks_1st_10th_20th(qapp):
    from datetime import date, timedelta
    from ui.history_dialog import _VolumeBars
    bars = _VolumeBars()
    bars.resize(700, 120)
    start = date(2026, 10, 1)
    bars.set_data([(start + timedelta(days=i), 1, 100 * (i % 7)) for i in range(46)])
    texts = [text for _x, text in bars.date_labels()]
    assert texts == ["01.10", "10.10", "20.10", "01.11", "10.11"]


def test_date_axis_keeps_month_starts_when_crowded(qapp):
    from datetime import date, timedelta
    from ui.history_dialog import _VolumeBars
    bars = _VolumeBars()
    bars.resize(260, 120)
    start = date(2026, 1, 1)
    bars.set_data([(start + timedelta(days=i), 1, 10) for i in range(365)])
    labels = bars.date_labels()
    texts = [text for _x, text in labels]
    # A year in 260 px has no room for 36 marks: only month starts survive.
    assert texts and all(t.startswith("01.") for t in texts)
    xs = [x for x, _t in labels]
    assert xs == sorted(xs) and len(set(xs)) == len(xs)


def test_picking_a_day_folds_the_chart_and_whole_period_restores_it(qapp, tmp_path, monkeypatch):
    from datetime import date
    h = _manager(tmp_path, monkeypatch, Tier.PRO)
    h.add("today's take")
    d = HistoryDialog(h)
    assert not d.volume.isHidden()
    d.volume.day_clicked.emit(date.today())
    assert d.volume.isHidden()
    assert not d.day_reset_btn.isHidden()
    assert d.list.count() == 1
    d.day_reset_btn.click()
    assert not d.volume.isHidden()
    assert d.day_reset_btn.isHidden()
    d.close()

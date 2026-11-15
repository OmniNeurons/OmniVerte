"""HistoryManager: Free session caps, Pro persistence, truncation, tier switches."""

from __future__ import annotations

import pytest

import licensing
from licensing import Entitlement, Tier
from services.history_store import HistoryStore
from ui.history_manager import (
    HISTORY_ENTRY_MAX_CHARS,
    HISTORY_FEED_LIMIT,
    KIND_FIX,
    HistoryManager,
)


@pytest.fixture
def tier(monkeypatch):
    """Switchable entitlement: `tier.set(Tier.PRO)`."""

    class _Tier:
        current = Tier.FREE

        def set(self, value):
            self.current = value

    holder = _Tier()
    monkeypatch.setattr(licensing, "get_entitlement", lambda: Entitlement(holder.current))
    return holder


@pytest.fixture
def db(tmp_path):
    return tmp_path / "history.db"


def _manager(db, **kw):
    return HistoryManager(store_factory=lambda: HistoryStore(db), **kw)


# ---------- Free ----------

def test_add_keeps_insertion_order_newest_last(tier, db):
    h = _manager(db)
    h.add("first")
    h.add("second", kind=KIND_FIX)
    entries = h.entries()
    assert [e.text for e in entries] == ["first", "second"]
    assert entries[1].kind == KIND_FIX


def test_blank_text_is_ignored(tier, db):
    h = _manager(db)
    h.add("   \n  ")
    assert h.entries() == []


def test_meta_is_preserved(tier, db):
    h = _manager(db)
    h.add("hola", kind="translation", meta={"direction": "EN ↔ ES"})
    assert h.entries()[0].meta["direction"] == "EN ↔ ES"


def test_free_entry_cap_is_15(tier, db):
    h = _manager(db)
    for i in range(20):
        h.add(f"e{i}")
    assert len(h.entries()) == 15
    assert h.entry_cap() == 15
    assert h.entries()[0].text == "e5"


def test_free_char_budget_drops_oldest(tier, db):
    h = _manager(db)
    h.add("a" * 1495)
    h.add("b" * 10)  # total over 1500 → oldest evicted
    assert [set(e.text) for e in h.entries()] == [{"b"}]


def test_single_oversized_entry_is_kept(tier, db):
    h = _manager(db)
    h.add("x" * 1600)
    assert len(h.entries()) == 1


def test_free_never_touches_the_database(tier, db):
    h = _manager(db)
    h.add("hello")
    assert not h.persistent
    assert not db.exists()


def test_entry_is_truncated_on_any_tier(tier, db):
    h = _manager(db)
    h.add("y" * (HISTORY_ENTRY_MAX_CHARS + 50))
    text = h.entries()[0].text
    assert len(text) == HISTORY_ENTRY_MAX_CHARS
    assert text.endswith("…")


# ---------- Pro ----------

def test_pro_history_survives_a_restart(tier, db):
    tier.set(Tier.PRO)
    h = _manager(db)
    h.add("one")
    h.add("two", kind=KIND_FIX)
    assert h.persistent
    h2 = _manager(db)
    assert [(e.text, e.kind) for e in h2.entries()] == [("one", "transcription"), ("two", KIND_FIX)]
    assert h2.entry_cap() is None
    assert h2.count() == 2


def test_pro_feed_shows_latest_20(tier, db):
    tier.set(Tier.PRO)
    h = _manager(db)
    for i in range(25):
        h.add(f"e{i}")
    assert len(h.entries()) == HISTORY_FEED_LIMIT
    assert h.entries()[-1].text == "e24"
    assert h.count() == 25


def test_pro_query_and_delete(tier, db):
    tier.set(Tier.PRO)
    h = _manager(db)
    h.add("договор Acme")
    h.add("other")
    [hit] = h.query(text="acme")
    h.delete(hit.id)
    assert [e.text for e in h.entries()] == ["other"]


def test_downgrade_keeps_file_but_stops_reading(tier, db):
    tier.set(Tier.PRO)
    h = _manager(db)
    h.add("kept for later")
    tier.set(Tier.FREE)
    h.on_entitlement_changed()
    assert not h.persistent
    assert h.entries() == []
    assert db.exists()
    tier.set(Tier.PRO)
    h.on_entitlement_changed()
    assert [e.text for e in h.entries()] == ["kept for later"]


def test_clear_on_free_wipes_leftover_pro_file(tier, db):
    tier.set(Tier.PRO)
    _manager(db).add("left behind")
    tier.set(Tier.FREE)
    h = _manager(db)
    h.add("session")
    h.clear()
    assert h.entries() == []
    assert not db.exists()


def test_apply_retention_is_noop_on_free(tier, db):
    h = _manager(db, retention_days=lambda: 1)
    h.apply_retention()
    assert not db.exists()

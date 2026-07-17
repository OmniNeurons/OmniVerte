"""HistoryManager: ordering, empty-skip, and the char-budget trim policy."""

from __future__ import annotations

from ui.history_manager import (
    HISTORY_MAX_CHARS,
    KIND_FIX,
    HistoryManager,
)


def test_add_keeps_insertion_order_newest_last():
    h = HistoryManager()
    h.add("first")
    h.add("second", kind=KIND_FIX)
    entries = h.entries()
    assert [e.text for e in entries] == ["first", "second"]
    assert entries[1].kind == KIND_FIX


def test_blank_text_is_ignored():
    h = HistoryManager()
    h.add("   \n  ")
    assert h.entries() == []


def test_meta_is_preserved():
    h = HistoryManager()
    h.add("hola", kind="translation", meta={"direction": "EN ↔ ES"})
    assert h.entries()[0].meta["direction"] == "EN ↔ ES"


def test_trim_drops_oldest_past_budget():
    h = HistoryManager()
    h.add("a" * (HISTORY_MAX_CHARS - 5))
    h.add("b" * 10)  # total now over budget → oldest entry evicted
    remaining = h.entries()
    assert len(remaining) == 1
    assert set(remaining[0].text) == {"b"}


def test_single_oversized_entry_is_kept():
    h = HistoryManager()
    h.add("x" * (HISTORY_MAX_CHARS + 100))
    # A lone entry over the limit is kept rather than dropped to emptiness.
    assert len(h.entries()) == 1

"""HistoryStore: encryption at rest, purge policy, filters, volume, recovery."""

from __future__ import annotations

import sqlite3
import time
from datetime import date, datetime, timedelta

import pytest

from services.history_store import HistoryStore, KeyringKey


class _MemKey:
    def __init__(self):
        self.key = None

    def get(self):
        return self.key

    def set(self, key):
        self.key = key


@pytest.fixture
def store(tmp_path):
    s = HistoryStore(tmp_path / "history.db", _MemKey())
    yield s
    s.close()


def test_round_trip_keeps_text_kind_and_meta(store):
    store.add("привет мир", "translation", {"direction": "→ EN"})
    [e] = store.recent(5)
    assert (e.text, e.kind, e.meta) == ("привет мир", "translation", {"direction": "→ EN"})
    assert e.id is not None


def test_text_is_not_stored_in_plaintext(tmp_path):
    path = tmp_path / "history.db"
    s = HistoryStore(path, _MemKey())
    s.add("Секретный контракт Acme на 5 миллионов", "transcription")
    s.close()
    raw = b"".join(
        p.read_bytes() for p in tmp_path.iterdir() if p.name.startswith("history.db")
    )
    assert "Секретный".encode("utf-8") not in raw
    assert b"Acme" not in raw


def test_key_lives_in_keyring_by_default(tmp_path):
    s = HistoryStore(tmp_path / "history.db")  # KeyringKey → in-memory test keyring
    s.add("hello", "transcription")
    s.close()
    assert KeyringKey().get() is not None
    s2 = HistoryStore(tmp_path / "history.db")
    assert [e.text for e in s2.recent(5)] == ["hello"]
    s2.close()


def test_recent_is_newest_last_and_limited(store):
    for i in range(5):
        store.add(f"e{i}", "transcription", timestamp=datetime(2026, 1, 1, 10, i))
    assert [e.text for e in store.recent(3)] == ["e2", "e3", "e4"]


def test_purge_by_age(store):
    now = time.time()
    store.add("old", "transcription", timestamp=datetime.fromtimestamp(now - 40 * 86400))
    store.add("new", "transcription", timestamp=datetime.fromtimestamp(now - 86400))
    assert store.purge(30, None, now=now) == 1
    assert [e.text for e in store.recent(10)] == ["new"]


def test_purge_by_char_ceiling_drops_oldest(store):
    base = datetime.now()
    for i in range(4):
        store.add(str(i) * 100, "transcription", timestamp=base + timedelta(seconds=i))
    store.purge(365, 250)
    assert [e.text[0] for e in store.recent(10)] == ["2", "3"]


def test_query_filters_text_kind_and_dates(store):
    store.add("Договор с Acme", "transcription", timestamp=datetime(2026, 3, 1, 9))
    store.add("acme invoice", "translation", timestamp=datetime(2026, 3, 2, 9))
    store.add("unrelated", "transcription", timestamp=datetime(2026, 3, 3, 9))
    assert [e.text for e in store.query(text="ACME")] == ["acme invoice", "Договор с Acme"]
    assert [e.text for e in store.query(text="acme", kinds=["transcription"])] == ["Договор с Acme"]
    got = store.query(date_from=date(2026, 3, 2), date_to=date(2026, 3, 3))
    assert [e.text for e in got] == ["unrelated", "acme invoice"]


def test_query_pages(store):
    for i in range(5):
        store.add(f"x{i}", "transcription", timestamp=datetime(2026, 1, 1, 10, i))
    assert [e.text for e in store.query(limit=2, offset=0)] == ["x4", "x3"]
    assert [e.text for e in store.query(limit=2, offset=2)] == ["x2", "x1"]
    assert [e.text for e in store.query(text="x", limit=2, offset=4)] == ["x0"]


def test_daily_volume_and_totals(store):
    store.add("aaa", "transcription", timestamp=datetime(2026, 3, 1, 9))
    store.add("bb", "transcription", timestamp=datetime(2026, 3, 1, 18))
    store.add("c", "fix", timestamp=datetime(2026, 3, 4, 9))
    assert store.daily_volume() == [(date(2026, 3, 1), 2, 5), (date(2026, 3, 4), 1, 1)]
    count, chars, oldest = store.totals()
    assert (count, chars, oldest) == (3, 6, datetime(2026, 3, 1, 9))


def test_delete_one(store):
    a = store.add("a", "transcription")
    store.add("b", "transcription")
    store.delete(a.id)
    assert [e.text for e in store.recent(5)] == ["b"]


def test_clear_removes_file_and_key(tmp_path):
    keys = _MemKey()
    s = HistoryStore(tmp_path / "history.db", keys)
    s.add("x", "transcription")
    s.clear()
    assert not (tmp_path / "history.db").exists()
    assert keys.key is None


def test_db_without_key_is_quarantined(tmp_path):
    path = tmp_path / "history.db"
    keys = _MemKey()
    s = HistoryStore(path, keys)
    s.add("x", "transcription")
    s.close()
    keys.key = None  # key lost (Credential Manager wiped)
    s2 = HistoryStore(path, keys)
    assert s2.recent(5) == []
    assert (tmp_path / "history.db.corrupt").exists()
    s2.close()


def test_wrong_key_is_quarantined(tmp_path):
    path = tmp_path / "history.db"
    keys = _MemKey()
    s = HistoryStore(path, keys)
    s.add("x", "transcription")
    s.close()
    keys.key = b"\x00" * 32
    s2 = HistoryStore(path, keys)
    assert s2.recent(5) == []
    assert (tmp_path / "history.db.corrupt").exists()
    s2.close()


def test_garbage_file_is_quarantined(tmp_path):
    path = tmp_path / "history.db"
    path.write_bytes(b"not a database at all" * 100)
    keys = _MemKey()
    keys.key = b"\x01" * 32
    s = HistoryStore(path, keys)
    s.add("fresh", "transcription")
    assert [e.text for e in s.recent(5)] == ["fresh"]
    s.close()


def test_swapped_clear_columns_fail_authentication(tmp_path):
    path = tmp_path / "history.db"
    s = HistoryStore(path, _MemKey())
    s.add("secret", "transcription")
    s.add("other", "transcription")
    s._conn.execute("UPDATE entries SET kind = 'fix' WHERE id = 1")
    # The tampered row is skipped rather than returned with a forged kind.
    assert [e.text for e in s.recent(5)] == ["other"]
    s.close()

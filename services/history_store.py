# file: services/history_store.py

"""
Encrypted on-disk history (Pro). SQLite at %APPDATA%\\OmniVerte\\history.db.

Only the metadata needed to filter, purge and chart without decrypting stays in
the clear: timestamp, kind and character count. The text and its meta travel as
one AES-GCM blob per row, keyed by a random 256-bit key that lives in Windows
Credential Manager (``HISTORY_KEY``, keyring service ``OmniVerte``) — never on
disk next to the database. The row's ``ts|kind`` is bound in as associated
data, so swapping the clear columns between rows fails authentication.

Text search decrypts the candidate rows in Python: the Pro budget caps the
whole store at ~1M characters, which makes that a few-millisecond scan and
spares us SQLCipher/FTS (a native dependency, and FTS would index plaintext).

No Qt here — the store is unit-tested on its own; `ui.history_manager` is the
Qt-facing facade.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, List, Mapping, Optional, Tuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "OmniVerte"
HISTORY_KEY_NAME = "HISTORY_KEY"
DB_FILENAME = "history.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      REAL    NOT NULL,
    kind    TEXT    NOT NULL,
    chars   INTEGER NOT NULL,
    nonce   BLOB    NOT NULL,
    payload BLOB    NOT NULL
);
CREATE INDEX IF NOT EXISTS entries_ts ON entries(ts);
"""


@dataclass(frozen=True)
class StoredEntry:
    id: int
    timestamp: datetime
    kind: str
    text: str
    meta: Mapping[str, str] = field(default_factory=dict)


class KeyringKey:
    """Default key provider: the AES key in Credential Manager."""

    def get(self) -> Optional[bytes]:
        import keyring

        try:
            raw = keyring.get_password(KEYRING_SERVICE, HISTORY_KEY_NAME)
        except Exception as e:
            logger.error(f"history key read failed: {e}")
            return None
        if not raw:
            return None
        try:
            key = base64.b64decode(raw)
        except Exception:
            return None
        return key if len(key) == 32 else None

    def set(self, key: Optional[bytes]) -> None:
        import keyring

        try:
            if key:
                keyring.set_password(
                    KEYRING_SERVICE, HISTORY_KEY_NAME, base64.b64encode(key).decode("ascii")
                )
            else:
                try:
                    keyring.delete_password(KEYRING_SERVICE, HISTORY_KEY_NAME)
                except keyring.errors.PasswordDeleteError:
                    pass
        except Exception as e:
            logger.error(f"history key write failed: {e}")


def default_db_path() -> Path:
    # Same directory rule as services.config_store._appdata_dir (not imported:
    # that module pulls dotenv; this one must stay light).
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / "OmniVerte" / DB_FILENAME


def _aad(ts: float, kind: str) -> bytes:
    return f"{ts!r}|{kind}".encode("utf-8")


def _day_bounds(d: date) -> Tuple[float, float]:
    start = datetime.combine(d, datetime.min.time())
    return start.timestamp(), (start + timedelta(days=1)).timestamp()


class HistoryStore:
    """Encrypted append-mostly history table. Thread-safe (one connection + lock)."""

    def __init__(self, path: Optional[Path] = None, key_provider=None):
        self.path = Path(path) if path is not None else default_db_path()
        self._keys = key_provider if key_provider is not None else KeyringKey()
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._aes: Optional[AESGCM] = None

    # ---------- lifecycle ----------

    @staticmethod
    def exists_at(path: Optional[Path] = None) -> bool:
        return (Path(path) if path is not None else default_db_path()).exists()

    def _open(self) -> sqlite3.Connection:
        """Open (and if needed create) the DB; reconcile it with the key."""
        if self._conn is not None:
            return self._conn
        key = self._keys.get()
        if self.path.exists() and key is None:
            # A DB without its key is unreadable forever — park it, start over.
            self._quarantine("key missing")
        if key is None:
            key = AESGCM.generate_key(bit_length=256)
            self._keys.set(key)
        self._aes = AESGCM(key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = self._connect()
            if not self._probe(conn):
                conn.close()
                self._quarantine("key does not decrypt rows")
                conn = self._connect()
        except sqlite3.DatabaseError as e:
            self._quarantine(f"database error: {e}")
            conn = self._connect()
        self._conn = conn
        return conn

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
        except sqlite3.DatabaseError:
            # Release the file handle, or Windows refuses the quarantine rename.
            conn.close()
            raise
        return conn

    def _probe(self, conn: sqlite3.Connection) -> bool:
        row = conn.execute(
            "SELECT ts, kind, nonce, payload FROM entries ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return True
        try:
            self._decrypt(row[0], row[1], row[2], row[3])
            return True
        except Exception:
            return False

    def _quarantine(self, reason: str) -> None:
        logger.warning(f"history.db unusable ({reason}) — moving it aside to .corrupt")
        target = self.path.with_name(self.path.name + ".corrupt")
        for suffix in ("-wal", "-shm"):
            side = self.path.with_name(self.path.name + suffix)
            try:
                side.unlink()
            except FileNotFoundError:
                pass
            except OSError as e:
                logger.warning(f"could not remove {side}: {e}")
        try:
            if target.exists():
                target.unlink()
            self.path.replace(target)
        except FileNotFoundError:
            pass

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None
                self._aes = None

    # ---------- crypto ----------

    def _encrypt(self, ts: float, kind: str, text: str, meta: Mapping[str, str]) -> Tuple[bytes, bytes]:
        nonce = os.urandom(12)
        blob = json.dumps({"t": text, "m": dict(meta or {})}, ensure_ascii=False).encode("utf-8")
        return nonce, self._aes.encrypt(nonce, blob, _aad(ts, kind))

    def _decrypt(self, ts: float, kind: str, nonce: bytes, payload: bytes) -> Tuple[str, dict]:
        data = json.loads(self._aes.decrypt(nonce, payload, _aad(ts, kind)).decode("utf-8"))
        return data.get("t", ""), dict(data.get("m") or {})

    def _rows_to_entries(self, rows: Iterable[tuple]) -> List[StoredEntry]:
        out: List[StoredEntry] = []
        for rid, ts, kind, nonce, payload in rows:
            try:
                text, meta = self._decrypt(ts, kind, nonce, payload)
            except (InvalidTag, ValueError) as e:
                logger.warning(f"history row {rid} failed to decrypt: {e}")
                continue
            out.append(StoredEntry(rid, datetime.fromtimestamp(ts), kind, text, meta))
        return out

    # ---------- writes ----------

    def add(
        self,
        text: str,
        kind: str,
        meta: Optional[Mapping[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> StoredEntry:
        ts = (timestamp or datetime.now()).timestamp()
        meta = dict(meta or {})
        with self._lock:
            conn = self._open()
            nonce, payload = self._encrypt(ts, kind, text, meta)
            cur = conn.execute(
                "INSERT INTO entries(ts, kind, chars, nonce, payload) VALUES (?,?,?,?,?)",
                (ts, kind, len(text), nonce, payload),
            )
            return StoredEntry(cur.lastrowid, datetime.fromtimestamp(ts), kind, text, meta)

    def delete(self, entry_id: int) -> None:
        with self._lock:
            self._open().execute("DELETE FROM entries WHERE id = ?", (entry_id,))

    def purge(self, retention_days: int, max_chars: Optional[int], now: Optional[float] = None) -> int:
        """Drop rows older than the retention window, then oldest rows until the
        total character count fits ``max_chars`` (None = no cap). Returns the
        number of rows removed."""
        now = time.time() if now is None else now
        removed = 0
        with self._lock:
            conn = self._open()
            cutoff = now - retention_days * 86400
            removed += conn.execute("DELETE FROM entries WHERE ts < ?", (cutoff,)).rowcount
            if max_chars is not None:
                total = conn.execute("SELECT COALESCE(SUM(chars),0) FROM entries").fetchone()[0]
                if total > max_chars:
                    drop_ids = []
                    for rid, chars in conn.execute("SELECT id, chars FROM entries ORDER BY ts, id"):
                        if total <= max_chars:
                            break
                        drop_ids.append(rid)
                        total -= chars
                    conn.executemany("DELETE FROM entries WHERE id = ?", [(i,) for i in drop_ids])
                    removed += len(drop_ids)
        return removed

    def clear(self) -> None:
        """Wipe every row, the files and the key. Safe on a store never opened."""
        with self._lock:
            self.close()
            for suffix in ("", "-wal", "-shm"):
                p = self.path.with_name(self.path.name + suffix)
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass
                except OSError as e:
                    logger.warning(f"could not remove {p}: {e}")
            self._keys.set(None)

    # ---------- reads ----------

    def recent(self, n: int) -> List[StoredEntry]:
        """Newest-last list of the latest ``n`` entries."""
        with self._lock:
            rows = self._open().execute(
                "SELECT id, ts, kind, nonce, payload FROM entries ORDER BY ts DESC, id DESC LIMIT ?",
                (n,),
            ).fetchall()
            return list(reversed(self._rows_to_entries(rows)))

    def query(
        self,
        text: Optional[str] = None,
        kinds: Optional[Iterable[str]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[StoredEntry]:
        """Newest-first page of entries matching every given filter.

        Date bounds are inclusive local calendar days. ``text`` is a
        case-insensitive substring match on the decrypted text."""
        where, args = self._where(kinds, date_from, date_to)
        sql = f"SELECT id, ts, kind, nonce, payload FROM entries{where} ORDER BY ts DESC, id DESC"
        needle = (text or "").strip().casefold()
        with self._lock:
            conn = self._open()
            if not needle:
                rows = conn.execute(sql + " LIMIT ? OFFSET ?", (*args, limit, offset)).fetchall()
                return self._rows_to_entries(rows)
            matched: List[StoredEntry] = []
            skipped = 0
            for entry in self._rows_to_entries(conn.execute(sql, args)):
                if needle not in entry.text.casefold():
                    continue
                if skipped < offset:
                    skipped += 1
                    continue
                matched.append(entry)
                if len(matched) >= limit:
                    break
            return matched

    def daily_volume(
        self, date_from: Optional[date] = None, date_to: Optional[date] = None
    ) -> List[Tuple[date, int, int]]:
        """[(day, entries, chars)] oldest first, only days that have entries."""
        where, args = self._where(None, date_from, date_to)
        with self._lock:
            rows = self._open().execute(
                f"SELECT ts, chars FROM entries{where} ORDER BY ts", args
            ).fetchall()
        buckets: dict[date, list[int]] = {}
        for ts, chars in rows:
            b = buckets.setdefault(datetime.fromtimestamp(ts).date(), [0, 0])
            b[0] += 1
            b[1] += chars
        return [(d, c, n) for d, (c, n) in sorted(buckets.items())]

    def totals(self) -> Tuple[int, int, Optional[datetime]]:
        """(entries, chars, oldest timestamp or None)."""
        with self._lock:
            count, chars, oldest = self._open().execute(
                "SELECT COUNT(*), COALESCE(SUM(chars),0), MIN(ts) FROM entries"
            ).fetchone()
        return count, chars, (datetime.fromtimestamp(oldest) if oldest is not None else None)

    @staticmethod
    def _where(kinds, date_from, date_to) -> Tuple[str, tuple]:
        clauses, args = [], []
        kinds = list(kinds) if kinds else []
        if kinds:
            clauses.append(f"kind IN ({','.join('?' * len(kinds))})")
            args.extend(kinds)
        if date_from is not None:
            clauses.append("ts >= ?")
            args.append(_day_bounds(date_from)[0])
        if date_to is not None:
            clauses.append("ts < ?")
            args.append(_day_bounds(date_to)[1])
        return ((" WHERE " + " AND ".join(clauses)) if clauses else ""), tuple(args)

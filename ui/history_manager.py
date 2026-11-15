# file: ui/history_manager.py

"""
History of generated text — the Qt-facing facade over two backends:

- **Free**: in-memory, this session only, capped by the tier's
  ``history_entries`` / ``history_chars`` limits (oldest dropped first). The
  encrypted database is neither opened nor written.
- **Pro** (``Feature.PERSISTENT_HISTORY``): every entry goes to the encrypted
  SQLite store (`services.history_store`), purged by age
  (``HISTORY_RETENTION_DAYS``) and by the tier's ``history_chars`` ceiling.

The mode is re-read on every call that cares, plus `on_entitlement_changed()`
from the bridge, so an in-session activation/expiry switches without a restart.
A downgrade leaves the database on disk untouched (it comes back with Pro);
`clear()` wipes it on any tier.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, List, Mapping, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from i18n import t

logger = logging.getLogger(__name__)

# One entry is truncated past this many characters before it is kept (a pasted
# novel must not evict the whole history). The card and clipboard still get the
# full text — only the history copy is shortened.
HISTORY_ENTRY_MAX_CHARS = 100_000
TRUNCATION_MARK = "…"

# How many of the newest entries the main window's feed shows. The search
# dialog reaches the rest.
HISTORY_FEED_LIMIT = 20

# Fallback caps when the entitlement carries none (a token whose `limits` claim
# omits them, a stripped build without licensing).
_FREE_ENTRIES = 15
_FREE_CHARS = 1500
_PRO_CHARS = 1_000_000

# Canonical kinds — DATA, not chrome. These strings are stored on every
# HistoryEntry, compared against (`entry.kind in (...)` in main_window) and
# passed in by the audio pipeline. They are never translated; `kind_label()`
# below is what turns one into something a human reads.
KIND_TRANSCRIPTION = "transcription"
KIND_TRANSLATION = "translation"
KIND_FIX = "fix"
KIND_CASUAL = "casual"
KIND_PROFESSIONAL = "professional"
KIND_CUSTOM = "custom"

ALL_KINDS = (
    KIND_TRANSCRIPTION,
    KIND_TRANSLATION,
    KIND_FIX,
    KIND_CASUAL,
    KIND_PROFESSIONAL,
    KIND_CUSTOM,
)

# kind -> catalog KEY. Deliberately keys rather than text: a module-level dict of
# `t()` results would be built once at import, freezing every Activity Feed label
# in whatever locale happened to be active then. The lookup happens in
# `kind_label()`, per call, at render time.
KIND_LABEL_KEYS = {
    KIND_TRANSCRIPTION: "history.kind.transcription",
    KIND_TRANSLATION: "history.kind.translation",
    KIND_FIX: "history.kind.fix",
    KIND_CASUAL: "history.kind.casual",
    KIND_PROFESSIONAL: "history.kind.professional",
    KIND_CUSTOM: "history.kind.custom",
}


def kind_label(kind: str, fallback: Optional[str] = None) -> str:
    """Human-readable name for a history `kind`, in the active UI locale.

    An unknown kind returns `fallback` (or the raw kind when none is given)
    rather than a catalog miss — callers each have their own sensible stand-in.
    """
    key = KIND_LABEL_KEYS.get(kind)
    if key is None:
        return fallback if fallback is not None else kind
    return t(key)


@dataclass(frozen=True)
class HistoryEntry:
    timestamp: datetime
    text: str
    kind: str = KIND_TRANSCRIPTION
    # Operation-specific metadata. Currently only translation uses it
    # ({"direction": "RU → EN"}). Kept open-ended so future kinds can attach
    # their own context without bumping the model again.
    meta: Mapping[str, str] = field(default_factory=dict)
    # Row id in the encrypted store; None for an in-memory (Free) entry.
    id: Optional[int] = None


def _truncate(text: str) -> str:
    if len(text) <= HISTORY_ENTRY_MAX_CHARS:
        return text
    return text[: HISTORY_ENTRY_MAX_CHARS - len(TRUNCATION_MARK)].rstrip() + TRUNCATION_MARK


class HistoryManager(QObject):
    """Session (Free) or persistent encrypted (Pro) history of generated text."""

    changed = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        store_factory: Optional[Callable[[], object]] = None,
        retention_days: Optional[Callable[[], int]] = None,
    ):
        """``store_factory`` builds the `HistoryStore` lazily (tests inject a
        temp-path one); ``retention_days`` returns the live setting (the app
        passes ``lambda: config.history_retention_days``)."""
        super().__init__(parent)
        self._entries: List[HistoryEntry] = []
        self._store_factory = store_factory
        self._retention_days = retention_days or (lambda: 30)
        self._store = None
        # Newest-last cache of the store's latest HISTORY_FEED_LIMIT rows.
        self._recent: List[HistoryEntry] = []
        self._persistent = self._is_persistent()
        if self._persistent:
            self._reload_recent()

    # ---------- tier ----------

    @staticmethod
    def _entitlement():
        from licensing import get_entitlement

        return get_entitlement()

    def _is_persistent(self) -> bool:
        try:
            from licensing import Feature

            return self._entitlement().has(Feature.PERSISTENT_HISTORY)
        except Exception:
            return False

    @property
    def persistent(self) -> bool:
        """True when history is saved to disk (Pro)."""
        return self._persistent

    def _caps(self) -> Tuple[Optional[int], int]:
        """(max entries or None for unlimited, max total chars) for the tier."""
        try:
            from licensing import UNLIMITED

            ent = self._entitlement()
            entries = ent.limit("history_entries")
            chars = ent.limit("history_chars")
        except Exception:
            return _FREE_ENTRIES, _FREE_CHARS
        if entries == UNLIMITED:
            entries_cap = None
        elif entries > 0:
            entries_cap = entries
        else:
            entries_cap = _FREE_ENTRIES
        if chars == UNLIMITED or chars <= 0:
            chars = _PRO_CHARS if self._persistent else _FREE_CHARS
        return entries_cap, chars

    def entry_cap(self) -> Optional[int]:
        """Session entry cap shown as 'n/cap' in the feed, None when unlimited."""
        return self._caps()[0]

    # ---------- store ----------

    def _get_store(self):
        if self._store is None:
            if self._store_factory is not None:
                self._store = self._store_factory()
            else:
                from services.history_store import HistoryStore

                self._store = HistoryStore()
        return self._store

    @staticmethod
    def _from_stored(s) -> HistoryEntry:
        return HistoryEntry(timestamp=s.timestamp, text=s.text, kind=s.kind, meta=s.meta, id=s.id)

    def _reload_recent(self) -> None:
        try:
            self._recent = [self._from_stored(s) for s in self._get_store().recent(HISTORY_FEED_LIMIT)]
        except Exception as e:
            logger.error(f"history store read failed: {e}")
            self._recent = []

    # ---------- public API ----------

    def add(
        self,
        text: str,
        kind: str = KIND_TRANSCRIPTION,
        meta: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Append text with current timestamp; trim per the tier's budget."""
        text = _truncate((text or "").strip())
        if not text:
            return
        meta = dict(meta) if meta else {}
        self._persistent = self._is_persistent()

        if self._persistent:
            try:
                store = self._get_store()
                store.add(text, kind, meta)
                store.purge(self._retention_days(), self._caps()[1])
            except Exception as e:
                logger.error(f"history store write failed: {e}")
            self._reload_recent()
        else:
            self._entries.append(HistoryEntry(datetime.now(), text, kind, meta))
            self._trim()
        self.changed.emit()

    def entries(self) -> List[HistoryEntry]:
        """Newest-last entries for the feed: the session list on Free, the latest
        HISTORY_FEED_LIMIT stored rows on Pro."""
        if self._persistent:
            return list(self._recent)
        return list(self._entries[-HISTORY_FEED_LIMIT:])

    def session_entries(self) -> List[HistoryEntry]:
        """Every in-memory (Free) entry, newest-last."""
        return list(self._entries)

    def count(self) -> int:
        """Total entries: stored rows on Pro, session entries on Free."""
        return self.totals()[0]

    def totals(self) -> Tuple[int, int, Optional[datetime]]:
        """(entries, chars, oldest timestamp) of what the tier currently holds."""
        if self._persistent:
            try:
                return self._get_store().totals()
            except Exception as e:
                logger.error(f"history store read failed: {e}")
                return 0, 0, None
        oldest = self._entries[0].timestamp if self._entries else None
        return len(self._entries), sum(len(e.text) for e in self._entries), oldest

    def query(self, **filters) -> List[HistoryEntry]:
        """Newest-first page from the store (Pro). On Free: the session list,
        newest first — filters are a Pro capability and are ignored."""
        if not self._persistent:
            return list(reversed(self._entries))
        try:
            return [self._from_stored(s) for s in self._get_store().query(**filters)]
        except Exception as e:
            logger.error(f"history query failed: {e}")
            return []

    def daily_volume(
        self, date_from: Optional[date] = None, date_to: Optional[date] = None
    ) -> List[Tuple[date, int, int]]:
        if not self._persistent:
            return []
        try:
            return self._get_store().daily_volume(date_from, date_to)
        except Exception as e:
            logger.error(f"history volume read failed: {e}")
            return []

    def delete(self, entry_id: int) -> None:
        if not self._persistent or entry_id is None:
            return
        try:
            self._get_store().delete(entry_id)
        except Exception as e:
            logger.error(f"history delete failed: {e}")
        self._reload_recent()
        self.changed.emit()

    def clear(self) -> None:
        """Forget everything: the session list, and the encrypted store + its key
        on any tier (a Free user can wipe what an expired Pro left behind)."""
        self._entries.clear()
        self._recent = []
        try:
            if self._store is not None:
                self._store.clear()
            else:
                from services.history_store import HistoryStore

                store = self._store_factory() if self._store_factory is not None else HistoryStore()
                store.clear()
        except Exception as e:
            logger.error(f"history clear failed: {e}")
        self._store = None
        self.changed.emit()

    def apply_retention(self) -> None:
        """Purge stored rows past the retention window / char ceiling (Pro only;
        on Free the database is not touched)."""
        self._persistent = self._is_persistent()
        if not self._persistent:
            return
        try:
            self._get_store().purge(self._retention_days(), self._caps()[1])
        except Exception as e:
            logger.error(f"history purge failed: {e}")
        self._reload_recent()
        self.changed.emit()

    def on_entitlement_changed(self, *_args) -> None:
        """Switch mode after an activation/expiry. The session list survives an
        upgrade only in memory (it is not migrated to disk); a downgrade stops
        reading the store but leaves the file as it is."""
        persistent = self._is_persistent()
        if persistent != self._persistent:
            self._persistent = persistent
            if persistent:
                self._reload_recent()
            else:
                self._recent = []
                if self._store is not None:
                    try:
                        self._store.close()
                    except Exception:
                        pass
                    self._store = None
        if not persistent:
            self._trim()
        self.changed.emit()

    # ---------- Free trim ----------

    def _trim(self) -> None:
        # Entry cap first (the hard ceiling), then the char budget. Read live so
        # an in-session activation lifts the cap on the next add.
        entries_cap, chars_cap = self._caps()
        if entries_cap is not None:
            while len(self._entries) > entries_cap:
                self._entries.pop(0)

        total = sum(len(e.text) for e in self._entries)
        while total > chars_cap and len(self._entries) > 1:
            dropped = self._entries.pop(0)
            total -= len(dropped.text)
        # If a single entry alone is over the limit, keep it (truncating
        # individual messages would be more confusing than helpful).

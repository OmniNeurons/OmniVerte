# file: ui/history_manager.py

"""
In-memory session history of generated text. Lives for the entire app session
(survives hiding/showing the main window), evaporates on app exit.

Constraint: total character count across all entries ≤ HISTORY_MAX_CHARS.
When new entries push past the limit, oldest entries get dropped one-by-one
until the budget is back under the limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Mapping, Optional

from PySide6.QtCore import QObject, Signal

from i18n import t

HISTORY_MAX_CHARS = 2000

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


class HistoryManager(QObject):
    """Append-only ring buffer of HistoryEntry, capped by total character count."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._entries: List[HistoryEntry] = []

    def add(
        self,
        text: str,
        kind: str = KIND_TRANSCRIPTION,
        meta: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Append text with current timestamp; trim oldest until under budget."""
        text = (text or "").strip()
        if not text:
            return

        self._entries.append(
            HistoryEntry(
                timestamp=datetime.now(),
                text=text,
                kind=kind,
                meta=dict(meta) if meta else {},
            )
        )
        self._trim()
        self.changed.emit()

    def entries(self) -> List[HistoryEntry]:
        """Newest-last list of entries."""
        return list(self._entries)

    def _trim(self) -> None:
        # Tier cap (Free = 10 entries; Pro = UNLIMITED). Read live so an
        # in-session activation lifts the cap on the next add without a restart.
        # Applied before the char budget so the entry count is the hard ceiling.
        cap = self._entry_cap()
        if cap is not None:
            while len(self._entries) > cap:
                self._entries.pop(0)

        total = sum(len(e.text) for e in self._entries)
        while total > HISTORY_MAX_CHARS and len(self._entries) > 1:
            dropped = self._entries.pop(0)
            total -= len(dropped.text)
        # If a single entry alone is over the limit, keep it (truncating
        # individual messages would be more confusing than helpful).

    @staticmethod
    def _entry_cap() -> Optional[int]:
        """Max session entries from the active entitlement, or None for unlimited.

        Resolution failures (missing licensing deps in a stripped build, etc.)
        fall back to the Free cap rather than crashing the history path."""
        from licensing import UNLIMITED, get_entitlement

        try:
            limit = get_entitlement().limit("history_entries")
        except Exception:
            limit = 10
        return None if limit == UNLIMITED else limit

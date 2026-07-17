# file: ui/hotkey_capture.py

"""
"Press a key" capture for hotkey fields — the same trick the tray uses to
rebind an activation key, made reusable in the settings UI.

The tray listens for a new key with a single blocking `keyboard.read_key()` on
a daemon thread (see `AudioWriter.listen_for_new_activation_key`). We reuse that
exact primitive here: a small "Catch the key" button next to a hotkey `LineEdit`
grabs the next keypress and drops its name into the field. The field stays the
single source of truth, so a page's existing load/apply/validate code is
unchanged — capture just fills the box instead of the user typing into it.

Deliberately no rebind here: capture only writes text into the edit; the normal
Save flow (`GeneralPage.apply_to` → Config → live re-register) applies it, so it
goes through the same duplicate-key validation as a typed value.
"""

from __future__ import annotations

import logging
import re
import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget

from qfluentwidgets import FluentIcon as FIF, LineEdit, PushButton

import keyboard  # same lib the tray uses to capture the next keypress

from i18n import t

logger = logging.getLogger(__name__)

_FKEY_RE = re.compile(r"f\d{1,2}", re.IGNORECASE)

# Catalog KEYS, not text: a module-level `t()` would resolve once at import and
# pin the button's label to that locale forever. Every use site below calls
# `t()` in a method body, so the label follows the active locale.
_CATCH_KEY = "hotkeycapture.catch"
_LISTENING_KEY = "hotkeycapture.listening"
_CAPTURE_BTN_WIDTH = 140


def normalize_hotkey(name: str) -> str:
    """Normalise a captured key name to the form the fields already use.

    `keyboard.read_key()` returns lower-case names ("f9", "esc", "space"); the
    hotkey fields, defaults and placeholders all use capitalised forms ("F9").
    Normalising keeps a captured key visually identical to a typed one — and,
    since validation dedupes case-insensitively, avoids a captured "f9" reading
    as different from a typed "F9".
    """
    name = (name or "").strip()
    if not name:
        return name

    def _fmt(token: str) -> str:
        if _FKEY_RE.fullmatch(token):   # function keys → F9, F10
            return token.upper()
        if len(token) == 1:             # single letters/digits → A, 1
            return token.upper()
        return token.capitalize()       # esc → Esc, ctrl → Ctrl, space → Space

    # `read_key()` returns a single key, but be tolerant of "+"-joined combos.
    return "+".join(_fmt(part) for part in name.split("+"))


class _KeyCaptureController(QObject):
    """Wires a "Catch the key" button to fill a LineEdit with the next keypress.

    `keyboard.read_key()` blocks until a key is pressed, so it must run off the
    Qt thread — otherwise the window freezes. The captured name is marshalled
    back to the GUI thread via a signal (Qt widgets are not thread-safe), which
    is the only safe way to touch the edit from the worker.

    Only ONE field may be armed at a time across the whole page (`_active`). A
    blocking `read_key()` can't be interrupted, so several armed fields would all
    wake on a single keypress and every one of them would grab the same key —
    which is exactly the "changing two hotkeys at once" bug. The class-level
    token fixes it two ways: arming a field disarms any other, and a captured key
    is only applied by the controller that is *still* the active one, so any
    lingering worker thread (a cancelled field, or a second reader woken by the
    same press) resolves to a no-op.

    `_active` is only ever read/written on the GUI thread (button click and the
    queued `_captured` slot), so it needs no lock.
    """

    _captured = Signal(str)
    _active: "_KeyCaptureController | None" = None

    def __init__(self, edit: LineEdit, button: PushButton, parent: QWidget) -> None:
        super().__init__(parent)
        self._edit = edit
        self._button = button
        self._captured.connect(self._on_captured)
        button.clicked.connect(self._start)

    def _start(self) -> None:
        cls = _KeyCaptureController
        # Clicking the armed button again cancels the capture (toggle off).
        if cls._active is self:
            self._disarm()
            return
        # Move the single "armed" slot to this field, disarming whoever held it.
        if cls._active is not None:
            cls._active._disarm()
        cls._active = self
        self._button.setText(t(_LISTENING_KEY))
        # Keep the button enabled so a second click can cancel; a fresh daemon
        # thread does the blocking read (mirrors the tray's rebind listener).
        threading.Thread(target=self._capture, daemon=True).start()

    def _capture(self) -> None:
        # Mirror the tray exactly: a plain blocking read of the next key. No
        # suppress — the tray's rebind path doesn't suppress either, and the
        # focused window during capture is our own settings window.
        key = ""
        try:
            key = keyboard.read_key()
        except Exception as e:  # pragma: no cover — defensive, keyboard rarely throws
            logger.error(f"Hotkey capture failed: {e}", exc_info=True)
        self._captured.emit(key or "")

    def _on_captured(self, key: str) -> None:
        # Apply only if we're still the armed field. A stale thread (this field
        # was cancelled, or another reader woke on the same press) lands here
        # with `_active` pointing elsewhere/None and must not touch its edit.
        if _KeyCaptureController._active is not self:
            return
        _KeyCaptureController._active = None
        if key:
            self._edit.setText(normalize_hotkey(key))
        self._button.setText(t(_CATCH_KEY))

    def _disarm(self) -> None:
        """Drop the armed state and restore the button label (no key applied)."""
        if _KeyCaptureController._active is self:
            _KeyCaptureController._active = None
        self._button.setText(t(_CATCH_KEY))


def make_capture_field(edit: LineEdit) -> QWidget:
    """Return a `[ edit | Catch the key ]` container for a hotkey field.

    `edit` stays the source of truth (the caller keeps its reference for
    load/apply/validate); this only adds a button that captures the next
    keypress into it. Drop the returned widget into `make_form_row` in place of
    the bare edit.
    """
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    button = PushButton(t(_CATCH_KEY))
    button.setIcon(FIF.EDIT)
    button.setFixedWidth(_CAPTURE_BTN_WIDTH)
    button.setCursor(Qt.PointingHandCursor)
    button.setToolTip(t("hotkeycapture.tooltip"))

    layout.addWidget(edit, alignment=Qt.AlignVCenter)
    layout.addWidget(button, alignment=Qt.AlignVCenter)

    # Parent the controller to the container so it lives as long as the row and
    # isn't garbage-collected out from under the button's clicked signal.
    box._capture_controller = _KeyCaptureController(edit, button, box)
    return box

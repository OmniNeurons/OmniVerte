"""Hotkey capture: normalisation + the Catch-the-key button wiring reused from the tray."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication

from ui.hotkey_capture import normalize_hotkey


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _reset_active():
    # `_active` is class-level shared state; keep it from leaking across tests.
    from ui.hotkey_capture import _KeyCaptureController

    _KeyCaptureController._active = None
    yield
    _KeyCaptureController._active = None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("f9", "F9"),
        ("F9", "F9"),
        ("f12", "F12"),
        ("a", "A"),
        ("1", "1"),
        ("esc", "Esc"),
        ("space", "Space"),
        ("ctrl+shift+s", "Ctrl+Shift+S"),
        ("  f10  ", "F10"),
        ("", ""),
    ],
)
def test_normalize_hotkey(raw, expected):
    assert normalize_hotkey(raw) == expected


def test_capture_field_keeps_edit_as_source_of_truth(qapp):
    from qfluentwidgets import LineEdit

    from ui.hotkey_capture import make_capture_field

    edit = LineEdit()
    box = make_capture_field(edit)

    # The edit stays reachable/usable by the page (load/apply/validate use it).
    assert edit.parent() is not None
    assert box.findChild(type(edit)) is edit


def test_captured_key_lands_normalised_in_the_edit(qapp):
    from qfluentwidgets import LineEdit

    from ui.hotkey_capture import _KeyCaptureController, make_capture_field

    edit = LineEdit()
    box = make_capture_field(edit)
    ctrl = box._capture_controller

    # Arm this field (what a button click does), then simulate the worker thread
    # reporting a captured key — skips real keyboard IO.
    _KeyCaptureController._active = ctrl
    ctrl._on_captured("f9")

    assert edit.text() == "F9"
    assert _KeyCaptureController._active is None  # disarmed after applying


def test_only_the_armed_field_receives_the_key(qapp):
    """Regression: a single keypress must not fill two hotkey fields at once.

    Two armed fields each run a blocking read that wakes on the same press; only
    the field that is currently armed may apply the captured key.
    """
    from qfluentwidgets import LineEdit

    from ui.hotkey_capture import _KeyCaptureController, make_capture_field

    edit_a = LineEdit()
    edit_b = LineEdit()
    # Keep the containers alive — a layout would in the real UI; here nothing
    # else references them, and Qt deletes an unparented widget out from under us.
    box_a = make_capture_field(edit_a)
    box_b = make_capture_field(edit_b)
    ctrl_a = box_a._capture_controller
    ctrl_b = box_b._capture_controller

    # Field A is the armed one; B is a stale reader from a cancelled/earlier arm.
    _KeyCaptureController._active = ctrl_a

    # Both worker threads wake on the same press, in either order.
    ctrl_b._on_captured("f9")  # stale — must be ignored
    ctrl_a._on_captured("f9")  # armed — applies

    assert edit_a.text() == "F9"
    assert edit_b.text() == ""


def test_second_catch_moves_the_armed_slot(qapp, monkeypatch):
    """Clicking Catch on another field disarms the first (single armed field)."""
    import ui.hotkey_capture as hc
    from qfluentwidgets import LineEdit

    from ui.hotkey_capture import _KeyCaptureController, make_capture_field

    # Keep the worker off the real keyboard: return instantly instead of blocking
    # on a live read_key() hook.
    monkeypatch.setattr(hc.keyboard, "read_key", lambda: "")

    box_a = make_capture_field(LineEdit())
    box_b = make_capture_field(LineEdit())
    ctrl_a = box_a._capture_controller
    ctrl_b = box_b._capture_controller

    _KeyCaptureController._active = ctrl_a
    ctrl_b._start()  # arming B must steal the slot from A

    assert _KeyCaptureController._active is ctrl_b
    ctrl_b._disarm()
    assert _KeyCaptureController._active is None

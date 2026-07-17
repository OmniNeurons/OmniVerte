"""Auto-paste suppression in ``process_text``.

The transcript reaches the user two ways: the ``transcript_ready`` signal (into
the main window's text card) and a clipboard + Ctrl+V auto-paste into whatever
editor had focus. When the focused window at recording start was our OWN window
(cursor in the text card), the auto-paste would land in that same card and
duplicate the text. ``process_text`` must skip the Ctrl+V in that case.

AudioWriter is built with ``__new__`` (its real ``__init__`` loads a Whisper
model); everything ``process_text`` touches is stubbed so we assert on the paste
decision, not the transcription pipeline.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import ctypes

import pytest

from services import audio_writer as aw
from services.audio_writer import AudioWriter


# ---------- _hwnd_is_own_process ----------

def _patch_fake_ctypes(monkeypatch, *, returned_pid):
    """Replace aw.ctypes so GetWindowThreadProcessId writes `returned_pid`."""

    def fake_get_thread_pid(hwnd, pid_ref):
        pid_ref.value = returned_pid
        return 0

    fake = SimpleNamespace(
        c_ulong=ctypes.c_ulong,
        byref=lambda x: x,  # our fake writes .value directly on the c_ulong
        windll=SimpleNamespace(
            user32=SimpleNamespace(GetWindowThreadProcessId=fake_get_thread_pid)
        ),
    )
    monkeypatch.setattr(aw, "ctypes", fake)


def test_hwnd_is_own_process_true_when_pid_matches(monkeypatch):
    w = AudioWriter.__new__(AudioWriter)
    monkeypatch.setattr(aw.os, "getpid", lambda: 4242)
    _patch_fake_ctypes(monkeypatch, returned_pid=4242)
    assert w._hwnd_is_own_process(0xABCD) is True


def test_hwnd_is_own_process_false_when_pid_differs(monkeypatch):
    w = AudioWriter.__new__(AudioWriter)
    monkeypatch.setattr(aw.os, "getpid", lambda: 4242)
    _patch_fake_ctypes(monkeypatch, returned_pid=9999)
    assert w._hwnd_is_own_process(0xABCD) is False


def test_hwnd_is_own_process_false_for_null_hwnd(monkeypatch):
    w = AudioWriter.__new__(AudioWriter)
    # No ctypes call should be needed; a null hwnd is short-circuited.
    monkeypatch.setattr(aw, "ctypes", None)
    assert w._hwnd_is_own_process(0) is False


# ---------- process_text auto-paste decision ----------

def _writer_for_process_text(monkeypatch):
    """Bare writer with every process_text side effect stubbed/spied."""
    w = AudioWriter.__new__(AudioWriter)
    w._session_gen = 1
    w.active_action = "transcribe"
    w._skip_next_paste = False
    w._foreground_was_own = False
    w._prev_foreground_hwnd = 0  # skip the SetForegroundWindow block by default
    w.ui_bridge = MagicMock()
    w.history_manager = MagicMock()
    w._apply_action_transform = lambda text: "corrected"
    w.drop_all = MagicMock()
    w.press_and_talk = MagicMock()

    monkeypatch.setattr(aw.pyperclip, "copy", MagicMock())
    monkeypatch.setattr(aw.time, "sleep", lambda *_: None)
    monkeypatch.setattr(aw.keyboard, "send", MagicMock())
    return w


def test_process_text_skips_paste_when_own_window_was_focused(monkeypatch):
    w = _writer_for_process_text(monkeypatch)
    w._foreground_was_own = True

    w.process_text("raw", session_gen=1)

    aw.keyboard.send.assert_not_called()
    # Text still delivered via the signal and the clipboard.
    w.ui_bridge.transcript_ready.emit.assert_called_once_with("corrected")
    aw.pyperclip.copy.assert_called_once_with("corrected")


def test_process_text_pastes_when_external_window_was_focused(monkeypatch):
    w = _writer_for_process_text(monkeypatch)
    w._foreground_was_own = False

    w.process_text("raw", session_gen=1)

    aw.keyboard.send.assert_called_once_with("ctrl+v")


def test_process_text_double_tap_skip_takes_precedence(monkeypatch):
    w = _writer_for_process_text(monkeypatch)
    w._skip_next_paste = True
    w._foreground_was_own = False

    w.process_text("raw", session_gen=1)

    aw.keyboard.send.assert_not_called()

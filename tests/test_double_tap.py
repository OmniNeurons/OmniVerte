"""The double-tap / deferred-stop gesture state machine (`toggle_recording`).

This is the most failure-prone logic in the app: it juggles several flags and a
``threading.Timer`` across the keyboard-hook, timer, and GUI threads. The tests
pin down each timing zone deterministically by faking the clock and the Timer —
no real threads, no real sleeps.

AudioWriter is built with ``__new__`` (its real ``__init__`` would load a
Whisper model); ``start_recording`` / ``stop_recording`` are stubbed so we
assert on intent, not side effects.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services import audio_writer as aw
from services.audio_writer import AudioWriter


class FakeTimer:
    """Stand-in for threading.Timer that never fires on its own — the test
    calls ``fire()`` to simulate the 300ms elapsing."""

    def __init__(self, interval, fn):
        self.interval = interval
        self.fn = fn
        self.started = False
        self.cancelled = False
        self.daemon = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        if not self.cancelled:
            self.fn()


@pytest.fixture
def clock(monkeypatch):
    state = {"now": 1000.0}
    monkeypatch.setattr(aw.time, "time", lambda: state["now"])
    return state


@pytest.fixture
def timers(monkeypatch):
    created: list[FakeTimer] = []

    def factory(interval, fn):
        timer = FakeTimer(interval, fn)
        created.append(timer)
        return timer

    monkeypatch.setattr(aw.threading, "Timer", factory)
    return created


@pytest.fixture
def writer(clock, timers):
    w = AudioWriter.__new__(AudioWriter)
    w.last_toggle_time = 0.0
    w._pending_stop_timer = None
    w._skip_next_paste = False
    w.double_tap_opens_window = True
    w.is_recording = False
    w.active_action = "transcribe"
    w._pending_action = "transcribe"
    w.ui_bridge = MagicMock()
    w.start_recording = MagicMock()
    w.stop_recording = MagicMock()
    return w


def test_single_press_from_idle_starts_and_locks_action(writer):
    writer._pending_action = "translate"
    writer.toggle_recording()
    writer.start_recording.assert_called_once()
    assert writer.active_action == "translate"


def test_mechanical_bounce_is_ignored(writer, clock):
    writer.last_toggle_time = clock["now"] - 0.02  # 20ms — below the 50ms floor
    writer.toggle_recording()
    writer.start_recording.assert_not_called()
    writer.stop_recording.assert_not_called()


def test_double_tap_while_recording_opens_window_without_stopping(writer, clock):
    writer.is_recording = True
    writer.last_toggle_time = clock["now"] - 0.1  # 100ms → double-tap
    writer.toggle_recording()
    writer.ui_bridge.show_window_requested.emit.assert_called_once()
    assert writer._skip_next_paste is True
    writer.stop_recording.assert_not_called()


def test_double_tap_respects_disabled_open_setting(writer, clock):
    writer.double_tap_opens_window = False
    writer.is_recording = True
    writer.last_toggle_time = clock["now"] - 0.1
    writer.toggle_recording()
    writer.ui_bridge.show_window_requested.emit.assert_not_called()
    assert writer._skip_next_paste is False


def test_single_press_while_recording_defers_the_stop(writer, clock, timers):
    writer.is_recording = True
    writer.last_toggle_time = clock["now"] - 1.0  # >300ms → normal single press
    writer.toggle_recording()

    # Stop is deferred, not immediate — the keyboard thread must not block.
    writer.stop_recording.assert_not_called()
    assert len(timers) == 1 and timers[0].started
    assert writer._pending_stop_timer is timers[0]

    # When the deferred timer fires with no follow-up tap, the real stop runs.
    timers[0].fire()
    writer.stop_recording.assert_called_once()


def test_double_tap_after_pending_stop_cancels_timer_and_stops(writer, clock, timers):
    writer.is_recording = True
    writer.last_toggle_time = clock["now"] - 1.0
    writer.toggle_recording()  # schedules deferred stop
    pending = timers[0]

    clock["now"] += 0.1  # second tap 100ms later → double-tap
    writer.toggle_recording()

    assert pending.cancelled is True
    writer.ui_bridge.show_window_requested.emit.assert_called_once()
    writer.stop_recording.assert_called_once()
    assert writer._pending_stop_timer is None

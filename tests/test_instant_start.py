"""First-word loss on slow machines: the hotkey fires on key-DOWN, and the
indicator says "recording" only once the mic has really delivered a frame.

Two guarantees:

* a held hotkey (OS auto-repeat) toggles exactly once per physical press, and a
  missed key-up cannot leave the hotkey dead;
* "recording" is never emitted before the first audio frame of the session.
"""

from __future__ import annotations

import queue
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from services import audio_writer as aw
from services.audio_writer import AudioWriter


# ---------- key-down trigger + auto-repeat filter ----------

@pytest.fixture
def kb():
    """Fake keyboard lib surface: captures the release watcher, tracks 'pressed'.

    Saved/restored by hand, not via monkeypatch: ``aw.keyboard`` is conftest's
    MagicMock stub, and monkeypatch's undo *deletes* an attribute the mock had
    only auto-created — after which the stub raises AttributeError on it for
    every later test in the run.
    """
    state = SimpleNamespace(watchers=[], pressed=True, unhooked=[])

    def hook(cb):
        state.watchers.append(cb)
        return cb

    fakes = {"hook": hook, "unhook": state.unhooked.append,
             "is_pressed": lambda key: state.pressed}
    saved = {name: getattr(aw.keyboard, name) for name in fakes}
    for name, fake in fakes.items():
        setattr(aw.keyboard, name, fake)
    yield state
    for name, old in saved.items():
        setattr(aw.keyboard, name, old)


@pytest.fixture
def clock(monkeypatch):
    now = {"t": 100.0}
    monkeypatch.setattr(aw.time, "monotonic", lambda: now["t"])
    return now


def _writer():
    w = AudioWriter.__new__(AudioWriter)
    w.hotkeys = {"quick": "F9", "translate": "F10"}
    w.toggle_recording = MagicMock()
    return w


def _release(kb):
    kb.pressed = False
    kb.watchers[-1](SimpleNamespace(event_type="up"))


def test_hotkeys_are_registered_on_key_down():
    add = aw.keyboard.add_hotkey     # the stub's own mock — see the kb fixture note
    add.reset_mock()
    w = _writer()
    w.activation_mode = "keyboard"
    w.activation_hooks = {}
    w.suppress_hotkeys = True
    w.press_and_talk()
    assert add.call_args_list
    assert all(c.kwargs["trigger_on_release"] is False for c in add.call_args_list)


def test_auto_repeat_of_a_held_key_toggles_once(kb, clock):
    w = _writer()
    w._on_hotkey("quick")
    for _ in range(20):            # repeat delay, then ~30ms repeats
        clock["t"] += 0.5
        w._on_hotkey("quick")
    w.toggle_recording.assert_called_once()


def test_release_then_press_toggles_again(kb, clock):
    w = _writer()
    w._on_hotkey("quick")
    _release(kb)
    kb.pressed = True
    clock["t"] += 0.15             # a double-tap-fast second press still counts
    w._on_hotkey("translate")
    assert w.toggle_recording.call_count == 2
    assert w._pending_action == "translate"
    # The first press's watcher was removed when the second one armed its own.
    assert kb.unhooked == [kb.watchers[0]]


def test_key_up_of_another_key_does_not_release(kb, clock):
    w = _writer()
    w._on_hotkey("quick")
    kb.watchers[-1](SimpleNamespace(event_type="up"))   # hotkey still pressed
    clock["t"] += 0.3
    w._on_hotkey("quick")
    w.toggle_recording.assert_called_once()


def test_missed_key_up_self_heals(kb, clock):
    w = _writer()
    w._on_hotkey("quick")
    clock["t"] += aw.HOTKEY_REPEAT_GAP + 0.1   # no repeats, no key-up seen
    w._on_hotkey("quick")
    assert w.toggle_recording.call_count == 2


# ---------- honest "recording" indicator ----------

def _announce_writer():
    w = AudioWriter.__new__(AudioWriter)
    w._session_gen = 1
    w.is_recording = True
    w._capture_announced = False
    w._capture_live = threading.Event()
    w.audio_queue = queue.Queue()
    w.ui_bridge = MagicMock()
    return w


def test_first_frame_flips_the_indicator():
    w = _announce_writer()
    w.audio_callback(np.zeros((160, 1), dtype=np.int16), 160, None, None)
    assert w._capture_live.is_set()
    w.ui_bridge.safe_emit_status.assert_not_called()   # no Qt on the audio thread

    w._announce_recording(1, w._capture_live)
    w.ui_bridge.safe_emit_status.assert_called_once_with("recording")
    assert w._capture_announced is True


def test_silent_device_still_announces_after_timeout(monkeypatch):
    monkeypatch.setattr(aw, "FIRST_FRAME_TIMEOUT", 0.01)
    w = _announce_writer()
    w._announce_recording(1, w._capture_live)
    w.ui_bridge.safe_emit_status.assert_called_once_with("recording")


@pytest.mark.parametrize("gen, recording", [(2, True), (1, False)])
def test_stale_or_stopped_session_is_not_announced(gen, recording):
    w = _announce_writer()
    w._capture_live.set()
    w._session_gen = gen
    w.is_recording = recording
    w._announce_recording(1, w._capture_live)
    w.ui_bridge.safe_emit_status.assert_not_called()
    assert w._capture_announced is False


def test_start_recording_does_not_claim_recording_before_audio(monkeypatch):
    w = AudioWriter.__new__(AudioWriter)
    w.transcription_backend = "openai"
    w._model_state = "ready"
    w._session_source = "batch"
    w.is_recording = False
    w._skip_next_paste = False
    w._pending_stop_timer = None
    w._session_gen = 0
    w.streaming = False
    w.fs = 16000
    w.ui_bridge = MagicMock()
    w.config = MagicMock()
    w.config.get.return_value = ""
    monkeypatch.setattr(aw, "ctypes", SimpleNamespace(
        windll=SimpleNamespace(user32=SimpleNamespace(
            GetForegroundWindow=lambda: 0))))
    monkeypatch.setattr(w, "_hwnd_is_own_process", lambda hwnd: False)
    monkeypatch.setattr(aw, "sd", SimpleNamespace(InputStream=MagicMock()))
    monkeypatch.setattr(aw.threading, "Thread", MagicMock())   # announcer never runs
    monkeypatch.setattr(aw.threading, "Timer", MagicMock())

    w.start_recording()

    assert w.is_recording is True
    assert w._capture_announced is False
    w.ui_bridge.safe_emit_status.assert_not_called()


# ---------- pre-opened (unstarted) input stream ----------

def _standby_writer(monkeypatch, device=""):
    """Bare writer whose 'opened' streams are MagicMocks we can inspect.

    The standby thread is run inline: these tests are about the hand-over
    logic, not about which thread does the (blocking) device open.
    """
    w = AudioWriter.__new__(AudioWriter)
    w._standby = None
    w._standby_lock = threading.Lock()
    w.is_recording = False
    w.fs = 16000
    w.config = MagicMock()
    w.config.get.side_effect = lambda key, default="": device
    opened = []

    def _open(index):
        stream = MagicMock(name=f"stream{len(opened)}")
        opened.append(stream)
        return stream

    monkeypatch.setattr(w, "_open_input_stream", _open)
    monkeypatch.setattr(aw, "resolve_input_device", lambda cfg: None)
    monkeypatch.setattr(aw, "PREOPEN_INPUT_STREAM", True)
    monkeypatch.setattr(
        w, "_prepare_standby_stream", lambda: w._open_standby())
    return w, opened


def test_standby_is_opened_but_never_started(monkeypatch):
    w, opened = _standby_writer(monkeypatch)
    w._prepare_standby_stream()
    assert len(opened) == 1
    opened[0].start.assert_not_called()      # the whole point: no capture
    w._prepare_standby_stream()              # idempotent for the same device
    assert len(opened) == 1


def test_take_standby_hands_over_matching_stream_once(monkeypatch):
    w, opened = _standby_writer(monkeypatch)
    w._prepare_standby_stream()
    assert w._take_standby("") is opened[0]
    assert w._take_standby("") is None       # consumed


def test_standby_for_another_device_is_closed_not_used(monkeypatch):
    w, opened = _standby_writer(monkeypatch)
    w._prepare_standby_stream()
    assert w._take_standby("name::Other mic") is None
    opened[0].close.assert_called_once()


def test_device_change_swaps_the_standby(monkeypatch):
    w, opened = _standby_writer(monkeypatch)
    w._prepare_standby_stream()
    w.config.get.side_effect = lambda key, default="": "name::Other mic"
    w._prepare_standby_stream()
    assert len(opened) == 2
    opened[0].close.assert_called_once()
    assert w._standby == (opened[1], "name::Other mic")


def test_no_standby_is_opened_while_recording(monkeypatch):
    w, opened = _standby_writer(monkeypatch)
    w.is_recording = True
    w._prepare_standby_stream()
    assert opened == [] and w._standby is None


def test_drop_standby_closes_it(monkeypatch):
    w, opened = _standby_writer(monkeypatch)
    w._prepare_standby_stream()
    w._drop_standby()
    opened[0].close.assert_called_once()
    assert w._standby is None


def test_stale_standby_falls_back_to_a_fresh_open(monkeypatch):
    """A pre-opened stream whose device vanished must not break the hotkey."""
    w, opened = _standby_writer(monkeypatch)
    w._prepare_standby_stream()
    opened[0].start.side_effect = RuntimeError("device unplugged")
    w.transcription_backend = "openai"
    w._model_state = "ready"
    w._session_source = "batch"
    w._skip_next_paste = False
    w._pending_stop_timer = None
    w._session_gen = 0
    w.streaming = False
    w.ui_bridge = MagicMock()
    monkeypatch.setattr(aw, "ctypes", SimpleNamespace(
        windll=SimpleNamespace(user32=SimpleNamespace(
            GetForegroundWindow=lambda: 0))))
    monkeypatch.setattr(w, "_hwnd_is_own_process", lambda hwnd: False)
    monkeypatch.setattr(aw.threading, "Thread", MagicMock())
    monkeypatch.setattr(aw.threading, "Timer", MagicMock())

    w.start_recording()

    assert w.is_recording is True
    opened[0].close.assert_called_once()
    assert w.stream is opened[1]
    opened[1].start.assert_called_once()

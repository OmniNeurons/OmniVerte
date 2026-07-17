# file: tests/test_rec_indicator.py

"""State-machine tests for the floating recording pill (ui/rec_indicator.py).

The widget is painted by hand, so there's nothing to snapshot; what matters — and
what regresses silently — is the mode it *chooses* for a given pair of axes plus
the mic level, especially the silence→no-signal flip that is the whole reason the
pill exists. Time is injected via ``_clock`` so the 1.5 s silence window is a
deterministic arithmetic test, not a sleep.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication

from ui.rec_indicator import (
    BAR_COUNT,
    PROP_FRAMES,
    SILENCE_SEC,
    RecordingIndicator,
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def widget(qapp):
    w = RecordingIndicator()
    # Deterministic, injectable clock; tests advance it explicitly.
    w._t = 1000.0
    w._clock = lambda: w._t
    yield w
    w._stop_anim()
    w.deleteLater()


# ---------- mode precedence ----------

def test_idle_hides(widget):
    assert widget._active_mode() is None


def test_disabled_never_shows(widget):
    widget.on_status("recording")
    widget.set_enabled(False)
    assert widget._active_mode() is None


def test_loading_overrides_session(widget):
    widget.on_status("recording")
    widget.on_model_state("loading")
    assert widget._active_mode() == "loading"


def test_processing_mode(widget):
    widget.on_status("processing")
    assert widget._active_mode() == "processing"


def test_failed_and_ready_hide(widget):
    widget.on_status("idle")
    for state in ("failed", "ready"):
        widget.on_model_state(state)
        assert widget._active_mode() is None


# ---------- recording ↔ no-signal (the point of the redesign) ----------

def test_fresh_recording_is_listening_not_silent(widget):
    widget.on_status("recording")  # grants the grace period at _clock() = now
    assert widget._active_mode() == "recording"


def test_sustained_silence_flips_to_nosignal(widget):
    widget.on_status("recording")
    widget._t += SILENCE_SEC + 0.1
    assert widget._active_mode() == "nosignal"


def test_signal_returns_to_listening(widget):
    widget.on_status("recording")
    widget._t += SILENCE_SEC + 0.1
    assert widget._active_mode() == "nosignal"
    widget.on_audio_level(0.5)  # loud sample refreshes the last-signal stamp
    assert widget._active_mode() == "recording"


def test_quiet_sample_does_not_reset_silence(widget):
    widget.on_status("recording")
    widget._t += SILENCE_SEC + 0.1
    widget.on_audio_level(0.0)  # below SIGNAL_EPS — must not count as signal
    assert widget._active_mode() == "nosignal"


# ---------- level → equalizer mapping ----------

def test_level_history_is_bounded(widget):
    for _ in range(BAR_COUNT + 10):
        widget.on_audio_level(0.1)
    assert len(widget._levels) == BAR_COUNT


def test_louder_maps_higher(widget):
    widget.on_audio_level(0.2)
    loud = widget._levels[-1]
    widget.on_audio_level(0.02)
    quiet = widget._levels[-1]
    widget.on_audio_level(0.0)
    silent = widget._levels[-1]
    assert loud > quiet > silent
    assert silent == 0.0
    assert loud <= 1.0  # mapping is clamped


def test_new_recording_clears_history(widget):
    for _ in range(BAR_COUNT):
        widget.on_audio_level(0.9)
    widget.on_status("recording")
    assert set(widget._levels) == {0.0}


# ---------- level polling (timer pulls from level_provider) ----------

def test_tick_polls_provider_only_while_recording(qapp):
    """The animation tick reads the live level from level_provider — but only in
    the recording state, so silence detection isn't reset outside a session."""
    level = {"v": 0.0}
    w = RecordingIndicator(level_provider=lambda: level["v"])
    w._t = 1000.0
    w._clock = lambda: w._t
    try:
        w.on_status("recording")
        # Silence: provider yields ~0, so ticks past the window flip to no-signal.
        w._t += SILENCE_SEC + 0.1
        w._tick()
        assert w._active_mode() == "nosignal"
        # A loud sample on the next tick refreshes the signal stamp → recording.
        level["v"] = 0.5
        w._tick()
        assert w._active_mode() == "recording"
        # Leaving recording: the provider is no longer polled (would otherwise
        # keep resetting the stamp). Prove it by checking a processing tick is inert.
        w.on_status("processing")
        stamp = w._last_signal_ts
        level["v"] = 0.9
        w._tick()
        assert w._last_signal_ts == stamp
    finally:
        w._stop_anim()
        w.deleteLater()


# ---------- propeller (processing / loading) ----------

def test_propeller_frames_are_nonempty(widget):
    assert len(widget._prop_frames) == PROP_FRAMES
    # Every rotation step lights at least a blade's worth of cells.
    assert all(len(frame) >= 3 for frame in widget._prop_frames)


def test_propeller_frames_differ_across_rotation(widget):
    # A rotating bar must not paint the same cells every frame (that would read
    # as a static cross, not a spinning propeller).
    as_sets = [frozenset(f) for f in widget._prop_frames]
    assert len(set(as_sets)) > 1

# file: services/ui_bridge.py

"""
Cross-thread bridge between non-UI subsystems (audio, keyboard hooks, pystray)
and Qt UI components. Qt signals auto-marshal to the main thread when emitter
and receiver live in different threads, which is what we need everywhere except
inside Qt itself.

Status values are canonical strings:
  - "idle"        — no recording, no processing
  - "recording"   — audio is being captured
  - "processing"  — recording stopped, transcription / correction in flight
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class UIBridge(QObject):
    """Single bus carrying everything UI components subscribe to."""

    # Final corrected text (after OpenAI grammar pass, if any).
    transcript_ready = Signal(str)

    # Raw transcript from Whisper before correction. Currently unused by the
    # main window — reserved for future "show raw" UX.
    raw_transcript_ready = Signal(str)

    # Canonical status string: "idle" / "recording" / "processing".
    status_changed = Signal(str)

    # Backend model readiness — an axis ORTHOGONAL to status_changed. Values:
    # "loading" / "ready" / "failed". Kept on its own signal (not folded into
    # status_changed) because the streaming_transcribe loop spams status_changed
    # hundreds of times/sec and would clobber a "loading" value. UI sinks combine
    # the two axes with a simple precedence: loading/failed paint over the
    # idle/ready baseline; recording/processing only happen once the model is
    # ready (guaranteed by the start_recording guard), so the axes never collide.
    model_state_changed = Signal(str)

    # Tray menu → "Show window" — main window connects to this.
    show_window_requested = Signal()

    # Tray menu / main-window gear → "Settings". A single handler in the main
    # process owns one SettingsWindow instance and raises it on repeat requests,
    # so no matter how many times (or from where) this fires, at most one window
    # exists. Replaces the old out-of-process `--settings` subprocess spawn.
    settings_requested = Signal()

    # Main-window tier badge → open Settings directly on the License page. Same
    # single-window handler as settings_requested, just deep-linked to a page.
    license_requested = Signal()

    # Emitted after the settings window saves. Listeners (tray, main window)
    # reload config-driven labels live — no app restart needed.
    settings_saved = Signal()

    # Emitted after a license is activated/cleared (license settings page) so the
    # entitlement cache has been refreshed. Listeners re-apply gates live: the
    # main-window tier badge, the glossary term cap on the voice + manual paths.
    entitlement_changed = Signal()

    # Theme toggled from the main-window header. Value is the new theme name
    # ("light" / "dark"). Lets an open settings window repaint itself live.
    theme_changed = Signal(str)

    # UI language switched (from the settings save). Value is the new locale
    # code ("en" / "ru"). Emitted only on an ACTUAL change and only AFTER the
    # i18n catalog's locale has been set, so every sink can simply call t() and
    # re-render. Unlike theme_changed, no settings window listens: a settings
    # window is destroyed on save and rebuilt fresh, so it is replaced rather
    # than retranslated. The long-lived main window is the one that listens.
    language_changed = Signal(str)

    # Tray menu → "Exit" — app.quit() handler connects to this.
    quit_requested = Signal()

    # Tray menu → "Show / Hide floating indicator" — value is the new enabled state.
    floating_indicator_toggled = Signal(bool)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._last_status: str | None = None
        self._last_model_state: str | None = None

        # Live mic level [0..1]. Written by the realtime audio callback, polled by
        # the indicator's timer. A plain float, NOT a Qt signal — emitting
        # cross-thread signals from the audio callback ~25×/sec starved the
        # keyboard hook thread past the OS LowLevelHooks timeout and dropped
        # hotkeys. A bare store is GIL-atomic, allocation-free and touches no Qt
        # machinery.
        self.audio_level: float = 0.0

    def safe_emit_status(self, status: str) -> None:
        """
        Emit status_changed only when value actually changes. AudioWriter's
        streaming_transcribe loop sets the status hundreds of times per second
        with the same value — without dedup the UI gets flooded.
        """
        if status == self._last_status:
            return
        self._last_status = status
        self.status_changed.emit(status)

    def safe_emit_model_state(self, state: str, force: bool = False) -> None:
        """
        Emit model_state_changed, deduped like safe_emit_status. ``force=True``
        re-emits even when the value is unchanged — used when the user pokes the
        hotkey while the model is still loading, so the indicator re-asserts the
        "loading"/"failed" cue instead of silently swallowing a deduped repeat.
        """
        if state == self._last_model_state and not force:
            return
        self._last_model_state = state
        self.model_state_changed.emit(state)

    def last_model_state(self) -> str | None:
        """Last emitted model state, so a sink connected late can sync itself."""
        return self._last_model_state

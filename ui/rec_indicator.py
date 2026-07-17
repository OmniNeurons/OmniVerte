# file: ui/rec_indicator.py

"""
Small floating "pill" that signals recording state — a rounded dark capsule with
a status dot, a label, and a right-hand visualization, drawn to match the
template in ``data/widjet.jpg``.

Two visualizations, one per phase, both confined to the same small right-hand
region so the pill's shape and weight stay constant:
  - **recording** — a scrolling equalizer of the live microphone level (a rolling
    history of the amplitude, newest bar at the right). If the level stays near
    zero for ``SILENCE_SEC`` the pill flips to a **no-signal** state (flat bars,
    pulsing red dot, "No signal" text). This is the whole point of the redesign:
    a dead or switched-away microphone used to produce silence with no visible
    cue, so it was impossible to tell recording from a hang.
  - **processing / loading** — a low-res, blocky spinning propeller in that same
    region, a calm indeterminate "working" cue. Grey, never the dot's accent
    colour: the accent lives in the status dot, the visualization stays neutral.
    (Earlier this ran a bright segment around the whole contour; that read as
    garish and its rounded route didn't sit on the near-rectangular body.)

Qt-native, painted entirely in ``paintEvent`` (no child widgets), which keeps it
click-through and cheap. Session/model state arrives via UIBridge signals, so it
behaves identically regardless of the emit thread:
  - ``status_changed``       → :meth:`on_status`        (session axis)
  - ``model_state_changed``  → :meth:`on_model_state`   (model axis)
  - ``language_changed``     → :meth:`on_language_changed`
  - ``floating_indicator_toggled`` → :meth:`set_enabled`

The live mic level is NOT pushed — it is **polled** each animation tick from
``level_provider`` (wired to ``UIBridge.audio_level``, a plain field the realtime
audio callback writes). This deliberately keeps the high-priority PortAudio thread
off Qt: pushing a cross-thread signal ~25×/sec from it starved the keyboard hook
past the OS LowLevelHooks timeout and dropped hotkeys.

Visibility can be disabled by the user via the tray's "Show floating indicator"
toggle (persisted as SHOW_FLOATING_INDICATOR in config_store).
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, Slot
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QWidget

from i18n import t

logger = logging.getLogger(__name__)

# ---- palette ----
BG_COLOR = QColor(24, 24, 27, 235)          # dark capsule, slightly translucent
BORDER_COLOR = QColor(255, 255, 255, 28)    # faint outline for definition
TEXT_COLOR = QColor(236, 236, 240)
TEXT_ALERT_COLOR = QColor(244, 120, 120)    # "no signal" text
BAR_COLOR = QColor(224, 224, 230)
PROP_COLOR = QColor(150, 150, 158)          # neutral grey propeller

# Status → dot color.
DOT_RECORDING = QColor(230, 70, 70)
DOT_NOSIGNAL = QColor(244, 60, 60)          # pulsed via alpha in the timer
DOT_PROCESSING = QColor(235, 200, 50)
DOT_LOADING = QColor(139, 92, 246)          # violet, matches STATUS_DOT_LOADING

# ---- layout (logical px) ----
WIDTH = 208
HEIGHT = 44
PAD = 14
DOT_CX = 20.0
DOT_R = 5.0
TEXT_X = 34.0
VIZ_W = 44.0                                 # right-hand visualization region
VIZ_RIGHT = WIDTH - PAD                       # 194
VIZ_LEFT = VIZ_RIGHT - VIZ_W                  # 150
TEXT_GAP = 12.0                               # breathing room before the viz
TEXT_RIGHT = VIZ_LEFT - TEXT_GAP              # 138
TEXT_W = TEXT_RIGHT - TEXT_X                  # 104

# ---- equalizer / level mapping ----
BAR_COUNT = 12
# rms (≈0.02–0.2 for speech) → bar fill in [0, 1]. Gamma < 1 lifts quiet speech
# so it's visible; gain scales the typical range up to near-full height.
LEVEL_GAMMA = 0.5
LEVEL_GAIN = 3.2
SIGNAL_EPS = 0.006      # raw rms above this counts as "there is sound"
SILENCE_SEC = 1.5       # recording silence past this → no-signal state

# ---- propeller (processing / loading) ----
PROP_CELLS = 7          # grid is PROP_CELLS × PROP_CELLS — deliberately low-res
PROP_CELL_PX = 4.5
PROP_GAP = 0.9          # inter-cell gap → blocky, pixelated look
PROP_FRAMES = 12        # rotation steps over a half turn (2-blade symmetry)
PROP_TICKS_PER_FRAME = 2  # advance one frame every N timer ticks → mechanical

# ---- animation ----
TICK_MS = 33            # ~30 fps for the propeller + no-signal dot pulse
PHASE_STEP = 0.016      # dot-pulse phase advanced per tick


class RecordingIndicator(QWidget):
    """Frameless, always-on-top, click-through status pill at top-left of screen."""

    POS_X = 20
    POS_Y = 80

    def __init__(self, level_provider=None):
        # Live mic level source, polled each tick while recording. A callable
        # returning the current normalized RMS [0..1] — wired to
        # UIBridge.audio_level, a plain field the audio callback writes. Polling
        # (not a pushed Qt signal) is what keeps the realtime audio thread off Qt
        # entirely; see the field's comment in services/ui_bridge.py.
        self._level_provider = level_provider or (lambda: 0.0)

        flags = (
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
            | Qt.WindowTransparentForInput
        )
        super().__init__(None, flags)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(WIDTH, HEIGHT)
        self.move(self.POS_X, self.POS_Y)

        self._enabled = True  # respects user toggle from tray
        # Two orthogonal axes, combined in _active_mode(): the voice-session
        # status and the backend model state. Model "loading" overrides.
        self._session_status = "idle"
        self._model_state = "ready"

        # Live equalizer history: mapped level per bar, newest appended right.
        self._levels: deque[float] = deque([0.0] * BAR_COUNT, maxlen=BAR_COUNT)
        # Clock is an attribute so tests can inject a fake monotonic source.
        self._clock = time.monotonic
        self._last_signal_ts = 0.0  # last time raw rms exceeded SIGNAL_EPS
        self._phase = 0.0           # dot-pulse phase [0, 1)
        self._ticks = 0             # timer tick counter → propeller frame

        self._font = QFont()
        self._font.setPointSize(8)
        self._font.setWeight(QFont.DemiBold)
        self._font.setCapitalization(QFont.AllUppercase)
        self._font.setLetterSpacing(QFont.AbsoluteSpacing, 0.5)

        # Precomputed propeller frames (lists of lit (col, row) cells).
        self._prop_frames = self._build_propeller_frames()

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        # Start hidden — only shown when a mode becomes active.

    # ---------- propeller geometry ----------

    @staticmethod
    def _build_propeller_frames() -> list[list[tuple[int, int]]]:
        """A rotating two-blade bar on a small square grid, one cell-set per
        rotation step. Precomputed once — painting just picks a frame."""
        n = PROP_CELLS
        c0 = (n - 1) / 2.0
        radius = c0 + 0.5
        frames: list[list[tuple[int, int]]] = []
        for k in range(PROP_FRAMES):
            ang = math.pi * k / PROP_FRAMES
            dx, dy = math.cos(ang), math.sin(ang)
            cells: list[tuple[int, int]] = []
            for row in range(n):
                for col in range(n):
                    x, y = col - c0, row - c0
                    if math.hypot(x, y) > radius:
                        continue
                    # Perpendicular distance to the blade line through center.
                    if abs(x * dy - y * dx) <= 0.6:
                        cells.append((col, row))
            frames.append(cells)
        return frames

    # ---------- toggling visibility from tray ----------

    def set_enabled(self, enabled: bool) -> None:
        """User-visible on/off toggle. When off, never shows regardless of status."""
        self._enabled = enabled
        if not enabled:
            self._stop_anim()
            self.hide()
        else:
            self._sync()

    # ---------- signal slots ----------

    @Slot(str)
    def on_status(self, status: str) -> None:
        """Connect to UIBridge.status_changed (session axis)."""
        if status == "recording" and self._session_status != "recording":
            # Fresh recording: grant the grace period and start the waveform flat
            # so a lingering old level can't flash a stale bar.
            self._last_signal_ts = self._clock()
            self._levels = deque([0.0] * BAR_COUNT, maxlen=BAR_COUNT)
        self._session_status = status
        self._sync()

    @Slot(str)
    def on_model_state(self, state: str) -> None:
        """Connect to UIBridge.model_state_changed (model axis)."""
        self._model_state = state
        self._sync()

    def _ingest_level(self, rms: float) -> None:
        """Fold one raw RMS sample [0, 1] into the equalizer: map it to a bar
        height, push it into the rolling history, and refresh the last-signal
        timestamp that drives silence detection. No repaint — the caller (the
        animation tick) syncs once per frame."""
        rms = max(0.0, rms)
        if rms > SIGNAL_EPS:
            self._last_signal_ts = self._clock()
        mapped = min(1.0, (rms ** LEVEL_GAMMA) * LEVEL_GAIN)
        self._levels.append(mapped)

    def on_audio_level(self, rms: float) -> None:
        """Thin push wrapper kept for tests / callers that feed a level directly;
        no longer wired to any signal (the widget polls _level_provider instead)."""
        self._ingest_level(rms)
        # Only paints when a mode is active; a stray level while idle is dropped.
        self._sync()

    @Slot()
    def on_language_changed(self, *_args) -> None:
        """Connect to UIBridge.language_changed — relabel the pill in place."""
        if self.isVisible():
            self.update()

    # ---------- state machine ----------

    def _is_silent(self) -> bool:
        return (self._clock() - self._last_signal_ts) > SILENCE_SEC

    def _active_mode(self) -> str | None:
        """The mode to paint, or None to hide. Same precedence as the old dot:
        model "loading" wins; then recording (or its no-signal variant); then
        processing; everything else (idle / ready / failed) hides."""
        if not self._enabled:
            return None
        if self._model_state == "loading":
            return "loading"
        if self._session_status == "recording":
            return "nosignal" if self._is_silent() else "recording"
        if self._session_status == "processing":
            return "processing"
        return None

    def _sync(self) -> None:
        """Show/hide + arm/stop the animation timer for the current mode, repaint."""
        mode = self._active_mode()
        if mode is None:
            self._stop_anim()
            if self.isVisible():
                self.hide()
            return
        if not self.isVisible():
            self.show()
        self._start_anim()
        self.update()

    def _start_anim(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def _stop_anim(self) -> None:
        if self._timer.isActive():
            self._timer.stop()

    def _tick(self) -> None:
        """Advance animation phase and re-evaluate the mode (recording→no-signal
        happens purely from elapsed time, so the timer must catch it)."""
        self._phase = (self._phase + PHASE_STEP) % 1.0
        self._ticks += 1
        # Poll the live mic level only while recording — outside a recording the
        # provider is stale/zero and would keep resetting silence detection.
        if self._session_status == "recording":
            self._ingest_level(self._level_provider())
        self._sync()

    # ---------- painting ----------

    def paintEvent(self, _event):
        mode = self._active_mode()
        if mode is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Capsule background + faint outline.
        radius = HEIGHT / 2
        body = QRectF(1, 1, WIDTH - 2, HEIGHT - 2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(BG_COLOR)
        painter.drawRoundedRect(body, radius - 1, radius - 1)
        painter.setPen(QPen(BORDER_COLOR, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(body, radius - 1, radius - 1)

        self._paint_dot(painter, mode)
        self._paint_label(painter, mode)
        if mode == "recording" or mode == "nosignal":
            self._paint_equalizer(painter)
        else:  # processing / loading
            self._paint_propeller(painter)

    def _dot_color(self, mode: str) -> QColor:
        if mode == "loading":
            return DOT_LOADING
        if mode == "processing":
            return DOT_PROCESSING
        if mode == "nosignal":
            # Pulse the alpha so a dead mic reads as an alarm, not a steady light.
            c = QColor(DOT_NOSIGNAL)
            pulse = 0.55 + 0.45 * abs((self._phase * 2.0) - 1.0)
            c.setAlphaF(pulse)
            return c
        return DOT_RECORDING

    def _paint_dot(self, painter: QPainter, mode: str) -> None:
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._dot_color(mode))
        painter.drawEllipse(QPointF(DOT_CX, HEIGHT / 2), DOT_R, DOT_R)

    def _label_text(self, mode: str) -> str:
        key = {
            "loading": "indicator.loading",
            "processing": "indicator.processing",
            "nosignal": "indicator.nosignal",
            "recording": "indicator.recording",
        }[mode]
        return t(key)

    def _paint_label(self, painter: QPainter, mode: str) -> None:
        text = self._label_text(mode)
        # Auto-fit: shrink the font until the word fits the text column, so long
        # translations ("TRANSCRIPTION", "TRASCRIZIONE") never clip a final glyph.
        font = QFont(self._font)
        fm = QFontMetricsF(font)
        adv = fm.horizontalAdvance(text)
        if adv > TEXT_W and adv > 0:
            font.setPointSizeF(max(6.5, font.pointSizeF() * (TEXT_W / adv)))
        painter.setFont(font)
        painter.setPen(TEXT_ALERT_COLOR if mode == "nosignal" else TEXT_COLOR)
        rect = QRectF(TEXT_X, 0, TEXT_W, HEIGHT)
        painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, text)

    def _paint_equalizer(self, painter: QPainter) -> None:
        n = BAR_COUNT
        gap = 1.7
        bw = (VIZ_W - (n - 1) * gap) / n
        max_h = HEIGHT - 18.0
        min_h = 2.0
        cy = HEIGHT / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(BAR_COLOR)
        for i, level in enumerate(self._levels):
            h = min_h + (max_h - min_h) * max(0.0, min(1.0, level))
            x = VIZ_LEFT + i * (bw + gap)
            painter.drawRoundedRect(QRectF(x, cy - h / 2, bw, h), bw / 2, bw / 2)

    def _paint_propeller(self, painter: QPainter) -> None:
        """Low-res spinning propeller, centered in the same small viz region."""
        frame = self._prop_frames[(self._ticks // PROP_TICKS_PER_FRAME) % PROP_FRAMES]
        grid = PROP_CELLS * PROP_CELL_PX
        ox = VIZ_LEFT + (VIZ_W - grid) / 2
        oy = (HEIGHT - grid) / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(PROP_COLOR)
        for col, row in frame:
            x = ox + col * PROP_CELL_PX
            y = oy + row * PROP_CELL_PX
            painter.drawRect(QRectF(x, y, PROP_CELL_PX - PROP_GAP, PROP_CELL_PX - PROP_GAP))

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

Provider trouble is shown here too, in yellow, because this is where the user is
looking while dictating — and because a click-through, focus-less overlay is the
one surface whose text can never end up pasted into their document:
  - a **notice** — one alert (credits ran out, key rejected, switched to a
    fallback provider…) under the status row. It stays for the rest of the
    session it happened in and ``NOTICE_SEC`` after that session ends, so it is
    still on screen when the text lands; with no session running the pill shows
    alone as an "Attention" card for the same ``NOTICE_SEC``.
  - a **banner** — while recordings run on a fallback provider, the pill is
    expanded downwards with a "<primary> unavailable — using <fallback>" line.
In both cases the widget grows (wider + taller) and gets a yellow outline; with
neither it is the original compact capsule.

Qt-native, painted entirely in ``paintEvent`` (no child widgets), which keeps it
click-through and cheap. Session/model state arrives via UIBridge signals, so it
behaves identically regardless of the emit thread:
  - ``status_changed``       → :meth:`on_status`        (session axis)
  - ``model_state_changed``  → :meth:`on_model_state`   (model axis)
  - ``language_changed``     → :meth:`on_language_changed`
  - ``floating_indicator_toggled`` → :meth:`set_enabled`
  - ``api_error``            → :meth:`on_api_error`          (notice)
  - ``provider_failover``    → :meth:`on_provider_failover`  (notice + banner)
  - ``quick_fallback``       → :meth:`on_quick_fallback`     (notice)
  - ``provider_degraded``    → :meth:`on_provider_degraded`  (banner; new session)

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

# Provider alerts (notice / degraded banner): one bright yellow for the text,
# the "Attention" dot and the outline of the expanded pill. Deliberately louder
# than DOT_PROCESSING's muted yellow — this is the thing that must be noticed.
ALERT_YELLOW = QColor(250, 204, 21)
ALERT_BORDER = QColor(250, 204, 21, 150)

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

# ---- expanded form (alert text under the status row) ----
# WIDTH/HEIGHT above describe the compact capsule and the status ROW of the
# expanded form alike; with alert text the widget is WIDTH_WIDE wide and grows
# down by the wrapped text's height. The row's right-hand viz follows the
# current width (see _viz_left), so it stays against the right edge.
WIDTH_WIDE = 300
NOTE_TOP = HEIGHT - 7.0                       # text starts just under the row
NOTE_BOTTOM = 13.0                            # padding below the last line
NOTICE_SEC = 5.0                              # notice lifetime once no session runs
_SESSION_ACTIVE = ("recording", "processing")

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

        # Alert text is a sentence, not a one-word status: normal case, a touch
        # larger, no letter-spacing — uppercase small caps would be unreadable.
        self._note_font = QFont()
        self._note_font.setPointSize(9)
        self._note_font.setWeight(QFont.Medium)

        # Provider alerts. Both hold CODES/labels, not rendered text, so a UI
        # language switch re-renders them (text is built in _alert_text()).
        #   _notice: ("api", context, kind, provider)
        #          | ("failover", failed, kind, fallback)
        #          | ("quick", engine, kind, serving) | None
        #   _banner: (failed, fallback) | None — recordings run on a fallback
        self._notice: tuple | None = None
        self._notice_deadline = 0.0   # only meaningful while no session runs
        self._banner: tuple[str, str] | None = None
        # (text, (w, h)) of the last measured alert — word-wrap measuring every
        # 33 ms tick would be wasted work, the text changes a few times a day.
        self._size_cache: tuple[str, tuple[int, int]] = ("", (WIDTH, HEIGHT))

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
        # Session just ended (text pasted, or it failed): a notice raised during
        # it gets its full NOTICE_SEC from NOW — the moment the user's eyes come
        # back from the text — not from whenever the provider failed mid-session.
        if (status not in _SESSION_ACTIVE
                and self._session_status in _SESSION_ACTIVE
                and self._notice is not None):
            self._notice_deadline = self._clock() + NOTICE_SEC
        self._session_status = status
        self._sync()

    # ---------- provider alerts ----------

    def _set_notice(self, notice: tuple) -> None:
        self._notice = notice
        self._notice_deadline = self._clock() + NOTICE_SEC
        self._sync()

    @Slot(str, str, str)
    def on_api_error(self, context: str, kind: str, provider: str) -> None:
        """Connect to UIBridge.api_error — one API failure as a yellow notice."""
        self._set_notice(("api", context, kind, provider))

    @Slot(str, str, str)
    def on_provider_failover(self, failed: str, kind: str, fallback: str) -> None:
        """Connect to UIBridge.provider_failover — the primary provider was
        dropped mid-session. Notice now; and the banner from now on, since the
        rest of THIS session already runs on the fallback (later sessions get
        theirs from provider_degraded)."""
        self._banner = (failed, fallback)
        self._set_notice(("failover", failed, kind, fallback))

    @Slot(str, str, str)
    def on_quick_fallback(self, engine: str, kind: str, serving: str) -> None:
        """Connect to UIBridge.quick_fallback — the live session failed, the
        text came through ``serving`` instead. Arrives after (and replaces) a
        failover notice raised by the same replay: this one names both the
        failed engine and who served, so nothing is lost."""
        self._set_notice(("quick", engine, kind, serving))

    @Slot(str, str)
    def on_provider_degraded(self, failed: str, fallback: str) -> None:
        """Connect to UIBridge.provider_degraded — emitted once per recording
        start. Sets or clears (both empty) the banner, and doubles as the "new
        session" marker that retires the previous session's notice."""
        self._notice = None
        self._banner = (failed, fallback) if failed else None
        self._sync()

    def _alert_text(self, mode: str | None) -> str:
        """The yellow text for ``mode`` ("" = compact pill). A notice outranks
        the banner: it is the news, the banner is the standing condition.
        Model loading shows neither — it is not a provider matter."""
        if mode is None or mode == "loading":
            return ""
        # Lazy import, like the tray's sink: keeps the provider SDK imports out
        # of this widget's import path.
        from services.api_errors import (
            degraded_text, failover_text, notice_text, quick_fallback_text,
        )

        if self._notice is not None:
            tag, *args = self._notice
            render = {"failover": failover_text, "quick": quick_fallback_text}
            return render.get(tag, notice_text)(*args)
        if self._banner is not None:
            return degraded_text(*self._banner)
        return ""

    def _size_for(self, text: str) -> tuple[int, int]:
        """Widget size for the given alert text (compact when empty)."""
        if not text:
            return (WIDTH, HEIGHT)
        if self._size_cache[0] != text:
            fm = QFontMetricsF(self._note_font)
            box = fm.boundingRect(
                QRectF(0, 0, WIDTH_WIDE - 2 * PAD, 1000),
                int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop), text,
            )
            h = int(math.ceil(NOTE_TOP + box.height() + NOTE_BOTTOM))
            self._size_cache = (text, (WIDTH_WIDE, h))
        return self._size_cache[1]

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
        # No session running: a still-fresh notice keeps the pill up on its own.
        if self._notice is not None and self._clock() < self._notice_deadline:
            return "notice"
        return None

    def _sync(self) -> None:
        """Show/hide + arm/stop the animation timer for the current mode, resize
        for the alert text, repaint."""
        mode = self._active_mode()
        if mode is None:
            # Retire a notice that has had its time, so it cannot resurface
            # under the next session's status row.
            if (self._notice is not None
                    and self._session_status not in _SESSION_ACTIVE
                    and self._clock() >= self._notice_deadline):
                self._notice = None
            self._stop_anim()
            if self.isVisible():
                self.hide()
            return
        # Runs on the GUI thread only (signal slots + the widget's own timer).
        size = self._size_for(self._alert_text(mode))
        if size != (self.width(), self.height()):
            self.setFixedSize(*size)
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

        note = self._alert_text(mode)

        # Background + outline. The corner radius is the capsule's in both
        # forms: compact it yields the capsule, expanded a card with the same
        # rounded corners — so growing downwards reads as the same object.
        # The outline turns yellow whenever alert text is shown.
        radius = HEIGHT / 2
        body = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(BG_COLOR)
        painter.drawRoundedRect(body, radius - 1, radius - 1)
        painter.setPen(QPen(ALERT_BORDER if note else BORDER_COLOR, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(body, radius - 1, radius - 1)

        self._paint_dot(painter, mode)
        self._paint_label(painter, mode)
        if mode == "recording" or mode == "nosignal":
            self._paint_equalizer(painter)
        elif mode != "notice":  # processing / loading; a bare notice has no viz
            self._paint_propeller(painter)
        if note:
            self._paint_note(painter, note)

    def _viz_left(self) -> float:
        """Left edge of the right-hand viz region at the CURRENT width (equals
        the module's VIZ_LEFT while compact)."""
        return self.width() - PAD - VIZ_W

    def _paint_note(self, painter: QPainter, text: str) -> None:
        painter.setFont(self._note_font)
        painter.setPen(ALERT_YELLOW)
        rect = QRectF(PAD, NOTE_TOP, self.width() - 2 * PAD, self.height() - NOTE_TOP)
        painter.drawText(rect, int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop), text)

    def _dot_color(self, mode: str) -> QColor:
        if mode == "loading":
            return DOT_LOADING
        if mode == "notice":
            # Same alarm pulse as no-signal, in the alert yellow.
            c = QColor(ALERT_YELLOW)
            c.setAlphaF(0.55 + 0.45 * abs((self._phase * 2.0) - 1.0))
            return c
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
            "notice": "indicator.attention",
        }[mode]
        return t(key)

    def _paint_label(self, painter: QPainter, mode: str) -> None:
        text = self._label_text(mode)
        # Text column at the current width; a bare notice has no viz to leave
        # room for, so its label may run to the right padding.
        if mode == "notice":
            text_w = self.width() - PAD - TEXT_X
        else:
            text_w = self._viz_left() - TEXT_GAP - TEXT_X
        # Auto-fit: shrink the font until the word fits the text column, so long
        # translations ("TRANSCRIPTION", "TRASCRIZIONE") never clip a final glyph.
        font = QFont(self._font)
        fm = QFontMetricsF(font)
        adv = fm.horizontalAdvance(text)
        if adv > text_w and adv > 0:
            font.setPointSizeF(max(6.5, font.pointSizeF() * (text_w / adv)))
        painter.setFont(font)
        if mode == "notice":
            painter.setPen(ALERT_YELLOW)
        else:
            painter.setPen(TEXT_ALERT_COLOR if mode == "nosignal" else TEXT_COLOR)
        rect = QRectF(TEXT_X, 0, text_w, HEIGHT)
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
        viz_left = self._viz_left()
        for i, level in enumerate(self._levels):
            h = min_h + (max_h - min_h) * max(0.0, min(1.0, level))
            x = viz_left + i * (bw + gap)
            painter.drawRoundedRect(QRectF(x, cy - h / 2, bw, h), bw / 2, bw / 2)

    def _paint_propeller(self, painter: QPainter) -> None:
        """Low-res spinning propeller, centered in the same small viz region."""
        frame = self._prop_frames[(self._ticks // PROP_TICKS_PER_FRAME) % PROP_FRAMES]
        grid = PROP_CELLS * PROP_CELL_PX
        ox = self._viz_left() + (VIZ_W - grid) / 2
        oy = (HEIGHT - grid) / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(PROP_COLOR)
        for col, row in frame:
            x = ox + col * PROP_CELL_PX
            y = oy + row * PROP_CELL_PX
            painter.drawRect(QRectF(x, y, PROP_CELL_PX - PROP_GAP, PROP_CELL_PX - PROP_GAP))

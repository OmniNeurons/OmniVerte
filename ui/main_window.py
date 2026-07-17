# file: ui/main_window.py

"""
Main application window — Fluent redesign.

Layout (top → bottom):
  - Header bar (status dot + app title + status text · theme / settings buttons)
  - Two cards side-by-side: Original (latest transcription) | Result (AI output)
  - Action bar: translation pill + segmented Fix/Casual/Professional/Custom
  - Activity Feed: compact session history with operation kind + preview

The window is hidden by default at startup and is summoned from the tray
("Show window"). Closing it (×) hides rather than quits — the app keeps
running in the tray.

Translate / Fix / rewrite operations run on a QThreadPool worker so OpenAI
calls don't freeze the UI. Results are delivered back to the GUI thread via
Qt signals.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Callable, Optional

import openai
import pyperclip
from PySide6.QtCore import (
    QObject,
    QRunnable,
    Qt,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QPainter,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from qframelesswindow import FramelessWindow, StandardTitleBar
from qfluentwidgets import (
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    RoundMenu,
    Theme,
    TransparentToolButton,
    setTheme,
)
from shiboken6 import isValid

from i18n import t
from services.config_store import Config
from services.glossary import Glossary
from services.text_operations import (
    BUSINESS_STYLE,
    CONVERSATIONAL_STYLE,
    fix_text,
    rewrite_text,
    translate_text,
)
from services.ui_bridge import UIBridge
from ui.custom_style_dialog import CustomStyleDialog
from ui.history_manager import (
    KIND_CASUAL,
    KIND_CUSTOM,
    KIND_FIX,
    KIND_PROFESSIONAL,
    KIND_TRANSLATION,
    HistoryEntry,
    HistoryManager,
    kind_label,
)
from ui import style
from ui.style import main_window_qss, palette

logger = logging.getLogger(__name__)


# ---------- async worker for OpenAI calls ----------

class _WorkerSignals(QObject):
    # finished carries (result, kind, label, meta). Bundling the operation
    # context into the signal — rather than capturing it in a lambda on the
    # connect side — lets us connect directly to a bound method, which
    # guarantees a QueuedConnection back to the GUI thread. A lambda receiver
    # has no QObject affinity and PySide6 falls back to DirectConnection,
    # which silently runs the GUI updates on the worker thread → hangs.
    finished = Signal(str, str, str, object)
    failed = Signal(str, str)  # message, label (log only — see _run_operation)


class _OperationWorker(QRunnable):
    """Runs a callable in a thread pool slot and emits result via signals."""

    def __init__(
        self,
        fn: Callable[[], str],
        kind: str,
        label: str,
        meta: Optional[dict] = None,
    ):
        super().__init__()
        self._fn = fn
        self._kind = kind
        self._label = label
        self._meta = dict(meta) if meta else {}
        self.signals = _WorkerSignals()

    def run(self):
        logger.info(f"Worker started: {self._label}")
        try:
            result = self._fn()
        except Exception as e:
            logger.warning(f"Worker failed ({self._label}): {e}")
            self.signals.failed.emit(str(e), self._label)
            return
        logger.info(f"Worker finished: {self._label} ({len(result or '')} chars)")
        self.signals.finished.emit(result or "", self._kind, self._label, self._meta)


# ---------- small reusable widgets ----------

class _StatusDot(QLabel):
    """10×10 coloured circle driven by UIBridge canonical status strings."""

    def __init__(self):
        super().__init__()
        self.setObjectName("statusDot")
        self.setFixedSize(10, 10)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._status = "idle"
        self.set_status("idle")

    def _apply_color(self, color: str):
        # inline style overrides the QSS default so the dot's colour
        # reflects the live status without re-applying the whole sheet
        self.setStyleSheet(f"background-color: {color}; border-radius: 5px;")

    def set_status(self, status: str):
        # Remember the last status so the dot can be re-tinted on a theme switch.
        self._status = status
        p = palette()
        if status == "recording":
            self._apply_color(p.STATUS_DOT_RECORDING)
        elif status == "processing":
            self._apply_color(p.STATUS_DOT_PROCESSING)
        elif status == "loading":
            self._apply_color(p.STATUS_DOT_LOADING)
        elif status == "error":
            self._apply_color(p.STATUS_DOT_ERROR)
        else:
            self._apply_color(p.STATUS_DOT_IDLE)

    def retint(self):
        """Re-apply the colour for the current status after a theme switch."""
        self.set_status(self._status)


def _drop_shadow(widget: QWidget) -> None:
    """Apply the soft 'card' shadow per spec: 28px blur, 8px y-offset.

    The shadow colour is theme-dependent (subtle navy on light, deeper black on
    dark), so it reads from the active palette and is re-applied on theme switch.
    """
    eff = widget.graphicsEffect()
    if not isinstance(eff, QGraphicsDropShadowEffect):
        eff = QGraphicsDropShadowEffect(widget)
        eff.setBlurRadius(28)
        eff.setOffset(0, 8)
        widget.setGraphicsEffect(eff)
    eff.setColor(QColor(*palette().SHADOW_RGBA))


def _strip_text_colors(doc) -> None:
    """Drop every trace of foreground/background colour from `doc` at three
    levels — paragraph background, block char format (paragraph-end caret),
    and per-fragment char formats. Bold/italic/size/family stay untouched.

    Sweeping the live document after paste is what catches Slack/Word HTML
    that puts colour on a block style rather than a leaf span, and what makes
    a theme switch instantly fix anything that was pasted earlier."""
    block = doc.begin()
    while block.isValid():
        c = QTextCursor(block)

        # Paragraph background (e.g. Slack's <p style="background-color:#f8f8f8">).
        bf = QTextBlockFormat(block.blockFormat())
        bf.clearBackground()
        c.setBlockFormat(bf)

        # Block char format — drives the caret at paragraph end.
        bcf = QTextCharFormat(block.charFormat())
        bcf.clearForeground()
        bcf.clearBackground()
        c.setBlockCharFormat(bcf)

        # Per-fragment formats.
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid():
                ncf = QTextCharFormat(frag.charFormat())
                ncf.clearForeground()
                ncf.clearBackground()
                fc = QTextCursor(doc)
                fc.setPosition(frag.position())
                fc.setPosition(
                    frag.position() + frag.length(),
                    QTextCursor.KeepAnchor,
                )
                fc.setCharFormat(ncf)
            it += 1
        block = block.next()


class _DocViewTextEdit(QTextEdit):
    """QTextEdit that drops pasted inline colours so the theme always wins.

    Browser / Word / Slack clipboards ship char formats (and paragraph
    backgrounds) with concrete colours; those win over our QSS default and
    turn pasted text into a dark blob on a dark card. We let Qt do the actual
    paste so structure, lists and bold/italic survive, then sweep the whole
    document — fragments, block char format, paragraph background — and reset
    the cursor's own current format so the next keystroke isn't tinted either."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Multi-line placeholder. Qt's built-in placeholderText only paints a
        # single line, so we draw our own — same font as typed text, muted, and
        # it disappears the moment the document has content (like a placeholder).
        self._multiline_placeholder = ""

    def setMultilinePlaceholder(self, text: str):
        self._multiline_placeholder = text or ""
        self.viewport().update()

    def insertFromMimeData(self, source):
        super().insertFromMimeData(source)
        _strip_text_colors(self.document())
        # After a rich paste the cursor inherits the source's last char format.
        # Reset it so subsequent typing / plain-text pastes take the theme too.
        self.setCurrentCharFormat(QTextCharFormat())

    def paintEvent(self, event):
        super().paintEvent(event)
        # Only while the document is empty — then it reads as a placeholder.
        if not self._multiline_placeholder or not self.document().isEmpty():
            return
        painter = QPainter(self.viewport())
        # Muted, semi-transparent take on the body text colour — reads as a hint,
        # not as filled content. Mirrors how the native placeholder looks.
        col = QColor(palette().TEXT_MUTED)
        col.setAlpha(170)
        painter.setPen(col)
        # Match the typed-text size (docView QSS sets font-size: 15px); a
        # stylesheet font isn't reflected in self.font(), so pin it explicitly.
        font = self.font()
        font.setPixelSize(15)
        painter.setFont(font)
        margin = int(self.document().documentMargin())
        rect = self.viewport().rect().adjusted(margin, margin, -margin, -margin)
        painter.drawText(
            rect,
            Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
            self._multiline_placeholder,
        )
        painter.end()


# ---------- document card (header + toolbar + text view) ----------

class _DocumentCard(QFrame):
    """
    Reusable card that holds a title, a row of ghost toolbar buttons, and a
    document-style QTextEdit. The Original and Result cards both build on this.
    """

    def __init__(self, title: str, placeholder: str = ""):
        super().__init__()
        self.setObjectName("card")
        self.setFrameShape(QFrame.NoFrame)
        _drop_shadow(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(10)

        # --- header row: title (+ optional badge) ··· toolbar ---
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        header_row.addWidget(self.title_label)

        # Badge ("Generated") shown next to the title — hidden by default.
        self.badge_dot = QLabel()
        self.badge_dot.setFixedSize(6, 6)
        self.badge_dot.setStyleSheet(
            f"background-color: {palette().SUCCESS}; border-radius: 3px;"
        )
        # Deliberately built empty: the owner (MainWindow) registers this label
        # with `_tr`, which both sets the text and puts it on the retranslate
        # list. Setting it here too would just be a duplicate that the first
        # language switch silently corrects.
        self.badge_label = QLabel()
        self.badge_label.setObjectName("cardSubtitle")
        self.badge_dot.hide()
        self.badge_label.hide()
        header_row.addSpacing(8)
        header_row.addWidget(self.badge_dot)
        header_row.addWidget(self.badge_label)

        header_row.addStretch(1)

        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar_layout.setSpacing(4)
        header_row.addLayout(self.toolbar_layout)

        outer.addLayout(header_row)

        # --- text view (document surface — no border, big padding) ---
        # Subclass used so pasted rich-text from external sources can't bring
        # its own foreground colour and become invisible in dark mode.
        self.text_edit = _DocViewTextEdit()
        self.text_edit.setObjectName("docView")
        # Multi-line empty-state hint, painted inside the field like a native
        # placeholder (same font, muted, vanishes once you type).
        self.text_edit.setMultilinePlaceholder(placeholder)
        self.text_edit.setFrameShape(QFrame.NoFrame)
        self.text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.text_edit.document().setDocumentMargin(4)
        # Increase line spacing for the document feel.
        self.text_edit.setStyleSheet(
            "QTextEdit#docView { line-height: 1.55; }"
        )
        outer.addWidget(self.text_edit, stretch=1)

    def add_toolbar_button(self, text: str, callback: Callable[[], None]) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("ghost")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        self.toolbar_layout.addWidget(btn)
        return btn

    def apply_theme(self):
        """Re-tint the inline-styled bits that QSS can't reach (badge dot,
        card shadow). The cascaded sheet handles everything else."""
        self.badge_dot.setStyleSheet(
            f"background-color: {palette().SUCCESS}; border-radius: 3px;"
        )
        _drop_shadow(self)
        # Drop any inline foreground from previously-pasted fragments so they
        # repaint in the new theme's colour instead of staying invisible.
        _strip_text_colors(self.text_edit.document())

    def set_title(self, title: str):
        self.title_label.setText(title)

    def set_generated_badge(self, visible: bool):
        self.badge_dot.setVisible(visible)
        self.badge_label.setVisible(visible)

    def text(self) -> str:
        return self.text_edit.toPlainText()

    def set_text(self, value: str):
        self.text_edit.setPlainText(value or "")

    def set_placeholder(self, text: str):
        # Multi-line empty-state copy — shown only while the document is empty.
        self.text_edit.setMultilinePlaceholder(text)


# ---------- activity feed item ----------

class _FeedItem(QFrame):
    """One row in the Activity Feed: time + kind label · preview text."""

    clicked = Signal(HistoryEntry)

    def __init__(self, entry: HistoryEntry):
        super().__init__()
        self.setObjectName("feedItem")
        self.setFrameShape(QFrame.NoFrame)
        self._entry = entry
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        # left column: time + kind
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(2)
        time_lbl = QLabel(entry.timestamp.strftime("%H:%M"))
        time_lbl.setObjectName("feedTime")
        self.kind_lbl = QLabel()
        self.kind_lbl.setObjectName("feedKind")
        self.retranslate()
        left.addWidget(time_lbl)
        left.addWidget(self.kind_lbl)
        # Fixed-ish width so multiple rows line up.
        left_wrap = QWidget()
        left_wrap.setLayout(left)
        left_wrap.setFixedWidth(170)
        layout.addWidget(left_wrap)

        # right column: preview (1 line truncated to 2 with elide)
        preview_lbl = QLabel(self._preview_text(entry.text))
        preview_lbl.setObjectName("feedPreview")
        preview_lbl.setWordWrap(True)
        preview_lbl.setMaximumHeight(40)
        layout.addWidget(preview_lbl, stretch=1)

    def retranslate(self):
        """Re-render the one translatable string in this row: the kind label.

        Everything else the row shows is data — the timestamp and the transcript
        preview. `__init__` calls this too, so exactly one place composes the
        string and a relabelled row cannot drift from a freshly-built one.
        """
        text = kind_label(self._entry.kind, self._entry.kind.title())
        direction = self._entry.meta.get("direction") if self._entry.meta else None
        if direction:
            # The direction ("EN → RU") is derived from the language pair, which
            # is config data — not translated.
            text = f"{text} · {direction}"
        self.kind_lbl.setText(text)

    @staticmethod
    def _preview_text(text: str) -> str:
        # Collapse newlines and trim to keep the row compact.
        flat = " ".join(text.split())
        if len(flat) > 160:
            flat = flat[:160].rstrip() + "…"
        return flat

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._entry)
        super().mouseReleaseEvent(event)


# ---------- main window ----------

class MainWindow(FramelessWindow):
    """
    Main window. Owned by the app for its full lifetime; never destroyed.

    Subclasses qframelesswindow.FramelessWindow → frameless with a native
    Windows-style titleBar (min/max/close). On Win11 we additionally try to
    apply a mica backdrop via WindowEffect; failures fall back silently to a
    plain solid background.
    """

    def __init__(
        self,
        ui_bridge: UIBridge,
        history_manager: HistoryManager,
        openai_client: Optional[openai.OpenAI],
        config: Config,
        icon_path: Optional[str] = None,
    ):
        super().__init__()
        # MUST precede every _build_* call: `_tr` appends to it at build time.
        self._retranslatables: list[tuple[QWidget, str, str, dict]] = []
        # Cached state behind the Result card's title, so `retranslate()` can
        # re-render it with no new event: (phase, kind, meta), phase being
        # "idle" | "working" | "done". Mirrors how `_model_state` /
        # `_session_status` back `_repaint_status()`.
        self._result_state: tuple[str, Optional[str], dict] = ("idle", None, {})
        self._bridge = ui_bridge
        self._history = history_manager
        self._client = openai_client
        self._config = config
        # Own glossary instance for the manual action buttons (layer A). The
        # AudioWriter holds its own for the voice path; both read the same
        # glossary.json. Reloaded in show_and_focus alongside the config.
        self._glossary = Glossary()
        self._apply_glossary_entitlement()
        self._thread_pool = QThreadPool.globalInstance()

        # Resolve the saved theme and set the active palette before any widget
        # is built, so the first paint is already in the right theme.
        self._theme = (config.get("THEME") or "light").strip().lower()
        style.set_theme(self._theme)

        # The default FramelessWindow titleBar is just a draggable strip with
        # no buttons — swap it for StandardTitleBar so we get native-feeling
        # min/max/close. We keep its title label + icon visible so the app name
        # rides in the top control row, alongside min/max/close.
        self.setTitleBar(StandardTitleBar(self))

        self._tr(self, "app.title", setter="setWindowTitle")
        self.resize(1040, 720)
        self.setMinimumSize(860, 600)

        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._build_ui()
        self._wire_signals()
        # Apply the Fluent theme + Mica backdrop + inline tints now that all
        # widgets exist. Single source of truth for both first paint and live
        # toggles.
        self._apply_theme()
        self._refresh_settings_labels()
        self._refresh_tier_badge()
        self._refresh_feed()

        # Center on screen once at construction. Neither qframelesswindow nor
        # qfluentwidgets position their windows, so they fall back to Windows'
        # default placement — which cascades each new top-level window down and
        # to the right of screen centre. The Settings window happens to land
        # centred; the main window visibly didn't. We set an explicit centred
        # position here so both feel the same. Done once (not per show_and_focus)
        # so reopening from the tray doesn't yank a user-moved window back.
        self._center_on_screen()

    # ---------- i18n ----------

    def _tr(self, widget, key: str, setter: str = "setText", **fmt):
        """Apply catalog `key` to `widget` now AND register it for replay on a
        language change. Call at BUILD time instead of `widget.setText(t(key))`.

        This window is the one that never gets rebuilt: the tray menu and every
        settings page are thrown away and re-created, so their `t()` calls run
        again on their own. Here the widgets outlive the locale, so something has
        to remember which key painted which widget. Registering at the call site
        means the registry IS the retranslate list — there is no second list to
        forget to update, which is the entire failure mode of a hand-written
        `retranslate_ui()`.

        Register PERMANENT chrome only. Anything rebuilt from scratch (feed items
        via `_refresh_feed`) must NOT be registered: the entry would outlive the
        C++ object and raise `RuntimeError: Internal C++ object already deleted`
        from a signal handler — i.e. a crash on language switch. Anything whose
        text is computed from live state (the status label, the Result card
        title, the translate pill) must not be registered either; it is
        re-rendered by the pure repaint functions `retranslate()` calls instead.

        `setter` covers the sinks this window uses: setText, setToolTip,
        setWindowTitle, setMultilinePlaceholder.
        """
        getattr(widget, setter)(t(key, **fmt))
        self._retranslatables.append((widget, setter, key, fmt))
        return widget

    @Slot(str)
    def retranslate(self, _locale: str = ""):
        """Re-render every user-visible string in the active locale, in place.

        Two halves, and the split is the point:
          * the `_tr` registry — static chrome, replayed key by key;
          * the existing pure re-render functions — everything driven by cached
            state (`_model_state`, `_result_state`, config-derived labels). They
            already existed for other reasons and take no arguments, so no status
            or transcript event has to be replayed to get the text right.
        """
        live: list[tuple[QWidget, str, str, dict]] = []
        for entry in self._retranslatables:
            widget, setter, key, fmt = entry
            # A registered widget should never die (that is the rule `_tr`
            # documents), but a stale entry here would raise out of a signal
            # handler and read to the user as "the language switch broke the
            # app". Drop it instead.
            if not isValid(widget):
                logger.debug(f"Dropping retranslatable for deleted widget: {key}")
                continue
            getattr(widget, setter)(t(key, **fmt))
            live.append(entry)
        self._retranslatables = live

        self._update_theme_button()
        self._refresh_tier_badge()
        # These two write disjoint sets of widgets (see
        # _no_key_tooltip_controls), so their order is free.
        self._refresh_client_tooltip()
        # Superset of what a settings save refreshes: the pill, the hotkey-hint
        # placeholder and the Custom tooltip are all config-derived text.
        self._refresh_settings_labels()
        self._repaint_status()
        self._repaint_result_title()
        # Feed rows relabel themselves in place rather than going through
        # _refresh_feed(). That rebuild destroys and re-creates every row, and
        # the deferred deleteLater() collapses the scroll container to zero
        # height for one event-loop pass — long enough to clamp the user's
        # scroll position to the top. A new transcript arriving *should* jump to
        # the newest row; a language switch should not move the view at all.
        # (`_refresh_history_count` is not needed here: it renders "3/10".)
        for item in self.feed_container.findChildren(_FeedItem):
            item.retranslate()

    # ---------- UI construction ----------

    def _build_ui(self):
        root = QWidget(self)
        root.setObjectName("mainRoot")
        root.setStyleSheet(main_window_qss())
        self.root = root

        outer = QVBoxLayout(root)
        # Pad enough to clear the titleBar overlay on top.
        title_bar_h = max(self.titleBar.height(), 32)
        outer.setContentsMargins(24, title_bar_h + 4, 24, 20)
        outer.setSpacing(16)

        outer.addWidget(self._build_header())
        outer.addLayout(self._build_content_row(), stretch=1)
        outer.addLayout(self._build_action_bar())
        outer.addWidget(self._build_activity_feed())

        # FramelessWindow has no central-widget API — embed our content via
        # our own layout. The titleBar (StandardTitleBar) is a child positioned
        # at (0, 0); since we add `root` to a layout that covers the full
        # window, root paints OVER the titleBar's button area unless we raise
        # titleBar above it explicitly. Without the .raise_() call min/max/
        # close are still functional but hidden behind root.
        host_layout = QVBoxLayout(self)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)
        host_layout.addWidget(root)
        self.titleBar.raise_()

        # Disable text-operation buttons if no OpenAI client is configured.
        if self._client is None:
            for btn in self._operation_buttons():
                btn.setEnabled(False)
            self.translate_pill.setEnabled(False)
        self._refresh_client_tooltip()

    def _no_key_tooltip_controls(self) -> list[QWidget]:
        """Controls whose tooltip is the no-key sentence — or nothing at all.

        Everything in `_operation_buttons()` EXCEPT custom_btn, plus the
        translate pill. custom_btn is disabled alongside the others, but its
        tooltip belongs to `_refresh_settings_labels()`, which puts the
        configured style's name in it. Derived by subtraction rather than
        re-listed, so a new operation button added to `_operation_buttons()`
        still picks the no-key tooltip up for free.
        """
        return [b for b in self._operation_buttons() if b is not self.custom_btn] + [
            self.translate_pill
        ]

    def _refresh_client_tooltip(self):
        """The "no key" tooltip on the text-operation controls, or none.

        Split out from the enable/disable logic so `retranslate()` can re-render
        the sentence without also re-enabling buttons behind an in-flight
        operation. Not `_tr`-registered: whether the tooltip exists at all is a
        function of live state (the client), not of the locale.

        Writes only the tooltips it owns (`_no_key_tooltip_controls`). It used to
        blanket-write every operation button, which made three separate call
        sites silently responsible for running `_refresh_settings_labels()`
        afterwards to repair custom_btn — and when a key WAS configured the
        sentence is "", so getting that order wrong erased the Custom button's
        tooltip rather than merely mislabelling it.
        """
        tip = t("main.tooltip.no_key") if self._client is None else ""
        for control in self._no_key_tooltip_controls():
            control.setToolTip(tip)

    # ---------- theme ----------

    def _apply_theme(self):
        """Single point that paints the whole window in the active theme: Fluent
        components, our cascaded QSS sheet, inline-tinted widgets, and the Win11
        Mica backdrop. Safe to call repeatedly — used for both the first paint
        and live toggles."""
        dark = style.is_dark()
        # qfluentwidgets repaints its own components (title-bar min/max/close).
        setTheme(Theme.DARK if dark else Theme.LIGHT)
        # Our objectName-scoped rules ride on the root widget's sheet.
        self.root.setStyleSheet(main_window_qss())
        # Inline-styled bits the cascade can't reach.
        self.status_dot.retint()
        self._retint_translate_icon()
        self.original_card.apply_theme()
        self.result_card.apply_theme()
        _drop_shadow(self.feed_wrapper)
        # Win11 Mica backdrop follows the theme; silent no-op on older/other OS.
        try:
            self.windowEffect.setMicaEffect(self.winId(), isDarkMode=dark)
        except Exception as e:
            logger.debug(f"Mica effect not applied: {e}")
        self._update_theme_button()

    def _update_theme_button(self):
        # One whole sentence per direction rather than interpolating a bare
        # "light"/"dark": those are canonical THEME values, and a language that
        # inflects the adjective inside the frame cannot work with a hole.
        self.theme_btn.setToolTip(
            t("main.tooltip.theme.light" if style.is_dark() else "main.tooltip.theme.dark")
        )

    def _on_toggle_theme(self):
        new_theme = "light" if style.is_dark() else "dark"
        self._theme = new_theme
        self._config.set("THEME", new_theme)
        style.set_theme(new_theme)
        self._apply_theme()
        self._bridge.theme_changed.emit(new_theme)
        logger.info(f"Theme switched to {new_theme}")

    @Slot(str)
    def _on_theme_changed(self, name: str):
        # React to a theme change initiated elsewhere; guard against the echo of
        # our own emit (we apply before emitting, so the value already matches).
        if (name or "").strip().lower() == ("dark" if style.is_dark() else "light"):
            return
        style.set_theme(name)
        self._apply_theme()

    def _build_header(self) -> QWidget:
        # Single ~44px bar: live status on the left, control icons on the right,
        # and the tagline pinned to the TRUE window centre. The app name itself
        # rides in the top control row (StandardTitleBar).
        bar = QWidget()
        bar.setObjectName("headerBar")
        bar.setFixedHeight(44)

        # A grid lets the tagline sit in the same cell as the status/control row
        # but centred on the full bar width — so it stays put no matter how wide
        # the status word gets ("Ready" → "Listening…" → "Transcribing…").
        grid = QGridLayout(bar)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        # --- foreground row: status (left) ··· controls (right) ---
        row = QHBoxLayout()
        # The outer layout insets every row by 24px; nudge to 20px left (to sit
        # flush with the cards below) and 16px right (tighter for the icons).
        row.setContentsMargins(-4, 0, -8, 0)
        row.setSpacing(0)

        self.status_dot = _StatusDot()
        # Not `_tr`-registered — `_repaint_status()` owns this label from the
        # first status event on, and re-renders it from cached state.
        self.status_text = QLabel(t("main.status.ready"))
        self.status_text.setObjectName("statusText")
        row.addWidget(self.status_dot)
        row.addSpacing(8)
        row.addWidget(self.status_text)

        row.addStretch(1)

        # Tier chip (Free / Pro) — a flat, borderless text button matching the
        # icon buttons beside it (no outline). Click opens Settings → License.
        self.tier_badge = QPushButton()
        self.tier_badge.setObjectName("tierChip")
        self.tier_badge.setCursor(Qt.PointingHandCursor)
        self.tier_badge.clicked.connect(lambda: self._bridge.license_requested.emit())
        row.addWidget(self.tier_badge)
        row.addSpacing(4)

        # TransparentToolButton has built-in Fluent hover/press states + the
        # right cursor — much more interactive than a plain QPushButton with
        # our barely-visible SURFACE_HOVER tint.
        self.theme_btn = TransparentToolButton(FIF.CONSTRACT)
        self.theme_btn.setFixedSize(34, 34)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._on_toggle_theme)
        row.addWidget(self.theme_btn)

        row.addSpacing(4)

        self.settings_btn = TransparentToolButton(FIF.SETTING)
        self.settings_btn.setFixedSize(34, 34)
        self._tr(self.settings_btn, "main.tooltip.settings", setter="setToolTip")
        self.settings_btn.clicked.connect(self._open_settings)
        row.addWidget(self.settings_btn)

        # --- centred tagline, overlaying the same grid cell ---
        # Same brand line the About card shows — one key, not a copy of it.
        tagline = self._tr(QLabel(), "app.tagline")
        tagline.setObjectName("headerTagline")

        grid.addLayout(row, 0, 0)
        grid.addWidget(tagline, 0, 0, Qt.AlignCenter)

        return bar

    def _build_content_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        # Negative top margin tightens the gap to the header bar above without
        # touching the spacing of the rows further down.
        row.setContentsMargins(0, -12, 0, 0)
        row.setSpacing(20)

        # --- Original card ---
        # No placeholder passed, and none registered: this card's empty state is
        # the hotkey-hints onboarding text, owned start-to-finish by
        # `_refresh_settings_labels()` (which __init__ calls before the window is
        # ever shown, and which retranslate() re-runs). A placeholder here would
        # be overwritten before anyone could read it — a string, and a
        # translation of it in every locale, that no user can ever see.
        self.original_card = _DocumentCard(title=t("main.card.original.title"))
        self._tr(self.original_card.title_label, "main.card.original.title")
        self._tr(self.original_card.badge_label, "main.card.badge.generated")
        self._tr(
            self.original_card.add_toolbar_button("", self._copy_original),
            "main.button.copy",
        )
        self._tr(
            self.original_card.add_toolbar_button("", self._clear_original),
            "main.button.clear",
        )
        row.addWidget(self.original_card, stretch=1)

        # --- Result card ---
        self.result_card = _DocumentCard(
            title=t("main.card.result.title"),
            placeholder=t("main.card.result.placeholder"),
        )
        # Title stays off the registry — `_repaint_result_title()` owns it.
        self._tr(
            self.result_card.text_edit,
            "main.card.result.placeholder",
            setter="setMultilinePlaceholder",
        )
        self._tr(self.result_card.badge_label, "main.card.badge.generated")
        self._tr(
            self.result_card.add_toolbar_button("", self._copy_result),
            "main.button.copy",
        )
        self._tr(
            self.result_card.add_toolbar_button("", self._clear_result),
            "main.button.clear",
        )
        row.addWidget(self.result_card, stretch=1)

        return row

    def _build_action_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(20)

        # --- translation pill ---
        self.translate_pill = QPushButton()
        self.translate_pill.setObjectName("translatePill")
        self.translate_pill.setCursor(Qt.PointingHandCursor)
        self.translate_pill.clicked.connect(self._on_translate_pill_clicked)
        row.addWidget(self.translate_pill, stretch=0)

        row.addStretch(1)

        # --- segmented rewrite buttons ---
        seg = QHBoxLayout()
        seg.setContentsMargins(0, 0, 0, 0)
        seg.setSpacing(8)

        def _segment(label: str, callback: Callable[[], None]) -> QPushButton:
            btn = QPushButton(label)
            btn.setObjectName("segment")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(callback)
            seg.addWidget(btn)
            return btn

        self.fix_btn = self._tr(_segment("", self._on_fix), "main.button.fix_grammar")
        self.casual_btn = self._tr(_segment("", self._on_casual), "main.button.casual")
        self.professional_btn = self._tr(
            _segment("", self._on_professional), "main.button.professional"
        )
        # Custom: first click with no prompt configured pops the editor dialog
        # (one-time setup); after that, the button just runs the rewrite. To
        # change the prompt later the user goes to Settings → Custom style.
        # Its TOOLTIP is config-driven and lives in `_refresh_settings_labels()`.
        self.custom_btn = self._tr(_segment("", self._on_custom), "main.button.custom")

        row.addLayout(seg)
        return row

    def _build_activity_feed(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("card")
        wrapper.setFrameShape(QFrame.NoFrame)
        wrapper.setFixedHeight(150)
        _drop_shadow(wrapper)
        self.feed_wrapper = wrapper

        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(18, 12, 18, 12)
        outer.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        title = self._tr(QLabel(), "main.feed.title")
        title.setObjectName("cardTitle")
        header_row.addWidget(title)
        header_row.addStretch(1)
        # Live count vs the tier cap (Free = N/10). Neutral; accented at the cap.
        self.history_count_label = QLabel("")
        self.history_count_label.setObjectName("historyCount")
        header_row.addWidget(self.history_count_label)
        outer.addLayout(header_row)

        self.feed_scroll = QScrollArea()
        self.feed_scroll.setObjectName("feedScroll")
        self.feed_scroll.setWidgetResizable(True)
        self.feed_scroll.setFrameShape(QFrame.NoFrame)
        self.feed_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.feed_container = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(2)
        self.feed_layout.addStretch(1)
        self.feed_scroll.setWidget(self.feed_container)

        outer.addWidget(self.feed_scroll, stretch=1)
        return wrapper

    # ---------- helpers ----------

    def _operation_buttons(self) -> list[QPushButton]:
        return [
            self.fix_btn,
            self.casual_btn,
            self.professional_btn,
            self.custom_btn,
        ]

    # ---------- signal wiring ----------

    def _wire_signals(self):
        self._bridge.transcript_ready.connect(self._on_transcript_ready)
        self._bridge.status_changed.connect(self._on_status_changed)
        self._bridge.model_state_changed.connect(self._on_model_state)
        self._bridge.settings_saved.connect(self._on_settings_saved)
        self._bridge.entitlement_changed.connect(self._on_entitlement_changed)
        self._bridge.theme_changed.connect(self._on_theme_changed)
        # Unlike the settings window (destroyed and rebuilt on save), this window
        # lives for the whole session and has to relabel itself in place.
        self._bridge.language_changed.connect(self.retranslate)
        self._history.changed.connect(self._refresh_feed)

    # ---------- entitlement (license tier) ----------

    def _apply_glossary_entitlement(self):
        """Cap the manual-button glossary to the current tier (Free = 5,
        Pro/Enterprise = 200). Mirrors AudioWriter.apply_entitlement."""
        from licensing import get_entitlement

        self._glossary.set_active_cap(get_entitlement().limit("glossary_terms"))

    def _refresh_tier_badge(self):
        from licensing import get_entitlement

        try:
            tier = get_entitlement().tier.value
        except Exception:
            tier = "free"
        # The tier's name ("Free"/"Pro") is what the product is sold as and
        # stays Latin in every locale — see the License page.
        self.tier_badge.setText(tier.capitalize())
        self.tier_badge.setToolTip(t("main.tooltip.license"))
        # Toggle a dynamic property so QSS can accent a paid (non-free) chip.
        # Membership test, not a tier comparison — keeps gating out of the UI.
        self.tier_badge.setProperty("pro", tier in ("pro", "enterprise"))
        # Re-polish so the property change takes effect immediately.
        self.tier_badge.style().unpolish(self.tier_badge)
        self.tier_badge.style().polish(self.tier_badge)

    @Slot()
    def _on_entitlement_changed(self):
        self._apply_glossary_entitlement()
        self._refresh_tier_badge()
        self._refresh_history_count()

    # ---------- settings-driven labels ----------

    def _refresh_settings_labels(self):
        """Re-render every config-driven label. A strict SUBSET of
        `retranslate()`, so an unrelated settings save doesn't pay for a full
        relabel of the window — and so neither path can drift from the other.

        None of these widgets is `_tr`-registered: their text is a function of
        config, not of a catalog key alone.
        """
        # PRIMARY_LANGUAGE / SECONDARY_LANGUAGE hold English language NAMES —
        # config values, not chrome — so the codes they collapse to stay Latin
        # in every locale. Only the "Auto ·" frame around them is translated.
        primary = self._config.get("PRIMARY_LANGUAGE") or "English"
        secondary = self._config.get("SECONDARY_LANGUAGE") or "Russian"
        self.translate_pill.setText(t(
            "main.pill.translate",
            primary=self._lang_code(primary),
            secondary=self._lang_code(secondary),
        ))
        # Tooltip spells out what the label's ↔ only implies (auto-direction) and
        # names the languages in full. Config-derived like the label, so it lives
        # here, not in the _tr registry.
        self.translate_pill.setToolTip(t(
            "main.pill.translate.tooltip",
            primary=primary,
            secondary=secondary,
        ))
        self._retint_translate_icon()

        # Left card's empty state doubles as onboarding: which hotkey does what.
        self.original_card.set_placeholder(self._hotkey_hints_text())

        style_name = (self._config.get("CUSTOM_STYLE_NAME") or "").strip()
        style_prompt = (self._config.get("CUSTOM_STYLE_PROMPT") or "").strip()
        if style_prompt:
            # `name` is the user's own style name — data, interpolated verbatim.
            self.custom_btn.setToolTip(
                t("main.tooltip.custom.named", name=style_name)
                if style_name
                else t("main.tooltip.custom.generic")
            )
        else:
            self.custom_btn.setToolTip(t("main.tooltip.custom.unset"))

    def _retint_translate_icon(self):
        # Globe rendered in the active accent (turquoise); follows theme switches.
        self.translate_pill.setIcon(FIF.GLOBE.icon(color=QColor(palette().ACCENT)))

    def _custom_style_label(self) -> str:
        """Display name of the style the custom hotkey applies.

        HOTKEY_CUSTOM_STYLE holds a canonical value (casual/professional/custom);
        two of the three resolve to a catalog label, and the third is whatever the
        user named their own style — data, returned verbatim.
        """
        style = (self._config.get("HOTKEY_CUSTOM_STYLE") or "custom").strip().lower()
        if style == "casual":
            return t("main.hint.style.casual")
        if style == "professional":
            return t("main.hint.style.professional")
        return (self._config.get("CUSTOM_STYLE_NAME") or "").strip() or t("main.hint.style.custom")

    def _hotkey_hints_text(self) -> str:
        # One key per LINE rather than one per block: each line is an
        # independent sentence, and joining them here keeps the "\n" out of the
        # catalog, where a translator could lose it.
        mode = (self._config.get("ACTIVATION_MODE") or "keyboard").strip().lower()
        if mode == "mouse":
            btn = (self._config.get("MOUSE_ACTIVATION_BUTTON") or "middle").strip().lower()
            return "\n".join((
                t("main.hint.mouse.dictate", button=t(f"main.mouse.{btn}")),
                t("main.hint.mouse.hotkeys"),
            ))
        transcribe = self._config.get("HOTKEY_TRANSCRIBE") or self._config.get("ACTIVATION_KEY") or "F9"
        translate = self._config.get("HOTKEY_TRANSLATE") or "F10"
        custom = self._config.get("HOTKEY_CUSTOM") or "F11"
        return "\n".join((
            t("main.hint.keyboard.transcribe", key=transcribe),
            t("main.hint.keyboard.translate", key=translate),
            t("main.hint.keyboard.custom", key=custom, style=self._custom_style_label()),
        ))

    @staticmethod
    def _lang_code(name: str) -> str:
        # Short ISO-ish display label for the pill; falls back to first 2 chars.
        table = {
            "English": "EN", "Russian": "RU", "Spanish": "ES",
            "German": "DE", "French": "FR", "Italian": "IT",
            "Portuguese": "PT", "Chinese": "ZH", "Japanese": "JA",
            "Korean": "KO", "Polish": "PL", "Dutch": "NL",
            "Turkish": "TR", "Arabic": "AR", "Ukrainian": "UK",
        }
        return table.get(name, name[:2].upper())

    # ---------- slots ----------

    @Slot(str)
    def _on_transcript_ready(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        self.original_card.set_text(text)
        logger.debug(f"MainWindow received transcript ({len(text)} chars)")

    @Slot(str)
    def _on_status_changed(self, status: str):
        # Session status is one of two axes; the model-state axis (loading/failed)
        # takes precedence. Remember it and let _repaint_status() decide.
        self._session_status = status
        self._repaint_status()

    @Slot(str)
    def _on_model_state(self, state: str):
        # "ready" hands control back to the session-status axis; "loading"/
        # "failed" paint over it (the model isn't usable, so recording can't run
        # anyway — see AudioWriter.start_recording's guard).
        self._model_state = state
        self._repaint_status()

    def _repaint_status(self):
        """Combine the session-status and model-state axes into the dot + label.
        Precedence: a non-ready model (loading/failed) wins; otherwise the live
        session status (idle/recording/processing) shows through."""
        ms = getattr(self, "_model_state", "ready")
        if ms == "loading":
            self.status_dot.set_status("loading")
            self.status_text.setText(t("main.status.loading"))
            return
        if ms == "failed":
            self.status_dot.set_status("error")
            self.status_text.setText(t("main.status.failed"))
            return
        status = getattr(self, "_session_status", "idle")
        self.status_dot.set_status(status)
        # Canonical status -> catalog KEY. Keys, not text: a dict of `t()`
        # results would resolve once when this function is first entered and the
        # literals would freeze in that locale.
        self.status_text.setText(t({
            "recording": "main.status.recording",
            "processing": "main.status.processing",
            "error": "main.status.error",
        }.get(status, "main.status.ready")))

    @Slot()
    def _refresh_feed(self):
        # Drop the existing item widgets (keep the trailing stretch at index -1).
        while self.feed_layout.count() > 1:
            item = self.feed_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # Newest at top — reverse the underlying list (which is newest-last).
        for entry in reversed(self._history.entries()):
            row = _FeedItem(entry)
            row.clicked.connect(self._on_feed_item_clicked)
            self.feed_layout.insertWidget(self.feed_layout.count() - 1, row)

        self._refresh_history_count()

    def _refresh_history_count(self):
        """Show 'used / cap' for the session history; tint it at the cap. On an
        unlimited tier show just the count."""
        from licensing import UNLIMITED, get_entitlement

        try:
            cap = get_entitlement().limit("history_entries")
        except Exception:
            cap = 10
        n = len(self._history.entries())
        if cap == UNLIMITED:
            self.history_count_label.setText(f"{n}")
            at_cap = False
        else:
            self.history_count_label.setText(f"{n}/{cap}")
            at_cap = n >= cap
        self.history_count_label.setProperty("warn", at_cap)
        self.history_count_label.style().unpolish(self.history_count_label)
        self.history_count_label.style().polish(self.history_count_label)

    @Slot(HistoryEntry)
    def _on_feed_item_clicked(self, entry: HistoryEntry):
        # Clicking a feed item loads its text into the appropriate card so the
        # user can re-run an operation on it.
        if entry.kind in (KIND_TRANSLATION, KIND_FIX, KIND_CASUAL, KIND_PROFESSIONAL, KIND_CUSTOM):
            self.result_card.set_text(entry.text)
            self.result_card.set_generated_badge(True)
            # No meta: a feed click shows the bare kind, without the "· EN ↔ RU"
            # suffix a freshly-run translation gets.
            self._result_state = ("done", entry.kind, {})
            self._repaint_result_title()
        else:
            self.original_card.set_text(entry.text)

    # ---------- card actions ----------

    def _copy_original(self):
        self._copy_to_clipboard(self.original_card.text())

    def _copy_result(self):
        self._copy_to_clipboard(self.result_card.text())

    def _clear_original(self):
        self.original_card.set_text("")

    def _clear_result(self):
        self.result_card.set_text("")
        self.result_card.set_generated_badge(False)
        self._result_state = ("idle", None, {})
        self._repaint_result_title()

    # ---------- result card title ----------

    def _repaint_result_title(self):
        """Render the Result card's title from `self._result_state`.

        Pure function of cached state, like `_repaint_status()` — which is what
        lets `retranslate()` fix a title set three operations ago without
        re-running the operation.
        """
        phase, kind, meta = self._result_state
        if phase == "idle" or kind is None:
            self.result_card.set_title(t("main.card.result.title"))
            return
        # The title of a generated result IS its history kind — same label the
        # Activity Feed puts on the row this run will create. One key, not two.
        title = kind_label(kind, t("main.card.result.title"))
        direction = (meta or {}).get("direction")
        if direction:
            title = f"{title} · {direction}"
        if phase == "working":
            title = t("main.card.result.working", label=title)
        self.result_card.set_title(title)

    def _insert_again(self):
        text = self.original_card.text().strip()
        if not text:
            return
        self._copy_to_clipboard(text)
        # Best-effort paste; safe because the user explicitly clicked.
        try:
            import keyboard
            keyboard.send("ctrl+v")
        except Exception as e:
            logger.warning(f"Insert again — paste failed: {e}")

    def _replace_original_with_result(self):
        result = self.result_card.text().strip()
        if not result:
            return
        self.original_card.set_text(result)

    def _copy_to_clipboard(self, text: str):
        try:
            pyperclip.copy(text or "")
        except Exception as e:
            logger.warning(f"pyperclip.copy failed: {e}")

    def _source_text(self) -> str:
        return self.original_card.text().strip()

    # ---------- translation pill popup ----------

    def _on_translate_pill_clicked(self):
        # Cheap UX: clicking the pill kicks off the translation immediately.
        # The dropdown indicator inside the pill text already advertises the
        # configured pair; for fine-grained control we expose the popup via
        # right-click instead.
        self._run_translate()

    def contextMenuEvent(self, event):
        # Right-click on the pill area shows the configured language pair and
        # a shortcut to settings. Done here (window-level) because attaching
        # context menus directly to QPushButton via setContextMenuPolicy plays
        # poorly with our hover styles.
        if self.translate_pill.underMouse():
            menu = RoundMenu(parent=self)
            primary = self._config.get("PRIMARY_LANGUAGE") or "English"
            secondary = self._config.get("SECONDARY_LANGUAGE") or "Russian"
            # Built on demand, so no registration: the menu never outlives the
            # click that opened it.
            info_action = QAction(
                t("main.menu.pair", primary=primary, secondary=secondary), self
            )
            info_action.setEnabled(False)
            menu.addAction(info_action)
            menu.addSeparator()
            settings_action = QAction(FIF.SETTING.icon(), t("main.menu.change_settings"), self)
            settings_action.triggered.connect(self._open_settings)
            menu.addAction(settings_action)
            menu.exec(event.globalPos())
            return
        super().contextMenuEvent(event)

    def _glossary_block(self):
        """Canonical-terms block for the manual action buttons (layer A), or None.

        Gated by the master switch, GLOSSARY_LLM_REWRITE (manual buttons are the
        rewrite/translate path), and a non-empty glossary — so prompts are
        unchanged when the feature is off or the glossary is empty.
        """
        if (self._config.get("GLOSSARY_ENABLED") or "false").strip().lower() != "true":
            return None
        if (self._config.get("GLOSSARY_LLM_REWRITE") or "false").strip().lower() != "true":
            return None
        if self._glossary.is_empty:
            return None
        return self._glossary.llm_block() or None

    def _run_translate(self):
        if self._client is None:
            return
        source = self._source_text()
        if not source:
            return
        primary = self._config.get("PRIMARY_LANGUAGE") or "English"
        secondary = self._config.get("SECONDARY_LANGUAGE") or "Russian"
        direction = f"{self._lang_code(primary)} ↔ {self._lang_code(secondary)}"
        glossary_block = self._glossary_block()
        self._run_operation(
            lambda: translate_text(
                self._client, source, primary, secondary, glossary_block=glossary_block
            ),
            kind=KIND_TRANSLATION,
            label=f"Translation · {direction}",
            meta={"direction": direction},
        )

    # ---------- rewrite actions ----------

    def _on_fix(self):
        if self._client is None:
            return
        source = self._source_text()
        if not source:
            return
        glossary_block = self._glossary_block()
        self._run_operation(
            lambda: fix_text(self._client, source, glossary_block=glossary_block),
            kind=KIND_FIX,
            label="Grammar correction",
        )

    def _on_casual(self):
        if self._client is None:
            return
        source = self._source_text()
        if not source:
            return
        glossary_block = self._glossary_block()
        self._run_operation(
            lambda: rewrite_text(
                self._client, source, CONVERSATIONAL_STYLE, glossary_block=glossary_block
            ),
            kind=KIND_CASUAL,
            label="Casual rewrite",
        )

    def _on_professional(self):
        if self._client is None:
            return
        source = self._source_text()
        if not source:
            return
        glossary_block = self._glossary_block()
        self._run_operation(
            lambda: rewrite_text(
                self._client, source, BUSINESS_STYLE, glossary_block=glossary_block
            ),
            kind=KIND_PROFESSIONAL,
            label="Professional rewrite",
        )

    def _on_custom(self):
        if self._client is None:
            return
        prompt = (self._config.get("CUSTOM_STYLE_PROMPT") or "").strip()
        if not prompt:
            self._open_custom_style_editor()
            return
        source = self._source_text()
        if not source:
            return
        glossary_block = self._glossary_block()
        self._run_operation(
            lambda: rewrite_text(
                self._client, source, prompt, glossary_block=glossary_block
            ),
            kind=KIND_CUSTOM,
            label="Custom rewrite",
        )

    def _open_custom_style_editor(self):
        # Free: authoring free-text styles is Pro. Route to Settings → Custom
        # style, where the profession templates live (those are Free), instead
        # of the editable dialog.
        from licensing import Feature, get_entitlement

        if not get_entitlement().has(Feature.CUSTOM_STYLE_EDITING):
            InfoBar.info(
                title="",
                content=t("main.toast.custom_style_pro"),
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )
            self._bridge.settings_requested.emit()
            return
        dialog = CustomStyleDialog(self._config, parent=self)
        if dialog.exec():
            self._refresh_settings_labels()

    # ---------- operation runner ----------

    def _run_operation(
        self,
        fn: Callable[[], str],
        kind: str,
        label: str,
        meta: Optional[dict] = None,
    ):
        """Run `fn` off the GUI thread and paint the Result card from `kind`.

        `label` is a LOG string only — English, stable, greppable across a
        support log. What the user reads is derived from `kind` + `meta` by
        `_repaint_result_title()`; deriving it means the card can be re-titled on
        a language switch, which a label captured at dispatch could never be.
        """
        logger.info(f"Dispatching operation: {label} (kind={kind})")
        for btn in self._operation_buttons():
            btn.setEnabled(False)
        self.translate_pill.setEnabled(False)
        self._result_state = ("working", kind, dict(meta) if meta else {})
        self._repaint_result_title()
        self.result_card.set_generated_badge(False)

        worker = _OperationWorker(fn, kind=kind, label=label, meta=meta)
        # Direct method binding (no lambda) — gives the slot a QObject context
        # so cross-thread emit lands on the GUI thread via QueuedConnection.
        worker.signals.finished.connect(self._on_operation_finished)
        worker.signals.failed.connect(self._on_operation_failed)
        self._thread_pool.start(worker)

    @Slot(str, str, str, object)
    def _on_operation_finished(self, result: str, kind: str, label: str, meta: object):
        logger.info(f"Operation finished on GUI thread: {label}")
        self.result_card.set_text(result or "")
        self._result_state = ("done", kind, dict(meta) if isinstance(meta, dict) else {})
        self._repaint_result_title()
        self.result_card.set_generated_badge(bool(result))
        self._copy_to_clipboard(result)
        if result:
            self._history.add(result, kind=kind, meta=meta if isinstance(meta, dict) else {})
        self._set_operation_buttons_enabled(True)

    @Slot(str, str)
    def _on_operation_failed(self, message: str, label: str):
        logger.warning(f"Operation failed on GUI thread: {label} — {message}")
        self._result_state = ("idle", None, {})
        self._repaint_result_title()
        self.result_card.set_generated_badge(False)
        self._set_operation_buttons_enabled(True)
        # `message` is the provider's own exception text — not ours to translate.
        QMessageBox.warning(self, t("main.dialog.operation_failed"), message)

    def _set_operation_buttons_enabled(self, enabled: bool):
        if enabled and self._client is None:
            return
        for btn in self._operation_buttons():
            btn.setEnabled(enabled)
        self.translate_pill.setEnabled(enabled)

    def set_openai_client(self, client) -> None:
        """Swap the OpenAI client live and re-evaluate the text-operation
        buttons. Called after a settings save so a key added in Settings makes
        Translate/Fix/Rewrite usable without a restart (and a removed key
        disables them). Mirrors the enable/disable done in the constructor."""
        self._client = client
        enabled = client is not None
        for btn in self._operation_buttons():
            btn.setEnabled(enabled)
        self.translate_pill.setEnabled(enabled)
        self._refresh_client_tooltip()

    # ---------- settings ----------

    def _open_settings(self):
        # Request the settings window via the bridge. A single handler in the
        # main process owns one SettingsWindow and raises it on repeat requests,
        # so clicking this button (or the tray item) any number of times yields
        # at most one window. Opening in-process means it appears instantly —
        # no subprocess spawn / bundle re-extraction.
        self._bridge.settings_requested.emit()

    def _on_settings_saved(self):
        # Config is reloaded by the settings handler before settings_saved
        # fires; we just refresh our config-driven labels.
        self._refresh_settings_labels()

    # ---------- window lifecycle ----------

    def closeEvent(self, event):
        # Hide to tray instead of quitting. Exit is only via tray "Close".
        event.ignore()
        self.hide()

    def _center_on_screen(self):
        """Move the window so its frame is centred on the active screen's work
        area (availableGeometry excludes the taskbar)."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def show_and_focus(self):
        try:
            self._config.reload()
        except Exception as e:
            logger.warning(f"Config reload failed: {e}")
        try:
            self._glossary.reload()
            self._apply_glossary_entitlement()
        except Exception as e:
            logger.warning(f"Glossary reload failed: {e}")
        self._refresh_settings_labels()
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
            except Exception:
                pass
        self.show()
        # Restore from minimized state if needed — Qt's show() alone doesn't
        # un-minimize a window that was minimized to the taskbar.
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

        # Qt's activateWindow() is blocked by the Windows foreground lock when
        # another app currently owns foreground (e.g. IDE on top of our hidden
        # window). The standard workaround is to briefly attach to the
        # foreground thread's input queue — SetForegroundWindow is then allowed
        # to switch focus to our hwnd. Without this, double-tap silently fails
        # to raise the window when it's already visible-but-behind.
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                fg_hwnd = user32.GetForegroundWindow()
                if fg_hwnd and fg_hwnd != hwnd:
                    fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
                    own_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                    if fg_thread and fg_thread != own_thread:
                        user32.AttachThreadInput(fg_thread, own_thread, True)
                        try:
                            user32.BringWindowToTop(hwnd)
                            user32.SetForegroundWindow(hwnd)
                        finally:
                            user32.AttachThreadInput(fg_thread, own_thread, False)
                    else:
                        user32.SetForegroundWindow(hwnd)
            except Exception as e:
                logger.debug(f"Force-foreground via AttachThreadInput failed: {e}")

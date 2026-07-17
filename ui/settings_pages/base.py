# file: ui/settings_pages/base.py

"""
Common scaffolding for settings pages: scrollable content with a fixed header
(title + hint) and a vertical stack of section cards. Each section card has
its own title/hint and rows of form fields.

A subclass overrides `build()` (called from __init__) to populate the content
layout with cards, and `load_from`/`apply_to`/`validate` to wire to Config.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from i18n import t
from services.config_store import Config
from ui import style


def make_section_card(
    title: str,
    hint: Optional[str] = None,
    header_widget: Optional[QWidget] = None,
) -> tuple[QFrame, QVBoxLayout]:
    """Return a styled section card frame + its inner vbox for content rows.

    Used by individual pages to group related fields without each having to
    re-implement the same header markup. Pass `header_widget` to pin a control
    (e.g. a master switch) to the right of the title row, so the section header
    itself becomes the toggle instead of a separate row below it.
    """
    card = QFrame()
    card.setObjectName("settingsCard")
    card.setFrameShape(QFrame.NoFrame)

    outer = QVBoxLayout(card)
    outer.setContentsMargins(22, 16, 22, 16)
    outer.setSpacing(8)

    title_lbl = QLabel(title)
    title_lbl.setObjectName("cardSectionTitle")
    if header_widget is not None:
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(title_lbl)
        header.addStretch(1)
        header.addWidget(header_widget, alignment=Qt.AlignVCenter)
        outer.addLayout(header)
    else:
        outer.addWidget(title_lbl)

    if hint:
        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("cardSectionHint")
        hint_lbl.setWordWrap(True)
        outer.addWidget(hint_lbl)

    body = QVBoxLayout()
    body.setContentsMargins(0, 6, 0, 0)
    body.setSpacing(10)
    outer.addLayout(body)

    return card, body


LABEL_COL_WIDTH = 240
"""Fixed width of the left (label + hint) column in form / switch rows.

Predictable hint wrapping is the goal: hints with the same column width wrap
at the same character count, so vertical rhythm between rows stays even and
controls in the right column always start from the same X. Wide enough for
labels like "Custom-style hotkey" without truncation; not so wide that hints
collapse to one line and waste the right half on every row."""


def make_form_row(
    label_text: str,
    widget: QWidget,
    hint: Optional[str] = None,
    stretch_widget: bool = False,
    trailing: Optional[QWidget] = None,
    align_right: bool = False,
    label_top: bool = False,
    hint_gap: int = 1,
    hint_under_label: bool = False,
    widget_indent: int = 0,
    label_trailing: Optional[QWidget] = None,
) -> QWidget:
    """Label-on-the-left, widget-on-the-right form row.

    The left column is a fixed width (`LABEL_COL_WIDTH`) so hints wrap
    predictably and controls in the right column align across rows.

    Three widget-placement modes:
      - `stretch_widget=True`     widget grows to fill the row (multi-line edits).
      - `align_right=True`        widget is pinned to the row's right edge — use
                                  this whenever a card has a mix of controls
                                  (switches, fields, dropdowns) so all of them
                                  line up on one right column.
      - default                   widget sits left, just past the label column.

    `trailing` (default mode only) drops a widget on the row's right edge,
    past the stretch — used for the onboarding "← enter your key here" hints
    that point back at a left-pinned field. Not compatible with `align_right`.

    `label_top` aligns the label to the top of the row instead of its vertical
    centre — use it with tall multi-line widgets (e.g. a 160px TextEdit) so the
    label sits next to the *first* line of the field rather than floating in the
    middle of it.

    `hint_gap` is the vertical space between the control line and the hint
    below it (only when the hint sits *under the row*). The 1px default is
    deliberately tight to match `make_switch_row`.

    `hint_under_label` stacks the hint directly beneath the label in the fixed
    left column (instead of under the whole row), with the control taking the
    right side at full height. Use it when the control is tall (multi-line
    edit) or opens a popup (combo) so the hint stays glued to the label it
    explains rather than drifting below a big field. Implies a top-aligned row.

    `widget_indent` adds horizontal space before a left-placed (default-mode)
    widget — nudges combos a little further right of the label column.

    `label_trailing` drops a small widget right after the label *text* inside the
    fixed left column (e.g. a "?" help icon). The label keeps its natural width
    and a stretch fills the rest of the column, so the right column still aligns
    across rows. Only honoured in the plain-label branch (the one the API-key
    rows use); ignored under `hint_under_label`.
    """
    row = QWidget()
    # Shared object name + styled background so the whole row gets a hover band
    # (label + hint + control light up together) — see settings_qss #settingsRow.
    row.setObjectName("settingsRow")
    row.setAttribute(Qt.WA_StyledBackground, True)
    row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    outer = QVBoxLayout(row)
    outer.setContentsMargins(0, 0, 0, 0)
    # Tight gap from the top row to the hint. The taller field widgets in
    # form-rows (LineEdit / ComboBox ~33px vs SwitchButton ~28px) already add
    # extra padding under the VCenter-aligned label — without a tiny spacing
    # the hint feels detached. 1px here brings the visual gap in line with
    # make_switch_row (which uses 4 against a shorter switch).
    outer.setSpacing(hint_gap)

    # --- top: label (fixed col) + control ---
    top = QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(14)

    # Vertical alignment of the control: hug the top whenever the hint lives in
    # the left column, otherwise centre against the label.
    v_align = Qt.AlignTop if hint_under_label else Qt.AlignVCenter

    if hint and hint_under_label:
        # Stack [label / hint] in the fixed left column, pinned to the top so
        # the description reads as a sub-line of the label right next to the
        # field — not a footnote below a tall control.
        left_col = QWidget()
        left_col.setFixedWidth(LABEL_COL_WIDTH)
        lc = QVBoxLayout(left_col)
        lc.setContentsMargins(0, 0, 0, 0)
        lc.setSpacing(2)
        lbl = QLabel(label_text)
        lbl.setObjectName("rowLabel")
        lc.addWidget(lbl)
        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("rowHint")
        hint_lbl.setWordWrap(True)
        lc.addWidget(hint_lbl)
        lc.addStretch(1)
        top.addWidget(left_col, alignment=Qt.AlignTop)
    elif label_trailing is not None:
        # Label text + a trailing control (e.g. a "?" help icon) packed into the
        # fixed-width left column. The label hugs its text and a stretch eats the
        # remainder so the right column lines up with plain-label rows.
        left_col = QWidget()
        left_col.setFixedWidth(LABEL_COL_WIDTH)
        lc = QHBoxLayout(left_col)
        lc.setContentsMargins(0, 0, 0, 0)
        lc.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setObjectName("rowLabel")
        lc.addWidget(lbl, alignment=Qt.AlignVCenter)
        lc.addWidget(label_trailing, alignment=Qt.AlignVCenter)
        lc.addStretch(1)
        top.addWidget(left_col, alignment=Qt.AlignVCenter)
    else:
        lbl = QLabel(label_text)
        lbl.setObjectName("rowLabel")
        lbl.setFixedWidth(LABEL_COL_WIDTH)
        if label_top:
            # Nudge the label down a touch so it lines up with the first text
            # line inside the field rather than the widget's very top edge.
            lbl.setContentsMargins(0, 6, 0, 0)
            top.addWidget(lbl, alignment=Qt.AlignTop)
        else:
            top.addWidget(lbl, alignment=Qt.AlignVCenter)

    if stretch_widget:
        top.addWidget(widget, stretch=1, alignment=v_align)
        if trailing is not None:
            top.addWidget(trailing, alignment=Qt.AlignVCenter | Qt.AlignRight)
    elif align_right:
        # All controls in such a card share a single right edge — eliminates
        # the visual jump between fields of different widths.
        top.addStretch(1)
        top.addWidget(widget, alignment=v_align | Qt.AlignRight)
    else:
        # Pin widget to the left of the row so columns line up across cards
        # even when widgets have different maxWidths (e.g. 220 vs 360).
        if widget_indent:
            top.addSpacing(widget_indent)
        top.addWidget(widget, alignment=v_align | Qt.AlignLeft)
        top.addStretch(1)
        if trailing is not None:
            top.addWidget(trailing, alignment=Qt.AlignVCenter | Qt.AlignRight)

    outer.addLayout(top)

    # --- hint underneath, full row width — wraps freely instead of being
    # crammed into the narrow label column. Skipped when the hint already sits
    # under the label (hint_under_label).
    if hint and not hint_under_label:
        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("rowHint")
        hint_lbl.setWordWrap(True)
        outer.addWidget(hint_lbl)

    return row


def pulse_field_glow(widget: QWidget) -> None:
    """One soft accent glow (fade in/out, ~1.5s) around a widget, then clear.

    Used as a first-run onboarding cue to draw the eye to the API-key fields.
    The accent colour is read from the active palette at call time so it honours
    the current (light/dark) theme. The animation is parented to the widget and
    stashed on it so it survives until `finished` removes the effect.
    """
    pal = style.palette()
    effect = QGraphicsDropShadowEffect(widget)
    effect.setOffset(0, 0)
    effect.setColor(QColor(pal.ACCENT))
    effect.setBlurRadius(0)
    widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"blurRadius", widget)
    anim.setDuration(1500)
    anim.setKeyValueAt(0.0, 0)
    anim.setKeyValueAt(0.5, 30)
    anim.setKeyValueAt(1.0, 0)
    anim.setEasingCurve(QEasingCurve.InOutSine)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    widget._onboarding_glow = anim  # keep a ref so it isn't GC'd mid-run
    anim.start()


def make_link_label(url: str, text: str, object_name: str = "rowLink") -> QLabel:
    """A plain QLabel with a clickable href, accent-coloured inline.

    A QLabel's link colour is the palette `Link` role, which our QSS `color:`
    rule can't reach — so the anchor colour is baked into the inline style at
    build time, read from the active accent so it honours the light/dark theme.
    Keeps the left edge flush with sibling labels (a HyperlinkButton's button
    padding would shift the text and break column alignment)."""
    accent = style.palette().ACCENT
    lbl = QLabel(f'<a href="{url}" style="color:{accent}; text-decoration:none;">{text}</a>')
    lbl.setObjectName(object_name)
    lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
    lbl.setOpenExternalLinks(True)
    return lbl


def make_help_button(
    title: str,
    steps: list[str],
    link_text: str,
    link_url: str,
    tooltip: Optional[str] = None,
) -> QWidget:
    """A small "?" icon that opens a Fluent bubble with steps + a link button.

    Used next to a field whose value the user may not yet have (e.g. an API
    key): clicking the icon pops a bubble carrying the `steps` lines and a
    `HyperlinkButton` to `link_url`. `duration=-1` keeps the bubble open until
    the user dismisses it — the default auto-dismiss would close it before they
    could reach the link.

    `tooltip` defaults to the generic "Where do I get a key?" via a None
    sentinel rather than a literal default argument: a default is evaluated once
    at import, which under i18n freezes it in whatever locale was active then.
    Same rule as everywhere else — the lookup happens in the body.

    qfluent's stock teaching tip wraps the bubble in a transparent
    shadow-gutter and draws a downward tail; on our flat UI that reads as ugly
    transparent borders. We flatten it into a plain solid card: drop the soft
    shadow, collapse the tail margin, and hug the outer gutter (same spirit as
    `qfluent_patches` for combo popups). We also wire the close (×) button — the
    `TeachingTip` constructor leaves `view.closed` unconnected, so without this
    the × does nothing."""
    from qfluentwidgets import (
        FluentIcon,
        HyperlinkButton,
        TeachingTip,
        TeachingTipTailPosition,
        TeachingTipView,
        TransparentToolButton,
    )

    btn = TransparentToolButton(FluentIcon.HELP)
    btn.setFixedSize(22, 22)
    btn.setIconSize(QSize(14, 14))
    btn.setCursor(Qt.PointingHandCursor)
    btn.setToolTip(tooltip if tooltip is not None else t("common.help.where_key"))

    def _show() -> None:
        # TeachingTipView (not FlyoutView): its paintEvent is a no-op so only
        # the bubble paints — a plain FlyoutView would paint its own rounded
        # rect on top, giving a double border inside the bubble.
        view = TeachingTipView(
            title=title,
            content="\n".join(steps),
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
        )
        link = HyperlinkButton(parent=view)
        link.setUrl(link_url)
        link.setText(link_text)
        link.setIcon(FluentIcon.LINK)
        view.addWidget(link, align=Qt.AlignLeft)

        # Build the tip directly (not TeachingTip.make) so we can flatten it
        # *before* showEvent computes the position — no post-show reposition jump.
        tip = TeachingTip(
            view,
            target=btn,
            duration=-1,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            parent=btn.window(),
        )
        view.closed.connect(tip.close)            # make the × button work
        tip.bubble.setGraphicsEffect(None)        # drop the soft drop-shadow
        tip.bubble.hBoxLayout.setContentsMargins(0, 0, 0, 0)  # kill the tail strip
        tip.hBoxLayout.setContentsMargins(1, 1, 1, 1)         # hug the bubble
        tip.show()

    btn.clicked.connect(_show)
    return btn


def make_pro_tag(text: Optional[str] = None) -> QWidget:
    """A small 'Pro' tag-link placed next to a locked (Pro) feature.

    Phase 1A (waitlist): clicking opens the public waitlist page rather than an
    in-app purchase — a funnel, not a nag popup. It's a plain flat QPushButton
    (objectName ``proTag``) so the settings QSS themes it as an accent pill and
    it re-tints with the light/dark theme like every other styled control.

    `text` takes a None sentinel rather than a "Pro" default argument — a
    default is evaluated at import, before the locale is known. ("Pro" is the
    tier's name and stays Latin in every locale, so this one is theoretical
    today; the rule is worth holding anyway, because the next such default
    won't be.)
    """
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QPushButton

    from licensing.config import WAITLIST_URL

    btn = QPushButton(text if text is not None else t("common.pro"))
    btn.setObjectName("proTag")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setToolTip(t("common.pro.tooltip"))
    btn.setFlat(True)
    btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(WAITLIST_URL)))
    return btn


def make_switch_row(label_text: str, switch: QWidget, hint: Optional[str] = None) -> QWidget:
    """Switch-on-the-right row, same column geometry as `make_form_row`.

    The label and its (optional) hint stack in the left column; the switch is
    vertically centred against that whole block rather than pinned to the top
    line — so it sits in the middle of the row's hover band instead of hugging
    the top edge when a hint pushes the row taller."""
    row = QWidget()
    # Same hover-band treatment as make_form_row — see settings_qss #settingsRow.
    row.setObjectName("settingsRow")
    row.setAttribute(Qt.WA_StyledBackground, True)

    top = QHBoxLayout(row)
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(14)

    # Left column: label, with the hint stacked beneath it so the switch can
    # centre against the combined height. stretch=1 pushes the switch to the
    # right edge (matching the align_right form rows in the same card).
    left = QVBoxLayout()
    left.setContentsMargins(0, 0, 0, 0)
    left.setSpacing(4)
    lbl = QLabel(label_text)
    lbl.setObjectName("rowLabel")
    left.addWidget(lbl)
    if hint:
        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("rowHint")
        hint_lbl.setWordWrap(True)
        left.addWidget(hint_lbl)
    top.addLayout(left, stretch=1)
    top.addWidget(switch, alignment=Qt.AlignVCenter | Qt.AlignRight)
    return row


class BasePage(QWidget):
    """Scrollable settings page with title + page hint + content cards.

    Subclasses set `PAGE_TITLE_KEY` / `PAGE_HINT_KEY` (i18n catalog keys) class
    attributes, and implement `build(content_layout)` to add their cards to
    the vertical content layout.
    """

    # Catalog KEYS, not text. These are class attributes, so a `t()` call here
    # would be evaluated at *import* — freezing every page title at whatever
    # locale happened to be active when the module was first imported, which no
    # amount of rebuilding the page ever undoes. A key is locale-free; the
    # PAGE_TITLE/PAGE_HINT properties do the lookup per instance, at build time.
    # Settings pages are rebuilt after every save (see SettingsWindow._on_save →
    # close → OmniVerte's spare prebuild), so that is all the freshness needed —
    # a page never has to retranslate itself in place.
    PAGE_TITLE_KEY: str = ""
    PAGE_HINT_KEY: str = ""
    # Stable id used as the widget's objectName — FluentWindow uses it to track
    # which page is active in the sidebar. Each subclass overrides this.
    PAGE_ID: str = "page"

    @property
    def PAGE_TITLE(self) -> str:  # noqa: N802 — property replacing a class attr
        return t(self.PAGE_TITLE_KEY) if self.PAGE_TITLE_KEY else ""

    @property
    def PAGE_HINT(self) -> str:  # noqa: N802
        return t(self.PAGE_HINT_KEY) if self.PAGE_HINT_KEY else ""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName(self.PAGE_ID)
        self._build_chrome()
        # Cards and rows go into self._content_layout, set up by _build_chrome.
        self.build(self._content_layout)
        self._content_layout.addStretch(1)

    # ---------- chrome ----------

    def _build_chrome(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        inner = QWidget()
        inner.setObjectName("settingsPage")
        scroll.setWidget(inner)

        v = QVBoxLayout(inner)
        # Right margin slightly larger so cards don't kiss the scrollbar.
        v.setContentsMargins(36, 24, 36, 96)  # bottom: clearance for floating action bar
        v.setSpacing(14)

        title = QLabel(self.PAGE_TITLE)
        title.setObjectName("pageTitle")
        v.addWidget(title)
        if self.PAGE_HINT:
            hint = QLabel(self.PAGE_HINT)
            hint.setObjectName("pageHint")
            hint.setWordWrap(True)
            v.addWidget(hint)

        self._content_layout = v

    # ---------- contract — subclasses override ----------

    def build(self, content_layout: QVBoxLayout) -> None:
        """Populate `content_layout` with section cards. Subclass override."""
        raise NotImplementedError

    def load_from(self, config: Config) -> None:
        """Populate widgets from the current Config state. Subclass override."""

    def apply_to(self, config: Config) -> None:
        """Persist widget values back to Config. Subclass override."""

    def validate(self) -> Optional[str]:
        """Return error message string if invalid, otherwise None."""
        return None

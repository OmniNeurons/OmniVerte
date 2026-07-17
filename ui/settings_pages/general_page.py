# file: ui/settings_pages/general_page.py

"""
General settings: UI language, activation method, clipboard usage, floating
indicator visibility. These currently live in the tray menu only; bringing
them into the settings window makes it the single source of truth.

The local-transcription device picker lives on the Transcription page: it only
means anything for the local backend, so it belongs next to the backend choice
it depends on, not among the app-wide preferences here.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qfluentwidgets import (
    ComboBox,
    LineEdit,
    RadioButton,
    SwitchButton,
)

from i18n import UI_LOCALE_LABELS, UI_LOCALES, current_locale, t
from services import autostart
from services.config_store import Config
from ui.hotkey_capture import make_capture_field
from .base import (
    BasePage,
    make_form_row,
    make_section_card,
    make_switch_row,
)


# Label KEY → stored value. The right-hand value is canonical and never
# translated: it is what lands in config.env and what AudioWriter compares
# against. Only the label is looked up, and `apply_to` reads the value by combo
# INDEX, so a translated label can never reach disk.
#
# These hold catalog keys rather than text because a module-level `t()` would be
# evaluated at import — freezing the labels in whatever locale happened to be
# active then, in a way no rebuild ever fixes. `_labels()` does the lookup at
# build time.
MOUSE_BUTTON_CHOICES = [
    ("general.mouse.middle", "middle"),
    ("general.mouse.left", "left"),
    ("general.mouse.right", "right"),
]
# Which rewrite style the custom hotkey (F11 by default) applies.
CUSTOM_STYLE_CHOICES = [
    ("general.style.casual", "casual"),
    ("general.style.professional", "professional"),
    ("general.style.custom", "custom"),
]

def _labels(choices: list[tuple[str, str]]) -> list[str]:
    """Resolve a CHOICES table's label keys against the active locale."""
    return [t(key) for key, _ in choices]

# Fixed widths so every control on the page lines up on the same right edge
# regardless of its natural width (hotkey edits are narrow, dropdowns wider).
HOTKEY_FIELD_WIDTH = 120
COMBO_FIELD_WIDTH = 180

# How far the sub-rows under a mode radio are indented — wide enough to clear
# the radio indicator and read as a nested group, not equal-rank siblings.
SUBSECTION_INDENT = 28


def _subsection(*rows: QWidget) -> QWidget:
    """Container that nests its rows under a parent (radio) header. Adds a left
    indent so the visual hierarchy is obvious and forwards `setEnabled` to all
    children, so disabling the whole sub-block greys out labels + hints + the
    control together (instead of just the control, leaving stale labels)."""
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(SUBSECTION_INDENT, 0, 0, 0)
    layout.setSpacing(10)
    for row in rows:
        layout.addWidget(row)
    return box


class GeneralPage(BasePage):
    PAGE_ID = "settings-general"
    PAGE_TITLE_KEY = "page.general.title"
    PAGE_HINT_KEY = "page.general.hint"

    def build(self, content_layout: QVBoxLayout) -> None:
        # --- Interface ---
        # First card on the landing page, deliberately: someone who cannot read
        # the current UI language needs to find this without navigating, and
        # General is the page the settings window opens on.
        card, body = make_section_card(
            t("general.interface.title"),
            t("general.interface.hint"),
        )
        self.ui_language_combo = ComboBox()
        for code in UI_LOCALES:
            # Native language names, not catalog strings: a picker has to be
            # readable by someone who cannot read the language currently active
            # — which is exactly the situation they are in when they open it.
            # userData carries the code, so the label never reaches config.
            self.ui_language_combo.addItem(UI_LOCALE_LABELS[code], userData=code)
        self.ui_language_combo.setFixedWidth(COMBO_FIELD_WIDTH)
        body.addWidget(make_form_row(
            t("general.interface.language"),
            self.ui_language_combo,
            hint=t("general.interface.language.hint"),
            align_right=True,
        ))
        content_layout.addWidget(card)

        # --- Activation ---
        card, body = make_section_card(
            t("general.activation.title"),
            t("general.activation.hint"),
        )

        # === Keyboard mode: radio acts as a section header, sub-rows nested ===
        self.mode_keyboard = RadioButton(t("general.activation.keyboard"))
        self.mode_keyboard.setChecked(True)
        body.addWidget(self.mode_keyboard)

        self.hotkey_edit = LineEdit()
        self.hotkey_edit.setPlaceholderText("F9")
        self.hotkey_edit.setFixedWidth(HOTKEY_FIELD_WIDTH)
        transcribe_row = make_form_row(
            t("general.hotkey.transcribe"),
            make_capture_field(self.hotkey_edit),
            hint=t("general.hotkey.transcribe.hint"),
            align_right=True,
        )

        self.hotkey_translate_edit = LineEdit()
        self.hotkey_translate_edit.setPlaceholderText("F10")
        self.hotkey_translate_edit.setFixedWidth(HOTKEY_FIELD_WIDTH)
        translate_row = make_form_row(
            t("general.hotkey.translate"),
            make_capture_field(self.hotkey_translate_edit),
            hint=t("general.hotkey.translate.hint"),
            align_right=True,
        )

        self.hotkey_custom_edit = LineEdit()
        self.hotkey_custom_edit.setPlaceholderText("F11")
        self.hotkey_custom_edit.setFixedWidth(HOTKEY_FIELD_WIDTH)
        custom_row = make_form_row(
            t("general.hotkey.custom"),
            make_capture_field(self.hotkey_custom_edit),
            hint=t("general.hotkey.custom.hint"),
            align_right=True,
        )

        self.custom_style_combo = ComboBox()
        self.custom_style_combo.addItems(_labels(CUSTOM_STYLE_CHOICES))
        self.custom_style_combo.setFixedWidth(COMBO_FIELD_WIDTH)
        # Instead of a plain "Applied style" row, pair the hotkey and the style
        # it applies inside one tinted panel — so the relationship between the
        # F11 button and this dropdown is unmistakable.
        custom_style_row = self._build_style_pair_panel(self.custom_style_combo)

        self.suppress_switch = SwitchButton()
        self.suppress_switch.setOnText(t("common.on"))
        self.suppress_switch.setOffText(t("common.off"))
        suppress_row = make_switch_row(
            t("general.suppress"),
            self.suppress_switch,
            hint=t("general.suppress.hint"),
        )

        # Group everything that belongs to the Keyboard mode under one widget
        # so disabling it on a mode switch also greys out the labels + hints,
        # not just the controls.
        self.keyboard_sub = _subsection(
            transcribe_row, translate_row, custom_row, custom_style_row, suppress_row,
        )
        body.addWidget(self.keyboard_sub)

        # === Mouse mode: same pattern, one sub-row ===
        # Extra breathing space so the two mode sections read as distinct;
        # without it the Mouse radio looks like just another sub-row of the
        # keyboard section above.
        body.addSpacing(8)
        self.mode_mouse = RadioButton(t("general.activation.mouse"))
        body.addWidget(self.mode_mouse)

        self.mouse_btn_combo = ComboBox()
        self.mouse_btn_combo.addItems(_labels(MOUSE_BUTTON_CHOICES))
        self.mouse_btn_combo.setFixedWidth(COMBO_FIELD_WIDTH)
        mouse_row = make_form_row(
            t("general.mouse.label"),
            self.mouse_btn_combo,
            hint=t("general.mouse.hint"),
            align_right=True,
        )
        self.mouse_sub = _subsection(mouse_row)
        body.addWidget(self.mouse_sub)

        self.mode_keyboard.toggled.connect(self._on_mode_toggle)
        content_layout.addWidget(card)

        # --- Behaviour toggles ---
        card, body = make_section_card(t("general.behaviour.title"))
        self.floating_switch = SwitchButton()
        self.floating_switch.setOnText(t("common.on"))
        self.floating_switch.setOffText(t("common.off"))
        body.addWidget(make_switch_row(
            t("general.behaviour.floating"),
            self.floating_switch,
            hint=t("general.behaviour.floating.hint"),
        ))

        self.double_tap_switch = SwitchButton()
        self.double_tap_switch.setOnText(t("common.on"))
        self.double_tap_switch.setOffText(t("common.off"))
        body.addWidget(make_switch_row(
            t("general.behaviour.double_tap"),
            self.double_tap_switch,
            hint=t("general.behaviour.double_tap.hint"),
        ))

        self.autostart_switch = SwitchButton()
        self.autostart_switch.setOnText(t("common.on"))
        self.autostart_switch.setOffText(t("common.off"))
        body.addWidget(make_switch_row(
            t("general.behaviour.autostart"),
            self.autostart_switch,
            hint=t("general.behaviour.autostart.hint"),
        ))
        content_layout.addWidget(card)

    # ---------- helpers ----------

    def _build_style_pair_panel(self, combo: QWidget) -> QWidget:
        """A softly-tinted panel that ties the custom hotkey to the rewrite
        style it applies — reads as `[F11] Custom → [ style ▾ ]`.

        The keycap badge mirrors whatever key is set in the Custom-style hotkey
        field above (live), so the mapping stays correct even after a rebind —
        no hard-coded "F11" to drift out of sync.
        """
        panel = QFrame()
        panel.setObjectName("stylePairPanel")

        outer = QVBoxLayout(panel)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(6)

        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(10)

        self.custom_hotkey_badge = QLabel("F11")
        self.custom_hotkey_badge.setObjectName("hotkeyBadge")
        line.addWidget(self.custom_hotkey_badge, alignment=Qt.AlignVCenter)

        name = QLabel(t("general.stylepair.name"))
        name.setObjectName("stylePairName")
        line.addWidget(name, alignment=Qt.AlignVCenter)

        arrow = QLabel("→")
        arrow.setObjectName("stylePairArrow")
        line.addWidget(arrow, alignment=Qt.AlignVCenter)

        line.addStretch(1)
        line.addWidget(combo, alignment=Qt.AlignVCenter | Qt.AlignRight)
        outer.addLayout(line)

        self.custom_style_hint = QLabel()
        self.custom_style_hint.setObjectName("rowHint")
        self.custom_style_hint.setWordWrap(True)
        outer.addWidget(self.custom_style_hint)

        # Keep the badge + hint copy in step with the (editable) hotkey field.
        self.hotkey_custom_edit.textChanged.connect(self._sync_custom_style_pair)
        self._sync_custom_style_pair()
        return panel

    def _sync_custom_style_pair(self) -> None:
        key = (
            self.hotkey_custom_edit.text().strip()
            or self.hotkey_custom_edit.placeholderText()
            or "F11"
        )
        self.custom_hotkey_badge.setText(key)
        self.custom_style_hint.setText(t("general.stylepair.hint", key=key))

    def _on_mode_toggle(self, _checked: bool):
        keyboard_mode = self.mode_keyboard.isChecked()
        # Disable the inactive sub-section as a whole — labels + hints get
        # greyed too, making the active/inactive state read at a glance.
        self.keyboard_sub.setEnabled(keyboard_mode)
        self.mouse_sub.setEnabled(not keyboard_mode)

    # ---------- Config interface ----------

    def load_from(self, config: Config) -> None:
        # "" means auto (follow the OS) and only a fresh install has it. Show
        # what the app is actually speaking right now rather than a separate
        # "Auto" entry: the user is looking at the resolved language, so an
        # "Auto" item would answer a question they didn't ask and hide the one
        # they did. Onboarding freezes this same value into config.
        ui_lang = (config.get("UI_LANGUAGE") or "").strip().lower() or current_locale()
        idx = self.ui_language_combo.findData(ui_lang)
        self.ui_language_combo.setCurrentIndex(idx if idx >= 0 else 0)

        mode = (config.get("ACTIVATION_MODE") or "keyboard").lower()
        if mode == "mouse":
            self.mode_mouse.setChecked(True)
        else:
            self.mode_keyboard.setChecked(True)

        # Transcribe key: prefer the new key, fall back to the legacy one.
        self.hotkey_edit.setText(config.get("HOTKEY_TRANSCRIBE") or config.get("ACTIVATION_KEY") or "F9")
        self.hotkey_translate_edit.setText(config.get("HOTKEY_TRANSLATE") or "F10")
        self.hotkey_custom_edit.setText(config.get("HOTKEY_CUSTOM") or "F11")

        current_style = (config.get("HOTKEY_CUSTOM_STYLE") or "custom").lower()
        for i, (_, value) in enumerate(CUSTOM_STYLE_CHOICES):
            if value == current_style:
                self.custom_style_combo.setCurrentIndex(i)
                break

        self.suppress_switch.setChecked((config.get("HOTKEYS_SUPPRESS") or "true").lower() == "true")

        current_btn = (config.get("MOUSE_ACTIVATION_BUTTON") or "middle").lower()
        for i, (_, value) in enumerate(MOUSE_BUTTON_CHOICES):
            if value == current_btn:
                self.mouse_btn_combo.setCurrentIndex(i)
                break

        self.floating_switch.setChecked((config.get("SHOW_FLOATING_INDICATOR") or "true").lower() == "true")
        self.double_tap_switch.setChecked((config.get("DOUBLE_TAP_OPENS_WINDOW") or "true").lower() == "true")

        # Autostart lives in the registry, not config — read the real state.
        self.autostart_switch.setChecked(autostart.is_enabled())

        self._on_mode_toggle(True)

    def apply_to(self, config: Config) -> None:
        # The combo's userData, never its label — the label is a native language
        # name shown to the user and would be meaningless in config.env.
        # OmniVerte._on_saved reads this back and switches the live locale.
        config.set("UI_LANGUAGE", self.ui_language_combo.currentData())

        mode = "keyboard" if self.mode_keyboard.isChecked() else "mouse"
        config.set("ACTIVATION_MODE", mode)

        # Always persist the user's currently-typed keys, even when mode=mouse,
        # so toggling back to keyboard later restores their preferred hotkeys.
        hotkey = self.hotkey_edit.text().strip() or "F9"
        config.set("HOTKEY_TRANSCRIBE", hotkey)
        config.set("ACTIVATION_KEY", hotkey)  # keep legacy key in sync
        config.set("HOTKEY_TRANSLATE", self.hotkey_translate_edit.text().strip() or "F10")
        config.set("HOTKEY_CUSTOM", self.hotkey_custom_edit.text().strip() or "F11")
        _, style_val = CUSTOM_STYLE_CHOICES[self.custom_style_combo.currentIndex()]
        config.set("HOTKEY_CUSTOM_STYLE", style_val)
        config.set("HOTKEYS_SUPPRESS", "true" if self.suppress_switch.isChecked() else "false")

        _, mouse_val = MOUSE_BUTTON_CHOICES[self.mouse_btn_combo.currentIndex()]
        config.set("MOUSE_ACTIVATION_BUTTON", mouse_val)

        config.set("SHOW_FLOATING_INDICATOR", "true" if self.floating_switch.isChecked() else "false")
        config.set("DOUBLE_TAP_OPENS_WINDOW", "true" if self.double_tap_switch.isChecked() else "false")

        # Autostart is registry-backed, not stored in config. Idempotent.
        autostart.set_enabled(self.autostart_switch.isChecked())

    def validate(self) -> Optional[str]:
        if not self.mode_keyboard.isChecked():
            return None
        # Action-name key → the field holding that action's hotkey. The name is
        # a catalog key rather than text so the error message declines properly
        # in languages where "Transcribe hotkey can't be empty" is not simply
        # the action's name with a suffix bolted on.
        fields = [
            ("general.action.transcribe", self.hotkey_edit),
            ("general.action.translate", self.hotkey_translate_edit),
            ("general.action.custom", self.hotkey_custom_edit),
        ]
        keys = [(name_key, edit.text().strip()) for name_key, edit in fields]
        for name_key, key in keys:
            if not key:
                return t("general.error.hotkey_empty", action=t(name_key))
        # Two actions on the same key would both fire — reject duplicates.
        normalised = [k.lower() for _, k in keys]
        if len(set(normalised)) != len(normalised):
            return t("general.error.hotkey_duplicate")
        return None

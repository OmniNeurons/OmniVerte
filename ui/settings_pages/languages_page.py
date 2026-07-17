# file: ui/settings_pages/languages_page.py

"""
Translation language pair. Direction between the two is auto-detected at
translate time, so the order is mostly cosmetic — but the two must differ.

This is the *dictation* axis and has nothing to do with the interface language
(General → Interface): what you speak is not what the app speaks back. The two
are deliberately separate settings — Russian developers dictate in Russian and
read English UIs, and vice versa.

The language *names* in these combos stay English, unlike the rest of the page.
They are not chrome: `apply_to` writes `currentText()` straight into
PRIMARY_LANGUAGE, and `services/text_operations.py` looks that value up in
SUPPORTED_LANGUAGES / LANGUAGE_TO_WHISPER_CODE. Translating the labels would
put "Английский" in config.env and silently break both the Whisper language
hint and the translate direction. Localizing them means giving the combo a
value/label split (`addItem(label, userData=value)` + `currentData()`, the way
the glossary pack picker already does it) — worth doing, but as its own change
where the persistence can be tested, not as a side effect of translating chrome.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import ComboBox, FluentIcon as FIF, TransparentPushButton

from i18n import t
from services.config_store import Config
from services.text_operations import SUPPORTED_LANGUAGES
from .base import BasePage, make_form_row, make_section_card


# Fixed width for both language combos so Primary and Secondary are identical
# regardless of the chosen name's length (e.g. "English" vs "Japanese") — the
# default size-to-content behaviour made the two rows look mismatched.
COMBO_WIDTH = 220


class LanguagesPage(BasePage):
    PAGE_ID = "settings-languages"
    PAGE_TITLE_KEY = "page.languages.title"
    PAGE_HINT_KEY = "page.languages.hint"

    def build(self, content_layout: QVBoxLayout) -> None:
        card, body = make_section_card(t("languages.pair.title"))

        # `hint_under_label` keeps each description tucked right under its
        # Primary/Secondary label, and `widget_indent` nudges the combo a bit
        # further right — so the open dropdown no longer lands on the hint and
        # it's obvious which language each control belongs to.
        self.primary_combo = ComboBox()
        self.primary_combo.addItems(list(SUPPORTED_LANGUAGES.keys()))
        self.primary_combo.setFixedWidth(COMBO_WIDTH)
        body.addWidget(make_form_row(
            t("languages.primary"),
            self.primary_combo,
            hint=t("languages.primary.hint"),
            hint_under_label=True,
            widget_indent=40,
        ))

        self.secondary_combo = ComboBox()
        self.secondary_combo.addItems(list(SUPPORTED_LANGUAGES.keys()))
        self.secondary_combo.setFixedWidth(COMBO_WIDTH)
        body.addWidget(make_form_row(
            t("languages.secondary"),
            self.secondary_combo,
            hint=t("languages.secondary.hint"),
            hint_under_label=True,
            widget_indent=40,
        ))

        # One-click swap of the two selections — handy for flipping the pair
        # (e.g. Russian ⇄ English) without re-picking both combos.
        self.swap_btn = TransparentPushButton(FIF.SYNC, t("languages.swap"))
        self.swap_btn.setToolTip(t("languages.swap.tooltip"))
        self.swap_btn.clicked.connect(self._swap_languages)
        swap_row = QWidget()
        swap_layout = QHBoxLayout(swap_row)
        swap_layout.setContentsMargins(0, 0, 0, 0)
        swap_layout.addWidget(self.swap_btn, alignment=Qt.AlignLeft)
        swap_layout.addStretch(1)
        body.addWidget(swap_row)

        content_layout.addWidget(card)

    def _swap_languages(self) -> None:
        primary = self.primary_combo.currentText()
        secondary = self.secondary_combo.currentText()
        pi = self.primary_combo.findText(secondary)
        si = self.secondary_combo.findText(primary)
        if pi >= 0:
            self.primary_combo.setCurrentIndex(pi)
        if si >= 0:
            self.secondary_combo.setCurrentIndex(si)

    def load_from(self, config: Config) -> None:
        primary = config.get("PRIMARY_LANGUAGE") or "English"
        secondary = config.get("SECONDARY_LANGUAGE") or "Russian"
        idx = self.primary_combo.findText(primary)
        if idx >= 0:
            self.primary_combo.setCurrentIndex(idx)
        idx = self.secondary_combo.findText(secondary)
        if idx >= 0:
            self.secondary_combo.setCurrentIndex(idx)

    def apply_to(self, config: Config) -> None:
        config.set("PRIMARY_LANGUAGE", self.primary_combo.currentText())
        config.set("SECONDARY_LANGUAGE", self.secondary_combo.currentText())

    def validate(self) -> Optional[str]:
        if self.primary_combo.currentText() == self.secondary_combo.currentText():
            return t("languages.error.must_differ")
        return None

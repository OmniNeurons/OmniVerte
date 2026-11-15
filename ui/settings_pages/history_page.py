# file: ui/settings_pages/history_page.py

"""
History settings: how long the Pro encrypted history keeps entries, what it
holds right now, and a one-click wipe.

The wipe runs immediately behind a confirmation — not in `apply_to` — because
Cancel on the settings window only skips writing config; it cannot un-delete.
It works on every tier: a Free user must be able to erase what an expired Pro
left on disk.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from qfluentwidgets import ComboBox, MessageBox, PushButton

from i18n import t
from services.config_store import Config
from .base import BasePage, make_form_row, make_pro_tag, make_section_card

# Retention choices offered in the combo, in days.
RETENTION_CHOICES = (7, 14, 30, 90, 180, 365)


class HistoryPage(BasePage):
    PAGE_ID = "settings-history"
    PAGE_TITLE_KEY = "page.history.title"
    PAGE_HINT_KEY = "page.history.hint"

    def __init__(self, history_manager=None, parent: Optional[QWidget] = None):
        # Set before super().__init__, which calls build().
        self._history = history_manager
        super().__init__(parent)

    def _manager(self):
        if self._history is None:
            # Standalone `--settings` run: no app-wide manager — build one; it
            # reads the same encrypted store on Pro.
            from ui.history_manager import HistoryManager

            self._history = HistoryManager()
        return self._history

    def build(self, content_layout: QVBoxLayout) -> None:
        self.pro_tag = make_pro_tag()
        card, body = make_section_card(
            t("settings.history.storage.title"),
            hint=t("settings.history.storage.hint"),
            header_widget=self.pro_tag,
        )

        self.retention_combo = ComboBox()
        self._retention_values: list[int] = []
        self._fill_retention(RETENTION_CHOICES)
        body.addWidget(make_form_row(
            t("settings.history.retention"),
            self.retention_combo,
            hint=t("settings.history.retention.hint"),
        ))

        self.pro_hint = QLabel(t("settings.history.pro_hint"))
        self.pro_hint.setObjectName("onboardingHint")
        self.pro_hint.setWordWrap(True)
        self.pro_hint.hide()
        body.addWidget(self.pro_hint)

        content_layout.addWidget(card)

        clear_card, clear_body = make_section_card(
            t("settings.history.clear.title"),
            hint=t("settings.history.clear.hint"),
        )
        self.status_label = QLabel("")
        self.status_label.setObjectName("rowHint")
        self.status_label.setWordWrap(True)
        clear_body.addWidget(self.status_label)

        self.clear_btn = PushButton(t("history.clear.button"))
        self.clear_btn.clicked.connect(self._on_clear)
        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 4, 0, 0)
        row_layout.addWidget(self.clear_btn)
        row_layout.setAlignment(self.clear_btn, Qt.AlignLeft)
        clear_body.addWidget(row)

        content_layout.addWidget(clear_card)

    # ---------- retention ----------

    def _fill_retention(self, values) -> None:
        self.retention_combo.clear()
        self._retention_values = list(values)
        for days in self._retention_values:
            self.retention_combo.addItem(t("settings.history.retention.days", days=days))

    def _select_retention(self, days: int) -> None:
        if days not in self._retention_values:
            # A hand-edited value outside the presets stays selectable as is.
            self._fill_retention(sorted({*RETENTION_CHOICES, days}))
        self.retention_combo.setCurrentIndex(self._retention_values.index(days))

    def selected_retention(self) -> int:
        i = self.retention_combo.currentIndex()
        if 0 <= i < len(self._retention_values):
            return self._retention_values[i]
        return 30

    # ---------- gate + status ----------

    def _apply_gate(self) -> None:
        from licensing import Feature, get_entitlement

        try:
            pro = get_entitlement().has(Feature.PERSISTENT_HISTORY)
        except Exception:
            pro = False
        self.retention_combo.setEnabled(pro)
        self.pro_hint.setVisible(not pro)
        self.pro_tag.setVisible(not pro)

    def _refresh_status(self) -> None:
        manager = self._manager()
        count, chars, oldest = manager.totals()
        if count == 0:
            self.status_label.setText(t("history.status.empty"))
        elif manager.persistent:
            self.status_label.setText(t(
                "history.status.stored",
                count=count, chars=f"{chars:,}".replace(",", " "),
                since=oldest.strftime("%d.%m.%Y") if oldest else "—",
            ))
        else:
            self.status_label.setText(t("history.status.session", count=count))

    def _on_clear(self) -> None:
        box = MessageBox(
            t("history.clear.confirm.title"),
            t("history.clear.confirm.text"),
            self.window(),
        )
        box.yesButton.setText(t("history.clear.button"))
        box.cancelButton.setText(t("common.cancel"))
        if not box.exec():
            return
        self._manager().clear()
        self._refresh_status()

    def refresh_entitlement_gates(self) -> None:
        self._apply_gate()
        self._refresh_status()

    # ---------- contract ----------

    def load_from(self, config: Config) -> None:
        self._select_retention(config.history_retention_days)
        self._apply_gate()
        self._refresh_status()

    def apply_to(self, config: Config) -> None:
        config.set("HISTORY_RETENTION_DAYS", str(self.selected_retention()))

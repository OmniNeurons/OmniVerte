# file: ui/custom_style_dialog.py

"""
Tiny modal for editing the "Custom" rewrite-style preset.

Reachable from the main window's gear icon next to the Custom button, and
also auto-opened on the first Custom-button click when the prompt is empty.
Writes to the same config keys (CUSTOM_STYLE_NAME, CUSTOM_STYLE_PROMPT) as
the onboarding dialog's Custom-style section.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from qframelesswindow import FramelessDialog, StandardTitleBar
from qfluentwidgets import Theme, setTheme

from i18n import t
from services.config_store import Config
from ui import style
from ui.style import dialog_qss


class CustomStyleDialog(FramelessDialog):
    """Edit the Custom rewrite-style name and prompt.

    Frameless + StandardTitleBar so the header themes with Fluent (light/dark)
    and matches the main and settings windows, instead of a native OS title bar
    that would stay light in dark mode.
    """

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config

        # Custom title bar — themed by Fluent, like the main window. A modal
        # editor can only be closed, so drop the min/max affordances.
        self.setTitleBar(StandardTitleBar(self))
        self.titleBar.minBtn.hide()
        self.titleBar.maxBtn.hide()
        self.titleBar.setDoubleClickEnabled(False)
        try:
            self.titleBar.iconLabel.hide()
        except Exception:
            pass

        self.setWindowTitle(t("customstyledialog.title"))
        self.titleBar.setTitle(t("customstyledialog.title"))
        # Resizable with a comfortable floor (matches the old dialog's behaviour);
        # the title bar adds height, so the minimum is a touch taller than before.
        self.setMinimumSize(440, 380)
        self.resize(460, 440)

        # Match the active palette: Fluent theme drives the title-bar buttons,
        # our sheet drives the body. The dialog is short-lived/modal, so it
        # doesn't need live re-theming while shown.
        setTheme(Theme.DARK if style.is_dark() else Theme.LIGHT)
        self.setStyleSheet(dialog_qss(style.palette()))

        self._build_ui()
        self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)
        # Clear the title-bar strip overlaid at the top (same trick as MainWindow).
        title_bar_h = max(self.titleBar.height(), 32)
        root.setContentsMargins(20, title_bar_h + 6, 20, 18)
        root.setSpacing(12)

        title = QLabel(t("customstyledialog.title"))
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        hint = QLabel(t("customstyledialog.hint"))
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 14)
        card_layout.setSpacing(10)

        name_label = QLabel(t("customstyledialog.name"))
        name_label.setObjectName("fieldLabel")
        card_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("customstyledialog.name.placeholder"))
        card_layout.addWidget(self.name_input)

        prompt_label = QLabel(t("customstyledialog.prompt"))
        prompt_label.setObjectName("fieldLabel")
        card_layout.addWidget(prompt_label)

        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText(t("customstyledialog.prompt.placeholder"))
        self.prompt_input.setMinimumHeight(110)
        card_layout.addWidget(self.prompt_input)

        root.addWidget(card)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton(t("common.save"))
        save_btn.setObjectName("primary")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)

        # Keep the title bar (and its close button) above the content layout.
        self.titleBar.raise_()

    def _populate(self):
        self.name_input.setText(self._config.get("CUSTOM_STYLE_NAME") or "")
        self.prompt_input.setPlainText(self._config.get("CUSTOM_STYLE_PROMPT") or "")

    def _on_save(self):
        name = self.name_input.text().strip()
        prompt = self.prompt_input.toPlainText().strip()

        # Pro gate on the number of *own* style presets (Free = 1). The current
        # model is a single editable slot, so the count of presets that already
        # exist (excluding the one being edited) is 0 and the guard always
        # passes — the code path is ready for when the multipreset store lands.
        # TODO: подключить к стору пресетов (current = len(own_presets - this)).
        current_preset_count = 0
        from licensing import get_entitlement

        if not get_entitlement().allows_count("style_presets", current_preset_count):
            self._show_preset_limit_hint()
            return

        self._config.set("CUSTOM_STYLE_NAME", name)
        self._config.set("CUSTOM_STYLE_PROMPT", prompt)
        self.accept()

    def _show_preset_limit_hint(self):
        """Unobtrusive nudge when the Free preset cap is hit (no nag, no timer)."""
        from qfluentwidgets import InfoBar, InfoBarPosition

        InfoBar.info(
            title="",
            content=t("customstyledialog.preset_limit"),
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self,
        )

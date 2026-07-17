# file: ui/settings_pages/custom_style_page.py

"""
Custom rewrite-style preset — the prompt and display name used by the
"Custom" rewrite button in the main window. Same two config keys as the
gear-button quick dialog (which remains for fast edits).
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from qfluentwidgets import FlowLayout, LineEdit, MessageBox, PushButton, TextEdit

from i18n import t
from services.config_store import Config
from .base import BasePage, make_form_row, make_pro_tag, make_section_card
from .custom_style_templates import CUSTOM_STYLE_TEMPLATES, StyleTemplate


class CustomStylePage(BasePage):
    PAGE_ID = "settings-custom-style"
    PAGE_TITLE_KEY = "page.customstyle.title"
    PAGE_HINT_KEY = "page.customstyle.hint"

    def build(self, content_layout: QVBoxLayout) -> None:
        # 'Pro' tag-link in the header → waitlist; hidden once editing unlocks.
        self.pro_tag = make_pro_tag()
        card, body = make_section_card(t("customstyle.preset.title"), header_widget=self.pro_tag)

        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText(t("customstyle.name.placeholder"))
        body.addWidget(make_form_row(
            t("customstyle.name"),
            self.name_edit,
            hint=t("customstyle.name.hint"),
            stretch_widget=True,
        ))

        self.prompt_edit = TextEdit()
        self.prompt_edit.setPlaceholderText(t("customstyle.prompt.placeholder"))
        self.prompt_edit.setMinimumHeight(160)
        # `hint_under_label`: the field is 160px tall, so a bottom-of-row hint
        # drifts way below the big box. Stack the description right under the
        # "Instruction" label in the left column, with the field on the right.
        body.addWidget(make_form_row(
            t("customstyle.prompt"),
            self.prompt_edit,
            hint=t("customstyle.prompt.hint"),
            stretch_widget=True,
            hint_under_label=True,
        ))

        # Free gate: editing the free-text instruction is Pro. The hint shows
        # only on Free (toggled in _apply_edit_gate); templates stay usable.
        self.pro_hint = QLabel(t("customstyle.pro_hint"))
        self.pro_hint.setObjectName("onboardingHint")
        self.pro_hint.setWordWrap(True)
        self.pro_hint.hide()
        body.addWidget(self.pro_hint)

        content_layout.addWidget(card)

        # Profession presets: one click fills the two fields above with a
        # ready-made starting point the user can then tweak.
        tpl_card, tpl_body = make_section_card(
            t("customstyle.templates.title"),
            hint=t("customstyle.templates.hint"),
        )
        btn_container = QWidget()
        flow = FlowLayout(btn_container, needAni=False)
        flow.setContentsMargins(0, 0, 0, 0)
        flow.setHorizontalSpacing(8)
        flow.setVerticalSpacing(8)
        for tpl in CUSTOM_STYLE_TEMPLATES:
            # The name is chrome, resolved here rather than in the template table
            # so it follows the UI locale. The prompt is model input and stays
            # English — see the templates module's docstring for why.
            name = t(tpl.name_key)
            btn = PushButton(f"{tpl.emoji} {name}")
            btn.setToolTip(t("customstyle.templates.tooltip", name=name))
            # Bound as `tpl`, not `t`: `t` is the catalog lookup in this module.
            btn.clicked.connect(lambda _=False, tpl=tpl: self._apply_template(tpl))
            flow.addWidget(btn)
        tpl_body.addWidget(btn_container)

        content_layout.addWidget(tpl_card)

    def _apply_template(self, tpl: StyleTemplate) -> None:
        """Copy a template into the two fields (import-copy, like a glossary pack).

        The name is resolved in the locale active at click time and then belongs
        to the user: it is an ordinary editable field that saves to
        CUSTOM_STYLE_NAME, so a later language switch does not rewrite it. That
        is the point — by then it is their style's name, not our label.
        """
        name = t(tpl.name_key)
        # Guard against silently clobbering text the user has already written.
        if self.prompt_edit.toPlainText().strip():
            box = MessageBox(
                t("customstyle.templates.replace.title"),
                t("customstyle.templates.replace.text", name=name),
                self.window(),
            )
            if not box.exec():
                return
        self.name_edit.setText(name)
        self.prompt_edit.setPlainText(tpl.prompt)

    def load_from(self, config: Config) -> None:
        self.name_edit.setText(config.get("CUSTOM_STYLE_NAME") or "")
        self.prompt_edit.setPlainText(config.get("CUSTOM_STYLE_PROMPT") or "")
        self._apply_edit_gate()

    def _apply_edit_gate(self) -> None:
        """Free can apply templates but not hand-edit the text; Pro edits freely.

        Disabling (not just read-only) greys the fields so they clearly read as
        unavailable. setPlainText still works on a disabled widget, so the
        template buttons keep populating the fields, and the chosen style saves
        and runs normally on Free."""
        from licensing import Feature, get_entitlement

        can_edit = get_entitlement().has(Feature.CUSTOM_STYLE_EDITING)
        self.name_edit.setEnabled(can_edit)
        self.prompt_edit.setEnabled(can_edit)
        self.pro_hint.setVisible(not can_edit)
        self.pro_tag.setVisible(not can_edit)

    def apply_to(self, config: Config) -> None:
        config.set("CUSTOM_STYLE_NAME", self.name_edit.text().strip())
        config.set("CUSTOM_STYLE_PROMPT", self.prompt_edit.toPlainText().strip())

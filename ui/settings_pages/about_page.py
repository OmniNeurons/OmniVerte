# file: ui/settings_pages/about_page.py

"""
Read-only "About" page: version, app id, project link. No apply step.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from i18n import t
from services.config_store import Config
from ui import style
from .base import BasePage, make_form_row, make_section_card


def _value_label(text: str) -> QLabel:
    """Right-column value label, themed via #rowValue (else it falls back to
    Qt's default near-black text — invisible on the dark palette)."""
    lbl = QLabel(text)
    lbl.setObjectName("rowValue")
    return lbl


def _link_label(url: str, text: str) -> QLabel:
    """Plain QLabel with a clickable href — keeps the left edge flush with
    sibling QLabels (HyperlinkButton has button-style internal padding that
    would shift the text right and break column alignment).

    The anchor colour comes from the active accent inline: a QLabel's link
    colour is the palette Link role, which our QSS `color:` rule can't reach, so
    the default dark-blue would be unreadable on the dark theme without this."""
    accent = style.palette().ACCENT
    lbl = QLabel(f'<a href="{url}" style="color:{accent}; text-decoration:none;">{text}</a>')
    lbl.setObjectName("rowLink")
    lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
    lbl.setOpenExternalLinks(True)
    return lbl


def _read_version() -> str:
    """Read VERSION file at the project root (or PyInstaller bundle root).

    The version itself is data and ships as-is; only the "we couldn't read it"
    fallback is chrome, so that one goes through the catalog."""
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for path in (
        os.path.join(here, "VERSION"),
        os.path.join(os.path.dirname(here), "VERSION"),
    ):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip() or t("about.version.unknown")
        except OSError:
            continue
    return t("about.version.unknown")


class AboutPage(BasePage):
    PAGE_ID = "settings-about"
    PAGE_TITLE_KEY = "page.about.title"
    PAGE_HINT_KEY = ""  # the page's own card carries the tagline; no page hint

    def build(self, content_layout: QVBoxLayout) -> None:
        card, body = make_section_card(
            t("app.title"),
            hint=t("app.tagline"),
        )

        # Every right-column value here is DATA, not chrome — the version string,
        # the Windows app id, the developer's name, the address and the URL are
        # the same bytes in every locale, so only the labels go through t().
        # "AppUserModelID" is a label but stays literal too: it is the exact
        # Windows API term, and a user grepping for why their taskbar grouping
        # broke needs to find that spelling, not a translation of it.
        body.addWidget(make_form_row(t("about.version"), _value_label(_read_version())))
        body.addWidget(make_form_row("AppUserModelID", _value_label("OmniVerte.App.1")))
        body.addWidget(make_form_row(t("about.developer"), _value_label("Arsenii Bandurin")))
        body.addWidget(make_form_row(
            t("about.email"),
            _link_label("mailto:arsenybandurin@gmail.com", "arsenybandurin@gmail.com"),
        ))
        body.addWidget(make_form_row(
            t("about.website"),
            _link_label("https://www.omnineurons.com", "www.omnineurons.com"),
        ))

        content_layout.addWidget(card)

    def load_from(self, config: Config) -> None:
        pass

    def apply_to(self, config: Config) -> None:
        pass

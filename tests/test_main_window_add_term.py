"""Header add-term button: always enabled, Pro deep-links, Free prompts."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from i18n._en import STRINGS as EN
from licensing import Entitlement, Tier
from services.config_store import Config
from services.ui_bridge import UIBridge
from ui.history_manager import HistoryManager
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp, appdata):
    win = MainWindow(
        ui_bridge=UIBridge(),
        history_manager=HistoryManager(),
        openai_client=None,
        config=Config(),
        icon_path=None,
    )
    yield win
    win.deleteLater()


def test_add_term_plus_stays_open_at_header_size(qapp):
    """Stock DictionaryAdd's vertical bar closes at 16px and reads as a minus.

    Composited on white, a real plus is a bright run of at least three pixels
    both across and down inside the corner badge.
    """
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QImage, QPainter

    from ui.icons import AddTermIcon

    # Header draws this glyph at 18px, a tenth larger than the gear.
    size = 18
    icon = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    icon.fill(QColor(0, 0, 0, 0))
    painter = QPainter(icon)
    AddTermIcon().render(painter, QRectF(0, 0, size, size))
    painter.end()

    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.drawImage(0, 0, icon)
    painter.end()

    def longest_bright_run(values) -> int:
        best = current = 0
        for value in values:
            current = current + 1 if value >= 220 else 0
            best = max(best, current)
        return best

    def red(x, y) -> int:
        return image.pixelColor(x, y).red()

    horizontal = max(
        longest_bright_run([red(x, y) for x in range(10, size)]) for y in range(10, size)
    )
    vertical = max(
        longest_bright_run([red(x, y) for y in range(9, size)]) for x in range(10, size)
    )
    assert horizontal >= 3
    assert vertical >= 3


def test_add_term_sits_between_the_license_chip_and_the_theme_button(window, qapp):
    window.show()
    qapp.processEvents()
    try:
        assert window.tier_badge.x() < window.add_term_btn.x() < window.theme_btn.x()
        assert window.add_term_btn.isEnabled()
        assert window.add_term_btn.toolTip() == EN["main.tooltip.add_term"]
    finally:
        window.hide()


def test_tagline_does_not_eat_clicks(window):
    tagline = window.findChild(QLabel, "headerTagline")
    assert tagline.testAttribute(Qt.WA_TransparentForMouseEvents)


def test_pro_emits_glossary_terms_requested(window, monkeypatch):
    monkeypatch.setattr("licensing.get_entitlement", lambda: Entitlement(Tier.PRO))
    hits = []
    window._bridge.glossary_terms_requested.connect(lambda: hits.append(True))
    window._on_add_term()
    assert hits == [True]


def test_free_prompts_and_does_not_open_glossary(window, monkeypatch):
    monkeypatch.setattr("licensing.get_entitlement", lambda: Entitlement(Tier.FREE))
    prompted = []
    monkeypatch.setattr(window, "_prompt_glossary_pro", lambda: prompted.append(True))
    hits = []
    window._bridge.glossary_terms_requested.connect(lambda: hits.append(True))
    window._on_add_term()
    assert prompted == [True]
    assert hits == []


def test_free_dialog_yes_opens_the_license_page(window, monkeypatch):
    monkeypatch.setattr(
        "ui.main_window.MessageBox.exec",
        lambda self: True,
    )
    hits = []
    window._bridge.license_requested.connect(lambda: hits.append(True))
    window._prompt_glossary_pro()
    assert hits == [True]

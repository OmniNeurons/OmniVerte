"""Languages settings page: the one-click swap of the primary/secondary pair."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def page(qapp):
    from ui.settings_pages.languages_page import LanguagesPage

    return LanguagesPage()


def test_swap_exchanges_selections(page):
    page.primary_combo.setCurrentText("English")
    page.secondary_combo.setCurrentText("Russian")

    page._swap_languages()

    assert page.primary_combo.currentText() == "Russian"
    assert page.secondary_combo.currentText() == "English"


def test_swap_is_reversible(page):
    page.primary_combo.setCurrentText("German")
    page.secondary_combo.setCurrentText("French")

    page._swap_languages()
    page._swap_languages()

    assert page.primary_combo.currentText() == "German"
    assert page.secondary_combo.currentText() == "French"

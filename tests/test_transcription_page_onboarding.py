"""First-run onboarding cue on the Transcription settings page.

The API-key hints must stay hidden until `enter_initial_setup()` reveals them,
and each hint must disappear once the user edits that field — verifying the
`textEdited` wiring (which, unlike `textChanged`, does not fire on the masked
placeholder that `load_from` writes programmatically).
"""

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
    from ui.settings_pages.transcription_page import TranscriptionPage

    return TranscriptionPage()


def test_hints_hidden_by_default(page):
    assert page.openai_hint.isVisible() is False
    assert page.groq_hint.isVisible() is False


def test_enter_initial_setup_reveals_hints(page):
    page.show()  # widgets report visibility only once shown
    page.enter_initial_setup()
    assert page.openai_hint.isVisible() is True
    assert page.groq_hint.isVisible() is True


def test_typing_hides_only_that_fields_hint(page):
    page.show()
    page.enter_initial_setup()

    # Simulate the user editing the OpenAI field (real edits emit textEdited).
    page.openai_key_edit.textEdited.emit("sk-typing")

    assert page.openai_hint.isVisible() is False
    assert page.groq_hint.isVisible() is True

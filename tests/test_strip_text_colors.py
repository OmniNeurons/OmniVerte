# file: tests/test_strip_text_colors.py

"""Regression tests for ui.main_window._strip_text_colors.

The original implementation mutated fragment char formats while iterating the
live fragment list. Clearing colours can make neighbouring fragments equal, at
which point Qt merges them and invalidates the iterators — on such pastes the
walk chased stale positions forever (a stream of "QTextCursor::setPosition:
Position out of range" and a frozen UI). The fixed version walks first and
applies afterwards; these tests pin the termination and the actual stripping.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QFont, QTextDocument, QTextFormat
from PySide6.QtWidgets import QApplication

from ui.main_window import _strip_text_colors


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _fragment_formats(doc):
    formats = []
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid():
                formats.append((frag.text(), frag.charFormat()))
            it += 1
        block = block.next()
    return formats


def _has_color(fmt) -> bool:
    return fmt.hasProperty(QTextFormat.ForegroundBrush) or fmt.hasProperty(
        QTextFormat.BackgroundBrush
    )


def test_mergeable_colored_neighbours_terminate_and_go_plain(app):
    # Two adjacent spans whose formats become identical once the colour is
    # cleared — the exact shape that merged fragments under the iterator's
    # feet and hung the old implementation.
    doc = QTextDocument()
    doc.setHtml(
        '<p><span style="color:#ff0000">red</span>'
        '<span style="color:#0000ff">blue</span> plain</p>'
    )
    _strip_text_colors(doc)
    assert doc.toPlainText() == "redblue plain"
    assert all(not _has_color(fmt) for _, fmt in _fragment_formats(doc))


def test_bold_survives_and_block_background_is_cleared(app):
    doc = QTextDocument()
    doc.setHtml(
        '<p style="background-color:#f8f8f8">'
        '<b style="color:#00aa00">bold</b> tail</p>'
    )
    _strip_text_colors(doc)

    formats = dict(_fragment_formats(doc))
    assert formats["bold"].fontWeight() == QFont.Bold
    assert not _has_color(formats["bold"])
    assert not doc.begin().blockFormat().hasProperty(QTextFormat.BackgroundBrush)


def test_colourless_document_is_untouched(app):
    doc = QTextDocument()
    doc.setHtml("<p><b>bold</b> and <i>italic</i></p>")
    before = doc.toHtml()
    _strip_text_colors(doc)
    # A clean document collects zero edits — nothing may change, not even
    # revision-level churn that would re-trigger textChanged listeners.
    assert doc.toHtml() == before

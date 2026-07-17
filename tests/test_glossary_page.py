"""Glossary settings page: flags↔config, lists↔glossary.json, and validation."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication

from services.glossary import Glossary
from ui.settings_pages.glossary_page import parse_replacement_lines


# ---------- pure parser (no Qt) ----------

def test_parse_valid_replacement_lines():
    out, errors = parse_replacement_lines("зет тюнинг => Z-tuning\n\nfoo => Bar")
    assert errors == []
    assert out == [
        {"heard": "зет тюнинг", "canonical": "Z-tuning"},
        {"heard": "foo", "canonical": "Bar"},
    ]


def test_parse_flags_missing_separator_and_empty_sides():
    out, errors = parse_replacement_lines("no separator here\n=> only canonical\nheard =>")
    assert out == []
    assert len(errors) == 3


# ---------- Qt page ----------

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(qapp, tmp_path):
    from ui.settings_pages.glossary_page import GlossaryPage

    p = GlossaryPage()
    # Point the page's glossary at a throwaway file, never the real %APPDATA%.
    p._glossary = Glossary(tmp_path / "glossary.json")
    return p


class FakeConfig:
    """Minimal Config stand-in: dict-backed get/set."""

    def __init__(self, data=None):
        self._d = dict(data or {})

    def get(self, key, default=None):
        return self._d.get(key, default)

    def set(self, key, value):
        self._d[key] = value


def test_apply_writes_flags_to_config_and_lists_to_glossary(page, tmp_path):
    cfg = FakeConfig()
    page.enable_switch.setChecked(True)
    page.fuzzy_switch.setChecked(False)
    page.threshold_spin.setValue(91)
    page.names_edit.setPlainText("Acme Corp\n\nMasterDrive")  # blank line dropped
    page.repl_edit.setPlainText("зет тюнинг => Z-tuning")

    page.apply_to(cfg)

    assert cfg.get("GLOSSARY_ENABLED") == "true"
    assert cfg.get("GLOSSARY_FUZZY_REPLACE") == "false"
    assert cfg.get("GLOSSARY_FUZZY_THRESHOLD") == "91"

    # Lists landed in glossary.json, not config.
    reloaded = Glossary(tmp_path / "glossary.json")
    assert reloaded.own_names == ["Acme Corp", "MasterDrive"]
    assert reloaded.replacements == [{"heard": "зет тюнинг", "canonical": "Z-tuning"}]


def test_names_box_merges_own_and_counterparties(page, tmp_path):
    """The merged Names box reads own_names + counterparties and writes own_names."""
    g = Glossary(tmp_path / "glossary.json")
    g.own_names = ["Acme Corp"]
    g.counterparties = ["Globex"]
    g.save()
    page._glossary = Glossary(tmp_path / "glossary.json")

    page.load_from(FakeConfig())
    text = page.names_edit.toPlainText()
    assert "Acme Corp" in text and "Globex" in text

    page.apply_to(FakeConfig())
    reloaded = Glossary(tmp_path / "glossary.json")
    assert reloaded.own_names == ["Acme Corp", "Globex"]
    assert reloaded.counterparties == []


def test_load_populates_from_config_and_glossary(page, tmp_path):
    g = Glossary(tmp_path / "glossary.json")
    g.services = ["Z-tuning"]
    g.replacements = [{"heard": "x", "canonical": "X"}]
    g.save()
    page._glossary = Glossary(tmp_path / "glossary.json")

    cfg = FakeConfig({"GLOSSARY_ENABLED": "true", "GLOSSARY_FUZZY_THRESHOLD": "77"})
    page.load_from(cfg)

    assert page.enable_switch.isChecked() is True
    assert page.threshold_spin.value() == 77
    assert "Z-tuning" in page.services_edit.toPlainText()
    assert "x => X" in page.repl_edit.toPlainText()


def test_validate_blocks_malformed_replacements(page):
    page.repl_edit.setPlainText("this line has no separator")
    assert page.validate() is not None

    page.repl_edit.setPlainText("good => fix")
    assert page.validate() is None

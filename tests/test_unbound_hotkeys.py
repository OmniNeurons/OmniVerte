"""Hotkeys may be left unbound ("" on file), and a caught key moves between actions.

Covers the engine (resolve/register/tray rebind) and the General settings page
(capture release, validate, save round-trip).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from services import audio_writer as aw
from services.audio_writer import AudioWriter, HOTKEY_ACTIONS, resolve_hotkey


class _DictConfig:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


# ---------- engine ----------

def test_resolve_hotkey_missing_key_gets_default_empty_stays_unbound():
    cfg = _DictConfig({"HOTKEY_QUICK": "", "HOTKEY_TRANSLATE": " F7 "})
    assert resolve_hotkey(cfg, "transcribe") == "F8"
    assert resolve_hotkey(cfg, "quick") == ""
    assert resolve_hotkey(cfg, "translate") == "F7"


def _keyboard_writer(hotkeys):
    w = AudioWriter.__new__(AudioWriter)
    w.activation_mode = "keyboard"
    w.activation_hooks = {}
    w.suppress_hotkeys = False
    w.hotkeys = dict(hotkeys)
    return w


def test_press_and_talk_skips_unbound_actions(monkeypatch):
    add = MagicMock(return_value="handle")
    monkeypatch.setattr(aw.keyboard, "add_hotkey", add)
    w = _keyboard_writer({"transcribe": "F9", "translate": "", "custom": "F11", "quick": ""})
    w.press_and_talk()
    assert sorted(c.args[0] for c in add.call_args_list) == ["F11", "F9"]
    assert set(w.activation_hooks) == {"transcribe", "custom"}


def test_tray_rebind_takes_the_key_from_its_previous_action(monkeypatch):
    monkeypatch.setattr(aw.time, "sleep", lambda _s: None)
    w = _keyboard_writer({"transcribe": "F9", "translate": "F10", "custom": "F11", "quick": "F8"})
    w.config = _DictConfig()
    w._unhook_all = MagicMock()
    w.press_and_talk = MagicMock()

    w.change_activation_key("f9", "quick")

    assert w.hotkeys["quick"] == "f9"
    assert w.hotkeys["transcribe"] == ""
    assert w.config.values["HOTKEY_TRANSCRIBE"] == ""
    assert w.config.values["HOTKEY_QUICK"] == "f9"
    assert w.hotkeys["translate"] == "F10"     # untouched


# ---------- settings page ----------

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(qapp, appdata):
    from ui.settings_pages import GeneralPage

    p = GeneralPage()
    p.mode_keyboard.setChecked(True)
    for key, edit in zip(("F9", "F8", "F10", "F11"),
                         (p.hotkey_edit, p.hotkey_quick_edit,
                          p.hotkey_translate_edit, p.hotkey_custom_edit)):
        edit.setText(key)
    yield p
    p.deleteLater()


def test_caught_key_is_released_from_the_other_action(page, monkeypatch):
    from ui.settings_pages import general_page

    info = MagicMock()
    monkeypatch.setattr(general_page.InfoBar, "info", info)
    page._release_hotkey(page.hotkey_quick_edit, "F9")
    assert info.call_count == 1
    assert page.hotkey_edit.text() == ""
    assert page.hotkey_translate_edit.text() == "F10"
    assert page.hotkey_quick_edit.text() == "F8"   # the target is the capture's to set


def test_empty_field_validates_and_saves_as_unbound(page, monkeypatch):
    from services.config_store import Config
    from ui.settings_pages import general_page

    monkeypatch.setattr(general_page.autostart, "set_enabled", lambda _on: None)
    page.hotkey_translate_edit.clear()
    assert page.validate() is None

    cfg = Config()
    page.apply_to(cfg)
    assert Config().get("HOTKEY_TRANSLATE") == ""            # survives a reload
    assert resolve_hotkey(Config(), "translate") == ""
    assert Config().get("HOTKEY_TRANSCRIBE") == "F9"


def test_all_fields_empty_is_rejected(page):
    from i18n import t

    for _, _, edit in page._hotkey_fields():
        edit.clear()
    assert page.validate() == t("general.error.hotkey_none_assigned")


def test_typed_duplicate_is_still_rejected(page):
    from i18n import t

    page.hotkey_translate_edit.setText("f9")
    assert page.validate() == t("general.error.hotkey_duplicate")


def test_page_covers_every_hotkey_action(page):
    config_keys = {k for k, _, _ in page._hotkey_fields()}
    assert config_keys == {s["config_key"] for s in HOTKEY_ACTIONS.values()}

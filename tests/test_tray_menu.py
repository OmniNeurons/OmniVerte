# file: tests/test_tray_menu.py

"""The tray menu: labels follow the UI language, `enabled=` state does not.

The tray is the one surface `QTranslator` could never have reached — pystray is
not Qt — and the one where translating a label used to be able to break
*behaviour* rather than just cosmetics. Several submenus decide `enabled=` by
comparing the current setting against an item's identity; when those were
display strings, they worked only because everything was English. These tests
pin the split: labels are looked up, comparisons use canonical values.

`setup_tray` builds the menu inside a closure and then starts a real icon
thread, so the icon and threading are stubbed. `pystray.Menu`/`MenuItem`
themselves are real — the menu under test is the one the user gets.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import i18n
from i18n import current_locale, set_locale
from services.config_store import Config
from services.ui_bridge import UIBridge


@pytest.fixture(autouse=True)
def _reset_locale():
    before = current_locale()
    yield
    set_locale(before)


@pytest.fixture
def audio_writer():
    """A stand-in in a known state: keyboard mode, middle button, local/cpu."""
    aw = MagicMock(name="audio_writer")
    aw.activation_mode = "keyboard"
    aw.hotkeys = {"transcribe": "F9", "translate": "F10", "custom": "F11"}
    aw.suppress_hotkeys = True
    aw.mouse_activation_button = "middle"
    aw.whisper_model_name = "small"
    aw.transcription_backend = "local"
    aw.use_device = "cpu"
    return aw


def _build_menu(audio_writer, config, monkeypatch):
    import tray_preparing.tray_placing as tp

    # Never create a real tray icon, and never start the icon's run() thread.
    monkeypatch.setattr(tp.pystray, "Icon", MagicMock(name="Icon"))
    monkeypatch.setattr(tp, "threading", MagicMock(name="threading"))
    return tp.setup_tray(audio_writer, UIBridge(), config).menu


def _flatten(menu, depth=0):
    """(text, enabled, depth) for every non-separator item, depth-first."""
    out = []
    for item in menu:
        if str(item) == "- - - -":
            continue
        out.append((item.text, bool(item.enabled), depth))
        if item.submenu:
            out.extend(_flatten(item.submenu, depth + 1))
    return out


def test_menu_is_translated(audio_writer, appdata, monkeypatch):
    set_locale("ru")
    texts = [text for text, _, _ in _flatten(_build_menu(audio_writer, Config(), monkeypatch))]
    assert "Показать окно" in texts
    assert "Show window" not in texts


def test_enabled_state_is_identical_across_locales(audio_writer, appdata, monkeypatch):
    """THE tray regression test.

    Several submenus disable the item representing the current setting, so it
    reads as "you are already here". That decision used to compare a *display*
    string ('Keyboard', 'OpenAI API'), which silently becomes false the moment
    the label is translated — every submenu would offer its already-active item
    as clickable and hide nothing. Position-for-position, the enabled flags must
    not move when the language does.
    """
    set_locale("en")
    en = _flatten(_build_menu(audio_writer, Config(), monkeypatch))
    set_locale("ru")
    ru = _flatten(_build_menu(audio_writer, Config(), monkeypatch))

    assert len(en) == len(ru), "menu shape changed with the language"
    en_flags = [(enabled, depth) for _, enabled, depth in en]
    ru_flags = [(enabled, depth) for _, enabled, depth in ru]
    assert en_flags == ru_flags

    # And it passes for the right reason: something IS actually disabled.
    assert any(not enabled for _, enabled, _ in en)


@pytest.mark.parametrize("locale", ["en", "ru"])
def test_active_setting_is_the_disabled_item(audio_writer, appdata, monkeypatch, locale):
    """The canonical values behind the labels still line up with the state."""
    set_locale(locale)
    items = _flatten(_build_menu(audio_writer, Config(), monkeypatch))
    disabled = {text for text, enabled, _ in items if not enabled}

    # activation_mode='keyboard' → the Keyboard item is the dead one.
    assert i18n.t("tray.mode.keyboard") in disabled
    assert i18n.t("tray.mode.mouse") not in disabled
    # mouse_activation_button='middle'
    assert i18n.t("general.mouse.middle") in disabled
    assert i18n.t("general.mouse.right") not in disabled
    # use_device='cpu' — device names are canonical in every locale.
    assert "cpu" in disabled
    assert "cuda" not in disabled
    # whisper_model_name='small' on the local backend.
    assert i18n.t("tray.model.local", model="small") in disabled


@pytest.mark.parametrize("locale", ["en", "ru"])
def test_identifiers_are_never_translated(audio_writer, appdata, monkeypatch, locale):
    """Model names, device names and the dictation language pair are VALUES.

    The language pair especially: PRIMARY_LANGUAGE holds an English display
    name that services/text_operations.py looks up. A Russian tray showing
    "Русский" here would be showing something that is not what is stored.
    """
    set_locale(locale)
    config = Config()
    texts = [text for text, _, _ in _flatten(_build_menu(audio_writer, config, monkeypatch))]

    assert "cuda" in texts and "cpu" in texts
    assert any("large-v3" in x for x in texts)
    assert any("gpt-4o-mini-transcribe" in x for x in texts)
    # The configured pair, verbatim.
    assert any(x == (config.get("PRIMARY_LANGUAGE") or "English") for x in texts)
    assert any(x == (config.get("SECONDARY_LANGUAGE") or "Russian") for x in texts)

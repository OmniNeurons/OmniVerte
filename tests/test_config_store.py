"""Config: defaults, escaping round-trip, secrets isolation, and migrations."""

from __future__ import annotations

from services.config_store import Config


def test_defaults_applied(appdata):
    c = Config()
    assert c.get("ACTIVATION_KEY") is None          # the transcribe action is gone
    assert c.get("HOTKEY_TRANSCRIBE") is None
    assert c.get("HOTKEY_QUICK") == "F9"
    assert c.get("DICTATION_AI_CORRECTION") == "false"
    assert c.get("THEME") == "light"
    assert c.get("BACKEND_PRIORITY") == "openai,groq,gemini,local"
    assert c.backend_priority == ["openai", "groq", "gemini", "local"]


def test_default_local_model_is_friendly_for_cpu(appdata):
    # `small` is chosen so a CPU-only first-run doesn't sit downloading 3GB of
    # large-v3 and then transcribe at a fraction of realtime. If someone bumps
    # this back to a heavy model by accident, this test catches it.
    c = Config()
    assert c.get("MODEL_LOCAL") == "small"
    assert c.get("WHISPER_MODEL") == "small"


def test_set_persists_across_instances(appdata):
    Config().set("THEME", "dark")
    assert Config().get("THEME") == "dark"


def test_escape_round_trip(appdata):
    # Quotes, backslashes and newlines must survive the dotenv write/read cycle —
    # without _escape, a prompt containing " silently gets dropped on reload.
    tricky = 'He said "hi"\\there\nsecond line'
    Config().set("CUSTOM_STYLE_PROMPT", tricky)
    assert Config().get("CUSTOM_STYLE_PROMPT") == tricky


def test_backend_priority_parsing(appdata):
    Config().set_backend_priority(["openai", "groq", "local"])
    assert Config().backend_priority == ["openai", "groq", "local"]


def test_backend_priority_defaults_when_blank(appdata):
    c = Config()
    c.set("BACKEND_PRIORITY", "")
    assert c.backend_priority == ["local"]


def test_secret_round_trip(appdata):
    c = Config()
    assert c.get_secret("OPEN_AI_API_KEY") is None
    c.set_secret("OPEN_AI_API_KEY", "sk-test")
    assert c.get_secret("OPEN_AI_API_KEY") == "sk-test"
    assert c.has_secret("OPEN_AI_API_KEY") is True
    c.set_secret("OPEN_AI_API_KEY", None)  # empty value deletes
    assert c.has_secret("OPEN_AI_API_KEY") is False


def test_secrets_never_written_to_config_file(appdata):
    c = Config()
    c.set_secret("OPEN_AI_API_KEY", "sk-super-secret")
    c.set("THEME", "dark")  # force a config.env write
    text = (appdata / "OmniVerte" / "config.env").read_text(encoding="utf-8")
    assert "sk-super-secret" not in text
    assert "OPEN_AI_API_KEY" not in text


def test_onboarding_flag(appdata):
    assert Config().onboarding_done() is False
    Config().mark_onboarding_done()
    assert Config().onboarding_done() is True


def _write_config(appdata, text):
    cfg_dir = appdata / "OmniVerte"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.env").write_text(text, encoding="utf-8")


def _on_file(appdata):
    return (appdata / "OmniVerte" / "config.env").read_text(encoding="utf-8")


def test_pre_quick_install_keeps_its_dictation_key(appdata):
    # Before the quick action existed, transcribe on F9 was the dictation key.
    _write_config(appdata, 'HOTKEY_TRANSCRIBE="F9"\n')
    c = Config()
    assert c.get("HOTKEY_QUICK") == "F9"
    assert c.get("HOTKEY_TRANSCRIBE") is None


def test_single_key_era_activation_key_becomes_dictation(appdata):
    _write_config(appdata, 'ACTIVATION_KEY="F7"\n')
    assert Config().get("HOTKEY_QUICK") == "F7"


def test_pre_quick_install_never_steals_a_translate_key(appdata):
    _write_config(appdata, 'HOTKEY_TRANSCRIBE="F10"\nHOTKEY_TRANSLATE="F10"\n')
    assert Config().get("HOTKEY_QUICK") == ""


def test_stock_f8_transcribe_is_dropped_when_dictation_has_a_key(appdata):
    _write_config(appdata, 'HOTKEY_TRANSCRIBE="F8"\nHOTKEY_QUICK="F9"\n')
    c = Config()
    assert c.get("HOTKEY_QUICK") == "F9"
    assert c.get("HOTKEY_TRANSCRIBE") is None


def test_unbound_dictation_takes_the_transcribe_key(appdata):
    _write_config(appdata, 'HOTKEY_TRANSCRIBE="F7"\nHOTKEY_QUICK=""\n')
    assert Config().get("HOTKEY_QUICK") == "F7"


def test_retired_keys_leave_the_file_on_next_write(appdata):
    _write_config(appdata, 'HOTKEY_TRANSCRIBE="F8"\nACTIVATION_KEY="F8"\n'
                           'TRANSCRIBE_HOTKEY_RETIRED="true"\nHOTKEY_QUICK="F9"\n')
    Config().set("THEME", "dark")
    text = _on_file(appdata)
    assert "HOTKEY_TRANSCRIBE" not in text
    assert "ACTIVATION_KEY" not in text
    assert "TRANSCRIBE_HOTKEY_RETIRED" not in text
    assert Config().get("HOTKEY_QUICK") == "F9"


def test_migrate_preferred_language(appdata):
    cfg_dir = appdata / "OmniVerte"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.env").write_text('PREFERRED_LANGUAGE="ru"\n', encoding="utf-8")
    c = Config()
    assert c.get("PRIMARY_LANGUAGE") == "Russian"
    # Secondary flips to English so the pair doesn't collapse to Russian/Russian.
    assert c.get("SECONDARY_LANGUAGE") == "English"
    # Legacy key is dropped entirely.
    assert c.get("PREFERRED_LANGUAGE") is None


def test_fresh_install_runs_onboarding(appdata, monkeypatch):
    # No config.env and no import from any legacy .env: a fresh install gets
    # defaults and onboarding stays pending.
    import services.config_store as cs

    monkeypatch.delenv("OPEN_AI_API_KEY", raising=False)

    c = Config()
    assert c.onboarding_done() is False
    assert c.get("THEME") == cs.DEFAULTS["THEME"]
    assert c.get_secret("OPEN_AI_API_KEY") is None


def test_fresh_install_ui_language_is_auto(appdata):
    # "" means "follow the OS" — resolved at startup, never persisted as "".
    assert Config().get("UI_LANGUAGE") == ""


def test_existing_install_is_pinned_to_english(appdata):
    # The whole point of _migrate_ui_language: someone who has been using the
    # app in English on a Russian Windows must not have it flip to Russian on
    # the release that adds the setting.
    cfg_dir = appdata / "OmniVerte"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.env").write_text('ONBOARDING_DONE="true"\n', encoding="utf-8")
    assert Config().get("UI_LANGUAGE") == "en"


def test_existing_install_keeps_an_explicit_ui_language(appdata):
    cfg_dir = appdata / "OmniVerte"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.env").write_text(
        'ONBOARDING_DONE="true"\nUI_LANGUAGE="ru"\n', encoding="utf-8"
    )
    assert Config().get("UI_LANGUAGE") == "ru"


def test_onboarding_freezes_the_resolved_ui_language(appdata):
    # Auto ("") must not survive onboarding: otherwise changing the Windows
    # display language later would silently change the app's, for a user who
    # never chose one.
    import i18n

    before = i18n.current_locale()
    try:
        i18n.set_locale("ru")
        c = Config()
        assert c.get("UI_LANGUAGE") == ""
        c.mark_onboarding_done()
        assert c.get("UI_LANGUAGE") == "ru"
        assert Config().get("UI_LANGUAGE") == "ru"
    finally:
        i18n.set_locale(before)


def test_onboarding_does_not_clobber_an_explicit_ui_language(appdata):
    import i18n

    before = i18n.current_locale()
    try:
        i18n.set_locale("ru")
        c = Config()
        c.set("UI_LANGUAGE", "en")
        c.mark_onboarding_done()
        assert c.get("UI_LANGUAGE") == "en"
    finally:
        i18n.set_locale(before)


import pytest  # noqa: E402

from services.config_store import choose_quick_engine  # noqa: E402


@pytest.mark.parametrize("pref, gemini, eleven, expected", [
    (None, True, True, "gemini"),
    ("elevenlabs", True, True, "elevenlabs"),
    ("elevenlabs", True, False, "gemini"),
    ("gemini", False, True, "elevenlabs"),
    (" Bogus ", True, True, "gemini"),
    ("gemini", False, False, None),
])
def test_choose_quick_engine(pref, gemini, eleven, expected):
    assert choose_quick_engine(pref, gemini, eleven) == expected


def test_config_quick_engine_reads_saved_keys(appdata):
    c = Config()
    assert c.quick_engine() is None
    c.set_secret("ELEVENLABS_API_KEY", "e")
    assert c.quick_engine() == "elevenlabs"
    c.set_secret("GEMINI_API_KEY", "g")
    assert c.quick_engine() == "gemini"

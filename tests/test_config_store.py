"""Config: defaults, escaping round-trip, secrets isolation, and migrations."""

from __future__ import annotations

from services.config_store import Config


def test_defaults_applied(appdata):
    c = Config()
    assert c.get("ACTIVATION_KEY") == "F9"
    assert c.get("THEME") == "light"
    assert c.get("BACKEND_PRIORITY") == "openai,groq,local"
    assert c.backend_priority == ["openai", "groq", "local"]


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


def test_migrate_legacy_activation_key_into_hotkey(appdata):
    cfg_dir = appdata / "OmniVerte"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.env").write_text('ACTIVATION_KEY="F8"\n', encoding="utf-8")
    # No HOTKEY_TRANSCRIBE on file → the customised legacy key is carried over.
    assert Config().get("HOTKEY_TRANSCRIBE") == "F8"


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

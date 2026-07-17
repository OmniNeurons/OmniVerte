# file: tests/test_i18n_catalog.py

"""UI string catalog: data integrity + the lookup contracts (no Qt needed).

The point of this file is that a translation cannot rot silently. Every check
here is derived from the catalog itself rather than from a hand-maintained list,
so adding a string or a locale extends the coverage automatically — nobody has
to remember to also update the tests.
"""

from __future__ import annotations

import string as _string

import pytest

import i18n
from i18n import (
    DEFAULT_LOCALE,
    UI_LOCALE_LABELS,
    UI_LOCALES,
    catalog,
    current_locale,
    set_locale,
    t,
)
from i18n._en import STRINGS as EN

# Every (locale, key) pair, so a failure names the exact miss rather than
# dumping a set diff of 300 keys.
LOCALE_KEY_PAIRS = [(loc, key) for loc in UI_LOCALES for key in sorted(EN)]
_PAIR_IDS = [f"{loc}-{key}" for loc, key in LOCALE_KEY_PAIRS]

# Keys whose value is a proper noun, protocol name or key label, and which are
# therefore expected to stay Latin in every locale. Transliterating them helps
# nobody and breaks the user's ability to search for them.
#
# Matched EXACTLY, never by prefix. A prefix would silently swallow the whole
# subtree: "common.pro" would exempt "common.pro.tooltip", which is a real
# sentence that IS translated — so a future regression of it back to English
# would go unnoticed by the very test meant to catch that. Each entry here is a
# hole in test_russian_strings_are_russian; keep the list short, exact, and
# justified.
_KEEP_LATIN = frozenset({
    "app.title",
    "common.pro",          # "Pro" — the tier's name, not a word
    # Provider names.
    "transcription.backend.name.openai",
    "transcription.backend.name.groq",
    # Invented company names used as an example of what to type in the box.
    "glossary.terms.names.placeholder",
    # Hardware acronyms, written Latin in Russian technical prose too.
    "transcription.device.cpu",
    "transcription.device.cuda",
    # Cloud provider names, in the tray's device picker and model groups.
    "tray.device.openai",
    "tray.device.groq",
    "tray.model.openai",
    "tray.model.groq",
})


@pytest.fixture(autouse=True)
def _reset_locale():
    """Every test starts from English and leaves the module singleton as it
    found it — set_locale is process-global, so a test that switches and dies
    would otherwise silently retune every test after it."""
    before = current_locale()
    set_locale(DEFAULT_LOCALE)
    yield
    set_locale(before)


def _is_cyrillic(s: str) -> bool:
    return any("Ѐ" <= ch <= "ӿ" or ch in "ёЁ" for ch in s)


def _literal_text(template: str) -> str:
    """A template with its {placeholders} removed — only the words a translator
    actually writes.

    Placeholder NAMES are Latin identifiers ({action}, {model}) and would
    otherwise read as untranslated English: "{action}: {key}" is entirely
    placeholders and has nothing to translate, but a naive isalpha() scan sees
    eight letters and demands Cyrillic.
    """
    return "".join(
        literal for literal, _, _, _ in _string.Formatter().parse(template) if literal
    )


# ---------- catalog integrity ----------

def test_default_locale_ships():
    assert DEFAULT_LOCALE in UI_LOCALES


def test_english_is_the_first_locale():
    """Picker order, and the fallback everything degrades to."""
    assert UI_LOCALES[0] == DEFAULT_LOCALE


@pytest.mark.parametrize("locale,key", LOCALE_KEY_PAIRS, ids=_PAIR_IDS)
def test_every_locale_covers_every_key(locale, key):
    """The no-missing-translation test. A key in _en.py that a locale lacks
    would degrade to English at runtime — readable, but silently untranslated,
    which is exactly the failure this feature exists to prevent."""
    assert key in catalog(locale), f"{locale!r} is missing {key!r}"


@pytest.mark.parametrize("locale", UI_LOCALES)
def test_no_locale_has_keys_english_lacks(locale):
    """Catches typo'd keys and strings left behind after an English copy edit
    removed the original. Such a key is unreachable — t() resolves against
    _en.py's key set — so it is pure dead weight, and usually a typo of a live
    key that is therefore NOT being translated."""
    extra = set(catalog(locale)) - set(EN)
    assert not extra, f"{locale!r} has keys not in _en.py (dead or typo'd): {sorted(extra)}"


@pytest.mark.parametrize("locale,key", LOCALE_KEY_PAIRS, ids=_PAIR_IDS)
def test_placeholder_parity(locale, key):
    """A translation must carry exactly the placeholders its English source has.

    Dropping one silently loses data in the UI (the mode name vanishes from
    "Activation mode: {mode}"). Inventing one makes t() fall back to English at
    runtime for that string only — a single stubbornly-English label that is
    maddening to track down. Both are caught here instead.
    """
    template = catalog(locale).get(key)
    if template is None:
        pytest.skip("covered by test_every_locale_covers_every_key")
    assert i18n._placeholders(template) == i18n._placeholders(EN[key]), (
        f"{locale}:{key} placeholders differ from English"
    )


@pytest.mark.parametrize("locale,key", LOCALE_KEY_PAIRS, ids=_PAIR_IDS)
def test_no_empty_values(locale, key):
    value = catalog(locale).get(key)
    if value is None:
        pytest.skip("covered by test_every_locale_covers_every_key")
    assert value.strip(), f"{locale}:{key} is empty/whitespace"


def test_keep_latin_entries_are_live_keys():
    """A _KEEP_LATIN entry that no longer names a real key is a silent hole —
    it exempts nothing today and would quietly exempt whatever reuses the name
    tomorrow."""
    assert _KEEP_LATIN <= set(EN), f"stale exemptions: {sorted(_KEEP_LATIN - set(EN))}"


def test_keep_latin_entries_are_actually_latin():
    """Guard on the exemption list: an entry whose Russian IS translated is a
    hole in the coverage, not a proper noun. It would let that string regress to
    English unnoticed by the one test meant to catch that."""
    translated = sorted(k for k in _KEEP_LATIN if _is_cyrillic(catalog("ru")[k]))
    assert not translated, (
        f"these are translated and must not be exempt from the script check: {translated}"
    )


@pytest.mark.parametrize("locale", UI_LOCALES)
def test_locale_labels_cover_every_locale(locale):
    """The picker must be able to name every language it offers."""
    assert UI_LOCALE_LABELS.get(locale, "").strip()


@pytest.mark.parametrize("key", sorted(EN), ids=sorted(EN))
def test_russian_strings_are_russian(key):
    """The RU catalog is actually translated, not English pasted through.

    Skipped when the check cannot mean anything:
      * keys that are deliberately Latin (_KEEP_LATIN);
      * an English source with no letters (a bare "F9", an emoji) — nothing to
        translate;
      * a *Russian* value with no letters. A translation is allowed to consist
        of punctuation where English used words: `glossary.packs.count.join`
        turns " and " into ", " because Russian re-shapes the surrounding
        fragments to dodge the 2-vs-5 plural problem. Such a value cannot be
        "English pasted through" — it does not match the English either — so
        there is no script to assert.
    """
    if key in _KEEP_LATIN:
        pytest.skip("deliberately Latin — see _KEEP_LATIN")
    ru = _literal_text(catalog("ru")[key])
    en = _literal_text(EN[key])
    if not any(ch.isalpha() for ch in en):
        pytest.skip("no letters to translate")
    if not any(ch.isalpha() for ch in ru):
        assert ru != en, f"ru:{key} is untranslated: {ru!r}"
        pytest.skip("deliberately letterless translation")
    assert _is_cyrillic(ru), f"ru:{key} looks untranslated: {ru!r}"


# ---------- lookup contracts ----------

def test_t_returns_english_by_default():
    assert t("languages.primary") == EN["languages.primary"]


def test_t_follows_the_active_locale():
    set_locale("ru")
    assert t("languages.primary") == catalog("ru")["languages.primary"]


def test_unknown_key_returns_the_key():
    """Conspicuous in the UI, and never an exception — t() runs in paint paths
    and signal handlers where raising is a crash the user reads as "the language
    switch broke the app"."""
    assert t("no.such.key") == "no.such.key"


def test_missing_translation_falls_back_to_english(monkeypatch):
    monkeypatch.setitem(i18n._CATALOGS, "ru", {})
    set_locale("ru")
    assert t("languages.primary") == EN["languages.primary"]


def test_unknown_locale_falls_back_to_english():
    """A stray UI_LANGUAGE in config.env must never stop the app from starting."""
    set_locale("kl")
    assert current_locale() == DEFAULT_LOCALE
    assert t("languages.primary") == EN["languages.primary"]


def test_catalog_of_unknown_locale_is_english():
    assert catalog("kl") is catalog(DEFAULT_LOCALE)


def test_set_locale_reports_only_real_changes():
    """Callers emit language_changed on a True return, so a no-op save must not
    fire a full retranslate of every window and the tray."""
    set_locale("en")
    assert set_locale("ru") is True
    assert set_locale("ru") is False
    assert set_locale("en") is True


def test_set_locale_is_case_and_space_insensitive():
    assert set_locale("  RU ") is True
    assert current_locale() == "ru"


def test_set_locale_empty_falls_back_without_warning():
    """"" is the config default meaning "auto" — callers resolve it before
    calling, but a direct pass must still land on English, not crash."""
    set_locale("ru")
    assert set_locale("") is True
    assert current_locale() == DEFAULT_LOCALE


def test_format_uses_named_placeholders():
    monkey = {"tray.test": "Mode: {mode}"}
    i18n._CATALOGS["en"].update(monkey)
    try:
        assert t("tray.test", mode="Keyboard") == "Mode: Keyboard"
    finally:
        del i18n._CATALOGS["en"]["tray.test"]


def test_bad_translation_template_degrades_to_english():
    """A translator who typos a placeholder gets English for that one string
    rather than a KeyError out of a Qt signal handler."""
    i18n._CATALOGS["en"]["tray.test"] = "Mode: {mode}"
    i18n._CATALOGS["ru"]["tray.test"] = "Режим: {rezhim}"
    try:
        set_locale("ru")
        assert t("tray.test", mode="Keyboard") == "Mode: Keyboard"
    finally:
        del i18n._CATALOGS["en"]["tray.test"]
        del i18n._CATALOGS["ru"]["tray.test"]


def test_placeholder_may_be_named_key():
    """`key` is a natural name for a placeholder — the General page's style-pair
    hint interpolates the live hotkey as {key}. t()'s own parameter is
    positional-only so the two cannot collide; without that this raises
    TypeError: got multiple values for argument 'key'.
    """
    assert "{key}" in EN["general.stylepair.hint"]
    assert "F11" in t("general.stylepair.hint", key="F11")


def test_extra_format_args_are_ignored():
    """str.format tolerates unused kwargs; asserting it means a caller passing a
    value a translation chose not to use is not an error."""
    i18n._CATALOGS["en"]["tray.test"] = "Plain"
    try:
        assert t("tray.test", mode="Keyboard") == "Plain"
    finally:
        del i18n._CATALOGS["en"]["tray.test"]


# ---------- links to the app's other language axes ----------

def test_ui_locales_are_app_language_codes():
    """UI locales must be Whisper language codes, like the glossary packs' are.

    The app has three language axes (dictation, pack terms, interface) and they
    must speak one vocabulary of codes, or mapping between them — which the
    General page and the pack picker both do — silently breaks. A language may
    ship no UI translation; a UI translation may never claim a language the app
    does not otherwise have.
    """
    from services.text_operations import LANGUAGE_TO_WHISPER_CODE

    assert set(UI_LOCALES) <= set(LANGUAGE_TO_WHISPER_CODE.values())

# file: tests/test_custom_style_templates.py

"""Data-integrity tests for the Custom style profession templates (no Qt).

Still Qt-free after these grew catalog checks: ``i18n`` is a plain string table
that imports Qt lazily, inside ``detect_system_locale()`` only.

A template's name is a catalog key now, so the invariants that used to hold for
one English string have to hold for its value in **every locale** — which makes
them stronger, not weaker. Each is parametrized over the templates × locales
cross product so that adding either extends the coverage on its own.
"""

import re

import pytest

from i18n import UI_LOCALES, catalog
from i18n._en import STRINGS as EN
from ui.settings_pages.custom_style_templates import (
    CUSTOM_STYLE_TEMPLATES,
    StyleTemplate,
)

EXPECTED_NAME_KEYS = {
    "customstyle.templates.lawyer.name",
    "customstyle.templates.doctor.name",
    "customstyle.templates.psychotherapist.name",
    "customstyle.templates.financial_advisor.name",
    "customstyle.templates.recruiter.name",
    "customstyle.templates.salesperson.name",
    "customstyle.templates.support.name",
    "customstyle.templates.insurance_agent.name",
    "customstyle.templates.professional.name",
    "customstyle.templates.programmer.name",
}

# Emoji and assorted pictographic ranges — enough to assert names stay text-only.
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0000FE00-\U0000FE0F\U00002B00-\U00002BFF]"
)

# `tpl`, never `t`: `t` is the catalog lookup, and a loop variable shadowing it
# is a trap for whoever adds the next t() call in a comprehension here.
_TPL_LOCALES = [(tpl, loc) for tpl in CUSTOM_STYLE_TEMPLATES for loc in UI_LOCALES]
_TPL_LOCALE_IDS = [f"{loc}-{tpl.name_key}" for tpl, loc in _TPL_LOCALES]


def test_all_ten_templates_present():
    assert len(CUSTOM_STYLE_TEMPLATES) == 10
    assert {tpl.name_key for tpl in CUSTOM_STYLE_TEMPLATES} == EXPECTED_NAME_KEYS


def test_every_name_key_is_a_real_catalog_key():
    """`t(tpl.name_key)` is a *computed* key, so test_i18n_call_sites' static
    scan cannot see it — it only checks `t("literal")`. Without this, a typo in
    the templates table ships as a raw `customstyle.templates.lawyr.name` on the
    button, with no exception and nothing in the logs."""
    missing = sorted(
        tpl.name_key for tpl in CUSTOM_STYLE_TEMPLATES if tpl.name_key not in EN
    )
    assert not missing, f"template name keys absent from _en.py: {missing}"


def test_fields_are_non_empty_and_stripped():
    for tpl in CUSTOM_STYLE_TEMPLATES:
        assert isinstance(tpl, StyleTemplate)
        for field in (tpl.emoji, tpl.name_key, tpl.prompt):
            assert field, f"empty field in {tpl.name_key!r}"
            assert field == field.strip(), f"unstripped field in {tpl.name_key!r}"


@pytest.mark.parametrize("tpl,locale", _TPL_LOCALES, ids=_TPL_LOCALE_IDS)
def test_name_is_non_empty_and_stripped_in_every_locale(tpl, locale):
    """`apply_to` strips before saving, but an untrimmed catalog value shows as
    a lopsided button label long before it reaches config."""
    name = catalog(locale).get(tpl.name_key)
    if name is None:
        pytest.skip("covered by test_every_locale_covers_every_key")
    assert name.strip(), f"{locale}:{tpl.name_key} is empty"
    assert name == name.strip(), f"{locale}:{tpl.name_key} is unstripped"


@pytest.mark.parametrize("tpl,locale", _TPL_LOCALES, ids=_TPL_LOCALE_IDS)
def test_name_carries_no_emoji_in_any_locale(tpl, locale):
    # The name feeds CUSTOM_STYLE_NAME (the Custom button tooltip); the emoji
    # belongs only on the button label, where the page prepends it. A translator
    # writing "⚖️ Юрист" is exactly the mistake this catches.
    name = catalog(locale).get(tpl.name_key)
    if name is None:
        pytest.skip("covered by test_every_locale_covers_every_key")
    assert not _EMOJI_RE.search(name), f"emoji leaked into {locale}:{name!r}"


@pytest.mark.parametrize("locale", UI_LOCALES)
def test_names_are_unique_in_every_locale(locale):
    """Key-uniqueness is trivially true and worthless; what matters is that no
    two buttons carry the same label. That can only break in a translation —
    "Professional / Business" and "Salesperson" both drifting to "Бизнес"."""
    names = [catalog(locale)[tpl.name_key] for tpl in CUSTOM_STYLE_TEMPLATES]
    assert len(names) == len(set(names)), f"duplicate template names in {locale!r}"


def test_no_leftover_base_reference():
    # Guards the adaptation: the templates must not refer to a separate "BASE"
    # block, since rewrite_text() already supplies those preservation rules.
    for tpl in CUSTOM_STYLE_TEMPLATES:
        assert "BASE" not in tpl.prompt, f"leftover BASE reference in {tpl.name_key!r}"


def test_prompt_letters_stay_latin():
    """The prompt bodies are model input and are deliberately NOT localized —
    see the templates module's docstring. This pins that decision: a well-meaning
    "the name is Russian, so the prompt should be too" edit trips here rather
    than shipping one hybrid system message per profession.

    Checks that every *letter* is ASCII, not that the whole string is: the bodies
    are full of em-dashes and curly quotes, which are punctuation and say nothing
    about language. The known gap is a translation into an unaccented Latin
    script — no character test separates that from English, the same limit
    test_glossary_packs documents for its Latin-script locales.
    """
    for tpl in CUSTOM_STYLE_TEMPLATES:
        foreign = sorted({ch for ch in tpl.prompt if ch.isalpha() and not ch.isascii()})
        assert not foreign, (
            f"{tpl.name_key}: prompt bodies stay English (model input, not "
            f"chrome) — found {foreign}"
        )

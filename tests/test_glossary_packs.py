# file: tests/test_glossary_packs.py

"""Profession packs: data integrity (no Qt) + the page's import-copy behaviour."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication

from i18n import UI_LOCALES, catalog
from i18n._en import STRINGS as EN
from services.glossary import _MIN_FUZZY_TOKEN_LEN, _STOP_WORDS, Glossary
from ui.settings_pages.glossary_packs import (
    DEFAULT_PACK_LOCALE,
    GLOSSARY_PACKS,
    PACK_LOCALES,
    GlossaryPack,
)

EXPECTED_IDS = {"legal", "medical", "it", "finance", "sales"}

# A pack's chrome follows the UI locale; its terms follow PACK_LOCALES. The two
# axes are unrelated and must not be conflated — hence the separate pair list.
PACK_UI_LOCALE_PAIRS = [(p, loc) for p in GLOSSARY_PACKS for loc in UI_LOCALES]
_UI_PAIR_IDS = [f"{p.pack_id}-{loc}" for p, loc in PACK_UI_LOCALE_PAIRS]

# Every (pack, locale) pair, for the content tests.
PACK_LOCALE_PAIRS = [(p, loc) for p in GLOSSARY_PACKS for loc in PACK_LOCALES]
_PAIR_IDS = [f"{p.pack_id}-{loc}" for p, loc in PACK_LOCALE_PAIRS]

# Locales whose written vocabulary is in a non-Latin script, and the test for it.
# Latin-script locales are absent on purpose: no character test separates Spanish
# from English — test_localized_packs_are_not_the_english_pack covers those.
_SCRIPT_CHECKS = {
    "ru": lambda s: any("Ѐ" <= ch <= "ӿ" or ch in "ёЁ" for ch in s),
    "zh": lambda s: any("㐀" <= ch <= "鿿" for ch in s),
    "ja": lambda s: any("぀" <= ch <= "ヿ" or "一" <= ch <= "鿿"
                        for ch in s),
}

# The IT pack is legitimately Latin-heavy in every locale (Russian devs write
# "Kubernetes"; so do Spanish and Japanese ones), and it is the pack that
# legitimately shares the most vocabulary across locales. Both localization
# checks exempt it.
_LATIN_HEAVY_PACKS = {"it"}


def _is_cyrillic(s: str) -> bool:
    return _SCRIPT_CHECKS["ru"](s)


# ---------- data integrity (no Qt) ----------

def test_expected_packs_present():
    assert {p.pack_id for p in GLOSSARY_PACKS} == EXPECTED_IDS


def test_ids_and_name_keys_are_unique():
    assert len({p.pack_id for p in GLOSSARY_PACKS}) == len(GLOSSARY_PACKS)
    assert len({p.name_key for p in GLOSSARY_PACKS}) == len(GLOSSARY_PACKS)


@pytest.mark.parametrize("locale", UI_LOCALES)
def test_pack_names_are_unique_in_every_locale(locale):
    """Key-uniqueness above is trivial; what matters is that no two buttons carry
    the same label, which can only break in a translation."""
    names = [catalog(locale)[p.name_key] for p in GLOSSARY_PACKS]
    assert len(names) == len(set(names)), f"duplicate pack names in {locale!r}"


def test_every_pack_covers_every_locale():
    for pack in GLOSSARY_PACKS:
        assert set(pack.locales) == set(PACK_LOCALES), pack.pack_id


def test_pack_locales_are_app_language_codes():
    """Pack locales are a subset of the app's languages — never a superset, and
    never a key the app has no language for ("cn" instead of "zh"). A subset is
    legitimate: a language may ship no pack. The reverse never is.

    A test, not an import: the packs are a pure string table and
    services.text_operations does `import openai` at module scope.
    """
    from services.text_operations import LANGUAGE_TO_WHISPER_CODE

    assert set(PACK_LOCALES) <= set(LANGUAGE_TO_WHISPER_CODE.values())


def test_default_pack_locale_is_a_real_locale():
    assert DEFAULT_PACK_LOCALE in PACK_LOCALES


def test_unknown_locale_falls_back_to_english():
    """A stray PRIMARY_LANGUAGE value must never leave a pack button dead.

    The probe is "xx", not a real code: every plausible language now *has* a
    pack, so a real code would test the opposite of what this means.
    """
    pack = GLOSSARY_PACKS[0]
    assert pack.content("xx") == pack.content("en")
    assert pack.term_count("xx") == pack.term_count("en")


@pytest.mark.parametrize("pack", GLOSSARY_PACKS, ids=lambda p: p.pack_id)
def test_pack_metadata_is_filled(pack: GlossaryPack):
    assert pack.emoji
    # `t(pack.name_key)` is a *computed* key, so test_i18n_call_sites' static
    # scan cannot see it — it only checks `t("literal")`. Without this, a typo in
    # _meta.py ships as a raw `glossary.packs.legl.name` on the button, with no
    # exception and nothing in the logs.
    missing = [k for k in (pack.name_key, pack.hint_key) if k not in EN]
    assert not missing, f"{pack.pack_id}: keys absent from _en.py: {missing}"


@pytest.mark.parametrize("pack,locale", PACK_UI_LOCALE_PAIRS, ids=_UI_PAIR_IDS)
def test_pack_chrome_is_filled_in_every_locale(pack: GlossaryPack, locale: str):
    """The name is the button label's text half (the emoji is prepended
    separately), so an untrimmed value shows as a lopsided button."""
    strings = catalog(locale)
    for key in (pack.name_key, pack.hint_key):
        value = strings.get(key)
        if value is None:
            pytest.skip("covered by test_every_locale_covers_every_key")
        assert value.strip(), f"{locale}:{key} is empty"
        assert value == value.strip(), f"{locale}:{key} is unstripped"


@pytest.mark.parametrize("pack,locale", PACK_LOCALE_PAIRS, ids=_PAIR_IDS)
def test_terms_are_clean_and_unique(pack: GlossaryPack, locale: str):
    terms = pack.content(locale).terms
    assert terms, f"{pack.pack_id}/{locale} has no terms"
    for term in terms:
        assert term == term.strip() and term, f"{pack.pack_id}: {term!r} not stripped"
        assert "=>" not in term, f"{pack.pack_id}: {term!r} looks like a replacement"
        assert "\n" not in term
    folded = [t.casefold() for t in terms]
    assert len(folded) == len(set(folded)), f"{pack.pack_id}/{locale}: duplicate terms"


@pytest.mark.parametrize("pack,locale", PACK_LOCALE_PAIRS, ids=_PAIR_IDS)
def test_replacements_are_well_formed(pack: GlossaryPack, locale: str):
    heard_seen: set[str] = set()
    for heard, canonical in pack.content(locale).replacements:
        assert heard.strip() and canonical.strip(), f"{pack.pack_id}: empty side"
        # Exact equality only: an entry that changes nothing is dead weight, but
        # a case-only change ("утп" -> "УТП") is precisely what most non-English
        # packs are for, and the map matches case-insensitively so it does fire.
        assert heard != canonical, f"{pack.pack_id}/{locale}: {heard!r} maps to itself"
        key = heard.casefold()
        assert key not in heard_seen, f"{pack.pack_id}: duplicate heard {heard!r}"
        heard_seen.add(key)


@pytest.mark.parametrize("pack,locale", PACK_LOCALE_PAIRS, ids=_PAIR_IDS)
def test_replacement_heard_sides_are_not_ordinary_speech(pack: GlossaryPack, locale: str):
    """Explicit replacements fire verbatim and word-bounded, with no fuzzy guard
    and no length floor — so a pack must never map a common function word.

    This is the reason _STOP_WORDS carries es/fr/de/it entries at all; on the
    fuzzy path the length floor does the real work.
    """
    for heard, _ in pack.content(locale).replacements:
        for token in heard.split():
            assert token.casefold() not in _STOP_WORDS, (
                f"{pack.pack_id}: {heard!r} contains stop word {token!r}"
            )


@pytest.mark.parametrize("pack,locale", PACK_LOCALE_PAIRS, ids=_PAIR_IDS)
def test_replacements_never_translate_the_user(pack: GlossaryPack, locale: str):
    """The invariant that killed the first draft of this data, generalized.

    The old form read scripts ("heard must be Cyrillic"), which only held while
    every pack bridged Russian speech. With es/de packs the heard side is Spanish
    or German and script says nothing — "anamnesis => medical history" is Latin
    on both sides and is exactly the bug.

    The language-neutral form of the same rule: a replacement canonicalizes a
    term this pack already declares, in this locale. It never introduces a new
    one. "анамнез => anamnesis" fails because "anamnesis" is not a term of the RU
    medical pack — which is precisely what made it a translation rather than a
    fix. It also means the canonical is guaranteed to be reachable by the ASR and
    LLM layers, which only ever see the *term lists*.
    """
    content = pack.content(locale)
    declared = {t.casefold() for t in content.terms}
    for heard, canonical in content.replacements:
        assert canonical.casefold() in declared, (
            f"{pack.pack_id}/{locale}: {canonical!r} is produced by a replacement "
            f"but is not a term of this pack — a replacement canonicalizes a term "
            f"the pack declares, it does not introduce a new (possibly translated) one"
        )


@pytest.mark.parametrize(
    "pack,locale",
    [(p, loc) for p, loc in PACK_LOCALE_PAIRS if loc in _SCRIPT_CHECKS],
    ids=[f"{p.pack_id}-{loc}" for p, loc in PACK_LOCALE_PAIRS if loc in _SCRIPT_CHECKS],
)
def test_non_latin_packs_use_their_own_script(pack: GlossaryPack, locale: str):
    """Guards the point of a localized pack: a Russian lawyer needs Russian terms.

    Only for locales whose script is distinguishable — see the note on
    _SCRIPT_CHECKS. The IT pack is exempt: it is Latin-heavy by design.
    """
    if pack.pack_id in _LATIN_HEAVY_PACKS:
        pytest.skip("the IT pack legitimately keeps Latin tool names in every locale")
    is_native = _SCRIPT_CHECKS[locale]
    terms = pack.content(locale).terms
    native = [t for t in terms if is_native(t)]
    assert len(native) > len(terms) * 0.6, (
        f"{pack.pack_id}/{locale} is mostly Latin — the localized pack is not "
        f"doing its job"
    )


@pytest.mark.parametrize(
    "pack,locale",
    [(p, loc) for p, loc in PACK_LOCALE_PAIRS if loc != "en"],
    ids=[f"{p.pack_id}-{loc}" for p, loc in PACK_LOCALE_PAIRS if loc != "en"],
)
def test_localized_packs_are_not_the_english_pack(pack: GlossaryPack, locale: str):
    """A locale's terms must be what that profession actually writes in that
    language — not the English list pasted in. Script cannot see this for
    es/fr/de/it, so measure overlap with English instead. 40% is generous
    (professional vocabulary genuinely shares "due diligence", "EBITDA") and
    still catches a wholesale copy-paste, the realistic failure at this scale.
    """
    if pack.pack_id in _LATIN_HEAVY_PACKS:
        pytest.skip("the IT pack legitimately shares Latin tool names across locales")
    en = {t.casefold() for t in pack.content("en").terms}
    here = [t.casefold() for t in pack.content(locale).terms]
    shared = sum(1 for t in here if t in en)
    assert shared < len(here) * 0.4, (
        f"{pack.pack_id}/{locale}: {shared}/{len(here)} terms are identical to "
        f"the English pack — this locale is not doing its job"
    )


def test_term_count_matches_contents():
    for pack, locale in PACK_LOCALE_PAIRS:
        content = pack.content(locale)
        assert pack.term_count(locale) == len(content.terms) + len(content.replacements)


def test_packs_fit_the_pro_cap():
    """A pack must be importable on Pro without instantly blowing the 200-term
    quality ceiling — otherwise the buttons we enable would produce a mostly
    faded list."""
    from licensing import TIER_LIMITS, Tier

    cap = TIER_LIMITS[Tier.PRO]["glossary_terms"]
    for pack, locale in PACK_LOCALE_PAIRS:
        assert pack.term_count(locale) <= cap, (
            f"{pack.pack_id}/{locale} alone exceeds the Pro cap"
        )


def test_short_terms_stay_out_of_the_fuzzy_index(tmp_path):
    """Abbreviations like ECG/УТП are safe only because the fuzzy index drops
    sub-4-char tokens. If that guard ever moves, this tells us before users do."""
    short = [
        t for p, loc in PACK_LOCALE_PAIRS for t in p.content(loc).terms
        if len(t) < _MIN_FUZZY_TOKEN_LEN and " " not in t
    ]
    assert short, "expected some short abbreviations in the packs"

    g = Glossary(tmp_path / "glossary.json")
    g.services = list(short)
    g._build_fuzzy_index()
    assert g._fuzzy_terms == []


@pytest.mark.parametrize("pack,locale", PACK_LOCALE_PAIRS, ids=_PAIR_IDS)
def test_no_pack_term_is_a_stop_word(pack: GlossaryPack, locale: str):
    """_STOP_WORDS is one flat, all-languages set because the runtime has no
    locale — the price is that a function word in one language silently drops an
    identical single-word term in another out of the fuzzy index. Nothing
    collides today. This is what tells the next locale's author if it does."""
    for term in pack.content(locale).terms:
        if " " in term or len(term) < _MIN_FUZZY_TOKEN_LEN:
            continue  # multi-word and short terms never consult the stop set
        assert term.casefold() not in _STOP_WORDS, (
            f"{pack.pack_id}/{locale}: {term!r} is a function word in some "
            f"shipped language — it will never fuzzy-match"
        )


# ---------- the page's import-copy behaviour ----------

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(qapp, tmp_path, monkeypatch):
    """A Glossary page on a throwaway file, with packs unlocked (Pro)."""
    import licensing
    from licensing import Entitlement, Tier

    monkeypatch.setattr(licensing, "get_entitlement", lambda: Entitlement(Tier.PRO))
    monkeypatch.setattr("ui.settings_pages.glossary_page.MessageBox", _AcceptingBox)
    from ui.settings_pages.glossary_page import GlossaryPage

    p = GlossaryPage()
    p._glossary = Glossary(tmp_path / "glossary.json")
    p._refresh_pack_status()
    return p


def _pack(pack_id: str) -> GlossaryPack:
    return next(p for p in GLOSSARY_PACKS if p.pack_id == pack_id)


def _set_locale(page, locale: str) -> None:
    page.pack_locale_combo.setCurrentIndex(PACK_LOCALES.index(locale))


def test_import_fills_services_and_replacements_not_names(page):
    """Pack terms must land in "Services & terms" — never in "Names", which holds
    the user's own company and outranks services in the engine's priority order."""
    pack = _pack("it")
    page.names_edit.setPlainText("Acme Corp")
    page._apply_pack(pack)

    content = pack.content("en")
    assert page.services_edit.toPlainText().splitlines() == content.terms
    assert page.names_edit.toPlainText() == "Acme Corp"
    repl_lines = page.repl_edit.toPlainText().splitlines()
    assert len(repl_lines) == len(content.replacements)
    assert repl_lines[0] == f"{content.replacements[0][0]} => {content.replacements[0][1]}"


def test_import_uses_the_selected_locale(page):
    _set_locale(page, "ru")
    page._apply_pack(_pack("legal"))

    lines = page.services_edit.toPlainText().splitlines()
    assert lines == _pack("legal").content("ru").terms
    assert "исковое заявление" in lines
    assert "affidavit" not in lines


def test_locale_switch_imports_the_other_language(page):
    """Both locales of one pack can coexist — they are just more lines. The
    dedup is by term, and the two languages share none."""
    _set_locale(page, "en")
    page._apply_pack(_pack("medical"))
    _set_locale(page, "ru")
    page._apply_pack(_pack("medical"))

    lines = page.services_edit.toPlainText().splitlines()
    assert "anamnesis" in lines and "анамнез" in lines
    expected = len(_pack("medical").content("en").terms) + len(
        _pack("medical").content("ru").terms
    )
    assert len(lines) == expected


# The page's locale handling is one currentData() lookup, so these three cases
# prove it for all eight locales. Parametrizing the Qt tests over locales would
# add 40 QApplication-bound cases exercising the same line.

def test_locale_defaults_to_primary_language(page):
    from tests.test_glossary_page import FakeConfig

    page.load_from(FakeConfig({"PRIMARY_LANGUAGE": "Russian"}))
    assert page._pack_locale() == "ru"


def test_locale_default_covers_the_non_default_languages(page):
    from tests.test_glossary_page import FakeConfig

    page.load_from(FakeConfig({"PRIMARY_LANGUAGE": "Japanese"}))
    assert page._pack_locale() == "ja"


def test_unknown_primary_language_falls_back_to_english(page):
    from tests.test_glossary_page import FakeConfig

    page.load_from(FakeConfig({"PRIMARY_LANGUAGE": "Klingon"}))
    assert page._pack_locale() == "en"


def test_legacy_preferred_language_is_ignored(page):
    """PREFERRED_LANGUAGE is popped by Config's migration and never written
    again. Reading it is why the picker silently pinned every user to English:
    the bug and the correct answer agree for an English user, so only a test on a
    non-English language keeps this fixed."""
    from tests.test_glossary_page import FakeConfig

    page.load_from(FakeConfig({"PREFERRED_LANGUAGE": "ru"}))
    assert page._pack_locale() == "en"


def test_import_appends_and_keeps_existing_lines(page):
    page.services_edit.setPlainText("тариф Орбита")
    page._apply_pack(_pack("legal"))

    lines = page.services_edit.toPlainText().splitlines()
    assert lines[0] == "тариф Орбита"
    assert lines[1:] == _pack("legal").content("en").terms


def test_importing_twice_adds_nothing(page):
    pack = _pack("finance")
    page._apply_pack(pack)
    first = page.services_edit.toPlainText()
    first_repl = page.repl_edit.toPlainText()

    page._apply_pack(pack)  # the "already loaded" branch — no confirm, no change
    assert page.services_edit.toPlainText() == first
    assert page.repl_edit.toPlainText() == first_repl


def test_import_skips_terms_the_user_already_typed(page):
    pack = _pack("it")
    page.services_edit.setPlainText("ROLLBACK")  # same term, different case
    page._apply_pack(pack)

    lines = page.services_edit.toPlainText().splitlines()
    assert lines.count("rollback") == 0
    assert lines[0] == "ROLLBACK"
    assert len(lines) == len(pack.content("en").terms)  # one skipped, no net growth


def test_declining_the_confirm_changes_nothing(page, monkeypatch):
    monkeypatch.setattr("ui.settings_pages.glossary_page.MessageBox", _DecliningBox)
    page._apply_pack(_pack("it"))
    assert page.services_edit.toPlainText() == ""
    assert page.repl_edit.toPlainText() == ""


def test_import_is_a_single_undo_step(page):
    """One Ctrl+Z takes the whole pack back out — the reason _append_lines goes
    through a cursor rather than setPlainText."""
    page.services_edit.setPlainText("тариф Орбита")
    page._apply_pack(_pack("legal"))
    page.services_edit.undo()
    assert page.services_edit.toPlainText() == "тариф Орбита"


def test_imported_terms_round_trip_into_the_glossary(page):
    """The end of the import-copy promise: saved pack terms are ordinary terms."""
    from tests.test_glossary_page import FakeConfig

    pack = _pack("it")
    page._apply_pack(pack)
    page.apply_to(FakeConfig())

    reloaded = Glossary(page._glossary.path)
    assert reloaded.services == pack.content("en").terms
    assert reloaded.own_names == []
    assert len(reloaded.replacements) == len(pack.content("en").replacements)


def test_jurisdiction_note_reaches_the_confirm_dialog(page, monkeypatch):
    """The Legal pack's jurisdiction caveat must be shown where the user decides,
    not buried in a docstring. Spain's Spanish legal pack is wrong for Mexico and
    the user is entitled to know before importing, not after."""
    seen = {}

    class _CapturingBox(_AcceptingBox):
        def __init__(self, title, content, parent=None):
            super().__init__(title, content, parent)
            seen["content"] = content

    monkeypatch.setattr("ui.settings_pages.glossary_page.MessageBox", _CapturingBox)
    _set_locale(page, "es")
    page._apply_pack(_pack("legal"))

    assert _pack("legal").content("es").note in seen["content"]


def test_packs_are_disabled_on_free(qapp, tmp_path, monkeypatch):
    import licensing
    from licensing import Entitlement, Tier

    monkeypatch.setattr(licensing, "get_entitlement", lambda: Entitlement(Tier.FREE))
    from ui.settings_pages.glossary_page import GlossaryPage

    p = GlossaryPage()
    p._glossary = Glossary(tmp_path / "glossary.json")
    p._refresh_pack_status()

    assert p.pack_buttons and not any(b.isEnabled() for b in p.pack_buttons)
    assert not p.pack_locale_combo.isEnabled()
    assert "Pro feature" in p.pack_status_label.text()


def test_russian_replacements_normalize_rather_than_translate(tmp_path):
    """End-to-end through the engine: the RU medical pack must fix "экг" -> "ЭКГ"
    and leave the doctor's Russian alone."""
    content = _pack("medical").content("ru")

    g = Glossary(tmp_path / "glossary.json")
    g.services = list(content.terms)
    g.replacements = [{"heard": h, "canonical": c} for h, c in content.replacements]
    g._build_fuzzy_index()

    out = g.apply_replacements("пациенту выполнено экг, анамнез без особенностей")
    assert "ЭКГ" in out
    assert "анамнез" in out  # not "anamnesis"


# ---------- MessageBox stand-ins ----------

class _AcceptingBox:
    """MessageBox stand-in whose exec() confirms. Mirrors the real one's surface
    (cancelButton.hide() is called on the informational branch)."""

    def __init__(self, title, content, parent=None):
        self.title, self.content = title, content
        self.cancelButton = _Btn()

    def exec(self):
        return 1


class _DecliningBox(_AcceptingBox):
    def exec(self):
        return 0


class _Btn:
    def hide(self):
        pass

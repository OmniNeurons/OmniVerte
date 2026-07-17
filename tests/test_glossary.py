"""Glossary: round-trip, priority views, prompt budgets, and corrupt-file recovery."""

from __future__ import annotations

import json

import pytest

from services.glossary import GLOSSARY_FILENAME, Glossary, inspect_file


def _write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def gpath(tmp_path):
    return tmp_path / GLOSSARY_FILENAME


# ---------- data model / round-trip ----------

def test_missing_file_is_empty(gpath):
    g = Glossary(gpath)
    assert g.is_empty is True
    assert g.all_terms() == []
    assert g.asr_prompt() == ""
    assert g.llm_block() == ""


def test_round_trip_save_load(gpath):
    g = Glossary(gpath)
    g.own_names = ["Acme Corp"]
    g.counterparties = ["ООО Ромашка"]
    g.services = ["Z-tuning"]
    g.replacements = [{"heard": "зет тюнинг", "canonical": "Z-tuning"}]
    g.save()

    reloaded = Glossary(gpath)
    assert reloaded.own_names == ["Acme Corp"]
    assert reloaded.counterparties == ["ООО Ромашка"]
    assert reloaded.services == ["Z-tuning"]
    assert reloaded.replacements == [{"heard": "зет тюнинг", "canonical": "Z-tuning"}]
    assert reloaded.is_empty is False


def test_all_terms_priority_order_and_dedup(gpath):
    _write(gpath, {
        "own_names": ["Acme"],
        "counterparties": ["Globex", "acme"],   # 'acme' dup of own 'Acme'
        "services": ["Orbit"],
    })
    g = Glossary(gpath)
    # own_names first, then counterparties, then services; case-insensitive dedup
    # drops the second 'acme'.
    assert g.all_terms() == ["Acme", "Globex", "Orbit"]


def test_canonical_terms_includes_replacement_canonicals(gpath):
    _write(gpath, {
        "own_names": ["Acme"],
        "replacements": [{"heard": "zee tuning", "canonical": "Z-tuning"}],
    })
    g = Glossary(gpath)
    assert "Z-tuning" in g.canonical_terms()
    assert "Acme" in g.canonical_terms()


# ---------- prompt representations ----------

def test_asr_prompt_truncates_by_priority(gpath):
    _write(gpath, {
        "own_names": ["AAAA"],
        "services": ["BBBB", "CCCC"],
    })
    g = Glossary(gpath)
    # Budget fits only the first term — own_names wins.
    assert g.asr_prompt(max_chars=4) == "AAAA"
    # Roomier budget keeps priority order.
    assert g.asr_prompt(max_chars=100) == "AAAA, BBBB, CCCC"


def test_llm_block_is_markdown_bullets(gpath):
    _write(gpath, {"own_names": ["Acme Corp"], "services": ["Z-tuning"]})
    g = Glossary(gpath)
    block = g.llm_block()
    assert "- Acme Corp" in block
    assert "- Z-tuning" in block


def test_empty_glossary_yields_no_prompt_fragments(gpath):
    g = Glossary(gpath)
    assert g.asr_prompt() == ""
    assert g.hotwords() == ""
    assert g.llm_block() == ""


# ---------- corrupt-file recovery ----------

def test_unparseable_json_is_quarantined_and_starts_empty(gpath):
    gpath.write_text("{ this is not json", encoding="utf-8")
    g = Glossary(gpath)
    assert g.is_empty is True
    # Original file renamed aside; a fresh empty glossary runs.
    assert (gpath.parent / (GLOSSARY_FILENAME + ".corrupt")).exists()
    assert not gpath.exists()


def test_non_object_root_is_quarantined(gpath):
    _write(gpath, ["not", "an", "object"])
    g = Glossary(gpath)
    assert g.is_empty is True
    assert (gpath.parent / (GLOSSARY_FILENAME + ".corrupt")).exists()


def test_partial_invalid_sections_drop_bad_keep_good(gpath):
    _write(gpath, {
        "own_names": ["Acme", 123, "", "Globex"],          # drop 123 and ""
        "counterparties": "not-a-list",                     # whole section ignored
        "replacements": [
            {"heard": "x", "canonical": "X"},               # good
            {"heard": "", "canonical": "Y"},                # drop (empty heard)
            {"canonical": "Z"},                             # drop (missing heard)
            "nope",                                         # drop (not an object)
        ],
    })
    g = Glossary(gpath)
    assert g.own_names == ["Acme", "Globex"]
    assert g.counterparties == []
    assert g.replacements == [{"heard": "x", "canonical": "X"}]
    # Recoverable — file is NOT quarantined.
    assert not (gpath.parent / (GLOSSARY_FILENAME + ".corrupt")).exists()


def test_unknown_version_reads_as_v1(gpath):
    _write(gpath, {"version": 99, "own_names": ["Acme"]})
    g = Glossary(gpath)
    assert g.own_names == ["Acme"]


def test_quarantine_overwrites_previous_corrupt(gpath):
    corrupt = gpath.parent / (GLOSSARY_FILENAME + ".corrupt")
    corrupt.write_text("old", encoding="utf-8")
    gpath.write_text("{ broken", encoding="utf-8")
    Glossary(gpath)
    # Only one .corrupt remains, holding the latest bad file.
    assert corrupt.read_text(encoding="utf-8").startswith("{ broken")


def test_reload_picks_up_external_edits(gpath):
    g = Glossary(gpath)
    assert g.is_empty
    _write(gpath, {"own_names": ["Acme"]})
    g.reload()
    assert g.own_names == ["Acme"]


# ---------- inspect_file (CLI/UI validator) ----------

def test_inspect_missing_file(gpath):
    report = inspect_file(gpath)
    assert report["ok"] is True
    assert any("does not exist" in p for p in report["problems"])


def test_inspect_valid_file_reports_counts(gpath):
    _write(gpath, {
        "own_names": ["Acme", "Globex"],
        "services": ["Z-tuning"],
        "replacements": [{"heard": "x", "canonical": "X"}],
    })
    report = inspect_file(gpath)
    assert report["ok"] is True
    assert report["counts"]["own_names"] == 2
    assert report["counts"]["services"] == 1
    assert report["counts"]["replacements"] == 1


def test_inspect_unparseable_is_not_ok(gpath):
    gpath.write_text("{ broken", encoding="utf-8")
    report = inspect_file(gpath)
    assert report["ok"] is False
    # inspect_file must NOT modify the file (no quarantine side effect).
    assert gpath.exists()
    assert not (gpath.parent / (GLOSSARY_FILENAME + ".corrupt")).exists()


def test_inspect_non_list_section_is_not_ok(gpath):
    _write(gpath, {"own_names": "Acme"})
    report = inspect_file(gpath)
    assert report["ok"] is False
    assert any("own_names" in p for p in report["problems"])


def test_inspect_flags_bad_elements_but_stays_ok(gpath):
    _write(gpath, {"own_names": ["Acme", 5], "replacements": [{"heard": "x"}]})
    report = inspect_file(gpath)
    # Element-level issues are recoverable by the loader → ok stays True.
    assert report["ok"] is True
    assert report["counts"]["own_names"] == 1
    assert report["counts"]["replacements"] == 0
    assert len(report["problems"]) >= 2


# ---------- layer C: apply_replacements ----------

def test_empty_glossary_leaves_text_unchanged(gpath):
    g = Glossary(gpath)
    assert g.apply_replacements("nothing to replace here") == "nothing to replace here"


def test_explicit_map_is_case_insensitive_and_hyphen_flexible(gpath):
    _write(gpath, {"replacements": [{"heard": "зет тюнинг", "canonical": "Z-tuning"}]})
    g = Glossary(gpath)
    # case-insensitive, and "зет-тюнинг" (hyphen) matches the spaced heard
    assert g.apply_replacements("про ЗЕТ ТЮНИНГ сегодня") == "про Z-tuning сегодня"
    assert g.apply_replacements("про зет-тюнинг сегодня") == "про Z-tuning сегодня"


def test_explicit_map_only_replaces_whole_words(gpath):
    _write(gpath, {"replacements": [{"heard": "cat", "canonical": "DOG"}]})
    g = Glossary(gpath)
    # "category" must not become "DOGegory"
    assert g.apply_replacements("a cat in a category") == "a DOG in a category"


def test_explicit_map_fires_inside_cjk_text(gpath):
    """CJK writes without spaces, so a \\b-bounded pattern can never match inside
    a sentence — every neighbour of a Chinese character is itself a word char.
    The map used to fire only when the term was the whole string, which meant it
    silently did nothing in real Chinese or Japanese text."""
    _write(gpath, {"replacements": [{"heard": "心电图", "canonical": "ECG"}]})
    g = Glossary(gpath)
    assert g.apply_replacements("患者的心电图未见异常") == "患者的ECG未见异常"
    # Japanese, and with the term at the very start of the text.
    _write(gpath, {"replacements": [{"heard": "心電図", "canonical": "ECG"}]})
    g = Glossary(gpath)
    assert g.apply_replacements("心電図は異常なし") == "ECGは異常なし"


def test_cjk_fix_does_not_loosen_latin_or_cyrillic_bounds(gpath):
    """The boundary is dropped per-edge, only where a boundary cannot exist. A
    term in a bounded script keeps its \\b and must still not match inside a word."""
    _write(
        gpath,
        {
            "replacements": [
                {"heard": "cat", "canonical": "DOG"},
                {"heard": "кот", "canonical": "КОТ"},
            ]
        },
    )
    g = Glossary(gpath)
    assert g.apply_replacements("a cat in a category") == "a DOG in a category"
    assert g.apply_replacements("кот и котлета") == "КОТ и котлета"


def test_fuzzy_snaps_near_miss_to_canonical(gpath):
    _write(gpath, {"own_names": ["MasterDrive"]})
    g = Glossary(gpath)
    # "masterdrife" is one edit away — above the default 88 threshold.
    out = g.apply_replacements("I use masterdrife daily")
    assert "MasterDrive" in out


def test_fuzzy_leaves_distant_words_alone(gpath):
    _write(gpath, {"own_names": ["MasterDrive"]})
    g = Glossary(gpath)
    assert g.apply_replacements("I went swimming today") == "I went swimming today"


def test_fuzzy_skips_short_and_stopword_tokens(gpath):
    # "the" is a stopword; "Zip" is a <4-char single term → excluded from fuzzy.
    _write(gpath, {"own_names": ["Zip"], "services": ["the"]})
    g = Glossary(gpath)
    text = "the zip file"
    # Neither "the" nor a 3-char term may drive a fuzzy replacement.
    assert g.apply_replacements(text) == text


def test_fuzzy_index_truncates_to_max_terms(gpath, caplog):
    _write(gpath, {"own_names": [f"Term{i:03d}" for i in range(10)]})
    g = Glossary(gpath)
    with caplog.at_level("WARNING"):
        # Cap below the term count → only the first 3 survive in the fuzzy index.
        g.apply_replacements("nothing", max_terms=3)
    grouped, truncated = g._grouped_fuzzy(3)
    assert truncated is True
    assert sum(len(v) for v in grouped.values()) == 3
    assert any("truncated" in r.message.lower() for r in caplog.records)


def test_preview_reports_changes_without_writing(gpath):
    _write(gpath, {
        "own_names": ["MasterDrive"],
        "replacements": [{"heard": "зет тюнинг", "canonical": "Z-tuning"}],
    })
    g = Glossary(gpath)
    before = gpath.read_text(encoding="utf-8")
    result, changes = g.preview("masterdrife и зет тюнинг")
    assert "MasterDrive" in result and "Z-tuning" in result
    vias = {c["via"] for c in changes}
    assert "map" in vias and "fuzzy" in vias
    # preview must not modify the file
    assert gpath.read_text(encoding="utf-8") == before


def test_fuzzy_disabled_without_rapidfuzz_keeps_explicit_map(gpath, monkeypatch):
    import services.glossary as gmod

    monkeypatch.setattr(gmod, "_rf_fuzz", None)
    _write(gpath, {
        "own_names": ["MasterDrive"],
        "replacements": [{"heard": "zee", "canonical": "Z"}],
    })
    g = Glossary(gpath)
    out = g.apply_replacements("zee and masterdrife")
    # explicit map still fires; fuzzy is silently skipped
    assert out == "Z and masterdrife"


# ---------- layer B safety net: ASR prompt-echo stripping ----------

def _echo_glossary(gpath):
    _write(gpath, {
        "own_names": ["TraderNet", "TypiChat"],
        "services": ["TN", "tenant_id", "tenant"],
    })
    return Glossary(gpath)


def test_strip_asr_echo_removes_trailing_term_list(gpath):
    # The real-world failure: Whisper appends the bias prompt verbatim after
    # the trailing silence of a long recording.
    g = _echo_glossary(gpath)
    text = (
        "не стесняться использовать умные термины, это тоже хорошо, если будет "
        "в его промте. TraderNet, TypiChat, TN, tenant_id, tenant."
    )
    assert g.strip_asr_echo(text) == (
        "не стесняться использовать умные термины, это тоже хорошо, если будет "
        "в его промте."
    )


def test_strip_asr_echo_removes_leading_term_list(gpath):
    g = _echo_glossary(gpath)
    text = "TraderNet, TypiChat, TN, tenant_id, tenant. Сегодня обсудим релиз."
    assert g.strip_asr_echo(text) == "Сегодня обсудим релиз."


def test_strip_asr_echo_pure_echo_becomes_empty(gpath):
    # A near-silent streaming chunk can transcribe to nothing but the prompt.
    g = _echo_glossary(gpath)
    assert g.strip_asr_echo("TraderNet, TypiChat, TN, tenant_id, tenant") == ""


def test_strip_asr_echo_strips_partial_echo_of_three_terms(gpath):
    g = _echo_glossary(gpath)
    text = "Запишем требования. TN, tenant_id, tenant."
    assert g.strip_asr_echo(text) == "Запишем требования."


def test_strip_asr_echo_keeps_single_term_at_edge(gpath):
    g = _echo_glossary(gpath)
    text = "Не забудь проверить TraderNet."
    assert g.strip_asr_echo(text) == text


def test_strip_asr_echo_keeps_two_terms_of_a_larger_glossary(gpath):
    # A 2-term tail of a 5-term glossary is more likely real speech than an echo.
    g = _echo_glossary(gpath)
    text = "Мы передаем tenant_id, tenant."
    assert g.strip_asr_echo(text) == text


def test_strip_asr_echo_full_echo_of_two_term_glossary(gpath):
    # Glossaries smaller than min_terms: a run covering the whole glossary
    # (but never a single term) still counts as an echo.
    _write(gpath, {"own_names": ["TraderNet", "TypiChat"]})
    g = Glossary(gpath)
    assert g.strip_asr_echo("Привет, мир. TraderNet, TypiChat.") == "Привет, мир."


def test_strip_asr_echo_requires_prompt_order(gpath):
    # Terms out of prompt order are genuine speech, not an echo.
    g = _echo_glossary(gpath)
    text = "Сравним tenant, tenant_id и затем TN"
    assert g.strip_asr_echo(text) == text


def test_strip_asr_echo_ignores_terms_mid_text(gpath):
    g = _echo_glossary(gpath)
    text = "Мы используем TraderNet, TypiChat, TN, tenant_id, tenant в проде каждый день."
    assert g.strip_asr_echo(text) == text


def test_strip_asr_echo_is_word_bounded(gpath):
    # "TN"/"tenant" inside larger words must not match.
    g = _echo_glossary(gpath)
    text = "Обновили POTN, subtenant_id, multitenant."
    assert g.strip_asr_echo(text) == text


def test_strip_asr_echo_drops_dangling_separator(gpath):
    g = _echo_glossary(gpath)
    text = "и не забудь, TraderNet, TypiChat, TN, tenant_id, tenant"
    assert g.strip_asr_echo(text) == "и не забудь"


def test_strip_asr_echo_empty_glossary_and_empty_text(gpath):
    g = Glossary(gpath)
    assert g.strip_asr_echo("какой-то текст") == "какой-то текст"
    assert g.strip_asr_echo("") == ""

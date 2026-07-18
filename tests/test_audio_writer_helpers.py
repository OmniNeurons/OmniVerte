"""Pure backend-selection helpers and the hallucination-filter normalization.

These don't need a constructed AudioWriter (which would load a Whisper model) —
the module functions are free, and the methods only touch a handful of
attributes, so we build a bare instance with ``__new__`` and set them by hand.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from services import audio_writer as aw
from services.audio_writer import AudioWriter, WHISPER_HALLUCINATIONS


def _bare_writer() -> AudioWriter:
    return AudioWriter.__new__(AudioWriter)


# ---------- module-level helpers ----------

def test_model_key_for_backend():
    assert aw._model_key_for_backend("openai") == "MODEL_OPENAI"
    assert aw._model_key_for_backend("local") == "MODEL_LOCAL"


@pytest.mark.parametrize(
    "model,expected",
    [
        ("large-v3", "local"),
        ("tiny", "local"),
        ("whisper-1", "openai"),
        ("gpt-4o-mini-transcribe", "openai"),
        ("whisper-large-v3-turbo", "groq"),
        ("definitely-not-a-model", None),
    ],
)
def test_backend_for_model(model, expected):
    assert aw._backend_for_model(model) == expected


# ---------- credential / priority logic ----------

def test_backend_has_creds():
    w = _bare_writer()
    w.client = object()
    w.groq_client = None
    assert w._backend_has_creds("local") is True
    assert w._backend_has_creds("openai") is True
    assert w._backend_has_creds("groq") is False
    assert w._backend_has_creds("bogus") is False


def test_pick_initial_backend_skips_credless_entries():
    w = _bare_writer()
    w.client = None
    w.groq_client = object()
    w.config = SimpleNamespace(backend_priority=["openai", "groq", "local"])
    assert w._pick_initial_backend() == "groq"


def test_pick_initial_backend_falls_back_to_local():
    w = _bare_writer()
    w.client = None
    w.groq_client = None
    w.config = SimpleNamespace(backend_priority=["openai", "groq"])
    assert w._pick_initial_backend() == "local"


def test_cloud_fallback_order_appends_other_cloud_when_it_has_creds():
    w = _bare_writer()
    w.transcription_backend = "openai"
    w.client = object()
    w.groq_client = object()
    assert w._cloud_fallback_order() == ["openai", "groq"]


def test_cloud_fallback_order_is_empty_for_local():
    w = _bare_writer()
    w.transcription_backend = "local"
    assert w._cloud_fallback_order() == []


# ---------- hallucination filter ----------

@pytest.mark.parametrize(
    "raw",
    ["Thank you.", "  thanks for watching!!! ", "Субтитры…", "СПАСИБО ЗА ПРОСМОТР"],
)
def test_known_hallucinations_normalize_into_the_filter_set(raw):
    # Mirrors the inline normalization in streaming_transcribe: lowercase and
    # strip trailing sentence punctuation before the membership check.
    normalized = raw.strip().lower().rstrip(".!?…").strip()
    assert normalized in WHISPER_HALLUCINATIONS


def test_real_speech_is_not_filtered():
    normalized = "let's ship this on friday".rstrip(".!?…")
    assert normalized not in WHISPER_HALLUCINATIONS


# ---------- cross-segment overlap dedup ----------

def test_overlap_join_dedups_two_week_boundary():
    # The real report: "две недели" fell on a 20s seam and got re-transcribed at
    # the head of the next segment. The previous segment's copy is kept; the
    # incoming duplicate (and its bridging punctuation) is dropped.
    segments = [
        "...у него на это было две недели.",
        "Две недели, и, соответственно, он должен был сделать выводы.",
    ]
    joined = aw._dedup_overlap_join(segments)
    assert joined == (
        "...у него на это было две недели. "
        "и, соответственно, он должен был сделать выводы."
    )
    assert joined.lower().count("две недели") == 1


def test_overlap_join_leaves_non_overlapping_segments_intact():
    segments = ["Hello there.", "General Kenobi."]
    assert aw._dedup_overlap_join(segments) == "Hello there. General Kenobi."


def test_overlap_join_matches_across_punctuation_and_case():
    # Whisper re-transcribes the same audio with different casing/punctuation at
    # the seam; the normalized word match still lines them up.
    segments = ["we finished the report", "The report was sent to the client"]
    assert aw._dedup_overlap_join(segments) == "we finished the report was sent to the client"


def test_overlap_join_drops_segment_that_is_entirely_overlap():
    segments = ["the quick brown fox", "quick brown fox"]
    assert aw._dedup_overlap_join(segments) == "the quick brown fox"


def test_overlap_join_multi_word_run_prefers_longest():
    segments = ["a b c d e", "d e f g"]  # 2-word overlap "d e"
    assert aw._dedup_overlap_join(segments) == "a b c d e f g"


def test_overlap_join_handles_empty_and_single():
    assert aw._dedup_overlap_join([]) == ""
    assert aw._dedup_overlap_join(["  "]) == ""
    assert aw._dedup_overlap_join(["only one"]) == "only one"
    assert aw._dedup_overlap_join(["", "second"]) == "second"


def test_overlap_word_count_reports_run_and_cut():
    prev = "было две недели."
    nxt = "Две недели, и дальше"
    k, cut = aw._overlap_word_count(prev, nxt)
    assert k == 2
    assert nxt[cut:] == ", и дальше"


# ---------- fuzzy seam dedup (Whisper re-transcribes the overlap differently) ----------

def test_overlap_join_dedups_fuzzy_seam_with_inserted_and_substituted_words():
    # The reported case: same audio, different transcription on each side of the
    # seam — an inserted leading "А" and "он" -> "она". Exact matching missed it;
    # fuzzy alignment anchors on the shared "…что … делает" and drops the
    # re-transcribed head. The previous segment's copy (with "он") is kept.
    segments = [
        "...потому что непонятно пока, что он делает.",
        "А что она делает?",
    ]
    joined = aw._dedup_overlap_join(segments)
    assert joined == "...потому что непонятно пока, что он делает."
    assert joined.lower().count("делает") == 1


def test_overlap_join_keeps_coincidental_midtail_word_match():
    # "is" matches near (not at) prev's end; this is genuine new speech, not a
    # seam re-transcription. The reach guard must reject it so nothing is eaten.
    segments = ["the meeting is on Friday", "the report is ready"]
    assert aw._dedup_overlap_join(segments) == "the meeting is on Friday the report is ready"


def test_overlap_join_keeps_lone_leading_stopword_overlap():
    # Only a single short function word coincides at the seam and it doesn't
    # reach prev's end — must not trigger a cut.
    segments = ["we shipped the feature", "and the team celebrated"]
    assert aw._dedup_overlap_join(segments) == "we shipped the feature and the team celebrated"


def test_overlap_join_dedups_with_inserted_filler_only():
    # Overlap re-transcribed verbatim but with an inserted leading filler word;
    # head-slack lets the alignment start past it.
    segments = ["let's finish the report", "So the report is done"]
    assert aw._dedup_overlap_join(segments) == "let's finish the report is done"


# ---------- mangled final word at the seam ----------

def test_overlap_join_dedups_mangled_final_word():
    # Straight from the log (2026-07-15 12:40): a 2.3s finalizing tail whose
    # whole text is the overlap's last word, re-transcribed "сервера" ->
    # "Сервиса". Word-level difflib saw zero matching blocks, so the anchor never
    # formed and "Сервиса." was appended as if it were new speech.
    segments = [
        "Это будет часть кода или будем подгружать с внешнего сервера?",
        "Сервиса.",
    ]
    assert aw._dedup_overlap_join(segments) == (
        "Это будет часть кода или будем подгружать с внешнего сервера?"
    )


def test_overlap_join_dedups_mangled_final_word_keeping_new_speech():
    # Same mangling, but the tail carries real speech after the overlap word:
    # only the re-transcribed word is dropped, the rest survives.
    segments = ["будем подгружать с внешнего сервера", "сервиса и базы данных"]
    assert aw._dedup_overlap_join(segments) == (
        "будем подгружать с внешнего сервера и базы данных"
    )


def test_overlap_join_dedups_when_final_word_and_neighbour_both_mangled():
    # The fuzzy chance is spent on prev's final word only; the mangled word
    # before it stays unmatched. MATCH_FRAC (0.5) still accepts the run.
    segments = ["поднять модуль по проверке лицензий", "лицензии и ключей"]
    assert aw._dedup_overlap_join(segments) == "поднять модуль по проверке лицензий и ключей"


def test_overlap_join_keeps_short_lookalike_final_word():
    # Below MIN_LEN the fuzzy chance is not offered: "код"/"кот" stay distinct,
    # so genuine new speech is not eaten.
    segments = ["он смотрит на код", "кот сидит рядом"]
    assert aw._dedup_overlap_join(segments) == "он смотрит на код кот сидит рядом"


def test_overlap_join_keeps_distant_lookalike_final_word():
    # Shares a prefix but diverges hard — JaroWinkler (77) rejects it.
    segments = ["мы перенесли это на сервера", "северный офис переехал"]
    assert aw._dedup_overlap_join(segments) == "мы перенесли это на сервера северный офис переехал"


def test_overlap_join_lone_fuzzy_hit_may_not_eat_the_word_ahead_of_it():
    # From the log: prev ends "А здесь нужно", nxt starts "подсвечивать нужный".
    # "нужно"~"нужный" (ratio 73) anchors on nxt's SECOND word with no exact word
    # corroborating the seam, so cutting to it would swallow "подсвечивать" —
    # genuine speech. Uncorroborated, the fuzzy hit may only drop itself.
    segments = [
        "то есть к нужному блоку, который соответствует секунде. А здесь нужно",
        "подсвечивать нужный набор строк, причем делать это на блоке перевода.",
    ]
    assert "подсвечивать" in aw._dedup_overlap_join(segments)


def test_overlap_join_fuzzy_hit_with_exact_corroboration_still_cuts_run():
    # Same shape, but exact words ("но пока еще не") back the seam, so the
    # mangled "развернул" -> "развернуто" may cut the whole re-transcribed run.
    segments = [
        "со всеми ошибками, логами и так далее. Но пока еще не развернул.",
        "Но пока еще не развернуто, приходится заниматься вручную.",
    ]
    assert aw._dedup_overlap_join(segments) == (
        "со всеми ошибками, логами и так далее. Но пока еще не развернул. "
        "приходится заниматься вручную."
    )


def test_seam_words_alike_is_position_blind_not_a_homophone_test():
    # Guards the documented contract: this predicate is only sound because it is
    # asked about prev's final word. It deliberately accepts near-homophones
    # that similarity alone cannot separate from the true pair.
    assert aw._seam_words_alike("сервера", "сервиса")  # the true pair: ratio 71
    assert aw._seam_words_alike("кода", "когда")       # ratio 89 — accepted, by design
    assert not aw._seam_words_alike("может", "можно")
    assert not aw._seam_words_alike("он", "она")       # short: exact-only


def test_overlap_join_without_rapidfuzz_falls_back_to_exact(monkeypatch):
    # rapidfuzz is optional: the mangled-word fallback goes quiet and the join
    # degrades to the old exact behaviour rather than raising.
    monkeypatch.setattr(aw, "_rf_fuzz", None)
    monkeypatch.setattr(aw, "_rf_jaro", None)
    segments = ["подгружать с внешнего сервера", "Сервиса."]
    assert aw._dedup_overlap_join(segments) == "подгружать с внешнего сервера Сервиса."
    # Exact seams still dedup without it.
    assert aw._dedup_overlap_join(["a b c d e", "d e f g"]) == "a b c d e f g"


# ---------- glossary layer-A gating ----------

def _writer_with_glossary(flags: dict, *, empty: bool):
    """Bare writer with a fake config (flag dict) and a stub glossary."""
    w = _bare_writer()
    w.config = SimpleNamespace(get=lambda k, d=None: flags.get(k, d))
    w.glossary = SimpleNamespace(
        is_empty=empty,
        llm_block=lambda: "" if empty else "- Acme Corp",
    )
    return w


def test_glossary_block_none_when_master_switch_off():
    w = _writer_with_glossary(
        {"GLOSSARY_ENABLED": "false", "GLOSSARY_LLM_CORRECTION": "true"}, empty=False
    )
    assert w._glossary_block("GLOSSARY_LLM_CORRECTION") is None


def test_glossary_block_none_when_layer_flag_off():
    w = _writer_with_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_LLM_REWRITE": "false"}, empty=False
    )
    assert w._glossary_block("GLOSSARY_LLM_REWRITE") is None


def test_glossary_block_none_when_empty():
    w = _writer_with_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_LLM_CORRECTION": "true"}, empty=True
    )
    assert w._glossary_block("GLOSSARY_LLM_CORRECTION") is None


def test_glossary_block_present_when_enabled_and_nonempty():
    w = _writer_with_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_LLM_CORRECTION": "true"}, empty=False
    )
    assert w._glossary_block("GLOSSARY_LLM_CORRECTION") == "- Acme Corp"


def _client_capturing_user_content():
    """MagicMock OpenAI client; returns a fixed reply, lets us read the prompt."""
    from unittest.mock import MagicMock

    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )
    return client


def test_normalize_to_primary_injects_glossary_rule_when_active():
    w = _writer_with_glossary(
        {
            "GLOSSARY_ENABLED": "true",
            "GLOSSARY_LLM_CORRECTION": "true",
            "PRIMARY_LANGUAGE": "English",
        },
        empty=False,
    )
    w.client = _client_capturing_user_content()
    w._normalize_to_primary("some raw text")
    user_content = w.client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "Acme Corp" in user_content
    assert "canonical" in user_content.lower()


def test_normalize_to_primary_omits_glossary_rule_when_off():
    w = _writer_with_glossary(
        {
            "GLOSSARY_ENABLED": "false",
            "GLOSSARY_LLM_CORRECTION": "true",
            "PRIMARY_LANGUAGE": "English",
        },
        empty=False,
    )
    w.client = _client_capturing_user_content()
    w._normalize_to_primary("some raw text")
    user_content = w.client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "canonical" not in user_content.lower()
    assert "7." not in user_content  # no appended 7th rule


def test_glossary_layers_gate_independently():
    # Correction on, rewrite off — same glossary, different layer flags.
    w = _writer_with_glossary(
        {
            "GLOSSARY_ENABLED": "true",
            "GLOSSARY_LLM_CORRECTION": "true",
            "GLOSSARY_LLM_REWRITE": "false",
        },
        empty=False,
    )
    assert w._glossary_block("GLOSSARY_LLM_CORRECTION") == "- Acme Corp"
    assert w._glossary_block("GLOSSARY_LLM_REWRITE") is None


# ---------- glossary layer-B gating (ASR bias) ----------

def _writer_with_asr_glossary(flags: dict, *, empty: bool):
    """Bare writer whose stub glossary exposes asr_prompt()/hotwords()."""
    w = _bare_writer()
    w.config = SimpleNamespace(get=lambda k, d=None: flags.get(k, d))
    w.glossary = SimpleNamespace(
        is_empty=empty,
        asr_prompt=lambda max_chars=600: "" if empty else "Acme Corp, Z-tuning",
        hotwords=lambda max_chars=1000: "" if empty else "Acme Corp, Z-tuning",
    )
    return w


def test_glossary_asr_active_gating():
    on = _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_ASR_BIAS": "true"}, empty=False
    )
    assert on._glossary_asr_active() is True
    # master off
    assert _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "false", "GLOSSARY_ASR_BIAS": "true"}, empty=False
    )._glossary_asr_active() is False
    # layer flag off
    assert _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_ASR_BIAS": "false"}, empty=False
    )._glossary_asr_active() is False
    # empty glossary
    assert _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_ASR_BIAS": "true"}, empty=True
    )._glossary_asr_active() is False


def test_whisper_glossary_kwargs_present_when_active():
    w = _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_ASR_BIAS": "true"}, empty=False
    )
    assert w._whisper_glossary_kwargs() == {"hotwords": "Acme Corp, Z-tuning"}


def test_whisper_glossary_kwargs_empty_when_off():
    w = _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "false", "GLOSSARY_ASR_BIAS": "true"}, empty=False
    )
    assert w._whisper_glossary_kwargs() == {}


def _cloud_client():
    """MagicMock OpenAI-compatible client; captures transcriptions.create kwargs."""
    from unittest.mock import MagicMock

    client = MagicMock()
    client.audio.transcriptions.create.return_value = SimpleNamespace(text="hi")
    return client


def test_cloud_transcribe_passes_prompt_when_active(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")
    w = _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_ASR_BIAS": "true"}, empty=False
    )
    w._whisper_language_hint = lambda: None
    client = _cloud_client()
    w._transcribe_via_cloud(str(audio), client, "openai", "whisper-1")
    kwargs = client.audio.transcriptions.create.call_args.kwargs
    assert kwargs["prompt"] == "Acme Corp, Z-tuning"


def test_cloud_transcribe_omits_prompt_when_off(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")
    w = _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "false", "GLOSSARY_ASR_BIAS": "true"}, empty=False
    )
    w._whisper_language_hint = lambda: None
    client = _cloud_client()
    w._transcribe_via_cloud(str(audio), client, "openai", "whisper-1")
    assert "prompt" not in client.audio.transcriptions.create.call_args.kwargs


# ---------- glossary layer-B echo scrub (ASR prompt echoed into the result) ----------

def test_transcribe_dispatch_scrubs_echo_when_active():
    w = _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_ASR_BIAS": "true"}, empty=False
    )
    w.glossary.strip_asr_echo = lambda text: "clean speech."
    w.transcription_backend = "local"
    w._transcribe_via_local_whisper = lambda path, streaming=False: (
        "clean speech. Acme Corp, Z-tuning."
    )
    assert w._transcribe_audio_file("a.wav") == "clean speech."


def test_transcribe_dispatch_leaves_text_alone_when_layer_off():
    w = _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "false", "GLOSSARY_ASR_BIAS": "true"}, empty=False
    )
    # With layer B off no prompt was sent, so the scrub must not even run.
    w.glossary.strip_asr_echo = lambda text: pytest.fail(
        "strip_asr_echo must not be called when layer B is inactive"
    )
    w.transcription_backend = "local"
    w._transcribe_via_local_whisper = lambda path, streaming=False: "raw text"
    assert w._transcribe_audio_file("a.wav") == "raw text"


def test_cloud_transcribe_result_is_scrubbed(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")
    w = _writer_with_asr_glossary(
        {"GLOSSARY_ENABLED": "true", "GLOSSARY_ASR_BIAS": "true"}, empty=False
    )
    w.glossary.strip_asr_echo = lambda text: text.replace(" Acme Corp, Z-tuning.", "")
    w._whisper_language_hint = lambda: None
    w.transcription_backend = "openai"
    w.client = _cloud_client()
    w.client.audio.transcriptions.create.return_value = SimpleNamespace(
        text="hello world. Acme Corp, Z-tuning."
    )
    w.groq_client = None
    w.config = SimpleNamespace(
        get=lambda k, d=None: {
            "GLOSSARY_ENABLED": "true",
            "GLOSSARY_ASR_BIAS": "true",
            "MODEL_OPENAI": "whisper-1",
        }.get(k, d),
        backend_priority=["openai"],
    )
    assert w._transcribe_audio_file(str(audio)) == "hello world."


# ---------- glossary layer-C scope (deterministic replacements) ----------

_FUZZY_ON = {
    "GLOSSARY_ENABLED": "true",
    "GLOSSARY_FUZZY_REPLACE": "true",
    "GLOSSARY_FUZZY_THRESHOLD": "88",
    "GLOSSARY_FUZZY_MAX_TERMS": "200",
}


def _writer_with_fuzzy(flags: dict, active_action: str, *, client):
    """Bare writer whose stub glossary spies on apply_replacements()."""
    w = _bare_writer()
    w.config = SimpleNamespace(get=lambda k, d=None: flags.get(k, d))
    calls = []
    w.glossary = SimpleNamespace(
        is_empty=False,
        llm_block=lambda: "- Acme",
        apply_replacements=lambda text, **kw: (calls.append(text) or f"CANON {text}"),
    )
    w._apply_calls = calls
    w.active_action = active_action
    w.client = client
    return w


def test_layer_c_runs_for_transcribe_and_survives_no_client():
    w = _writer_with_fuzzy(_FUZZY_ON, "transcribe", client=None)
    out = w._apply_action_transform("hello")
    assert w._apply_calls == ["hello"]      # layer C ran
    assert out == "CANON hello"             # ...and survived the no-client return


def test_layer_c_runs_before_normalize_for_transcribe():
    w = _writer_with_fuzzy(_FUZZY_ON, "transcribe", client=object())
    captured = {}
    w._normalize_to_primary = lambda raw: captured.__setitem__("raw", raw) or "NORM"
    out = w._apply_action_transform("hello")
    assert captured["raw"] == "CANON hello"  # normalize sees the C-corrected text
    assert out == "NORM"


def test_layer_c_skipped_for_translate(monkeypatch):
    import services.text_operations as ops

    monkeypatch.setattr(ops, "translate_to_language", lambda *a, **k: "TRANSLATED")
    w = _writer_with_fuzzy(_FUZZY_ON, "translate", client=object())
    out = w._apply_action_transform("hello")
    assert w._apply_calls == []              # layer C must NOT touch translate
    assert out == "TRANSLATED"


def test_layer_c_skipped_for_custom(monkeypatch):
    import services.text_operations as ops

    monkeypatch.setattr(ops, "rewrite_text", lambda *a, **k: "REWRITTEN")
    flags = {**_FUZZY_ON, "HOTKEY_CUSTOM_STYLE": "casual"}
    w = _writer_with_fuzzy(flags, "custom", client=object())
    out = w._apply_action_transform("hello")
    assert w._apply_calls == []
    assert out == "REWRITTEN"


def test_layer_c_not_run_when_flag_off():
    flags = {**_FUZZY_ON, "GLOSSARY_FUZZY_REPLACE": "false"}
    w = _writer_with_fuzzy(flags, "transcribe", client=None)
    out = w._apply_action_transform("hello")
    assert w._apply_calls == []
    assert out == "hello"


# ---------- live transcription resync after a settings save ----------

class _FakeConfig:
    """Minimal Config stand-in: secrets, priority, values, and a recorded set()."""

    def __init__(self, *, secrets=None, priority=None, values=None):
        self._secrets = dict(secrets or {})
        self.backend_priority = list(priority or [])
        self._values = dict(values or {})
        self.sets: dict[str, str] = {}

    def get_secret(self, key):
        return self._secrets.get(key)

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self.sets[key] = value
        self._values[key] = value

    def set_backend_priority(self, backends):
        self.backend_priority = list(backends)
        self.sets["BACKEND_PRIORITY"] = ",".join(backends)


def _patch_openai(monkeypatch):
    """Replace openai.OpenAI with a recorder; returns the list of kwargs seen."""
    calls: list[dict] = []

    def _factory(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(aw.openai, "OpenAI", _factory)
    return calls


def test_build_cloud_clients_from_secrets(monkeypatch):
    calls = _patch_openai(monkeypatch)
    w = _bare_writer()
    w.config = _FakeConfig(secrets={"OPEN_AI_API_KEY": "sk-x", "GROQ_API_KEY": "gk-y"})
    w._build_cloud_clients()

    assert w.client is not None
    assert w.groq_client is not None
    # Groq must be built against the Groq base_url; OpenAI must not be.
    groq_calls = [c for c in calls if c.get("base_url") == aw.GROQ_BASE_URL]
    assert len(groq_calls) == 1 and groq_calls[0]["api_key"] == "gk-y"
    assert any(c.get("base_url") is None and c["api_key"] == "sk-x" for c in calls)


def test_build_cloud_clients_none_without_secrets(monkeypatch):
    _patch_openai(monkeypatch)
    w = _bare_writer()
    w.config = _FakeConfig(secrets={})
    w._build_cloud_clients()
    assert w.client is None
    assert w.groq_client is None


def test_reload_transcription_settings_repicks_by_priority(monkeypatch):
    _patch_openai(monkeypatch)
    w = _bare_writer()
    reinit = []
    monkeypatch.setattr(w, "_reinit_backend_async", lambda: reinit.append(True))
    w.config = _FakeConfig(
        secrets={"GROQ_API_KEY": "gk"},  # only Groq has a key
        priority=["groq", "openai", "local"],
        values={"MODEL_GROQ": "whisper-large-v3-turbo", "USE_DEVICE": "cpu"},
    )
    w.reload_transcription_settings()

    assert w.transcription_backend == "groq"
    assert w.whisper_model_name == "whisper-large-v3-turbo"
    assert w.config.sets["TRANSCRIPTION_BACKEND"] == "groq"
    assert w.config.sets["WHISPER_MODEL"] == "whisper-large-v3-turbo"
    assert reinit == [True]  # background reload kicked exactly once


def test_reload_reads_audio_capture_settings(monkeypatch):
    _patch_openai(monkeypatch)
    w = _bare_writer()
    monkeypatch.setattr(w, "_reinit_backend_async", lambda: None)
    w.config = _FakeConfig(
        secrets={},
        priority=["local"],
        values={
            "MODEL_LOCAL": "small",
            "USE_DEVICE": "cpu",
            "AUDIO_ENHANCE": "off",
            "INPUT_DEVICE": "name::Desk Mic",
        },
    )
    w.reload_transcription_settings()
    assert w._audio_enhance_profile == "off"
    assert w._input_device_config == "name::Desk Mic"


def test_write_transcription_wav_calls_prepare(monkeypatch, tmp_path):
    _patch_openai(monkeypatch)
    w = _bare_writer()
    w.fs = 16000
    w._audio_enhance_profile = "light"
    calls = []

    def fake_prepare(samples, sample_rate, profile="light"):
        calls.append((sample_rate, profile, np.asarray(samples).shape))
        return np.asarray(samples, dtype=np.int16).reshape(-1)

    written = []

    def fake_wav_write(path, rate, data):
        written.append((path, rate, np.asarray(data).dtype, np.asarray(data).shape))

    monkeypatch.setattr(aw, "prepare_for_transcription", fake_prepare)
    monkeypatch.setattr(aw.wav, "write", fake_wav_write)

    pcm = np.zeros((1600, 1), dtype=np.int16)
    path = str(tmp_path / "seg.wav")
    w._write_transcription_wav(path, pcm)
    assert calls == [(16000, "light", (1600, 1))]
    assert written[0][0] == path
    assert written[0][1] == 16000
    assert written[0][2] == np.int16


def test_reload_picks_local_without_cloud_creds(monkeypatch):
    _patch_openai(monkeypatch)
    w = _bare_writer()
    monkeypatch.setattr(w, "_reinit_backend_async", lambda: None)
    w.config = _FakeConfig(
        secrets={},
        priority=["openai", "groq", "local"],
        values={"MODEL_LOCAL": "small", "USE_DEVICE": "cuda"},
    )
    w.reload_transcription_settings()

    assert w.transcription_backend == "local"
    assert w.whisper_model_name == "small"
    assert w.use_device == "cuda"


def test_reload_overrides_in_session_tray_pick(monkeypatch):
    _patch_openai(monkeypatch)
    w = _bare_writer()
    monkeypatch.setattr(w, "_reinit_backend_async", lambda: None)
    w.transcription_backend = "openai"  # a manual tray pick earlier this session
    w.config = _FakeConfig(
        secrets={"GROQ_API_KEY": "gk"},
        priority=["groq", "local"],  # openai not even in the list now
        values={"MODEL_GROQ": "whisper-large-v3-turbo", "USE_DEVICE": "cpu"},
    )
    w.reload_transcription_settings()
    # Settings is the source of truth: the save re-resolves to groq.
    assert w.transcription_backend == "groq"


def test_reload_rebuilds_client_so_new_key_works(monkeypatch):
    _patch_openai(monkeypatch)
    w = _bare_writer()
    monkeypatch.setattr(w, "_reinit_backend_async", lambda: None)
    # Start credless on local (clients None).
    w.client = None
    w.groq_client = None
    w.transcription_backend = "local"
    cfg = _FakeConfig(
        secrets={},
        priority=["openai", "local"],
        values={
            "MODEL_OPENAI": "gpt-4o-mini-transcribe",
            "MODEL_LOCAL": "small",
            "USE_DEVICE": "cpu",
        },
    )
    w.config = cfg
    # User adds an OpenAI key via Settings (persisted to the credential store).
    cfg._secrets["OPEN_AI_API_KEY"] = "sk-new"
    w.reload_transcription_settings()

    assert w.client is not None  # rebuilt from the new key
    assert w.transcription_backend == "openai"  # now creds-aware → flips to cloud
    assert w.whisper_model_name == "gpt-4o-mini-transcribe"


# ---------- tray model pick promotes the backend in BACKEND_PRIORITY ----------

def test_promote_backend_priority_moves_to_front():
    w = _bare_writer()
    w.config = _FakeConfig(priority=["openai", "groq", "local"])
    w._promote_backend_priority("local")
    assert w.config.backend_priority == ["local", "openai", "groq"]
    assert w.config.sets["BACKEND_PRIORITY"] == "local,openai,groq"
    # Idempotent when the backend is already the head.
    w._promote_backend_priority("local")
    assert w.config.backend_priority == ["local", "openai", "groq"]


def test_promote_backend_priority_tops_up_missing_backends():
    w = _bare_writer()
    w.config = _FakeConfig(priority=["local"])  # truncated list
    w._promote_backend_priority("openai")
    order = w.config.backend_priority
    assert order[0] == "openai"
    assert set(order) == {"openai", "groq", "local"}  # all backends reachable


def test_change_transcription_model_promotes_local(monkeypatch):
    w = _bare_writer()
    reinit = []
    monkeypatch.setattr(w, "_reinit_backend_async", lambda: reinit.append(True))
    w.config = _FakeConfig(
        priority=["openai", "groq", "local"],
        values={"MODEL_LOCAL": "small"},
    )
    w.change_transcription_model("large-v3")  # a local model

    assert w.transcription_backend == "local"
    assert w.whisper_model_name == "large-v3"
    assert w.config.backend_priority[0] == "local"  # Whisper is now the head
    assert w.config.sets["TRANSCRIPTION_BACKEND"] == "local"
    assert w.config.sets["WHISPER_MODEL"] == "large-v3"
    assert w.config.sets["MODEL_LOCAL"] == "large-v3"
    assert reinit == [True]


def test_change_transcription_model_promotes_cloud(monkeypatch):
    w = _bare_writer()
    monkeypatch.setattr(w, "_reinit_backend_async", lambda: None)
    w.config = _FakeConfig(priority=["openai", "groq", "local"])
    w.change_transcription_model("whisper-large-v3-turbo")  # a Groq model

    assert w.transcription_backend == "groq"
    assert w.config.backend_priority[0] == "groq"


def test_change_transcription_model_unknown_is_noop(monkeypatch):
    w = _bare_writer()
    reinit = []
    monkeypatch.setattr(w, "_reinit_backend_async", lambda: reinit.append(True))
    w.config = _FakeConfig(priority=["openai", "groq", "local"])
    w.change_transcription_model("definitely-not-a-model")

    assert "BACKEND_PRIORITY" not in w.config.sets  # priority untouched
    assert reinit == []  # no background reload

# file: services/glossary.py

"""
Corporate glossary: user-defined canonical terms (own names, counterparties,
services/terms, and an explicit ``heard -> canonical`` replacement map) that bias
the transcription pipeline so company-specific words are recognized and written
canonically. No local-model fine-tuning is involved.

One JSON artefact feeds three independently-flagged layers:

  A. canonical terms injected into the LLM correction / translate / rewrite prompt
  B. terms biasing the ASR step (cloud ``prompt``, local faster-whisper ``hotwords``)
  C. deterministic fuzzy replacements on the final transcript (transcribe only)

This module owns the data model and the per-layer *representations* only — the
wiring into the pipeline lives in ``services.audio_writer`` /
``services.text_operations``. It also owns :meth:`Glossary.strip_asr_echo`, the
layer-B safety net that removes the bias prompt when Whisper echoes it into the
transcript (typically after trailing silence).

Storage: a single file ``%APPDATA%\\OmniVerte\\glossary.json`` next to
``config.env``. The lists can be long and structured, so they live here rather
than in ``config.env``; the small on/off flags and thresholds stay in
``Config.DEFAULTS``.

Loading is total: it never raises and never silently disables the whole feature
on a bad file. An unparseable / wrong-shaped file is backed up to
``glossary.json.corrupt`` and an empty glossary is started; partially-invalid
sections are dropped element-by-element with a log, keeping whatever is valid.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

from services.config_store import _appdata_dir

try:  # Layer C only — the feature degrades to the explicit map without it.
    from rapidfuzz import fuzz as _rf_fuzz
except ImportError:  # pragma: no cover - exercised via the missing-module test
    _rf_fuzz = None

logger = logging.getLogger(__name__)

GLOSSARY_FILENAME = "glossary.json"
SCHEMA_VERSION = 1

# Priority order of the term lists: own names first (most important to get
# right), then counterparties, then services/terms. Drives both the flat
# all_terms() view and the priority-based truncation in asr_prompt()/hotwords().
_TERM_SECTIONS = ("own_names", "counterparties", "services")

# Word tokens for layer-C fuzzy matching. ``\w+`` is Unicode-aware for str
# patterns, so it covers Cyrillic; hyphens split a token in two (handled by
# normalizing hyphen->space on both sides so "Z-tuning" still lines up).
#
# Known limit: CJK writes without spaces, so this returns ONE token spanning a
# whole clause of Chinese or Japanese. The fuzzy pass is therefore inert on those
# languages — no term ever matches a clause-sized token. That is a documented,
# accepted gap, not an oversight: making it work needs a per-script tokenizer,
# metric, threshold and window, and the metric is the blocker — token_sort_ratio
# discards character order, scoring a scrambled 图电心 against 心电图 at 100.
# The explicit map handles CJK (see _heard_regex), and homophone substitution —
# the characteristic CJK recognition error — is exactly what it is good at.
_WORD_RE = re.compile(r"\w+")

# CJK scripts: kana, CJK ideographs (incl. extension A), compatibility ideographs
# and half-width kana. Used only by _heard_regex, to decide whether a word
# boundary can meaningfully be asserted at a term's edge.
_CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿ｦ-ﾟ]")

# Frequent function words, grouped by language for review and unioned into one
# flat set for use. A single-token window equal to one of these is never a
# fuzzy-replacement candidate (it would mangle ordinary speech).
#
# Be clear about how little this does on the fuzzy path: it is only consulted
# for single-token windows, in the same expression as `len(norm) <
# _MIN_FUZZY_TOKEN_LEN` (see _build_fuzzy_index / _apply_fuzzy), so every entry
# shorter than 4 characters is already dead weight there. The real fuzzy guard
# is the length floor, not this set.
#
# Its load-bearing consumer is the pack-data test suite. The *explicit* map has
# no length floor — _apply_explicit_map fires _heard_regex verbatim, however
# short — so tests/test_glossary_packs.py checks pack replacement "heard" sides
# against this set. There a two-letter entry is the whole point: it is what stops
# a pack author shipping ("para", "Pará") or ("и", "И").
#
# All shipped languages go in, whether or not they have a glossary pack: the
# fuzzy path processes the user's *speech*, which can be any app language.
# zh/ja are absent on purpose — with _WORD_RE (`\w+`) yielding one token per
# unspaced clause, "function word" has no referent there.
_STOP_WORDS_BY_LANGUAGE: dict[str, frozenset[str]] = {
    "ru": frozenset({
        "и", "в", "во", "не", "на", "с", "со", "что", "как", "а", "то", "от",
        "о", "об", "у", "за", "из", "по", "для", "до", "или", "но", "же", "бы",
        "ли", "это", "так", "вот", "я", "ты", "он", "она", "оно", "мы", "вы",
        "они", "мне", "меня", "тебя", "его", "её", "их", "был", "была", "быть",
    }),
    "en": frozenset({
        "the", "and", "of", "to", "a", "an", "in", "on", "at", "is", "it",
        "for", "with", "as", "by", "or", "be", "this", "that", "i", "you",
        "he", "she", "we", "they", "my", "are", "was", "were", "but", "not",
    }),
    "es": frozenset({
        "de", "la", "el", "que", "y", "en", "un", "una", "los", "las", "por",
        "para", "con", "no", "se", "del", "al", "es", "como", "pero", "esta",
        "este", "esto", "todo", "más", "sobre", "entre", "desde", "hasta",
        "cuando", "porque", "también", "yo", "tú", "él", "ella", "ser",
        "está", "son", "hay", "fue",
    }),
    "fr": frozenset({
        "le", "la", "les", "un", "une", "des", "de", "du", "et", "à", "au",
        "aux", "en", "dans", "pour", "par", "avec", "sur", "que", "qui",
        "ne", "pas", "plus", "ou", "mais", "comme", "cette", "ces", "son",
        "sont", "est", "être", "tout", "nous", "vous", "ils", "elle",
        "leur", "aussi", "dont",
    }),
    "de": frozenset({
        "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
        "einer", "und", "oder", "aber", "nicht", "ist", "sind", "war",
        "auf", "in", "im", "an", "am", "zu", "zum", "zur", "von", "vom",
        "mit", "für", "aus", "bei", "nach", "über", "durch", "auch",
        "dass", "sich", "wird", "werden", "haben", "hat", "als", "wie",
        "man", "noch", "nur", "schon",
    }),
    "it": frozenset({
        "il", "lo", "la", "i", "gli", "le", "un", "una", "di", "del", "della",
        "delle", "dei", "degli", "e", "o", "ma", "non", "che", "chi", "con",
        "per", "da", "in", "nel", "nella", "su", "come", "anche", "questo",
        "questa", "sono", "essere", "più", "quando", "perché", "già",
        "molto", "tutto", "dove",
    }),
}

# One flat set: the runtime asks "is this token a function word in any language
# we ship", because it cannot know which language it is reading. Glossary is
# built without a Config, sees plain text, and a real sentence mixes languages —
# PRIMARY and SECONDARY are live at once, and the RU IT pack exists precisely
# because Russian devs say "мёрж реквест" and write "merge request". A
# per-language lookup would not merely be more work; it would un-guard the
# English words inside a Russian sentence.
#
# The price, pinned by test_no_pack_term_is_a_stop_word: a function word in one
# language silently drops an identical single-word term in another out of the
# fuzzy index.
_STOP_WORDS: frozenset[str] = frozenset().union(*_STOP_WORDS_BY_LANGUAGE.values())

# Minimum normalized length for a single-token fuzzy candidate / term. Shorter
# tokens are too collision-prone for fuzzy matching; they stay reachable through
# the explicit replacement map only.
_MIN_FUZZY_TOKEN_LEN = 4


class Glossary:
    """The corporate glossary: data model + per-layer representations."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else _appdata_dir() / GLOSSARY_FILENAME
        # Active-term cap for the Free tier (see set_active_cap). None == no cap
        # (Pro / no gate) → byte-identical to a build without the feature. Set
        # before _load(), which builds the fuzzy index against it, and preserved
        # across reload() (which never resets it).
        self._active_cap: Optional[int] = None
        self._reset()
        self._load()

    # ---------- loading / recovery ----------

    def _reset(self) -> None:
        self.version = SCHEMA_VERSION
        self.own_names: list[str] = []
        self.counterparties: list[str] = []
        self.services: list[str] = []
        self.replacements: list[dict[str, str]] = []
        # Layer-C fuzzy index: priority-ordered (norm, canonical, n_words) for
        # 1–3-word terms, built once per load so apply_replacements doesn't
        # re-normalize on every call. Empty until _ingest populates it.
        self._fuzzy_terms: list[tuple[str, str, int]] = []
        self._warned_no_rapidfuzz = False

    def _load(self) -> None:
        self._reset()
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            self._quarantine(f"unreadable / invalid JSON: {e}")
            return
        if not isinstance(data, dict):
            self._quarantine("root is not a JSON object")
            return
        self._ingest(data)

    def _quarantine(self, reason: str) -> None:
        """Back up an unrecoverable file to ``.corrupt`` and start empty.

        We never auto-``save()`` here: the user's (broken) file is renamed aside
        so a fresh empty glossary can run and the bad copy survives for
        inspection / manual repair, but we don't overwrite their data.
        """
        self._reset()
        corrupt = self.path.with_name(self.path.name + ".corrupt")
        try:
            if corrupt.exists():
                corrupt.unlink()
            self.path.replace(corrupt)
            logger.warning(
                f"{self.path.name} invalid ({reason}); backed up to "
                f"{corrupt.name}, starting with an empty glossary"
            )
        except OSError as e:
            logger.warning(
                f"{self.path.name} invalid ({reason}); failed to back it up "
                f"({e}), starting with an empty glossary"
            )

    def _ingest(self, data: dict) -> None:
        version = data.get("version", SCHEMA_VERSION)
        if isinstance(version, int):
            self.version = version
            if version != SCHEMA_VERSION:
                logger.warning(
                    f"{self.path.name}: unknown version {version}, reading as v{SCHEMA_VERSION}"
                )
        for section in _TERM_SECTIONS:
            setattr(self, section, self._clean_terms(data.get(section), section))
        self.replacements = self._clean_replacements(data.get("replacements"))
        self._build_fuzzy_index()

    def _clean_terms(self, value, section: str) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            logger.warning(f"glossary section '{section}' is not a list, ignoring")
            return []
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            else:
                logger.warning(
                    f"glossary section '{section}': dropping non-string/empty entry {item!r}"
                )
        return out

    def _clean_replacements(self, value) -> list[dict[str, str]]:
        if value is None:
            return []
        if not isinstance(value, list):
            logger.warning("glossary 'replacements' is not a list, ignoring")
            return []
        out: list[dict[str, str]] = []
        for item in value:
            heard = item.get("heard") if isinstance(item, dict) else None
            canonical = item.get("canonical") if isinstance(item, dict) else None
            if (
                isinstance(heard, str)
                and isinstance(canonical, str)
                and heard.strip()
                and canonical.strip()
            ):
                out.append({"heard": heard.strip(), "canonical": canonical.strip()})
            else:
                logger.warning(
                    f"glossary replacement missing/empty heard|canonical, dropping: {item!r}"
                )
        return out

    def reload(self) -> None:
        """Re-read the file from disk (after the settings dialog saved lists)."""
        self._load()

    # ---------- persistence ----------

    def save(self) -> None:
        """Atomic write (tmp + replace), UTF-8, version-stamped."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": SCHEMA_VERSION,
            "own_names": self.own_names,
            "counterparties": self.counterparties,
            "services": self.services,
            "replacements": self.replacements,
        }
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        tmp.replace(self.path)

    # ---------- views ----------

    @property
    def is_empty(self) -> bool:
        return not (
            self.own_names or self.counterparties or self.services or self.replacements
        )

    def _all_terms_uncapped(self) -> list[str]:
        """Flat priority-ordered term list, case-insensitively de-duplicated.

        Order: own_names -> counterparties -> services. The active cap (if any)
        is applied by :meth:`all_terms` / :meth:`_active_split`, not here.
        """
        seen: set[str] = set()
        out: list[str] = []
        for section in _TERM_SECTIONS:
            for term in getattr(self, section):
                key = term.casefold()
                if key not in seen:
                    seen.add(key)
                    out.append(term)
        return out

    def _active_split(self) -> tuple[list[str], list[dict[str, str]]]:
        """Priority-ordered (terms, replacements) after applying the active cap.

        Section terms (own_names -> counterparties -> services, de-duped) come
        first, then replacements. With a cap of N the combined set is truncated
        to N entries — terms before replacements — so the Free tier feeds at most
        N terms into every layer. ``None`` cap returns everything unchanged.
        """
        terms = self._all_terms_uncapped()
        reps = list(self.replacements)
        cap = self._active_cap
        if cap is None:
            return terms, reps
        terms = terms[:cap]
        remaining = max(0, cap - len(terms))
        return terms, reps[:remaining]

    def all_terms(self) -> list[str]:
        """Flat priority-ordered term list (capped), case-insensitively de-duped.

        Order: own_names -> counterparties -> services. Replacement canonicals
        are added by :meth:`canonical_terms` (used by the LLM block), not here.
        """
        return self._active_split()[0]

    def canonical_terms(self) -> list[str]:
        """:meth:`all_terms` plus the canonical side of explicit replacements."""
        terms, reps = self._active_split()
        out = list(terms)
        seen = {t.casefold() for t in out}
        for rep in reps:
            key = rep["canonical"].casefold()
            if key not in seen:
                seen.add(key)
                out.append(rep["canonical"])
        return out

    # ---------- Free-tier active-term cap ----------

    def active_term_count(self) -> int:
        """Distinct terms that feed the layers when uncapped: de-duped section
        terms plus explicit replacements. This is the figure the Free cap is
        measured against and the glossary settings page shows as 'N terms'."""
        return len(self._all_terms_uncapped()) + len(self.replacements)

    def set_active_cap(self, cap: Optional[int]) -> None:
        """Limit how many terms (across all sections) feed the three layers.

        ``None`` or a negative value means unlimited (Pro / no gate). Applied on
        read only — ``glossary.json`` is never mutated. Rebuilds the layer-C
        fuzzy index so it reflects the new cap.
        """
        normalized = cap if (cap is not None and cap >= 0) else None
        if normalized == self._active_cap:
            return
        self._active_cap = normalized
        self._build_fuzzy_index()

    def _join_budgeted(self, terms: list[str], max_chars: int) -> str:
        """Join priority-ordered terms with ', ', truncating under ``max_chars``."""
        out: list[str] = []
        length = 0
        for term in terms:
            extra = len(term) + (2 if out else 0)  # ", " between entries
            if length + extra > max_chars:
                break
            out.append(term)
            length += extra
        return ", ".join(out)

    def asr_prompt(self, max_chars: int = 600) -> str:
        """Comma-separated terms for the cloud ``prompt`` / local ``initial_prompt``.

        Truncated by priority to stay under ``max_chars``. Whisper's prompt
        window is ~224 tokens, so we keep a conservative character budget.
        Returns ``""`` when there are no terms.
        """
        return self._join_budgeted(self.all_terms(), max_chars)

    def hotwords(self, max_chars: int = 1000) -> str:
        """Terms for faster-whisper ``hotwords=`` (a looser budget than the prompt)."""
        return self._join_budgeted(self.all_terms(), max_chars)

    def llm_block(self, max_chars: int = 1500) -> str:
        """Markdown bullet list of canonical terms for embedding in an LLM prompt.

        Returns ``""`` when empty. Truncated under ``max_chars`` to keep the
        correction prompt bounded.
        """
        out: list[str] = []
        length = 0
        for term in self.canonical_terms():
            line = f"- {term}"
            if length + len(line) + 1 > max_chars:
                break
            out.append(line)
            length += len(line) + 1
        return "\n".join(out)

    # ---------- layer B safety net: ASR prompt-echo stripping ----------

    @staticmethod
    def _is_word_char(ch: str) -> bool:
        return ch.isalnum() or ch == "_"

    def strip_asr_echo(self, text: str, min_terms: int = 3) -> str:
        """Strip an echo of the ASR bias prompt from the edges of ``text``.

        Whisper conditions on the bias prompt (cloud ``prompt`` / local
        ``hotwords``) as if it were preceding speech, and on low-information
        audio — trailing silence after a long recording, a near-silent
        streaming chunk — the decoder sometimes "continues" by emitting the
        prompt itself, so the raw term list appears verbatim at the start or
        end of the transcript.

        An echo is a run of glossary terms in prompt order (gaps allowed),
        separated only by punctuation/whitespace and anchored at an edge of
        the text. To avoid eating genuine speech the run must span at least
        ``min_terms`` terms (or the whole glossary when it has fewer, but
        never fewer than 2 — a single term at an edge was likely spoken).
        A user genuinely dictating their full term list in prompt order is
        indistinguishable from an echo and will also be stripped.
        """
        terms = [t.casefold() for t in self.all_terms()]
        required = max(2, min(min_terms, len(terms)))
        if not text or len(terms) < 2:
            return text
        cut = self._trailing_echo_start(text, terms, required)
        if cut is not None:
            # Drop a now-dangling list separator, but keep sentence punctuation.
            text = text[:cut].rstrip().rstrip(",;:").rstrip()
        cut = self._leading_echo_end(text, terms, required)
        if cut is not None:
            # The echo's own closing punctuation goes with it.
            text = text[cut:].lstrip(" \t\r\n.,;:!?…")
        return text

    def _trailing_echo_start(
        self, text: str, terms_cf: list[str], required: int
    ) -> Optional[int]:
        """Start index of a qualifying echo run at the end of ``text``, else None."""
        end = len(text)
        matched = 0
        next_idx = len(terms_cf)  # term indices must strictly decrease backwards
        while True:
            e = end
            while e > 0 and not self._is_word_char(text[e - 1]):
                e -= 1
            if e == 0:
                break
            hit = None
            for i in range(next_idx - 1, -1, -1):
                term = terms_cf[i]
                s = e - len(term)
                if s < 0 or text[s:e].casefold() != term:
                    continue
                if s > 0 and self._is_word_char(text[s - 1]):
                    continue
                hit = (i, s)
                break
            if hit is None:
                break
            next_idx, end = hit
            matched += 1
        return end if matched >= required else None

    def _leading_echo_end(
        self, text: str, terms_cf: list[str], required: int
    ) -> Optional[int]:
        """End index of a qualifying echo run at the start of ``text``, else None."""
        start = 0
        matched = 0
        prev_idx = -1  # term indices must strictly increase forwards
        n = len(text)
        while True:
            s = start
            while s < n and not self._is_word_char(text[s]):
                s += 1
            if s >= n:
                break
            hit = None
            for i in range(prev_idx + 1, len(terms_cf)):
                term = terms_cf[i]
                e = s + len(term)
                if e > n or text[s:e].casefold() != term:
                    continue
                if e < n and self._is_word_char(text[e]):
                    continue
                hit = (i, e)
                break
            if hit is None:
                break
            prev_idx, start = hit
            matched += 1
        return start if matched >= required else None

    # ---------- layer C: deterministic replacements (transcribe only) ----------

    @staticmethod
    def _normalize_for_match(s: str) -> str:
        """Casefold + collapse whitespace/hyphens to single spaces.

        Used on both sides of every comparison so "Z-tuning", "z tuning", and
        "Z  Tuning" all line up. Returns "" for an all-separator input.
        """
        return re.sub(r"[\s\-]+", " ", s).strip().casefold()

    def _build_fuzzy_index(self) -> None:
        """(Re)build the normalized 1–3-word fuzzy candidate list, in priority order.

        Word count is taken from the *normalized* form (so "Z-tuning" counts as
        two words and matches the two text tokens "Z" "tuning"). Single tokens
        shorter than ``_MIN_FUZZY_TOKEN_LEN`` or in the stop-word set are dropped
        — they remain reachable through the explicit replacement map.
        """
        out: list[tuple[str, str, int]] = []
        for term in self.all_terms():
            norm = self._normalize_for_match(term)
            if not norm:
                continue
            n = len(norm.split())
            if not (1 <= n <= 3):
                continue
            if n == 1 and (len(norm) < _MIN_FUZZY_TOKEN_LEN or norm in _STOP_WORDS):
                continue
            out.append((norm, term, n))
        self._fuzzy_terms = out

    def _grouped_fuzzy(self, max_terms: int) -> tuple[dict[int, list], bool]:
        """Group the (capped) fuzzy index by word count for length-bucketed search."""
        terms = self._fuzzy_terms
        truncated = max_terms > 0 and len(terms) > max_terms
        if truncated:
            terms = terms[:max_terms]
        grouped: dict[int, list[tuple[str, str]]] = {1: [], 2: [], 3: []}
        for norm, canonical, n in terms:
            grouped[n].append((norm, canonical))
        return grouped, truncated

    @staticmethod
    def _heard_regex(heard: str) -> Optional[re.Pattern]:
        """Word-bounded, case-insensitive, hyphen/space-flexible pattern for `heard`.

        The boundary is asserted only on edges where a word boundary can exist.
        ``\\b`` marks a \\w-to-non-\\w transition, and CJK writes without spaces:
        every neighbour of a Chinese or Japanese character is itself \\w, so the
        assertion can never hold *inside* a sentence. With it, "心电图 => ECG"
        matched only when the term was the entire string and silently did nothing
        in real text. Dropping it per-edge makes the CJK side match as a
        substring, which is the correct reading where no word boundaries exist.

        For Latin/Cyrillic edges nothing changes — the boundary is still required.
        """
        stripped = heard.strip()
        parts = [re.escape(p) for p in re.split(r"[\s\-]+", stripped) if p]
        if not parts:
            return None
        body = r"[\s\-]+".join(parts)
        lead = "" if _CJK_RE.match(stripped[0]) else r"\b"
        trail = "" if _CJK_RE.match(stripped[-1]) else r"\b"
        return re.compile(lead + body + trail, re.IGNORECASE)

    def _apply_explicit_map(self, text: str, changes: Optional[list]) -> str:
        """Apply the user's explicit heard->canonical map. Always runs (no fuzzy rules)."""
        for rep in self._active_split()[1]:
            pattern = self._heard_regex(rep["heard"])
            if pattern is None:
                continue
            canonical = rep["canonical"]

            def _sub(m, canonical=canonical):
                if changes is not None and m.group(0) != canonical:
                    changes.append({"from": m.group(0), "to": canonical, "via": "map"})
                return canonical

            text = pattern.sub(_sub, text)
        return text

    def _apply_fuzzy(
        self,
        text: str,
        grouped: dict[int, list],
        threshold: float,
        time_budget_ms: float,
        changes: Optional[list],
    ) -> str:
        """Slide a 1–3-word window over `text`, snapping near-misses to canonicals."""
        tokens = [(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(text)]
        if not tokens:
            return text
        deadline = time.monotonic() + time_budget_ms / 1000.0
        spans: list[tuple[int, int, str]] = []  # (start, end, canonical), non-overlapping
        i = 0
        ntok = len(tokens)
        while i < ntok:
            if time.monotonic() > deadline:
                logger.warning(
                    "glossary fuzzy replacement hit its time budget; returning a partial result"
                )
                break
            matched = False
            for n in (3, 2, 1):  # prefer the longest phrase match
                bucket = grouped.get(n)
                if not bucket or i + n > ntok:
                    continue
                window = tokens[i : i + n]
                norm = self._normalize_for_match(" ".join(w for w, _, _ in window))
                if n == 1 and (len(norm) < _MIN_FUZZY_TOKEN_LEN or norm in _STOP_WORDS):
                    continue
                best = None
                best_score = float(threshold)  # score_cutoff: never below the threshold
                for cand_norm, canonical in bucket:
                    score = _rf_fuzz.token_sort_ratio(
                        norm, cand_norm, score_cutoff=best_score
                    )
                    if score >= best_score:
                        best, best_score = canonical, score
                if best is not None:
                    start, end = window[0][1], window[-1][2]
                    original = text[start:end]
                    if original != best:
                        spans.append((start, end, best))
                        if changes is not None:
                            changes.append({"from": original, "to": best, "via": "fuzzy"})
                    i += n
                    matched = True
                    break
            if not matched:
                i += 1
        if not spans:
            return text
        out: list[str] = []
        last = 0
        for start, end, canonical in spans:
            out.append(text[last:start])
            out.append(canonical)
            last = end
        out.append(text[last:])
        return "".join(out)

    def _run_replacements(
        self,
        text: str,
        threshold: float,
        max_terms: int,
        time_budget_ms: float,
        track: bool,
    ) -> tuple[str, list]:
        changes: list = [] if track else []
        record = changes if track else None
        if not text:
            return text, changes
        text = self._apply_explicit_map(text, record)
        if _rf_fuzz is None:
            if self._fuzzy_terms and not self._warned_no_rapidfuzz:
                logger.warning(
                    "rapidfuzz not installed; glossary fuzzy replacement disabled "
                    "(the explicit map still applies)"
                )
                self._warned_no_rapidfuzz = True
            return text, changes
        grouped, truncated = self._grouped_fuzzy(max_terms)
        if truncated:
            logger.warning(
                f"glossary fuzzy index exceeds GLOSSARY_FUZZY_MAX_TERMS={max_terms}; "
                f"truncated to the top {max_terms} by priority"
            )
        if any(grouped.values()):
            text = self._apply_fuzzy(text, grouped, threshold, time_budget_ms, record)
        return text, changes

    def apply_replacements(
        self,
        text: str,
        threshold: float = 88,
        max_terms: int = 200,
        time_budget_ms: float = 50.0,
    ) -> str:
        """Layer C: explicit map (always) + fuzzy snap-to-canonical (transcribe only).

        Deterministic and self-contained — it never calls out to a model, so its
        result survives even when the downstream LLM correction is unavailable.
        Returns `text` unchanged when the glossary is empty or rapidfuzz is absent
        (the explicit map still applies in the latter case).
        """
        result, _ = self._run_replacements(
            text, threshold, max_terms, time_budget_ms, track=False
        )
        return result

    def preview(
        self,
        text: str,
        threshold: float = 88,
        max_terms: int = 200,
        time_budget_ms: float = 50.0,
    ) -> tuple[str, list]:
        """Dry-run :meth:`apply_replacements`, also returning the list of changes.

        Each change is ``{"from": ..., "to": ..., "via": "map"|"fuzzy"}``. Used by
        the CLI ``--preview`` and (later) the UI to show what a glossary will do.
        """
        return self._run_replacements(
            text, threshold, max_terms, time_budget_ms, track=True
        )


def inspect_file(path: Path) -> dict:
    """Validate a glossary file *without* modifying it — for the CLI/UI validator.

    Unlike :meth:`Glossary._load` (which silently repairs and quarantines), this
    reports every problem and never touches the file. Returns::

        {"ok": bool, "problems": [str], "counts": {section: int}}

    ``ok`` is False only for *structural* faults the loader can't repair into a
    usable glossary (unparseable JSON, non-object root, a section that isn't a
    list). Element-level issues (a non-string term, a malformed replacement) are
    listed as problems but leave ``ok`` True, mirroring the loader's tolerance.
    A missing file is reported as ``ok`` with zero counts.
    """
    result: dict = {"ok": True, "problems": [], "counts": {}}

    if not path.exists():
        result["problems"].append(
            f"{path} does not exist — an empty glossary will be used"
        )
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        result["ok"] = False
        result["problems"].append(f"cannot read/parse JSON: {e}")
        return result

    if not isinstance(data, dict):
        result["ok"] = False
        result["problems"].append("root is not a JSON object")
        return result

    version = data.get("version", SCHEMA_VERSION)
    if not isinstance(version, int):
        result["problems"].append(f"version is not an integer: {version!r}")
    elif version != SCHEMA_VERSION:
        result["problems"].append(
            f"unknown version {version} (will be read as v{SCHEMA_VERSION})"
        )

    for section in _TERM_SECTIONS:
        value = data.get(section)
        if value is None:
            result["counts"][section] = 0
            continue
        if not isinstance(value, list):
            result["ok"] = False
            result["problems"].append(f"section '{section}' is not a list")
            result["counts"][section] = 0
            continue
        good = 0
        for item in value:
            if isinstance(item, str) and item.strip():
                good += 1
            else:
                result["problems"].append(
                    f"section '{section}': non-string/empty entry {item!r}"
                )
        result["counts"][section] = good

    reps = data.get("replacements")
    if reps is None:
        result["counts"]["replacements"] = 0
    elif not isinstance(reps, list):
        result["ok"] = False
        result["problems"].append("'replacements' is not a list")
        result["counts"]["replacements"] = 0
    else:
        good = 0
        for item in reps:
            if (
                isinstance(item, dict)
                and isinstance(item.get("heard"), str)
                and isinstance(item.get("canonical"), str)
                and item["heard"].strip()
                and item["canonical"].strip()
            ):
                good += 1
            else:
                result["problems"].append(
                    f"replacement invalid (need non-empty heard+canonical): {item!r}"
                )
        result["counts"]["replacements"] = good

    return result


def _main(argv=None) -> int:
    """CLI: validate the glossary file (or dry-run replacements) before the UI exists.

    ``python -m services.glossary [--check] [PATH]`` validates and prints a
    summary; exit code is non-zero on a structural fault.
    ``python -m services.glossary --preview "<text>" [PATH]`` shows what layer C
    would replace in ``<text>``, without writing anything.
    """
    import argparse
    import sys

    # Glossaries are full of Cyrillic; the default Windows console codepage
    # (cp1252) can't encode it and print() would raise. Force UTF-8 output.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):  # pragma: no cover - non-reconfigurable stream
        pass

    parser = argparse.ArgumentParser(
        prog="python -m services.glossary",
        description="Validate the corporate glossary file or preview its replacements.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the glossary file (this is also the default action).",
    )
    parser.add_argument(
        "--preview",
        metavar="TEXT",
        help="Dry-run the deterministic replacements (layer C) on TEXT and print the result.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Glossary file to use (default: %%APPDATA%%/OmniVerte/glossary.json).",
    )
    args = parser.parse_args(argv)

    path = Path(args.path) if args.path else _appdata_dir() / GLOSSARY_FILENAME

    if args.preview is not None:
        glossary = Glossary(path)
        result, changes = glossary.preview(args.preview)
        print(f"Glossary file: {path}")
        print(f"Input:  {args.preview}")
        print(f"Output: {result}")
        if changes:
            print("Replacements:")
            for change in changes:
                print(f"  - {change['from']!r} -> {change['to']!r} (via {change['via']})")
        else:
            print("Replacements: none")
        return 0

    report = inspect_file(path)

    print(f"Glossary file: {path}")
    if report["counts"]:
        summary = ", ".join(f"{k}={v}" for k, v in report["counts"].items())
        print(f"Loaded: {summary}")
    if report["problems"]:
        print("Problems:")
        for problem in report["problems"]:
            print(f"  - {problem}")
    print("OK" if report["ok"] else "INVALID (structural fault)")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    import sys

    sys.exit(_main())

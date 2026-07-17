# file: ui/settings_pages/glossary_packs/__init__.py

"""
Profession term packs: ready-made glossary starting points, bundled with the app.

A pack is *seed data for the editor*, not a live layer. Loading one copies its
terms into the Glossary page's boxes (import-copy), where they become ordinary
user lines: editable, deletable, saved to ``glossary.json`` like anything typed
by hand. Nothing here is consulted by the transcription pipeline — by the time
audio is processed, a loaded pack is indistinguishable from hand-typed terms.
That is the whole point: no merge order, no precedence rules, no pack state to
carry in the hot path.

Consequence to keep in mind: a pack updated in a later release does NOT reach
users who already imported it. Packs are starting points, not subscriptions.

Bundled as Python (not JSON data files) so PyInstaller picks them up with the
normal module graph — no ``datas`` entry in the spec, no ``_MEIPASS`` lookup, no
missing-file failure mode in a frozen build. Mirrors ``custom_style_templates``.
The shape is plain data, so a future remote source would only have to build
``GlossaryPack`` objects from JSON; the page would not change.

Placement of a pack's content:

  * ``terms`` -> the page's "Services & terms" box (glossary ``services``).
    Never the "Names" box: that one holds *the user's own* company, clients and
    products, and generic jargon must not dilute it. The engine's priority order
    (own_names -> counterparties -> services) then falls out correctly on its
    own — when the ASR prompt / term cap truncates, the user's own names survive
    and pack jargon is dropped first.
  * ``replacements`` -> the "Replacements" box, as ``heard => canonical`` pairs.

Locales
-------
Every pack carries its terms in each of ``PACK_LOCALES``, one module per locale
(``_en.py``, ``_ru.py``, ...), and the user picks one when importing (defaulting
to ``PRIMARY_LANGUAGE``). A Russian lawyer needs "исковое заявление", not
"statement of claim"; translating one into the other would be the single worst
thing a glossary could do, since the whole feature exists to make the app write
*the user's* words. The pick is explicit rather than derived silently from the
language setting, because dictation language and professional vocabulary
genuinely diverge — Russian developers work in Russian and write "merge request".

Three language axes meet on this card, and keeping them apart is the whole
subtlety of the feature:

  * A pack's ``name``/``hint`` are **UI chrome** and follow the **UI locale**.
    ``_meta.py`` holds catalog keys; ``glossary_page`` resolves them at build
    time.
  * Its **terms** follow the **pack-language picker** above the buttons — the
    axis this package exists for.
  * Its ``note`` (jurisdiction, for the Legal and Finance packs) is written **in
    the pack's own language**: the German pack's note is German. It is a caveat
    about that pack's content, read by someone who just chose that language, and
    it rides in ``PackContent.note`` shown where the user decides to import.

So a Russian UI can offer «Юриспруденция» while the pack it imports is Spanish
and its note is in Spanish. All three are correct at once.

Locale keys are Whisper language codes, matching ``LANGUAGE_TO_WHISPER_CODE`` in
``services/text_operations.py``. That module is deliberately *not* imported here:
it does ``import openai`` at module scope, and this is a pure string table.
``test_pack_locales_are_app_language_codes`` enforces the link instead — pack
locales must be a subset of the app's languages (a language may ship no pack; a
pack may never claim a language the app does not have).

Replacements
------------
Sparse by design, and their job differs per locale:

  * Bridge borrowed jargon a speaker *pronounces* in their language but *writes*
    in Latin ("мёрж реквест" -> "merge request"). Layer C's fuzzy matcher cannot
    cross scripts, so only an explicit entry gets there.
  * Normalize case and hyphenation the recogniser writes inconsistently
    ("экг" -> "ЭКГ", "форс мажор" -> "форс-мажор", "iva" -> "IVA").

The bundled Chinese and Japanese packs ship **no homophone entries**, though the
homophone is the characteristic CJK error and the map can now fix it. Authoring
such pairs needs a native ear, and a wrong pair corrupts text that was correct —
so those packs' maps carry only Latin abbreviations (CT, K8s), the one category
verifiable from outside the language. A user who knows the homophones their own
dictation hits can add them by hand and they will fire.

What a replacement must never do is rewrite the user's language. Mapping
"анамнез" -> "anamnesis" does not fix a mishearing; it silently translates a
Russian doctor's note. The machine-checkable form of that rule, enforced by
``test_replacements_never_translate_the_user``: **a replacement may only produce
a term the pack already declares in the same locale.** It canonicalizes; it does
not introduce. That also guarantees every canonical is reachable by the ASR-bias
and LLM layers, which read the term lists and nothing else.

Safety notes
------------
Short abbreviations (ECG, ROI, УТП) are safe as terms: ``_MIN_FUZZY_TOKEN_LEN``
in ``services/glossary.py`` keeps sub-4-character tokens out of the fuzzy index
entirely, so they reach the user through ASR bias and the LLM block only and can
never be fuzzily snapped onto an innocent short word. For the same reason, terms
that are also ordinary words ("lead", "cliff", "hedge", "доля") are harmless:
they only ever map to themselves.

``_heard_regex`` matches word-bounded, case-insensitively, and treats spaces and
hyphens interchangeably — so "форс мажор" also catches "форс-мажор", and listing
both spellings is redundant rather than thorough. It does *not* equate ё/е or
doubled consonants, so those variants are listed separately where they matter.

**Chinese and Japanese get two and a half of layer C's three jobs.** ASR bias,
the LLM block and the explicit replacement map all work. The *fuzzy* pass does
not and will not: ``_WORD_RE`` (``\w+``) returns one token for a whole unspaced
clause, so no term ever matches. Making it work would need a per-script
tokenizer, metric, threshold and window — and the metric is the killer, since
``token_sort_ratio`` scores a fully scrambled 图电心 against 心电图 at 100.0
while a real homophone error scores 66.7 against a threshold of 88. The explicit
map handles homophones deterministically, which is the failure mode that
actually occurs. This is a known, accepted gap, not an oversight.
"""

from __future__ import annotations

from . import _de, _en, _es, _fr, _it, _ja, _ru, _zh
from ._meta import PACK_META
from ._types import DEFAULT_PACK_LOCALE, GlossaryPack, PackContent

# Locale modules, in the order the pack card's language picker shows them.
#
# Listed explicitly, never discovered with pkgutil/importlib: PyInstaller's
# module graph only follows static imports, so a scan would work in dev and then
# ship a frozen build whose pack card is empty. The explicit tuple is the price
# of not having that bug, and it doubles as the display order.
_LOCALE_MODULES = (_en, _ru, _es, _fr, _de, _it, _zh, _ja)

PACK_LOCALES: tuple[str, ...] = tuple(m.LOCALE for m in _LOCALE_MODULES)

GLOSSARY_PACKS: list[GlossaryPack] = [
    GlossaryPack(
        meta.pack_id,
        meta.emoji,
        meta.name_key,
        meta.hint_key,
        # Tolerant on purpose: a pack missing from one locale degrades to the
        # English fallback in content() rather than blowing up the settings
        # window at import time. test_every_pack_covers_every_locale is what
        # keeps that from silently happening.
        locales={
            m.LOCALE: m.PACKS[meta.pack_id]
            for m in _LOCALE_MODULES
            if meta.pack_id in m.PACKS
        },
    )
    for meta in PACK_META
]

__all__ = [
    "DEFAULT_PACK_LOCALE",
    "GLOSSARY_PACKS",
    "PACK_LOCALES",
    "GlossaryPack",
    "PackContent",
]

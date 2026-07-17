# file: ui/settings_pages/glossary_packs/_types.py

"""Data shapes for the profession packs. See the package docstring for the rules
the content itself obeys.

These live in their own module rather than in ``__init__``: every locale module
imports ``PackContent``, and a locale module importing from the package that is
in the middle of importing *it* is a cycle that only works by luck of ordering.
``from ._types import PackContent`` never can be.
"""

from __future__ import annotations

from typing import NamedTuple

# The locale every pack is guaranteed to have, and the fallback for an unknown
# key. Lives here (not in __init__) because GlossaryPack.content() needs it.
DEFAULT_PACK_LOCALE = "en"


class PackContent(NamedTuple):
    """One pack's content in one language."""

    terms: list[str]                      # -> "Services & terms" box
    replacements: list[tuple[str, str]]   # -> "Replacements" box, as (heard, canonical)
    # Per-locale caveat surfaced in the button tooltip and the import confirm —
    # chiefly jurisdiction for the Legal pack, whose vocabulary is bound to one
    # country's procedure ("Follows Spain's civil procedure (LEC)."). Named where
    # the user decides, not buried in a docstring they will never read.
    note: str = ""


class GlossaryPack(NamedTuple):
    # `name_key`/`hint_key` are catalog keys, not text: a pack's chrome follows
    # the UI locale, while `locales` below follows the card's pack-language
    # picker. The page resolves them when it builds the button — never here (the
    # `i18n` package docstring's freeze rule).
    pack_id: str                        # stable key, e.g. "legal" (tests, telemetry-free)
    emoji: str                          # button-label prefix, e.g. "⚖️"
    name_key: str                       # catalog key -> display name (no emoji)
    hint_key: str                       # catalog key -> one-line "what this covers", for the tooltip
    locales: dict[str, PackContent]     # locale key -> that language's content

    def content(self, locale: str) -> PackContent:
        """Content for ``locale``, falling back to English for an unknown key so
        a stray PRIMARY_LANGUAGE value can never leave the buttons dead."""
        return self.locales.get(locale) or self.locales[DEFAULT_PACK_LOCALE]

    def term_count(self, locale: str) -> int:
        """Terms this pack contributes, counted the way the cap counts them:
        section terms plus replacements (see ``Glossary.active_term_count``)."""
        content = self.content(locale)
        return len(content.terms) + len(content.replacements)

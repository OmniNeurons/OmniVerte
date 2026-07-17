# file: ui/settings_pages/glossary_packs/_meta.py

"""Pack identity and chrome, in button order.

Separated from the content so adding a locale never touches this file, and so
the five packs' identities are visible in one screen instead of scattered across
eight locale modules.

Chrome is a pair of **catalog keys**, not text: a pack's name and hint are UI
labels, so they follow the UI locale, and ``glossary_page`` resolves them when it
builds the button. The text itself lives in ``i18n/_en.py`` under
``glossary.packs.<pack_id>.{name,hint}``.

This module deliberately does not import ``i18n``. It is a plain string table
that needs no catalog to be read, and the import would put a ``t()`` one careless
edit away from module scope — where it would freeze in the boot locale (see the
``i18n`` package docstring's freeze rule; ``test_i18n_call_sites`` scans this
file).

The jurisdiction caveat, which varies per *pack* language rather than per UI
language, is not chrome and lives in ``PackContent.note``.
"""

from __future__ import annotations

from typing import NamedTuple


class PackMeta(NamedTuple):
    pack_id: str
    emoji: str
    name_key: str
    hint_key: str


# Order here is the order of the buttons on the Glossary settings page.
PACK_META: tuple[PackMeta, ...] = (
    PackMeta(
        "legal", "⚖️",
        "glossary.packs.legal.name", "glossary.packs.legal.hint",
    ),
    PackMeta(
        "medical", "🩺",
        "glossary.packs.medical.name", "glossary.packs.medical.hint",
    ),
    PackMeta(
        "it", "💻",
        "glossary.packs.it.name", "glossary.packs.it.hint",
    ),
    PackMeta(
        "finance", "📊",
        "glossary.packs.finance.name", "glossary.packs.finance.hint",
    ),
    PackMeta(
        "sales", "🤝",
        "glossary.packs.sales.name", "glossary.packs.sales.hint",
    ),
)

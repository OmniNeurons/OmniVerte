# file: i18n/_types.py

"""Shared constants for the UI string catalog.

These live in their own module rather than in ``__init__``: the locale modules
are imported *by* ``__init__``, so a locale module importing from the package
that is in the middle of importing it is a cycle that only works by luck of
ordering. ``from ._types import ...`` never can be.
"""

from __future__ import annotations

# The locale every key is guaranteed to have, and the fallback for an unknown
# locale or a key a translation is missing. English is the source of truth: a
# string exists in `_en.py` first and everything else is a translation of it.
DEFAULT_LOCALE = "en"

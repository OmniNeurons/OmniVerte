# file: i18n/__init__.py

"""
UI string catalog: every user-visible string in the app, in every language it
speaks.

This is a plain-Python lookup, deliberately *not* Qt's ``tr()``/``QTranslator``.
The app renders through two toolkits: PySide6 for the windows, and **pystray**
for the tray menu (``tray_preparing/tray_placing.py``), which is not Qt and
which ``QTranslator`` cannot reach. One dict-backed ``t()`` covers both, needs no
``lupdate``/``lrelease`` step in the build, and is directly unit-testable — see
``tests/test_i18n_catalog.py``, which is the thing that actually keeps the
translations honest.

Bundled as Python (not JSON data files) so PyInstaller picks the catalog up with
the normal module graph — no ``datas`` entry in the spec, no ``_MEIPASS`` lookup,
no missing-file failure mode in a frozen build. Mirrors ``glossary_packs``.

Layout
------
One module per locale (``_en.py``, ``_ru.py``, ...), each exporting ``LOCALE``
and ``STRINGS: dict[str, str]``. Adding a language is one new file plus one
entry in ``_LOCALE_MODULES`` — no code changes anywhere else.

Locale codes are Whisper language codes, matching ``LANGUAGE_TO_WHISPER_CODE``
in ``services/text_operations.py`` and the glossary packs' locale keys, so the
three language axes in this app speak one vocabulary. That module is
deliberately *not* imported here: it does ``import openai`` at module scope, and
this is a pure string table that the tray thread and the tests both import.
``test_ui_locales_are_app_language_codes`` enforces the link instead.

Keys
----
Dotted namespaces mirroring the UI tree (``general.hotkeys.title``,
``tray.mode.keyboard``, ``main.status.ready``), never the English text itself.
English-as-key reads nicely at the call site but collides the moment one English
word needs two translations by context — this app already has two unrelated
"Custom" (a rewrite style and a hotkey) and two "Language" — and it makes
"every locale covers every key" untestable, since a missing translation is
indistinguishable from a deliberate one. Dotted keys also survive an English
copy edit without touching every other locale.

THE ONE RULE
------------
**A ``t()`` call may only run inside a function body.** Never at module or class
scope. A module-level ``TITLE = t("x")`` or a class attribute
``PAGE_TITLE = t("x")`` is evaluated once, at import, under whatever locale
happened to be active then — and no amount of rebuilding the widget ever fixes
it. Module-scope constants hold *keys*; the lookup happens when the widget is
built. ``tests/test_i18n_retranslate.py`` is what catches a violation.
"""

from __future__ import annotations

import logging
import string as _string

from . import _de, _en, _es, _fr, _it, _ja, _ru, _zh
from ._types import DEFAULT_LOCALE

logger = logging.getLogger(__name__)

# Locale modules, in the order a language picker should show them.
#
# Listed explicitly, never discovered with pkgutil/importlib: PyInstaller's
# module graph only follows static imports, so a scan would work in dev and then
# ship a frozen build with an empty catalog — i.e. a UI showing raw dotted keys.
# The explicit tuple is the price of not having that bug, and it doubles as the
# display order.
_LOCALE_MODULES = (_en, _ru, _es, _fr, _de, _it, _zh, _ja)

_CATALOGS: dict[str, dict[str, str]] = {m.LOCALE: m.STRINGS for m in _LOCALE_MODULES}

UI_LOCALES: tuple[str, ...] = tuple(m.LOCALE for m in _LOCALE_MODULES)

# Display name for each locale, in that locale — a language picker must be
# readable by someone who cannot read the language currently active, which is
# exactly the situation they are in when they go looking for it. Native names,
# never translated, so this is data rather than catalog keys.
UI_LOCALE_LABELS: dict[str, str] = {
    "en": "English",
    "ru": "Русский",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "zh": "简体中文",
    "ja": "日本語",
}

_current: str = DEFAULT_LOCALE


def available_locales() -> tuple[str, ...]:
    """Locale codes this build ships, in picker order."""
    return UI_LOCALES


def current_locale() -> str:
    """The locale ``t()`` is currently resolving against."""
    return _current


def catalog(locale: str) -> dict[str, str]:
    """The raw string table for ``locale``, falling back to English.

    For tests and tooling. Callers rendering UI want ``t()`` instead — this
    returns the locale's own table, with no per-key English fallback.
    """
    return _CATALOGS.get(locale) or _CATALOGS[DEFAULT_LOCALE]


def set_locale(locale: str) -> bool:
    """Switch the active locale. Returns True only if the value actually changed.

    Self-deduping by design: callers wire this straight to a config value and
    emit a `language_changed` signal on a True return, so a save that didn't
    touch the language costs nothing and fires nothing.

    An unknown code falls back to English rather than raising — a stray
    UI_LANGUAGE in config.env must never be able to stop the app from starting.
    """
    global _current
    code = (locale or "").strip().lower()
    if code not in _CATALOGS:
        if code:
            logger.warning(f"Unknown UI locale {code!r}, falling back to {DEFAULT_LOCALE!r}")
        code = DEFAULT_LOCALE
    if code == _current:
        return False
    _current = code
    return True


def detect_system_locale() -> str:
    """The app locale best matching the OS UI language, or English.

    Qt is imported lazily so this module stays a pure string table that the
    tests and the pystray thread can import without a QApplication in reach.
    """
    try:
        from PySide6.QtCore import QLocale

        # QLocale.name() is like "ru_RU" — we key off the language half only.
        code = QLocale.system().name().split("_")[0].lower()
    except Exception as e:  # pragma: no cover — defensive; Qt is a hard dep
        logger.debug(f"System locale detection failed: {e}")
        return DEFAULT_LOCALE
    return code if code in _CATALOGS else DEFAULT_LOCALE


def _placeholders(template: str) -> set[str]:
    """Named ``{placeholder}`` fields in a format template.

    Shared with the catalog tests, which assert every translation carries the
    same placeholders as its English source — a template that drops ``{key}``
    silently loses data in the UI, and one that invents a placeholder the caller
    never passes would raise from inside a Qt signal handler.
    """
    return {
        name
        for _, name, _, _ in _string.Formatter().parse(template)
        if name
    }


def t(key: str, /, **fmt) -> str:
    """Look up ``key`` in the active locale and format it with ``fmt``.

    ``key`` is positional-only (the ``/``) so that a placeholder may be *named*
    ``key`` without colliding with this parameter: ``t("general.stylepair.hint",
    key="F11")`` is a real call site, and without the ``/`` it raises
    ``TypeError: got multiple values for argument 'key'``. Translators name
    placeholders after what they mean, not around our signature.

    Never raises — this is called from paint paths, signal handlers and the
    pystray menu thread, where an exception is at best an invisible widget and
    at worst a crash the user reads as "the language switch broke the app".

    Resolution, in order:
      1. the active locale's table
      2. English (a translation that has not caught up degrades to English,
         which is readable, rather than to nothing)
      3. the key itself — which surfaces in the UI as a conspicuous
         ``general.foo.title`` rather than a blank label, and which the catalog
         tests make unshippable

    Formatting uses ``str.format`` with **named** placeholders only. A template
    that references a placeholder the caller didn't pass falls back to the
    English template rather than raising; if that fails too, the unformatted
    template is returned. Positional ``{}`` is not supported: word order changes
    between languages, so a translator must be able to move a value around, and
    only a name lets them.
    """
    template = _CATALOGS.get(_current, {}).get(key)
    if template is None:
        template = _CATALOGS[DEFAULT_LOCALE].get(key)
    if template is None:
        logger.warning(f"Missing UI string for key {key!r}")
        return key
    if not fmt:
        return template
    try:
        return template.format(**fmt)
    except (KeyError, IndexError) as e:
        logger.warning(f"Bad format template for {key!r} in {_current!r}: {e}")
        fallback = _CATALOGS[DEFAULT_LOCALE].get(key, template)
        try:
            return fallback.format(**fmt)
        except (KeyError, IndexError):
            return fallback


__all__ = [
    "DEFAULT_LOCALE",
    "UI_LOCALES",
    "UI_LOCALE_LABELS",
    "available_locales",
    "catalog",
    "current_locale",
    "detect_system_locale",
    "set_locale",
    "t",
]

# file: tests/test_i18n_retranslate.py

"""The anti-rot suite: real widgets, built under a non-English locale, asserting
nothing English survives.

This is the test that makes the whole feature maintainable. A settings page is
translated by wrapping ~40 literals in `t()`, and the failure mode of that is
missing one — which produces a single English label in an otherwise Russian
window, invisible to anyone who reads English, and impossible to find by review
once the catalog is a few hundred keys deep. `test_no_english_leaks_under_ru`
finds it, names the page, and prints the exact string.

It maintains itself. There is no list of "strings that should be translated" to
keep in sync: the candidate set is derived from the catalog (English values
whose Russian differs), so adding a string to both locales automatically extends
the coverage, and deliberately-untranslated strings ("Pro", "F9", "Omni Verte")
drop out on their own because their RU value equals their EN value.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication, QWidget

import i18n
from i18n import DEFAULT_LOCALE, catalog, current_locale, set_locale
from i18n._en import STRINGS as EN
from services.config_store import Config
from services.ui_bridge import UIBridge
from ui.history_manager import HistoryManager
from ui.main_window import MainWindow
from ui.settings_pages import (
    AboutPage,
    CustomStylePage,
    GeneralPage,
    GlossaryPage,
    LanguagesPage,
    LicensePage,
    TranscriptionPage,
)

# Pages whose chrome has been migrated to the catalog. Grows as the mechanical
# `t()` pass covers each page; a page NOT listed here is simply not yet
# translated, which is a known state rather than a failure.
TRANSLATED_PAGES = [
    GeneralPage,
    LanguagesPage,
    TranscriptionPage,
    AboutPage,
    GlossaryPage,
    CustomStylePage,
    LicensePage,
]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _reset_locale():
    """set_locale is process-global; a test that switches and dies would
    otherwise silently retune every test after it."""
    before = current_locale()
    yield
    set_locale(before)


def _english_leak_candidates() -> set[str]:
    """English strings whose Russian translation actually differs.

    Comparing rendered text against the raw English catalog would false-positive
    on every deliberately-untranslated string — "Pro", "CPU", "F9", "Omni Verte".
    Excluding keys where RU == EN (or RU is missing) leaves only strings that
    MUST NOT appear on screen while the locale is Russian. No allowlist to keep
    in sync: the catalog is the source.
    """
    ru = catalog("ru")
    return {
        EN[key]
        for key in EN
        if EN[key] != ru.get(key, EN[key])
    }


def _rendered_strings(widget: QWidget) -> set[str]:
    """Every user-visible string in a widget tree.

    Covers the four sinks the settings UI actually uses. `windowTitle` is read
    off the root too, since a page's own title is not a child's `text()`.
    """
    out: set[str] = set()
    for child in [widget, *widget.findChildren(QWidget)]:
        for getter in ("text", "toolTip", "placeholderText", "windowTitle"):
            fn = getattr(child, getter, None)
            if not callable(fn):
                continue
            try:
                value = fn()
            except Exception:
                continue
            if isinstance(value, str) and value.strip():
                out.add(value)
    return out


@pytest.mark.parametrize(
    "page_cls", TRANSLATED_PAGES, ids=[p.__name__ for p in TRANSLATED_PAGES]
)
def test_no_english_leaks_under_ru(qapp, page_cls):
    """A freshly-built page under RU shows no string we have a Russian for.

    Catches all three ways this feature rots: a literal someone forgot to wrap
    in `t()`, a catalog lookup that got frozen at import (a module constant or
    class attribute), and a page that resolves its text once and caches it.
    """
    set_locale("ru")
    leaks = _english_leak_candidates() & _rendered_strings(page_cls())
    assert not leaks, f"{page_cls.__name__} rendered English under RU: {sorted(leaks)}"


@pytest.mark.parametrize(
    "page_cls", TRANSLATED_PAGES, ids=[p.__name__ for p in TRANSLATED_PAGES]
)
def test_page_title_follows_locale_on_rebuild(qapp, page_cls):
    """The core contract of the rebuild strategy: a page never retranslates
    itself in place, but a FRESH instance must pick up the current locale.

    This is the regression guard for PAGE_TITLE drifting back to a plain class
    attribute. As `PAGE_TITLE = t("...")` it would evaluate at import, freeze in
    whatever locale was active then, and survive every rebuild — the one bug in
    this feature that looks like it works right up until someone switches
    language.
    """
    set_locale(DEFAULT_LOCALE)
    english_title = page_cls().PAGE_TITLE
    set_locale("ru")
    assert page_cls().PAGE_TITLE != english_title


def test_leak_candidates_exclude_deliberately_latin_strings():
    """Guard on the guard: if this ever picked up "Pro" or the app name, the
    leak test would fail on every page for no reason, and the natural fix would
    be to start allowlisting — which is how these tests die."""
    candidates = _english_leak_candidates()
    assert "Omni Verte" not in candidates
    assert "Pro" not in candidates


def test_leak_candidates_are_not_empty():
    """If the derivation ever silently produced an empty set — a refactor of
    catalog(), a locale key rename — every leak test would pass vacuously and we
    would not notice for months."""
    assert len(_english_leak_candidates()) > 5


# ---------- the main window: retranslate in place ----------
#
# The settings pages above are covered by rebuilding them; the main window has
# no such luxury. It is constructed once at startup and lives until the app
# quits, so a language switch has to walk its existing widgets. Everything below
# tests that walk.


def _make_main_window(qapp) -> MainWindow:
    """A real MainWindow, headless. openai_client=None on purpose: it disables
    the text-operation buttons, which is the branch that carries the "OpenAI key
    required" tooltip — one of the strings most likely to be forgotten."""
    return MainWindow(
        ui_bridge=UIBridge(),
        history_manager=HistoryManager(),
        openai_client=None,
        config=Config(),
        icon_path=None,
    )


@pytest.fixture
def main_window(qapp, appdata):
    """`appdata` (conftest) points %APPDATA% at a tmp dir, so Config() writes a
    throwaway config.env rather than the developer's real one."""
    window = _make_main_window(qapp)
    yield window
    window.deleteLater()


def test_main_window_no_english_leaks_under_ru(qapp, appdata):
    """Built under RU — the same contract every settings page is held to."""
    set_locale("ru")
    window = _make_main_window(qapp)
    try:
        leaks = _english_leak_candidates() & _rendered_strings(window)
        assert not leaks, f"MainWindow rendered English under RU: {sorted(leaks)}"
    finally:
        window.deleteLater()


def test_main_window_retranslate_clears_english(main_window):
    """The one that matters: built under EN, switched to RU *in place*.

    A string can pass the build-under-RU test above and still fail here — it
    only needs to have been set with a bare `t()` instead of `_tr()`, so nothing
    remembers to re-render it. That is precisely the bug this window's registry
    exists to prevent, and it is invisible until someone changes language with
    the window already open.
    """
    set_locale("ru")
    main_window.retranslate("ru")
    leaks = _english_leak_candidates() & _rendered_strings(main_window)
    assert not leaks, f"MainWindow kept English after retranslate: {sorted(leaks)}"


def test_main_window_retranslate_repaints_status_from_cached_state(main_window):
    """The regression guard for the cached-state half of `retranslate()`.

    The status label is driven by events, not by the registry — nothing re-emits
    `model_state_changed` when the language changes. If `retranslate()` ever
    stops calling `_repaint_status()`, a window sitting on "Loading model…"
    keeps saying it in English until the next status change, which on a slow
    model load is exactly when the user is looking at it.
    """
    main_window._model_state = "loading"
    main_window._repaint_status()
    assert main_window.status_text.text() == EN["main.status.loading"]

    set_locale("ru")
    main_window.retranslate("ru")
    assert main_window.status_text.text() == catalog("ru")["main.status.loading"]


def test_main_window_retranslate_repaints_result_title_from_cached_state(main_window):
    """Same contract for the Result card's title, which is set from a transcript
    event's `kind` and would otherwise stay in the language of the last
    operation."""
    from ui.history_manager import KIND_FIX

    main_window._result_state = ("done", KIND_FIX, {})
    main_window._repaint_result_title()
    assert main_window.result_card.title_label.text() == EN["history.kind.fix"]

    set_locale("ru")
    main_window.retranslate("ru")
    assert main_window.result_card.title_label.text() == catalog("ru")["history.kind.fix"]


def test_main_window_retranslate_survives_a_deleted_registered_widget(main_window):
    """`_tr` documents "permanent chrome only" — this is what happens when
    someone registers something that isn't.

    A dead C++ object behind a live Python wrapper raises RuntimeError from
    `setText`, and `retranslate` runs inside a Qt signal handler, so the user
    reads the crash as "the language switch broke the app". Drop the entry
    instead, and keep going.
    """
    import shiboken6
    from PySide6.QtWidgets import QLabel

    doomed = main_window._tr(QLabel(parent=main_window), "main.feed.title")
    before = len(main_window._retranslatables)
    shiboken6.delete(doomed)

    main_window.retranslate("ru")  # must not raise

    assert len(main_window._retranslatables) == before - 1


# ---------- tooltip ownership ----------
#
# custom_btn is disabled alongside the other operation buttons, but its tooltip
# is config-driven and owned by `_refresh_settings_labels()` — it names the
# configured style. `_refresh_client_tooltip()` owns the *other* buttons' no-key
# sentence. These pin that boundary: it used to blanket-write every operation
# button, which left three call sites quietly responsible for repairing
# custom_btn afterwards, and one of them (retranslate) got it wrong.


def test_retranslate_keeps_the_config_driven_custom_tooltip(qapp, appdata):
    """A language switch must not repaint the Custom button with the no-key
    sentence that belongs to the OTHER buttons.
    """
    set_locale("en")
    window = _make_main_window(qapp)          # openai_client=None
    try:
        built = window.custom_btn.toolTip()
        assert built == EN["main.tooltip.custom.unset"], "precondition changed"

        # retranslate() renders against the CURRENT locale; its argument is only
        # the signal's payload. Switching the catalog is what OmniVerte._on_saved
        # does before emitting, so do the same here.
        set_locale("ru")
        window.retranslate("ru")
        assert window.custom_btn.toolTip() == catalog("ru")["main.tooltip.custom.unset"]
        # The sibling buttons DO carry the no-key sentence — proving the client
        # pass still ran, i.e. this passes for the right reason.
        assert window.fix_btn.toolTip() == catalog("ru")["main.tooltip.no_key"]
    finally:
        window.deleteLater()


def test_retranslate_does_not_wipe_the_custom_tooltip_with_a_client(qapp, appdata):
    """The nastier half, on the path a paying user is on.

    With a client configured the no-key sentence is "", so a
    `_refresh_client_tooltip()` that reached custom_btn did not merely
    mistranslate its tooltip — it erased it for the rest of the session.
    """
    set_locale("en")
    window = MainWindow(
        ui_bridge=UIBridge(),
        history_manager=HistoryManager(),
        openai_client=object(),               # any non-None stand-in
        config=Config(),
        icon_path=None,
    )
    try:
        assert window.custom_btn.toolTip() == EN["main.tooltip.custom.unset"]
        assert window.fix_btn.toolTip() == ""   # no key needed → no tooltip

        set_locale("ru")
        window.retranslate("ru")
        assert window.custom_btn.toolTip() == catalog("ru")["main.tooltip.custom.unset"]
        assert window.fix_btn.toolTip() == ""
    finally:
        window.deleteLater()


def test_retranslate_round_trip_restores_the_original_strings(qapp, appdata):
    """EN → RU → EN must land exactly where it started.

    A whole-window equality check, so it catches any widget whose text a
    retranslate drops, duplicates or fails to restore — without needing anyone
    to have predicted which widget that would be. (It is how the Custom tooltip
    bug above was found.)
    """
    set_locale("en")
    window = _make_main_window(qapp)
    try:
        before = _rendered_strings(window)
        set_locale("ru")
        window.retranslate("ru")
        assert _rendered_strings(window) != before, "retranslate did nothing"
        set_locale("en")
        window.retranslate("en")
        assert _rendered_strings(window) == before
    finally:
        window.deleteLater()


def test_set_openai_client_keeps_the_custom_tooltip(qapp, appdata):
    """Adding or removing a key must not touch the Custom button's tooltip.

    `set_openai_client` is called from OmniVerte._on_saved whenever settings are
    saved. It used to wipe custom_btn's tooltip to "" and only get away with it
    because the very next thing on that path (`settings_saved` →
    `_refresh_settings_labels`) happened to put it back. Nothing enforced that
    pairing — so this asserts the tooltip survives `set_openai_client` alone.
    """
    set_locale("en")
    window = _make_main_window(qapp)          # openai_client=None
    try:
        expected = EN["main.tooltip.custom.unset"]
        assert window.custom_btn.toolTip() == expected

        window.set_openai_client(object())    # a key was added
        assert window.custom_btn.toolTip() == expected
        assert window.fix_btn.toolTip() == ""
        assert window.custom_btn.isEnabled()  # still enabled/disabled as a group

        window.set_openai_client(None)        # and removed again
        assert window.custom_btn.toolTip() == expected
        assert window.fix_btn.toolTip() == EN["main.tooltip.no_key"]
        assert not window.custom_btn.isEnabled()
    finally:
        window.deleteLater()


def test_no_key_tooltip_covers_every_operation_button_but_custom(qapp, appdata):
    """The subtraction in `_no_key_tooltip_controls` must stay a subtraction.

    If someone re-lists the buttons by hand and forgets a new one, that button
    silently loses its no-key explanation while still being disabled — the user
    gets a dead control with no reason given.
    """
    set_locale("en")
    window = _make_main_window(qapp)
    try:
        covered = set(map(id, window._no_key_tooltip_controls()))
        operations = window._operation_buttons()
        assert id(window.custom_btn) not in covered
        for btn in operations:
            if btn is window.custom_btn:
                continue
            assert id(btn) in covered, "an operation button has no no-key tooltip"
        assert id(window.translate_pill) in covered
    finally:
        window.deleteLater()


# ---------- the Activity Feed ----------


def _feed_kinds(window) -> list[str]:
    from ui.main_window import _FeedItem

    return [
        item.kind_lbl.text() for item in window.feed_container.findChildren(_FeedItem)
    ]


def test_retranslate_relabels_feed_rows_in_place(qapp, appdata):
    """Feed rows must follow the locale without being rebuilt.

    They are the one part of the window that _could_ be regenerated wholesale
    (_refresh_feed exists and does exactly that), which makes it tempting to
    lean on it here — see test_retranslate_keeps_the_feed_scroll_position for
    why that is the wrong tool.
    """
    from ui.history_manager import KIND_FIX

    set_locale("en")
    history = HistoryManager()
    window = MainWindow(
        ui_bridge=UIBridge(), history_manager=history,
        openai_client=None, config=Config(), icon_path=None,
    )
    try:
        history.add("some transcribed text", kind=KIND_FIX)
        assert _feed_kinds(window) == [EN["history.kind.fix"]]

        set_locale("ru")
        window.retranslate("ru")
        assert _feed_kinds(window) == [catalog("ru")["history.kind.fix"]]
    finally:
        window.deleteLater()


def test_feed_row_direction_suffix_is_not_translated(qapp, appdata):
    """The "· EN → RU" suffix is derived from the language pair — config VALUES,
    not chrome — so it must survive a relabel unchanged."""
    from ui.history_manager import KIND_TRANSLATION

    set_locale("en")
    history = HistoryManager()
    window = MainWindow(
        ui_bridge=UIBridge(), history_manager=history,
        openai_client=None, config=Config(), icon_path=None,
    )
    try:
        history.add("текст", kind=KIND_TRANSLATION, meta={"direction": "EN → RU"})
        assert _feed_kinds(window) == [f"{EN['history.kind.translation']} · EN → RU"]

        set_locale("ru")
        window.retranslate("ru")
        expected = f"{catalog('ru')['history.kind.translation']} · EN → RU"
        assert _feed_kinds(window) == [expected]
    finally:
        window.deleteLater()


def test_retranslate_keeps_the_feed_scroll_position(qapp, appdata):
    """A language switch must not scroll the user's feed back to the top.

    Regression guard for retranslate() reaching for _refresh_feed(): that tears
    every row down and rebuilds it, and the deferred deleteLater() collapses the
    scroll container to zero height for one event-loop pass — which clamps the
    scrollbar to 0. Saving and restoring the offset around the rebuild does NOT
    fix it, because the clamp lands after the restore. Relabelling in place does.
    """
    from ui.history_manager import KIND_FIX

    set_locale("en")
    history = HistoryManager()
    window = MainWindow(
        ui_bridge=UIBridge(), history_manager=history,
        openai_client=None, config=Config(), icon_path=None,
    )
    try:
        window.resize(1040, 720)
        window.show()
        for i in range(12):
            history.add(f"entry number {i} with enough text to give the row height",
                        kind=KIND_FIX)
        qapp.processEvents()
        # Force a viewport smaller than the rows so the feed actually scrolls;
        # at its natural size a capped history fits without a scrollbar.
        window.feed_scroll.setFixedHeight(60)
        qapp.processEvents()

        bar = window.feed_scroll.verticalScrollBar()
        assert bar.maximum() > 0, "precondition: the feed must be scrollable"
        bar.setValue(bar.maximum() // 2)
        qapp.processEvents()
        offset = bar.value()
        assert offset > 0

        set_locale("ru")
        window.retranslate("ru")
        qapp.processEvents()
        assert bar.value() == offset
    finally:
        window.hide()
        window.deleteLater()

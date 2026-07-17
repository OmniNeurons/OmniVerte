# file: ui/settings_pages/glossary_page.py

"""
Corporate glossary settings: the on/off flags + fuzzy threshold (stored in
config.env) and the term lists + replacement map (stored in glossary.json).

Layout: the master switch sits in the first card's header; the term editors come
next, split across two tabs ("Names & terms" and "Replacements") so the lower
content stays visible instead of scrolling out of sight; the per-layer switches
+ threshold sit last, in a "Layers" card. The UI merges the old "own names"
and "counterparties" sections into one Names box (written back to ``own_names``,
with ``counterparties`` retired) — the on-disk schema is unchanged.

Unlike the other pages, this one owns its own ``Glossary`` instance: the small
flags round-trip through ``Config`` like everything else, but the long,
structured lists live in ``glossary.json`` and are read/written through the
glossary on ``load_from``/``apply_to``. ``validate()`` rejects a malformed
replacement map before anything is saved.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    ComboBox,
    FlowLayout,
    MessageBox,
    PushButton,
    SegmentedWidget,
    SpinBox,
    SwitchButton,
    TextEdit,
)

from i18n import t
from services.config_store import Config
from services.glossary import Glossary
from services.text_operations import LANGUAGE_TO_WHISPER_CODE
from ui import style
from .base import BasePage, make_form_row, make_pro_tag, make_section_card, make_switch_row
from .glossary_packs import (
    DEFAULT_PACK_LOCALE,
    GLOSSARY_PACKS,
    PACK_LOCALES,
    GlossaryPack,
)

# Pack locale ("ru") -> the name the app calls that language ("Russian"),
# inverted from the app's single language table. The pack picker therefore
# cannot name a language the Languages page doesn't, and cannot disagree with it
# about the name. Labels stay English for the same reason pack names do: the
# whole UI is English, and only the terms are localized.
_CODE_TO_LANGUAGE: dict[str, str] = {
    code: name for name, code in LANGUAGE_TO_WHISPER_CODE.items()
}


def _locale_label(locale: str) -> str:
    return _CODE_TO_LANGUAGE.get(locale, locale)


def _lines_to_list(text: str) -> list[str]:
    """Split a textarea into a clean list: one entry per non-blank, stripped line."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def _list_to_lines(items: list[str]) -> str:
    return "\n".join(items)


def _dedup(items: list[str]) -> list[str]:
    """Drop case-insensitive duplicates, preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _append_lines(edit: TextEdit, lines: list[str]) -> None:
    """Append lines to a term editor, one per line, as a single undoable step.

    Goes through a QTextCursor rather than setPlainText so the editor's undo
    stack survives: one Ctrl+Z takes back a whole pack import. beginEditBlock
    groups the inserts into that single step.
    """
    if not lines:
        return
    cursor = edit.textCursor()
    cursor.beginEditBlock()
    try:
        cursor.movePosition(QTextCursor.End)
        # Start on a fresh line unless the box is empty or already ends on one.
        current = edit.toPlainText()
        if current and not current.endswith("\n"):
            cursor.insertText("\n")
        cursor.insertText("\n".join(lines))
    finally:
        cursor.endEditBlock()


# Separator between the heard form and its canonical form in the replacements box.
_REPL_SEP = "=>"


def parse_replacement_lines(text: str) -> tuple[list[dict[str, str]], list[str]]:
    """Parse ``heard => canonical`` lines into replacement dicts + a list of errors.

    Shared by :meth:`GlossaryPage.validate` and :meth:`GlossaryPage.apply_to` so
    the page never saves a map it just flagged as invalid. Blank lines are
    skipped; a line missing the separator or either side is reported (1-based).
    """
    out: list[dict[str, str]] = []
    errors: list[str] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if _REPL_SEP not in line:
            errors.append(t("glossary.replacements.error.missing_sep", line=i, sep=_REPL_SEP))
            continue
        heard, _, canonical = line.partition(_REPL_SEP)
        heard, canonical = heard.strip(), canonical.strip()
        if not heard or not canonical:
            errors.append(t("glossary.replacements.error.empty_side", line=i, sep=_REPL_SEP))
            continue
        out.append({"heard": heard, "canonical": canonical})
    return out, errors


class _CapHighlighter(QSyntaxHighlighter):
    """Fades the lines of a term editor that fall outside the Free active cap.

    Over-cap terms are saved but never fed to any layer, so we render them in a
    translucent font as a live "won't be used yet" cue. The page owns the cap
    arithmetic and exposes it through ``is_dim(block_number)``; this just paints.

    A QSyntaxHighlighter (not cursor formatting on ``textChanged``) is used on
    purpose: ``QTextEdit.textChanged`` also fires when *formatting* changes, so
    formatting from inside a textChanged handler would recurse. The highlighter
    applies formats without emitting that signal, and clears prior formats each
    pass — so a line that re-enters the active set reverts to the normal colour
    on its own.
    """

    def __init__(self, document, dim_color, is_dim):
        super().__init__(document)
        self._fmt = QTextCharFormat()
        self._fmt.setForeground(dim_color)
        self._is_dim = is_dim

    def highlightBlock(self, text: str) -> None:
        if self._is_dim(self.currentBlock().blockNumber()):
            self.setFormat(0, len(text), self._fmt)


class GlossaryPage(BasePage):
    PAGE_ID = "settings-glossary"
    PAGE_TITLE_KEY = "page.glossary.title"
    PAGE_HINT_KEY = "page.glossary.hint"

    def __init__(self, parent=None):
        # Own glossary instance — the lists/replacements live in glossary.json,
        # not config.env. Built before BasePage.__init__ calls build().
        self._glossary = Glossary()
        super().__init__(parent)

    def build(self, content_layout: QVBoxLayout) -> None:
        # --- Master switch: lives in the section header, so the header itself
        # is the toggle (no separate "Enable glossary" row beneath a label). ---
        self.enable_switch = self._switch()
        card, _ = make_section_card(
            t("glossary.enable.title"),
            t("glossary.enable.hint"),
            header_widget=self.enable_switch,
        )
        content_layout.addWidget(card)

        # --- Free-tier term cap + profession packs (Pro gate) ---
        # 'Pro' tag-link in the header → waitlist; hidden once Pro unlocks packs.
        self.pack_pro_tag = make_pro_tag()
        pack_card, pack_body = make_section_card(
            t("glossary.packs.title"),
            t("glossary.packs.hint"),
            header_widget=self.pack_pro_tag,
        )
        self.pack_status_label = QLabel("")
        self.pack_status_label.setObjectName("cardSectionHint")
        self.pack_status_label.setWordWrap(True)
        pack_body.addWidget(self.pack_status_label)

        # Term language. Defaults to PREFERRED_LANGUAGE (see load_from) but stays
        # a separate, explicit choice: dictation language and professional
        # vocabulary diverge — Russian developers dictate in Russian and write
        # "merge request", while a Russian lawyer needs "исковое заявление".
        self.pack_locale_combo = ComboBox()
        self.pack_locale_combo.setFixedWidth(160)
        for loc in PACK_LOCALES:
            self.pack_locale_combo.addItem(_locale_label(loc), userData=loc)
        self.pack_locale_combo.currentIndexChanged.connect(
            lambda *_: self._refresh_pack_status()
        )
        pack_body.addWidget(make_form_row(
            t("glossary.packs.language"),
            self.pack_locale_combo,
            hint=t("glossary.packs.language.hint"),
            align_right=True,
        ))

        # One button per pack (mirrors the Custom style page's template row).
        # Enabled/disabled by _refresh_pack_status on the Pro gate.
        btn_container = QWidget()
        flow = FlowLayout(btn_container, needAni=False)
        flow.setContentsMargins(0, 0, 0, 0)
        flow.setHorizontalSpacing(8)
        flow.setVerticalSpacing(8)
        self.pack_buttons: list[PushButton] = []
        for pack in GLOSSARY_PACKS:
            # A pack's name is chrome and follows the UI locale; its terms follow
            # the picker above. Resolved here, not in _meta.py — freeze rule.
            btn = PushButton(f"{pack.emoji} {t(pack.name_key)}")
            btn.clicked.connect(lambda _=False, p=pack: self._apply_pack(p))
            flow.addWidget(btn)
            self.pack_buttons.append(btn)
        pack_body.addWidget(btn_container)
        content_layout.addWidget(pack_card)

        # --- Per-layer switches + threshold ---
        card, body = make_section_card(
            t("glossary.layers.title"),
            t("glossary.layers.hint"),
        )

        self.asr_switch = self._switch()
        self.correction_switch = self._switch()
        self.rewrite_switch = self._switch()
        self.fuzzy_switch = self._switch()

        self._sub_rows = [
            make_switch_row(
                t("glossary.layers.asr"),
                self.asr_switch,
                hint=t("glossary.layers.asr.hint"),
            ),
            make_switch_row(
                t("glossary.layers.correction"),
                self.correction_switch,
                hint=t("glossary.layers.correction.hint"),
            ),
            make_switch_row(
                t("glossary.layers.rewrite"),
                self.rewrite_switch,
                hint=t("glossary.layers.rewrite.hint"),
            ),
            make_switch_row(
                t("glossary.layers.fuzzy"),
                self.fuzzy_switch,
                hint=t("glossary.layers.fuzzy.hint"),
            ),
        ]
        for row in self._sub_rows:
            body.addWidget(row)

        self.threshold_spin = SpinBox()
        self.threshold_spin.setRange(70, 100)
        self.threshold_spin.setFixedWidth(120)
        body.addWidget(make_form_row(
            t("glossary.layers.threshold"),
            self.threshold_spin,
            hint=t("glossary.layers.threshold.hint"),
            align_right=True,
        ))

        self.enable_switch.checkedChanged.connect(self._on_enable_toggle)

        # --- Tabbed editors: term lists | replacements ---
        content_layout.addWidget(self._build_tabs())

        content_layout.addWidget(card)

    def _build_tabs(self):
        """Segmented 'Names & terms' / 'Replacements' editor, inside a section card.

        Tabs keep both editing surfaces visible up front instead of stacking them
        down a long scroll where the lower ones go unnoticed.
        """
        card, body = make_section_card(
            t("glossary.terms.title"),
            t("glossary.terms.hint"),
        )

        # Live cap counter — updates as you type so the Free 5-term limit (and
        # how much of it is left) is always visible, never a surprise on save.
        self.term_counter_label = QLabel("")
        self.term_counter_label.setObjectName("termCounter")
        self.term_counter_label.setWordWrap(True)
        body.addWidget(self.term_counter_label)

        self.pivot = SegmentedWidget()
        self.stack = QStackedWidget()

        names_tab = self._build_names_tab()
        repl_tab = self._build_replacements_tab()
        self._add_tab(names_tab, "names", t("glossary.terms.tab.names"))
        self._add_tab(repl_tab, "replacements", t("glossary.terms.tab.replacements"))

        # Recount live on every edit across all three term editors.
        self.names_edit.textChanged.connect(self._update_term_counter)
        self.services_edit.textChanged.connect(self._update_term_counter)
        self.repl_edit.textChanged.connect(self._update_term_counter)

        # Per-box dim flags (indexed by raw line/block number) + a highlighter on
        # each editor that fades the over-cap lines. _recompute_dim_flags() fills
        # the flags and rehighlights; it runs from _update_term_counter so the
        # fading tracks typing live and stays in lock-step with the counter.
        self._dim_flags: dict[str, list[bool]] = {"names": [], "services": [], "replacements": []}
        # rehighlight() re-applies char formats, which QTextEdit reports as a
        # content change → textChanged → back into here. This guard breaks that
        # loop so a recompute never re-triggers itself.
        self._refreshing_dim = False
        dim_color = QColor(style.palette().TEXT_MUTED)
        dim_color.setAlpha(110)
        self._highlighters = {
            "names": _CapHighlighter(
                self.names_edit.document(), dim_color, lambda n: self._is_dim("names", n)
            ),
            "services": _CapHighlighter(
                self.services_edit.document(), dim_color, lambda n: self._is_dim("services", n)
            ),
            "replacements": _CapHighlighter(
                self.repl_edit.document(), dim_color, lambda n: self._is_dim("replacements", n)
            ),
        }

        # Keep the pivot highlight in sync however the page is switched.
        self.stack.currentChanged.connect(
            lambda *_: self.pivot.setCurrentItem(self.stack.currentWidget().objectName())
        )
        self.pivot.setCurrentItem("names")
        self.stack.setCurrentWidget(names_tab)

        body.addWidget(self.pivot)
        body.addWidget(self.stack)
        return card

    def _add_tab(self, widget: QWidget, key: str, text: str) -> None:
        widget.setObjectName(key)
        self.stack.addWidget(widget)
        self.pivot.addItem(
            routeKey=key,
            text=text,
            onClick=lambda: self.stack.setCurrentWidget(widget),
        )

    def _build_names_tab(self) -> QWidget:
        """Two columns side by side: merged names | services & terms."""
        self.names_edit = self._term_box(t("glossary.terms.names.placeholder"))
        self.services_edit = self._term_box(t("glossary.terms.services.placeholder"))
        tab = QWidget()
        row = QHBoxLayout(tab)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)
        row.addLayout(self._titled_column(
            t("glossary.terms.names"),
            t("glossary.terms.names.hint"),
            self.names_edit,
        ))
        row.addLayout(self._titled_column(
            t("glossary.terms.services"),
            t("glossary.terms.services.hint"),
            self.services_edit,
        ))
        return tab

    def _build_replacements_tab(self) -> QWidget:
        self.repl_edit = TextEdit()
        self.repl_edit.setPlaceholderText(
            t("glossary.terms.replacements.placeholder", sep=_REPL_SEP)
        )
        self.repl_edit.setMinimumHeight(160)
        # Paste as plain text (same reasoning as _term_box).
        self.repl_edit.setAcceptRichText(False)
        tab = QWidget()
        col = QVBoxLayout(tab)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)
        hint = QLabel(t("glossary.terms.replacements.hint", sep=_REPL_SEP))
        hint.setObjectName("cardSectionHint")
        hint.setWordWrap(True)
        col.addWidget(hint)
        col.addWidget(self.repl_edit)
        return tab

    # ---------- small builders ----------

    @staticmethod
    def _switch() -> SwitchButton:
        sw = SwitchButton()
        sw.setOnText(t("common.on"))
        sw.setOffText(t("common.off"))
        return sw

    @staticmethod
    def _term_box(placeholder: str) -> TextEdit:
        edit = TextEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(110)
        # Paste as plain text — drop any font/size/bold/colour carried in from
        # the clipboard so terms always land in the editor's normal font.
        edit.setAcceptRichText(False)
        return edit

    @staticmethod
    def _titled_column(title: str, hint: str, edit: TextEdit) -> QVBoxLayout:
        """A heading + hint + text box, for one column of the 'Names & terms' tab."""
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("rowLabel")
        col.addWidget(title_lbl)
        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("rowHint")
        hint_lbl.setWordWrap(True)
        col.addWidget(hint_lbl)
        col.addWidget(edit)
        return col

    # ---------- behaviour ----------

    def _on_enable_toggle(self, *_):
        """Grey out the sub-switches and threshold when the master switch is off."""
        on = self.enable_switch.isChecked()
        for row in self._sub_rows:
            row.setEnabled(on)
        self.threshold_spin.setEnabled(on)

    # ---------- profession packs ----------

    def _pack_locale(self) -> str:
        """The term language currently picked in the pack card."""
        return self.pack_locale_combo.currentData() or DEFAULT_PACK_LOCALE

    def _apply_pack(self, pack: GlossaryPack) -> None:
        """Copy a pack's terms into the editors (import-copy).

        Additive, never destructive: pack terms are *appended* to what is already
        there, because a profession pack complements the user's own names rather
        than replacing them. Entries already present (case-insensitively — by
        term, and by the *heard* side for replacements) are skipped, so loading
        the same pack twice is a no-op rather than a pile of duplicates.

        Terms land in the "Services & terms" box, never "Names": that box is for
        the user's own company/clients, and it also outranks services in the
        engine's priority order — generic jargon must not push the user's own
        names out of the ASR prompt or the term cap.

        Nothing is saved here. The lines are plain editor text until the user
        hits Save, and the insert goes through a cursor (not setPlainText) so
        Ctrl+Z undoes the whole import in one step.
        """
        locale = self._pack_locale()
        content = pack.content(locale)

        # `term` (not `t`) as the loop name — `t` is the catalog lookup in this
        # module now, and shadowing it inside a comprehension is a trap waiting
        # for the first person to add a t() call in one.
        existing_terms = {
            term.casefold() for term in _lines_to_list(self.services_edit.toPlainText())
        }
        new_terms = [
            term for term in _dedup(content.terms) if term.casefold() not in existing_terms
        ]

        current_reps, _ = parse_replacement_lines(self.repl_edit.toPlainText())
        existing_heard = {r["heard"].casefold() for r in current_reps}
        new_reps: list[tuple[str, str]] = []
        for heard, canonical in content.replacements:
            key = heard.casefold()
            if key in existing_heard:
                continue
            existing_heard.add(key)  # also de-dupes within the pack itself
            new_reps.append((heard, canonical))

        locale_label = _locale_label(locale)
        if not new_terms and not new_reps:
            box = MessageBox(
                t("glossary.packs.already_loaded.title", pack=t(pack.name_key)),
                t("glossary.packs.already_loaded.text", language=locale_label),
                self.window(),
            )
            box.cancelButton.hide()
            box.exec()
            return

        parts = []
        if new_terms:
            parts.append(t("glossary.packs.count.terms", count=len(new_terms)))
        if new_reps:
            parts.append(t("glossary.packs.count.replacements", count=len(new_reps)))
        skipped = pack.term_count(locale) - len(new_terms) - len(new_reps)
        detail = (
            t(
                "glossary.packs.confirm.adds",
                what=t("glossary.packs.count.join").join(parts),
                language=locale_label,
            )
            + (" " + t("glossary.packs.confirm.skipped", count=skipped) if skipped else "")
            # The jurisdiction caveat belongs here, at the moment of the choice —
            # a Mexican lawyer should learn the Spanish legal pack follows Spain
            # before importing it, not by noticing the terms are wrong later.
            + (f"\n\n{content.note}" if content.note else "")
            + "\n\n" + t("glossary.packs.confirm.editable")
        )
        title = t("glossary.packs.confirm.title", pack=t(pack.name_key))
        if not MessageBox(title, detail, self.window()).exec():
            return

        _append_lines(self.services_edit, new_terms)
        _append_lines(
            self.repl_edit, [f"{h} {_REPL_SEP} {c}" for h, c in new_reps]
        )
        # textChanged → _update_term_counter fires on its own, refreshing the
        # counter and the over-cap fading. Only the pack card's own line needs a
        # nudge, since it reads the saved glossary rather than the editors.
        self._refresh_pack_status()

    # ---------- Config / Glossary interface ----------

    def load_from(self, config: Config) -> None:
        def flag(key: str, default: str = "true") -> bool:
            return (config.get(key) or default).strip().lower() == "true"

        self.enable_switch.setChecked(flag("GLOSSARY_ENABLED", "false"))
        self.asr_switch.setChecked(flag("GLOSSARY_ASR_BIAS"))
        self.correction_switch.setChecked(flag("GLOSSARY_LLM_CORRECTION"))
        self.rewrite_switch.setChecked(flag("GLOSSARY_LLM_REWRITE"))
        self.fuzzy_switch.setChecked(flag("GLOSSARY_FUZZY_REPLACE"))

        try:
            self.threshold_spin.setValue(int(config.get("GLOSSARY_FUZZY_THRESHOLD") or 88))
        except (TypeError, ValueError):
            self.threshold_spin.setValue(88)

        # Pack language: seed from the dictation language, then leave it alone —
        # it is a per-import choice, not a setting, so it is never saved back.
        #
        # PRIMARY_LANGUAGE holds a *display name* ("Russian"), not a code, so it
        # goes through LANGUAGE_TO_WHISPER_CODE. This used to read the legacy
        # PREFERRED_LANGUAGE ("ru") raw — a key Config.pop()s during migration
        # (config_store._migrate_preferred_language), so the lookup always missed
        # and silently pinned every user to English. It was invisible because the
        # bug and the correct answer agree for an English user.
        primary = (config.get("PRIMARY_LANGUAGE") or "").strip()
        code = LANGUAGE_TO_WHISPER_CODE.get(primary)
        locale = code if code in PACK_LOCALES else DEFAULT_PACK_LOCALE
        self.pack_locale_combo.setCurrentIndex(PACK_LOCALES.index(locale))

        # Lists/replacements come from glossary.json. Reload first so the page
        # reflects any external edits since this instance was constructed.
        self._glossary.reload()
        # "Own names" and "counterparties" are both just names — present them as
        # one merged list. Legacy files may still have both sections populated;
        # fold them together (case-insensitively de-duped) for display.
        self.names_edit.setPlainText(_list_to_lines(
            _dedup(self._glossary.own_names + self._glossary.counterparties)
        ))
        self.services_edit.setPlainText(_list_to_lines(self._glossary.services))
        self.repl_edit.setPlainText(
            "\n".join(
                f"{r['heard']} {_REPL_SEP} {r['canonical']}"
                for r in self._glossary.replacements
            )
        )
        self._refresh_pack_status()
        self._update_term_counter()
        self._on_enable_toggle()

    def _is_dim(self, box: str, block_number: int) -> bool:
        """Whether line ``block_number`` of ``box`` is over the active cap.

        Read by each editor's ``_CapHighlighter``; falls back to False (no fade)
        for any block not yet covered by the last :meth:`_recompute_dim_flags`.
        """
        flags = self._dim_flags.get(box, ())
        return flags[block_number] if 0 <= block_number < len(flags) else False

    def _recompute_dim_flags(self) -> None:
        """Recompute which editor lines fall outside the Free active cap, then
        rehighlight. Mirrors the engine's priority order exactly: distinct
        ``names`` then ``services`` terms fill the first ``cap`` slots, remaining
        slots go to valid replacement lines in order. Lines split raw (keeping
        blanks) so indices line up with the editors' block numbers."""
        if self._refreshing_dim:  # re-entered via rehighlight()'s textChanged
            return
        from licensing import get_entitlement

        cap = get_entitlement().limit("glossary_terms")

        names_raw = self.names_edit.toPlainText().split("\n")
        services_raw = self.services_edit.toPlainText().split("\n")
        repl_raw = self.repl_edit.toPlainText().split("\n")

        # cap < 0 == unlimited (reserved tiers): nothing is ever dimmed.
        if cap < 0:
            self._dim_flags = {
                "names": [False] * len(names_raw),
                "services": [False] * len(services_raw),
                "replacements": [False] * len(repl_raw),
            }
            self._rehighlight_all()
            return

        seen: dict[str, int] = {}  # casefold -> slot index of first occurrence
        slot = 0

        def term_flags(raw_lines: list[str]) -> list[bool]:
            """Dim flag per raw line for a section box (names/services)."""
            nonlocal slot
            out: list[bool] = []
            for line in raw_lines:
                term = line.strip()
                if not term:  # blank line: consumes no slot, never dimmed
                    out.append(False)
                    continue
                key = term.casefold()
                if key in seen:
                    out.append(seen[key] >= cap)  # duplicate inherits first occurrence
                else:
                    seen[key] = slot
                    out.append(slot >= cap)
                    slot += 1
            return out

        names_flags = term_flags(names_raw)
        services_flags = term_flags(services_raw)

        # Replacements fill whatever slots the section terms left free.
        remaining = max(0, cap - min(slot, cap))
        repl_flags: list[bool] = []
        repl_slot = 0
        for line in repl_raw:
            text = line.strip()
            if not text or _REPL_SEP not in text:
                repl_flags.append(False)  # blank / unparseable: not an active term
                continue
            heard, _, canonical = text.partition(_REPL_SEP)
            if not heard.strip() or not canonical.strip():
                repl_flags.append(False)
                continue
            repl_flags.append(repl_slot >= remaining)
            repl_slot += 1

        self._dim_flags = {
            "names": names_flags,
            "services": services_flags,
            "replacements": repl_flags,
        }
        self._rehighlight_all()

    def _rehighlight_all(self) -> None:
        """Re-run the highlighters, guarding against the textChanged re-entry that
        rehighlight() itself triggers (see ``_refreshing_dim``)."""
        self._refreshing_dim = True
        try:
            for hl in self._highlighters.values():
                hl.rehighlight()
        finally:
            self._refreshing_dim = False

    def _count_typed_terms(self) -> int:
        """Distinct terms currently in the editors (names+services deduped, plus
        valid replacement lines) — mirrors Glossary.active_term_count on the
        unsaved text so the counter tracks typing live."""
        names = _dedup(
            _lines_to_list(self.names_edit.toPlainText())
            + _lines_to_list(self.services_edit.toPlainText())
        )
        reps, _ = parse_replacement_lines(self.repl_edit.toPlainText())
        return len(names) + len(reps)

    def _update_term_counter(self) -> None:
        """Refresh the live 'used / cap' line and tint it when the cap is hit."""
        from licensing import TIER_LIMITS, Tier, get_entitlement

        cap = get_entitlement().limit("glossary_terms")
        total = self._count_typed_terms()
        pro_cap = TIER_LIMITS[Tier.PRO].get("glossary_terms", 200)

        at_or_over = cap >= 0 and total >= cap
        if cap < 0:  # unlimited (reserved tiers)
            text = t("glossary.terms.counter.unlimited", total=total)
        elif total <= cap:
            remaining = cap - total
            text = t(
                "glossary.terms.counter.used", total=total, cap=cap, remaining=remaining
            )
        elif cap < pro_cap:  # Free, over the cap → upsell, no data loss
            text = t(
                "glossary.terms.counter.over_free", cap=cap, total=total, pro_cap=pro_cap
            )
        else:  # Pro/Enterprise over the quality ceiling
            text = t("glossary.terms.counter.over_ceiling", cap=cap, total=total)
        self.term_counter_label.setText(text)
        self.term_counter_label.setProperty("warn", at_or_over)
        self.term_counter_label.style().unpolish(self.term_counter_label)
        self.term_counter_label.style().polish(self.term_counter_label)

        # Fade the lines that fall outside the active cap (shares one recompute
        # path with the counter so the two never disagree).
        self._recompute_dim_flags()

    def _refresh_pack_status(self) -> None:
        """Enable the pack buttons on the Pro gate (Feature.GLOSSARY) and say why.

        On Free the buttons are disabled: the active cap (5 terms) is smaller
        than any pack, so an import would land a list that is mostly inactive —
        gating the button and naming the reason beats letting the user load 60
        terms and discover 5 of them work. The term arithmetic itself belongs to
        the Terms card's live counter; this line only speaks about packs.
        """
        from licensing import Feature, get_entitlement

        ent = get_entitlement()
        unlocked = ent.has(Feature.GLOSSARY)
        self.pack_pro_tag.setVisible(not unlocked)
        self.pack_locale_combo.setEnabled(unlocked)
        for btn in self.pack_buttons:
            btn.setEnabled(unlocked)

        if unlocked:
            locale = self._pack_locale()
            self.pack_status_label.setText(
                t("glossary.packs.status.available", count=len(GLOSSARY_PACKS))
            )
            for pack, btn in zip(GLOSSARY_PACKS, self.pack_buttons):
                content = pack.content(locale)
                # The hint is chrome (UI locale); `content.note` is pack data and
                # stays in the pack's own language — a German pack's caveat is
                # German, read by someone who just picked German.
                tip = t(pack.hint_key) + " " + t(
                    "glossary.packs.tooltip.adds", count=pack.term_count(locale)
                )
                if content.note:
                    tip += f"\n{content.note}"
                btn.setToolTip(tip)
        else:
            cap = ent.limit("glossary_terms")
            self.pack_status_label.setText(t("glossary.packs.status.locked", cap=cap))
            for btn in self.pack_buttons:
                btn.setToolTip(t("glossary.packs.tooltip.locked"))

    def apply_to(self, config: Config) -> None:
        def store(key: str, switch: SwitchButton) -> None:
            config.set(key, "true" if switch.isChecked() else "false")

        store("GLOSSARY_ENABLED", self.enable_switch)
        store("GLOSSARY_ASR_BIAS", self.asr_switch)
        store("GLOSSARY_LLM_CORRECTION", self.correction_switch)
        store("GLOSSARY_LLM_REWRITE", self.rewrite_switch)
        store("GLOSSARY_FUZZY_REPLACE", self.fuzzy_switch)
        config.set("GLOSSARY_FUZZY_THRESHOLD", str(self.threshold_spin.value()))

        # validate() has already run (settings window aborts the save on the
        # first failure), so parsing here is safe; ignore the error list.
        replacements, _ = parse_replacement_lines(self.repl_edit.toPlainText())
        # The merged names box writes to own_names; counterparties is retired in
        # the UI, so clear it (a saved file thus migrates the old split into one).
        self._glossary.own_names = _lines_to_list(self.names_edit.toPlainText())
        self._glossary.counterparties = []
        self._glossary.services = _lines_to_list(self.services_edit.toPlainText())
        self._glossary.replacements = replacements
        self._glossary.save()

    def validate(self) -> Optional[str]:
        _, errors = parse_replacement_lines(self.repl_edit.toPlainText())
        if errors:
            shown = "; ".join(errors[:3])
            more = (
                ""
                if len(errors) <= 3
                else " " + t("glossary.replacements.error.more", count=len(errors) - 3)
            )
            return t("glossary.replacements.error.prefix", details=f"{shown}{more}")
        return None

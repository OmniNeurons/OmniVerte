# file: ui/settings_pages/transcription_page.py

"""
Transcription backend configuration: priority order, API keys (stored in the
Windows Credential Manager via keyring), per-backend model picks, and the
device the local backend runs on.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    ComboBox,
    PasswordLineEdit,
    PushButton,
    SwitchButton,
)

from i18n import t
from services.audio_prep import (
    encode_device_name,
    list_input_devices,
    normalize_enhance_profile,
)
from services.transcription_models import (
    GEMINI_TRANSCRIPTION_MODELS,
    GROQ_TRANSCRIPTION_MODELS,
    LOCAL_WHISPER_MODELS,
    OPENAI_TRANSCRIPTION_MODELS,
)
from services.config_store import Config
from .base import (
    LABEL_COL_WIDTH,
    BasePage,
    make_form_row,
    make_help_button,
    make_link_label,
    make_section_card,
    pulse_field_glow,
)


# Single canonical order for every card on this page — Backend priority, API
# keys, Model per backend. The eye reads "OpenAI → Groq → Gemini → Local" once
# and that mental map stays valid across the whole page. (The keys card has no
# Local row and ends with ElevenLabs, which is live-only and not a backend.)
BACKEND_ORDER = ("openai", "groq", "gemini", "local")

# Display name + one-line pitch per backend, as catalog KEYS rather than text.
# A `t()` at module scope resolves once, at import, and would pin every backend
# label to whatever locale happened to be active then — rebuilding the page
# never undoes it. `_backend_info()` does the lookup at build time instead.
# The dict's *keys* are backend ids: those are data (they hit config.env and
# `MODEL_<ID>`) and stay untranslated.
BACKEND_INFO_KEYS = {
    "openai": ("transcription.backend.name.openai", "transcription.backend.hint.openai"),
    "groq":   ("transcription.backend.name.groq",   "transcription.backend.hint.groq"),
    "gemini": ("transcription.backend.name.gemini", "transcription.backend.hint.gemini"),
    "local":  ("transcription.backend.name.local",  "transcription.backend.hint.local"),
}

BACKEND_MODELS = {
    "openai": OPENAI_TRANSCRIPTION_MODELS,
    "groq":   GROQ_TRANSCRIPTION_MODELS,
    "gemini": GEMINI_TRANSCRIPTION_MODELS,
    "local":  LOCAL_WHISPER_MODELS,
}

# Label KEY → stored value. The right-hand value is canonical and never
# translated: it is what lands in config.env and what AudioWriter compares
# against. Only the label is looked up, and `apply_to` reads the value by combo
# INDEX, so a translated label can never reach disk.
#
# Catalog keys rather than text because a module-level `t()` would resolve at
# import — freezing the labels in whatever locale happened to be active then, in
# a way no rebuild ever fixes. The lookup happens at build time.
DEVICE_CHOICES = [
    ("transcription.device.cpu", "cpu"),
    ("transcription.device.cuda", "cuda"),
]

# Matches the model combos above, so both cards' controls share a right edge.
COMBO_FIELD_WIDTH = 240
# Mic names from PortAudio can be long ("Microphone (Realtek...) (Windows WASAPI)").
MIC_COMBO_WIDTH = 320

# Enhance profile: label key → config value. Lookup at build time (not module
# scope) so locale switches rebuild correctly. Strong is intentionally absent
# until a real strong profile ships.
ENHANCE_CHOICES = [
    ("transcription.enhance.off", "off"),
    ("transcription.enhance.light", "light"),
]

# Where new users go to create a key for each cloud backend. Surfaced both as a
# "?" help bubble next to the field and a small always-visible "Get a key" link.
OPENAI_KEYS_URL = "https://platform.openai.com/api-keys"
GROQ_KEYS_URL = "https://console.groq.com/keys"
GEMINI_KEYS_URL = "https://aistudio.google.com/apikey"
ELEVENLABS_KEYS_URL = "https://elevenlabs.io/app/settings/api-keys"

logger = logging.getLogger(__name__)

# "Check" button results → (catalog key, tone). The states are
# services.key_check.RESULTS plus two the page produces itself ("checking",
# "empty"). Catalog KEYS, not text — same module-scope `t()` trap as above.
# Tone picks the colour (ui/style.py, QLabel#keyCheckStatus[tone=…]): "bad" is
# for answers the user must act on, "warn" for "could not tell / try later".
KEY_CHECK_STATES = {
    "checking":     ("transcription.keys.check.checking", "muted"),
    "empty":        ("transcription.keys.check.result.empty", "warn"),
    "ok":           ("transcription.keys.check.result.ok", "ok"),
    "ok_nobalance": ("transcription.keys.check.result.ok_nobalance", "warn"),
    "quota":        ("transcription.keys.check.result.quota", "bad"),
    "auth":         ("transcription.keys.check.result.auth", "bad"),
    "rate":         ("transcription.keys.check.result.rate", "warn"),
    "network":      ("transcription.keys.check.result.network", "warn"),
    "busy":         ("transcription.keys.check.result.busy", "warn"),
    "unknown":      ("transcription.keys.check.result.unknown", "warn"),
}


def _backend_info(backend_id: str) -> tuple[str, str]:
    """(display name, one-line pitch) for a backend, in the active locale."""
    name_key, hint_key = BACKEND_INFO_KEYS[backend_id]
    return t(name_key), t(hint_key)


def _openai_help_steps() -> list[str]:
    """Steps for the OpenAI key help bubble, resolved when the bubble is built.

    A module-level list of `t()` calls would freeze at import — same trap as
    BACKEND_INFO_KEYS above. See the `i18n` package docstring."""
    return [
        t("transcription.keys.openai.help.step1"),
        t("transcription.keys.openai.help.step2"),
        t("transcription.keys.openai.help.step3"),
        t("transcription.keys.openai.help.note"),
    ]


def _groq_help_steps() -> list[str]:
    """Steps for the Groq key help bubble. See `_openai_help_steps`."""
    return [
        t("transcription.keys.groq.help.step1"),
        t("transcription.keys.groq.help.step2"),
        t("transcription.keys.groq.help.step3"),
    ]


def _gemini_help_steps() -> list[str]:
    """Steps for the Gemini key help bubble. See `_openai_help_steps`."""
    return [
        t("transcription.keys.gemini.help.step1"),
        t("transcription.keys.gemini.help.step2"),
        t("transcription.keys.gemini.help.step3"),
    ]


def _elevenlabs_help_steps() -> list[str]:
    """Steps for the ElevenLabs key help bubble. See `_openai_help_steps`."""
    return [
        t("transcription.keys.elevenlabs.help.step1"),
        t("transcription.keys.elevenlabs.help.step2"),
        t("transcription.keys.elevenlabs.help.step3"),
    ]


# Sentinel: shown in the password field when a secret is present. Replacing it
# with the same string on save means "keep existing key"; replacing with empty
# means "delete the stored key"; replacing with anything else writes a new key.
MASKED_PLACEHOLDER = "••••••••••••••••"


class _RevealingPasswordEdit(PasswordLineEdit):
    """`PasswordLineEdit` whose eye button actually reveals the *stored* key,
    not just the masked placeholder we use as a presence indicator.

    The default PasswordLineEdit toggles QLineEdit echo mode; with our scheme
    the field text IS the bullet placeholder when a key is stored, so the
    eye just shows bullets-as-text — same characters, nothing useful. We hook
    `setPasswordVisible`: while the eye is held, fetch the real secret from
    keyring and inject it; on release, restore the placeholder."""

    def __init__(self, placeholder: str, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._fetch_real: Callable[[], str] | None = None
        self._restore_text: str | None = None

    def setRealKeyFetcher(self, fetcher: Callable[[], str]) -> None:
        """fetcher() returns the plaintext key, or '' if none stored."""
        self._fetch_real = fetcher

    def keyToCheck(self) -> str:
        """The key the "Check" button should probe: what the user typed, or —
        while the field still shows the masked placeholder — the stored one."""
        text = self.text().strip()
        if text == MASKED_PLACEHOLDER:
            return (self._fetch_real() or "") if self._fetch_real else ""
        return text

    def setPasswordVisible(self, isVisible: bool) -> None:
        if isVisible:
            if self.text() == MASKED_PLACEHOLDER and self._fetch_real:
                real = self._fetch_real() or ""
                if real:
                    self._restore_text = self.text()
                    # Bypass our own textEdited handlers (signal fires only on
                    # user typing; setText emits textChanged but not textEdited).
                    super().setText(real)
        else:
            if self._restore_text is not None:
                super().setText(self._restore_text)
                self._restore_text = None
        super().setPasswordVisible(isVisible)


class TranscriptionPage(BasePage):
    PAGE_ID = "settings-transcription"
    PAGE_TITLE_KEY = "page.transcription.title"
    PAGE_HINT_KEY = "page.transcription.hint"

    # Carries a key-check result from its worker thread back to the GUI
    # thread: provider id, result state (KEY_CHECK_STATES key), and the
    # generation the check was started with — see _on_check_key.
    _key_check_finished = Signal(str, str, int)

    def build(self, content_layout: QVBoxLayout) -> None:
        # Key-check plumbing, keyed by provider id. Set up first: BasePage
        # calls build() from its __init__, and the rows below register here.
        self._key_edits: dict[str, _RevealingPasswordEdit] = {}
        self._check_buttons: dict[str, PushButton] = {}
        self._check_status: dict[str, QLabel] = {}
        self._check_gen: dict[str, int] = {}
        self._key_check_finished.connect(self._on_key_check_finished)

        # --- Backend priority ---
        card, body = make_section_card(
            t("transcription.priority.title"),
            t("transcription.priority.hint"),
        )
        self.priority_list = QListWidget()
        self.priority_list.setObjectName("priorityList")
        self.priority_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.priority_list.setDefaultDropAction(Qt.MoveAction)
        self.priority_list.setSelectionMode(QAbstractItemView.SingleSelection)
        # Three short rows never need a scrollbar; size to content and hide
        # the inner scrollbar so it doesn't compete with the page's own.
        self.priority_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.priority_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body.addWidget(self.priority_list)
        content_layout.addWidget(card)

        # --- API keys ---
        card, body = make_section_card(
            t("transcription.keys.title"),
            t("transcription.keys.hint"),
        )
        # Every key the app can use sits in this one card, each with a line
        # saying what it is for. Two of them do live recognition: Gemini (the
        # same key also serves the Gemini batch backend) and ElevenLabs.
        self.openai_key_edit, self.openai_hint = self._add_key_row(
            body, "openai", OPENAI_KEYS_URL, _openai_help_steps(),
            t("transcription.keys.openai.nudge"),
        )
        self.groq_key_edit, self.groq_hint = self._add_key_row(
            body, "groq", GROQ_KEYS_URL, _groq_help_steps(),
            t("transcription.keys.groq.nudge"),
        )
        self.gemini_key_edit, self.gemini_hint = self._add_key_row(
            body, "gemini", GEMINI_KEYS_URL, _gemini_help_steps(),
            t("transcription.keys.gemini.nudge"),
        )
        # ElevenLabs goes last and gets no onboarding nudge: it is not a member
        # of the priority chain above — it serves only the live keys (quick,
        # translate, custom), and only when there is no Gemini key. It used to
        # have a "live recognition" card of its own, which read as "two engines,
        # one key field"; the per-row role line says the same thing better.
        self.elevenlabs_key_edit, _ = self._add_key_row(
            body, "elevenlabs", ELEVENLABS_KEYS_URL, _elevenlabs_help_steps(),
        )
        content_layout.addWidget(card)
        # We track which masked placeholders the user has touched so we know
        # whether to keep / overwrite / delete the stored key on save.
        self._openai_loaded_mask: Optional[str] = None
        self._groq_loaded_mask: Optional[str] = None
        self._gemini_loaded_mask: Optional[str] = None
        self._elevenlabs_loaded_mask: Optional[str] = None

        # --- Dictation text: what happens to the transcript before the paste.
        # Its own card: it applies whatever recognized the speech (live engine,
        # cloud batch or local Whisper), not just the live engines.
        card, body = make_section_card(
            t("transcription.dictation.title"),
            t("transcription.dictation.hint"),
        )
        self.quick_clean_switch = SwitchButton()
        self.quick_clean_switch.setOnText(t("common.on"))
        self.quick_clean_switch.setOffText(t("common.off"))
        body.addWidget(make_form_row(
            t("transcription.quick.clean.label"),
            self.quick_clean_switch,
            hint=t("transcription.quick.clean.hint"),
            align_right=True,
        ))
        self.dictation_ai_switch = SwitchButton()
        self.dictation_ai_switch.setOnText(t("common.on"))
        self.dictation_ai_switch.setOffText(t("common.off"))
        body.addWidget(make_form_row(
            t("transcription.dictation.ai.label"),
            self.dictation_ai_switch,
            hint=t("transcription.dictation.ai.hint"),
            align_right=True,
        ))
        content_layout.addWidget(card)

        # --- Per-backend models ---
        card, body = make_section_card(
            t("transcription.models.title"),
            t("transcription.models.hint"),
        )
        self.model_combos: dict[str, ComboBox] = {}
        for backend_id in BACKEND_ORDER:
            label = _backend_info(backend_id)[0]
            combo = ComboBox()
            combo.addItems(list(BACKEND_MODELS[backend_id]))
            combo.setFixedWidth(COMBO_FIELD_WIDTH)
            self.model_combos[backend_id] = combo
            body.addWidget(make_form_row(label, combo, align_right=True))
        content_layout.addWidget(card)

        # --- Microphone capture (input device + light enhance) ---
        # Orthogonal to the CUDA/CPU card below: this is *where audio comes
        # from* and how it is prepared before any backend sees it.
        card, body = make_section_card(
            t("transcription.mic.title"),
            t("transcription.mic.hint"),
        )
        self.mic_combo = ComboBox()
        self.mic_combo.setFixedWidth(MIC_COMBO_WIDTH)
        # Populated in load_from (needs a live PortAudio query). Placeholder
        # row so the layout is not empty before first load.
        self.mic_combo.addItem(t("transcription.mic.device.default"), userData="")
        body.addWidget(make_form_row(
            t("transcription.mic.device.label"),
            self.mic_combo,
            hint=t("transcription.mic.device.hint"),
            align_right=True,
        ))
        self.enhance_combo = ComboBox()
        self.enhance_combo.setFixedWidth(COMBO_FIELD_WIDTH)
        for key, value in ENHANCE_CHOICES:
            self.enhance_combo.addItem(t(key), userData=value)
        body.addWidget(make_form_row(
            t("transcription.enhance.label"),
            self.enhance_combo,
            hint=t("transcription.enhance.hint"),
            align_right=True,
        ))
        content_layout.addWidget(card)

        # --- Local transcription device ---
        # Last card: it only bites when `local` is the backend actually in use,
        # so it reads as a footnote to the priority/model choices above.
        card, body = make_section_card(
            t("transcription.device.title"),
            t("transcription.device.hint"),
        )
        self.device_combo = ComboBox()
        self.device_combo.addItems([t(key) for key, _ in DEVICE_CHOICES])
        self.device_combo.setFixedWidth(COMBO_FIELD_WIDTH)
        body.addWidget(make_form_row(
            t("transcription.device.label"),
            self.device_combo,
            hint=t("transcription.device.label.hint"),
            align_right=True,
        ))
        content_layout.addWidget(card)

    # ---------- helpers ----------

    def _build_password_edit(self, placeholder: str) -> _RevealingPasswordEdit:
        return _RevealingPasswordEdit(placeholder)

    def _build_key_hint(self, text: str) -> QLabel:
        """Right-of-field onboarding nudge, hidden until first-run setup shows it."""
        lbl = QLabel(text)
        lbl.setObjectName("onboardingHint")
        lbl.setVisible(False)
        return lbl

    def _add_key_row(
        self,
        body: QVBoxLayout,
        provider: str,
        keys_url: str,
        help_steps: list[str],
        nudge: str = "",
    ) -> tuple[_RevealingPasswordEdit, QLabel]:
        """Add one provider's row to the API-keys card; returns (field, nudge).

        All four rows are built here so they cannot drift apart: "?" help
        bubble by the label, "Check" button, the key field, the onboarding
        nudge + "Get a key" link, then the role line ("what this key is for",
        which is also where live recognition is flagged) and the hidden
        key-check verdict under it.
        """
        prefix = f"transcription.keys.{provider}"
        edit = self._build_password_edit(t(f"{prefix}.placeholder"))
        hint = self._build_key_hint(nudge)
        # `stretch_widget=True` so the key field fills the row — API keys are
        # long, narrow inputs only show the tail. The "?" help icon sits next to
        # the label; the onboarding nudge + a small "Get a key" link share the
        # trailing slot on the row's right edge.
        body.addWidget(self._with_check_status(
            provider,
            make_form_row(
                t(f"{prefix}.label"),
                self._key_field(provider, edit),
                hint=t(f"{prefix}.role"),
                label_trailing=make_help_button(
                    t(f"{prefix}.help.title"),
                    help_steps,
                    t(f"{prefix}.help.link"),
                    keys_url,
                ),
                trailing=self._key_trailing(hint, keys_url),
                stretch_widget=True,
            ),
        ))
        edit.textEdited.connect(lambda _: hint.setVisible(False))
        return edit, hint

    def _key_trailing(self, hint: QLabel, url: str) -> QWidget:
        """Right-of-field cluster: the (hidden) onboarding nudge plus an
        always-visible "Get a key" link to the provider's key page."""
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(hint, alignment=Qt.AlignVCenter)
        link = make_link_label(url, t("transcription.keys.get_link"), object_name="getKeyLink")
        lay.addWidget(link, alignment=Qt.AlignVCenter)
        return box

    # ---------- "Check" button beside each key ----------

    def _key_field(self, provider: str, edit: _RevealingPasswordEdit) -> QWidget:
        """The row's control: a "Check" button to the LEFT of the key field.

        Left, not right, so it stays put next to the label while the field
        stretches — and clear of the field's own eye button on the right."""
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        button = PushButton(t("transcription.keys.check"))
        button.setToolTip(t("transcription.keys.check.tooltip"))
        button.clicked.connect(lambda: self._on_check_key(provider))
        lay.addWidget(button, alignment=Qt.AlignVCenter)
        lay.addWidget(edit, stretch=1)
        self._key_edits[provider] = edit
        self._check_buttons[provider] = button
        # A verdict describes the key that was probed; once the field changes
        # it describes nothing, so it goes (and an in-flight probe is voided).
        edit.textEdited.connect(lambda _=None: self._clear_key_check(provider))
        return box

    def _with_check_status(self, provider: str, row: QWidget) -> QWidget:
        """Append the (hidden) verdict line under a key row, where a row hint
        would sit, indented to start under the button rather than the label."""
        status = QLabel("")
        status.setObjectName("keyCheckStatus")
        status.setWordWrap(True)
        # 14 = make_form_row's gap between the label column and the control.
        status.setContentsMargins(LABEL_COL_WIDTH + 14, 2, 0, 0)
        status.setVisible(False)
        row.layout().addWidget(status)
        self._check_status[provider] = status
        return row

    def _show_key_check(self, provider: str, state: str) -> None:
        key, tone = KEY_CHECK_STATES.get(state, KEY_CHECK_STATES["unknown"])
        status = self._check_status[provider]
        status.setText(t(key))
        status.setProperty("tone", tone)
        # A dynamic property only restyles after a re-polish.
        status.style().unpolish(status)
        status.style().polish(status)
        status.setVisible(True)

    def _clear_key_check(self, provider: str) -> None:
        # Bumping the generation makes a probe still in flight report into the
        # void instead of labelling the NEW text with the old key's verdict.
        self._check_gen[provider] = self._check_gen.get(provider, 0) + 1
        self._check_status[provider].setVisible(False)
        self._check_buttons[provider].setEnabled(True)

    def _on_check_key(self, provider: str) -> None:
        key = self._key_edits[provider].keyToCheck()
        if not key:
            self._show_key_check(provider, "empty")
            return
        gen = self._check_gen[provider] = self._check_gen.get(provider, 0) + 1
        # Probe with the model picked on this page (saved or not) — that is
        # the one dictation will use. ElevenLabs has no model combo.
        combo = self.model_combos.get(provider)
        model = combo.currentText() if combo is not None else None
        self._check_buttons[provider].setEnabled(False)
        self._show_key_check(provider, "checking")

        # The probe is a network call — off the UI thread, like the license
        # activation, so a slow provider never freezes the settings window.
        def _work() -> None:
            # Imported here: services.key_check pulls in the provider SDKs,
            # which this page deliberately keeps out of its import path.
            from services.key_check import check_key

            result = check_key(provider, key, model)
            try:
                self._key_check_finished.emit(provider, result, gen)
            except RuntimeError:
                # The settings window was closed (page deleted) meanwhile.
                logger.debug("Key check finished after the page was destroyed")

        threading.Thread(target=_work, name=f"key-check-{provider}", daemon=True).start()

    def _on_key_check_finished(self, provider: str, result: str, gen: int) -> None:
        if gen != self._check_gen.get(provider):
            return  # field edited or re-checked since — stale verdict
        self._check_buttons[provider].setEnabled(True)
        self._show_key_check(provider, result)

    def enter_initial_setup(self) -> None:
        """First-run only: reveal the key hints and glow the fields once."""
        self.openai_hint.setVisible(True)
        self.groq_hint.setVisible(True)
        self.gemini_hint.setVisible(True)
        pulse_field_glow(self.openai_key_edit)
        pulse_field_glow(self.groq_key_edit)
        pulse_field_glow(self.gemini_key_edit)

    def _populate_priority(self, ordered: list[str]) -> None:
        self.priority_list.clear()
        for backend_id in ordered:
            label, hint = _backend_info(backend_id)
            item = QListWidgetItem(f"≡   {label}     —   {hint}")
            item.setData(Qt.UserRole, backend_id)
            self.priority_list.addItem(item)
        self._fit_priority_height()

    def _fit_priority_height(self) -> None:
        """Size the list to its content so all backends are visible without
        an internal scrollbar competing with the page scroll."""
        count = self.priority_list.count()
        if count == 0:
            return
        # Per-row height from sizeHintForRow + the inner frame margin so the
        # last row isn't clipped. Add a small buffer for the QListWidget's
        # own frame (2-3 px each side under most styles).
        row_h = self.priority_list.sizeHintForRow(0)
        if row_h <= 0:
            row_h = 36  # fallback if Qt hasn't computed it yet
        total = row_h * count + 2 * self.priority_list.frameWidth() + 8
        self.priority_list.setFixedHeight(total)

    def _ordered_priority(self) -> list[str]:
        result: list[str] = []
        for i in range(self.priority_list.count()):
            item = self.priority_list.item(i)
            backend_id = item.data(Qt.UserRole)
            if backend_id:
                result.append(backend_id)
        return result

    # ---------- Config interface ----------

    def load_from(self, config: Config) -> None:
        current_order = config.backend_priority
        seen: set[str] = set()
        ordered: list[str] = []
        for b in current_order:
            if b in BACKEND_INFO_KEYS and b not in seen:
                ordered.append(b)
                seen.add(b)
        for b in BACKEND_ORDER:
            if b not in seen:
                ordered.append(b)
        self._populate_priority(ordered)

        # API keys: if a stored secret exists, show the masked placeholder so
        # the user can see "yes this is set" without exposing the actual value.
        # Wire each password edit's eye button to fetch the real key from the
        # credential manager while held — see _RevealingPasswordEdit.
        has_openai = config.has_secret("OPEN_AI_API_KEY")
        self._openai_loaded_mask = MASKED_PLACEHOLDER if has_openai else None
        self.openai_key_edit.setText(self._openai_loaded_mask or "")
        self.openai_key_edit.setRealKeyFetcher(
            lambda: config.get_secret("OPEN_AI_API_KEY") or ""
        )

        has_groq = config.has_secret("GROQ_API_KEY")
        self._groq_loaded_mask = MASKED_PLACEHOLDER if has_groq else None
        self.groq_key_edit.setText(self._groq_loaded_mask or "")
        self.groq_key_edit.setRealKeyFetcher(
            lambda: config.get_secret("GROQ_API_KEY") or ""
        )

        has_gemini = config.has_secret("GEMINI_API_KEY")
        self._gemini_loaded_mask = MASKED_PLACEHOLDER if has_gemini else None
        self.gemini_key_edit.setText(self._gemini_loaded_mask or "")
        self.gemini_key_edit.setRealKeyFetcher(
            lambda: config.get_secret("GEMINI_API_KEY") or ""
        )

        has_elevenlabs = config.has_secret("ELEVENLABS_API_KEY")
        self._elevenlabs_loaded_mask = MASKED_PLACEHOLDER if has_elevenlabs else None
        self.elevenlabs_key_edit.setText(self._elevenlabs_loaded_mask or "")
        self.elevenlabs_key_edit.setRealKeyFetcher(
            lambda: config.get_secret("ELEVENLABS_API_KEY") or ""
        )
        self.quick_clean_switch.setChecked(
            (config.get("QUICK_CLEAN_FILLERS") or "true").strip().lower() == "true"
        )
        self.dictation_ai_switch.setChecked(
            (config.get("DICTATION_AI_CORRECTION") or "false").strip().lower() == "true"
        )

        # Model selectors
        for backend_id, combo in self.model_combos.items():
            current = config.get(f"MODEL_{backend_id.upper()}")
            idx = combo.findText(current or "")
            if idx >= 0:
                combo.setCurrentIndex(idx)

        current_dev = (config.get("USE_DEVICE") or "cpu").lower()
        for i, (_, value) in enumerate(DEVICE_CHOICES):
            if value == current_dev:
                self.device_combo.setCurrentIndex(i)
                break

        self._populate_mic_combo(config.get("INPUT_DEVICE", "") or "")

        enhance = normalize_enhance_profile(config.get("AUDIO_ENHANCE", "light"))
        idx = self.enhance_combo.findData(enhance)
        if idx < 0:
            idx = self.enhance_combo.findData("light")
        if idx >= 0:
            self.enhance_combo.setCurrentIndex(idx)

    def _populate_mic_combo(self, selected_config: str) -> None:
        """Refresh the input-device list from PortAudio and restore selection."""
        self.mic_combo.blockSignals(True)
        self.mic_combo.clear()
        self.mic_combo.addItem(t("transcription.mic.device.default"), userData="")
        try:
            devices = list_input_devices()
        except Exception:
            devices = []
        for info in devices:
            # userData is the config value ("name::<name>"); label may include hostapi.
            self.mic_combo.addItem(info.display_label, userData=info.config_value)

        # Restore selection. If the saved device is missing from the live list,
        # keep a synthetic row so the user still sees what was stored and can
        # re-pick; resolve_input_device will fall back to default at record time.
        selected = (selected_config or "").strip()
        idx = self.mic_combo.findData(selected) if selected else 0
        if selected and idx < 0:
            # Bare name without prefix — try matching encode form.
            from services.audio_prep import decode_device_name

            bare = decode_device_name(selected)
            if bare:
                for i in range(self.mic_combo.count()):
                    data = self.mic_combo.itemData(i) or ""
                    if data == encode_device_name(bare) or (
                        isinstance(data, str) and data.endswith(bare)
                    ):
                        idx = i
                        break
            if idx < 0:
                self.mic_combo.addItem(
                    f"{bare or selected} (?)", userData=selected
                )
                idx = self.mic_combo.count() - 1
        self.mic_combo.setCurrentIndex(max(0, idx))
        self.mic_combo.blockSignals(False)

    def apply_to(self, config: Config) -> None:
        # Priority — fall back to ['local'] if everything got drag-deleted.
        priority = self._ordered_priority() or ["local"]
        config.set_backend_priority(priority)

        self._apply_secret(
            config,
            key="OPEN_AI_API_KEY",
            field_text=self.openai_key_edit.text(),
            loaded_mask=self._openai_loaded_mask,
        )
        self._apply_secret(
            config,
            key="GROQ_API_KEY",
            field_text=self.groq_key_edit.text(),
            loaded_mask=self._groq_loaded_mask,
        )
        self._apply_secret(
            config,
            key="GEMINI_API_KEY",
            field_text=self.gemini_key_edit.text(),
            loaded_mask=self._gemini_loaded_mask,
        )
        self._apply_secret(
            config,
            key="ELEVENLABS_API_KEY",
            field_text=self.elevenlabs_key_edit.text(),
            loaded_mask=self._elevenlabs_loaded_mask,
        )
        config.set(
            "QUICK_CLEAN_FILLERS",
            "true" if self.quick_clean_switch.isChecked() else "false",
        )
        config.set(
            "DICTATION_AI_CORRECTION",
            "true" if self.dictation_ai_switch.isChecked() else "false",
        )

        for backend_id, combo in self.model_combos.items():
            config.set(f"MODEL_{backend_id.upper()}", combo.currentText())

        _, dev_val = DEVICE_CHOICES[self.device_combo.currentIndex()]
        config.set("USE_DEVICE", dev_val)

        mic_data = self.mic_combo.currentData()
        config.set("INPUT_DEVICE", mic_data if isinstance(mic_data, str) else "")

        enhance_data = self.enhance_combo.currentData()
        if not isinstance(enhance_data, str) or not enhance_data:
            enhance_data = "light"
        config.set("AUDIO_ENHANCE", normalize_enhance_profile(enhance_data))

    def _apply_secret(
        self,
        config: Config,
        key: str,
        field_text: str,
        loaded_mask: Optional[str],
    ) -> None:
        """Translate (field, loaded_mask) → keep / overwrite / delete the keyring entry.

        * Loaded as masked, field unchanged       → keep existing
        * Loaded as masked, field cleared empty   → delete
        * Loaded as masked, field replaced        → overwrite with new value
        * Loaded as empty, field has content      → write new
        * Loaded as empty, field still empty      → no-op
        """
        text = field_text.strip()
        if loaded_mask is not None:
            if text == loaded_mask:
                return  # untouched
            if not text:
                config.set_secret(key, None)
                return
            config.set_secret(key, text)
        else:
            if text:
                config.set_secret(key, text)

    def validate(self) -> Optional[str]:
        if not self._ordered_priority():
            return t("transcription.error.priority_empty")
        return None

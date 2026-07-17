# file: ui/settings_pages/transcription_page.py

"""
Transcription backend configuration: priority order, API keys (stored in the
Windows Credential Manager via keyring), per-backend model picks, and the
device the local backend runs on.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
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
)

from i18n import t
from services.transcription_models import (
    GROQ_TRANSCRIPTION_MODELS,
    LOCAL_WHISPER_MODELS,
    OPENAI_TRANSCRIPTION_MODELS,
)
from services.config_store import Config
from .base import (
    BasePage,
    make_form_row,
    make_help_button,
    make_link_label,
    make_section_card,
    pulse_field_glow,
)


# Single canonical order for every card on this page — Backend priority, API
# keys, Model per backend. The eye reads "OpenAI → Groq → Local" once and that
# mental map stays valid across the whole page.
BACKEND_ORDER = ("openai", "groq", "local")

# Display name + one-line pitch per backend, as catalog KEYS rather than text.
# A `t()` at module scope resolves once, at import, and would pin every backend
# label to whatever locale happened to be active then — rebuilding the page
# never undoes it. `_backend_info()` does the lookup at build time instead.
# The dict's *keys* are backend ids: those are data (they hit config.env and
# `MODEL_<ID>`) and stay untranslated.
BACKEND_INFO_KEYS = {
    "openai": ("transcription.backend.name.openai", "transcription.backend.hint.openai"),
    "groq":   ("transcription.backend.name.groq",   "transcription.backend.hint.groq"),
    "local":  ("transcription.backend.name.local",  "transcription.backend.hint.local"),
}

BACKEND_MODELS = {
    "openai": OPENAI_TRANSCRIPTION_MODELS,
    "groq":   GROQ_TRANSCRIPTION_MODELS,
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

# Where new users go to create a key for each cloud backend. Surfaced both as a
# "?" help bubble next to the field and a small always-visible "Get a key" link.
OPENAI_KEYS_URL = "https://platform.openai.com/api-keys"
GROQ_KEYS_URL = "https://console.groq.com/keys"


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

    def build(self, content_layout: QVBoxLayout) -> None:
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
        self.openai_key_edit = self._build_password_edit(t("transcription.keys.openai.placeholder"))
        self.openai_hint = self._build_key_hint(t("transcription.keys.openai.nudge"))
        # `stretch_widget=True` so the key field fills the row — API keys are
        # long, narrow inputs only show the tail. The "?" help icon sits next to
        # the label; the onboarding nudge + a small "Get a key" link share the
        # trailing slot on the row's right edge.
        body.addWidget(
            make_form_row(
                t("transcription.keys.openai.label"),
                self.openai_key_edit,
                label_trailing=make_help_button(
                    t("transcription.keys.openai.help.title"),
                    _openai_help_steps(),
                    t("transcription.keys.openai.help.link"),
                    OPENAI_KEYS_URL,
                ),
                trailing=self._key_trailing(self.openai_hint, OPENAI_KEYS_URL),
                stretch_widget=True,
            )
        )
        self.openai_key_edit.textEdited.connect(
            lambda _: self.openai_hint.setVisible(False)
        )

        self.groq_key_edit = self._build_password_edit(t("transcription.keys.groq.placeholder"))
        self.groq_hint = self._build_key_hint(t("transcription.keys.groq.nudge"))
        body.addWidget(
            make_form_row(
                t("transcription.keys.groq.label"),
                self.groq_key_edit,
                label_trailing=make_help_button(
                    t("transcription.keys.groq.help.title"),
                    _groq_help_steps(),
                    t("transcription.keys.groq.help.link"),
                    GROQ_KEYS_URL,
                ),
                trailing=self._key_trailing(self.groq_hint, GROQ_KEYS_URL),
                stretch_widget=True,
            )
        )
        self.groq_key_edit.textEdited.connect(
            lambda _: self.groq_hint.setVisible(False)
        )
        content_layout.addWidget(card)
        # We track which masked placeholders the user has touched so we know
        # whether to keep / overwrite / delete the stored key on save.
        self._openai_loaded_mask: Optional[str] = None
        self._groq_loaded_mask: Optional[str] = None

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

    def enter_initial_setup(self) -> None:
        """First-run only: reveal the key hints and glow the fields once."""
        self.openai_hint.setVisible(True)
        self.groq_hint.setVisible(True)
        pulse_field_glow(self.openai_key_edit)
        pulse_field_glow(self.groq_key_edit)

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

        for backend_id, combo in self.model_combos.items():
            config.set(f"MODEL_{backend_id.upper()}", combo.currentText())

        _, dev_val = DEVICE_CHOICES[self.device_combo.currentIndex()]
        config.set("USE_DEVICE", dev_val)

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

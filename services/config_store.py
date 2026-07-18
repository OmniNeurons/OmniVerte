# file: services/config_store.py

"""
Single source of truth for app settings and secrets.

- Non-secret settings live in ``%APPDATA%\\OmniVerte\\config.env`` (dotenv
  format, edited by the app at runtime).
- Secret values (API keys) live in the OS credential manager via ``keyring``.
  On Windows this is the Credential Manager (DPAPI-protected).

On a fresh install (no ``config.env`` yet) defaults are applied and onboarding
runs — there is no import from a legacy ``.env``.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import keyring
import keyring.errors
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

APP_NAME = "OmniVerte"
KEYRING_SERVICE = "OmniVerte"

# Keys treated as secrets — stored only in keyring, never in config.env.
SECRET_KEYS = frozenset({"OPEN_AI_API_KEY", "GROQ_API_KEY"})

# Fallback values for non-secret settings.
DEFAULTS: dict[str, str] = {
    "ACTIVATION_KEY": "F9",
    "ACTIVATION_MODE": "keyboard",
    "MOUSE_ACTIVATION_BUTTON": "middle",
    # Per-action global hotkeys (keyboard mode). Each is hard-captured
    # (suppressed) so the focused app never sees the keypress — see
    # HOTKEYS_SUPPRESS. HOTKEY_TRANSCRIBE supersedes the legacy ACTIVATION_KEY.
    "HOTKEY_TRANSCRIBE": "F9",
    "HOTKEY_TRANSLATE": "F10",
    "HOTKEY_CUSTOM": "F11",
    # Which rewrite style the custom hotkey applies: casual | professional |
    # custom. On a fresh install (no config yet) F11 defaults to the
    # "professional" preset — a useful out-of-the-box rewrite that needs no
    # setup, unlike "custom" which does nothing until the user writes a
    # CUSTOM_STYLE_PROMPT. Users can switch to casual/custom in settings.
    "HOTKEY_CUSTOM_STYLE": "professional",
    # When true, hotkeys are swallowed via a low-level keyboard hook so they
    # never reach the foreground window. Set false to fall back to pass-through
    # (observe-only) if suppression causes conflicts or latency.
    "HOTKEYS_SUPPRESS": "true",
    "TRANSCRIPTION_BACKEND": "local",
    # `small` is the fresh-install default: large-v3 is ~3GB to download and
    # transcribes well under realtime on a CPU, which is a brutal first-run
    # impression. Users with a CUDA GPU can switch to large-v3 in settings.
    "WHISPER_MODEL": "small",
    "USE_DEVICE": "cpu",
    # Comma-separated ordered list of backends to try at init.
    # First one with valid credentials becomes active — so on a fresh install
    # with no API keys this collapses to local, but the moment an OpenAI (then
    # Groq) key is entered that cloud backend takes over.
    "BACKEND_PRIORITY": "openai,groq,local",
    # Per-backend model preference. The currently active model
    # (WHISPER_MODEL) is derived from these based on the active backend.
    "MODEL_LOCAL": "small",
    "MODEL_OPENAI": "gpt-4o-mini-transcribe",
    "MODEL_GROQ": "whisper-large-v3-turbo",
    # Mic capture: empty INPUT_DEVICE = PortAudio system default. Non-empty
    # values are "name::<device name>" (see services.audio_prep). AUDIO_ENHANCE
    # is off|light (default light): high-pass + capped AGC before WAV write.
    "INPUT_DEVICE": "",
    "AUDIO_ENHANCE": "light",
    "ONBOARDING_DONE": "false",
    # Two languages the user works between. Used by the smart-translate flow
    # in the main window: direction is auto-detected from the source text.
    # Stored as human-readable English names matching SUPPORTED_LANGUAGES.
    "PRIMARY_LANGUAGE": "English",
    "SECONDARY_LANGUAGE": "Russian",
    # Custom rewrite-style preset for the "Custom" button. Name is optional
    # and shows up as the button's tooltip; prompt is the actual instruction.
    "CUSTOM_STYLE_NAME": "",
    "CUSTOM_STYLE_PROMPT": "",
    # UI theme: "light" or "dark". Toggled live from the main-window header.
    "THEME": "light",
    # Interface language, as a Whisper language code ("en"/"ru") matching
    # i18n.UI_LOCALES. Orthogonal to PRIMARY_LANGUAGE: what the app *speaks to
    # you* is not what you dictate in — a Russian speaker may well want an
    # English UI, and a Russian UI does not imply Russian dictation.
    # "" means auto — resolve from the OS UI language at startup. Only a fresh
    # install ever sees it (see _migrate_ui_language), and onboarding writes the
    # resolved value back so the choice is sticky from then on.
    "UI_LANGUAGE": "",
    # ----- Corporate glossary -----
    # Master switch for all glossary layers; off by default so behavior is
    # byte-identical to a build without the feature until a user opts in. The
    # term lists themselves live in glossary.json (not here) — only these small
    # flags/thresholds round-trip through config.env.
    "GLOSSARY_ENABLED": "false",
    # Layer B: bias the ASR step (cloud `prompt`, local faster-whisper `hotwords`).
    "GLOSSARY_ASR_BIAS": "true",
    # Layer A in the transcribe auto-correction (_normalize_to_primary).
    "GLOSSARY_LLM_CORRECTION": "true",
    # Layer A in translate/rewrite — both the auto translate/custom hotkey actions
    # and the manual main-window buttons. Separate flag so the glossary can stay
    # in correction but be kept out of translation/rewriting where it sometimes
    # over-normalizes.
    "GLOSSARY_LLM_REWRITE": "true",
    # Layer C: deterministic fuzzy replacements on the final transcript
    # (transcribe action only). The threshold/cap are consumed once layer C lands.
    "GLOSSARY_FUZZY_REPLACE": "true",
    "GLOSSARY_FUZZY_THRESHOLD": "88",
    "GLOSSARY_FUZZY_MAX_TERMS": "200",
}


def _appdata_dir() -> Path:
    """Per-user config directory. Uses %APPDATA% on Windows, ~/.config elsewhere."""
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / APP_NAME


class Config:
    """Loads, persists, and exposes app settings + secrets."""

    def __init__(self):
        self.dir = _appdata_dir()
        self.path = self.dir / "config.env"
        self._values: dict[str, str] = {}
        self._load()

    # ---------- loading / persistence ----------

    def _load(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            raw = dotenv_values(self.path) or {}
            self._values = {k: v for k, v in raw.items() if v is not None}

        # Must run before defaults are applied — they inspect which keys the
        # user actually has on file.
        self._migrate_hotkeys()
        self._migrate_ui_language()

        for k, v in DEFAULTS.items():
            self._values.setdefault(k, v)

        self._migrate_preferred_language()

    def _migrate_hotkeys(self) -> None:
        """One-shot: carry a customised legacy ACTIVATION_KEY into HOTKEY_TRANSCRIBE.

        Older versions had a single ACTIVATION_KEY. The per-action design keys
        transcription off HOTKEY_TRANSCRIBE; if a user customised ACTIVATION_KEY
        (e.g. to F8) we copy it so their key isn't silently reset to the F9
        default. Only fires when HOTKEY_TRANSCRIBE isn't already on file.
        """
        if "HOTKEY_TRANSCRIBE" not in self._values:
            legacy = self._values.get("ACTIVATION_KEY")
            if legacy:
                self._values["HOTKEY_TRANSCRIBE"] = legacy
                logger.info(f"Migrated legacy ACTIVATION_KEY={legacy} → HOTKEY_TRANSCRIBE")

    def _migrate_ui_language(self) -> None:
        """One-shot: pin existing installs to English so an update never
        changes the language of a UI the user already knows.

        UI_LANGUAGE defaults to "" (auto = follow the OS), which is what we want
        for someone opening the app for the first time. But applying that to an
        install that predates the setting would silently flip a long-time
        Russian-Windows user's familiar English UI to Russian on update — a
        change they never asked for, in the one release where they also cannot
        guess that "Язык интерфейса" under General is what puts it back.

        So: an install that has already finished onboarding gets an explicit
        "en" and keeps what it had. Only a genuinely fresh install auto-detects.
        Must run before defaults are applied — after setdefault, every install
        looks like it has UI_LANGUAGE and ONBOARDING_DONE on file.
        """
        if "UI_LANGUAGE" in self._values:
            return
        if self._values.get("ONBOARDING_DONE", "").strip().lower() == "true":
            self._values["UI_LANGUAGE"] = "en"
            logger.info("Existing install predates UI_LANGUAGE → pinned to 'en'")

    def _migrate_preferred_language(self) -> None:
        """One-shot: collapse legacy PREFERRED_LANGUAGE (en/ru) into PRIMARY_LANGUAGE.

        Older versions stored a separate Whisper-only language hint as a short
        code. The unified design uses PRIMARY_LANGUAGE (display name) for both
        translation direction and the Whisper hint, so the old key is dropped.
        We map en→English / ru→Russian only when PRIMARY_LANGUAGE is still at
        its default, to avoid clobbering a user-set value.
        """
        legacy = self._values.pop("PREFERRED_LANGUAGE", None)
        if not legacy:
            return
        if self._values.get("PRIMARY_LANGUAGE") == DEFAULTS["PRIMARY_LANGUAGE"]:
            mapped = {"en": "English", "ru": "Russian"}.get(legacy.lower())
            if mapped:
                self._values["PRIMARY_LANGUAGE"] = mapped
                # Default SECONDARY_LANGUAGE is "Russian" — if migration also
                # sets PRIMARY to Russian, the pair collapses to Russian/Russian
                # which breaks the auto-direction translate flow. Flip secondary
                # to English in that case.
                if self._values.get("SECONDARY_LANGUAGE") == mapped:
                    other = "English" if mapped == "Russian" else "Russian"
                    self._values["SECONDARY_LANGUAGE"] = other
                logger.info(f"Migrated legacy PREFERRED_LANGUAGE={legacy} → PRIMARY_LANGUAGE={mapped}")
        # Persist removal of the legacy key (and any migration).
        self._write(self._values)

    def reload(self) -> None:
        """Re-read the config file from disk.

        The settings dialog runs out-of-process and writes to the same file —
        callers that hold a long-lived Config (tray, main window) should call
        this after a save round-trip to pick up new values without restarting.
        """
        self._values = {}
        self._load()

    @staticmethod
    def _escape(value: str) -> str:
        # dotenv decodes \\, \", \n, \r inside double-quoted values, so escape
        # those four to survive the round-trip. Without this, a prompt with a "
        # produces a malformed line that dotenv_values silently drops on reload.
        return (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )

    def _write(self, values: dict[str, str]) -> None:
        lines = [f'{k}="{self._escape(v)}"' for k, v in values.items()]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------- non-secret values ----------

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if key in self._values:
            return self._values[key]
        if default is not None:
            return default
        return DEFAULTS.get(key)

    def set(self, key: str, value: str) -> None:
        self._values[key] = value
        self._write(self._values)

    # ---------- secrets ----------

    def get_secret(self, key: str) -> Optional[str]:
        try:
            return keyring.get_password(KEYRING_SERVICE, key)
        except Exception as e:
            logger.error(f"keyring read failed for {key}: {e}")
            return None

    def set_secret(self, key: str, value: Optional[str]) -> None:
        try:
            if value:
                keyring.set_password(KEYRING_SERVICE, key, value)
            else:
                try:
                    keyring.delete_password(KEYRING_SERVICE, key)
                except keyring.errors.PasswordDeleteError:
                    pass
        except Exception as e:
            logger.error(f"keyring write failed for {key}: {e}")

    def has_secret(self, key: str) -> bool:
        return bool(self.get_secret(key))

    # ---------- backend priority helpers ----------

    @property
    def backend_priority(self) -> list[str]:
        raw = self.get("BACKEND_PRIORITY") or "local"
        order = [b.strip() for b in raw.split(",") if b.strip()]
        return order or ["local"]

    def set_backend_priority(self, backends: list[str]) -> None:
        self.set("BACKEND_PRIORITY", ",".join(backends))

    # ---------- onboarding state ----------

    def onboarding_done(self) -> bool:
        return (self.get("ONBOARDING_DONE") or "false").lower() == "true"

    def mark_onboarding_done(self) -> None:
        # Freeze the auto-detected UI language into an explicit choice. Until
        # now UI_LANGUAGE may be "" (= follow the OS); leaving it that way means
        # a user who later changes their Windows display language would find
        # Omni Verte silently changed language too, having never picked one.
        # By onboarding's end the app has been speaking one language at them for
        # a whole wizard — that is the choice, so make it explicit and sticky.
        if not (self.get("UI_LANGUAGE") or "").strip():
            from i18n import current_locale

            self.set("UI_LANGUAGE", current_locale())
        self.set("ONBOARDING_DONE", "true")

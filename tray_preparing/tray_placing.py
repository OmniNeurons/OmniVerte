import pystray
from PIL import Image, ImageDraw
import threading
import time
import sys
import os

import logging
from i18n import t
from services.audio_writer import (
    AudioWriter,
    HOTKEY_ACTIONS,
    LOCAL_WHISPER_MODELS,
    OPENAI_TRANSCRIPTION_MODELS,
    GROQ_TRANSCRIPTION_MODELS,
)
from services.ui_bridge import UIBridge

# Configure logger
logger = logging.getLogger(__name__)

# Status → dot color drawn over the tray icon. Covers both the session-status
# axis (recording/processing) and the model-state axis (loading/failed).
_STATUS_DOT_COLORS = {
    "recording":  (220, 70, 70, 255),
    "processing": (235, 200, 50, 255),
    "loading":    (139, 92, 246, 255),  # violet, matches STATUS_DOT_LOADING
    "failed":     (185, 28, 28, 255),   # red, matches STATUS_DOT_ERROR
}

def get_resource_path(filename):
    """
    Get the path to a resource file, handling both normal and PyInstaller bundled modes.

    Args:
        filename: Name of the resource file

    Returns:
        str: Full path to the resource file
    """
    if hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller bundle
        return os.path.join(sys._MEIPASS, filename)
    else:
        # Running from source
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

def _load_base_icon() -> Image.Image:
    """Load favicon.ico into a 64x64 RGBA image, with a simple fallback."""
    try:
        icon_path = get_resource_path('favicon.ico')
        if os.path.exists(icon_path):
            image = Image.open(icon_path).convert("RGBA")
            return image.resize((64, 64), Image.Resampling.LANCZOS)
    except Exception as e:
        logger.warning(f"Failed to load favicon.ico: {e}")

    logger.debug("Using fallback tray icon")
    image = Image.new('RGBA', (64, 64), (255, 255, 255, 0))
    dc = ImageDraw.Draw(image)
    dc.rectangle([22, 22, 42, 42], fill=(0, 0, 0, 255))
    return image


def create_image():
    """Public name kept for compatibility — returns the idle icon."""
    return _load_base_icon()


def _make_status_icon(base: Image.Image, status: str) -> Image.Image:
    """
    Return a copy of `base` with a colored dot in the bottom-right corner for
    recording/processing statuses; return `base` unchanged for "idle".
    """
    color = _STATUS_DOT_COLORS.get(status)
    if color is None:
        return base

    img = base.copy()
    dc = ImageDraw.Draw(img)
    w, h = img.size
    diameter = int(w * 0.55)
    x0 = w - diameter - 2
    y0 = h - diameter - 2
    dc.ellipse(
        [x0, y0, x0 + diameter, y0 + diameter],
        fill=color,
        outline=(20, 20, 20, 220),
        width=2,
    )
    return img

def on_exit(icon, ui_bridge: UIBridge):
    """Handles application exit from the system tray."""
    icon.stop()
    ui_bridge.quit_requested.emit()


def setup_tray(audio_writer: AudioWriter, ui_bridge: UIBridge, config):
    """
    Sets up the system tray icon and menu for the application.

    Args:
        audio_writer: Instance of AudioWriter for controlling voice input.
        ui_bridge: UIBridge for cross-thread signals (status, show_window, quit).
        config: Config instance — used for the floating-indicator toggle state.

    Returns:
        pystray.Icon: The created system tray icon.
    """
    base_icon = _load_base_icon()
    icon = pystray.Icon("Omni Verte", base_icon, "Omni Verte", menu=None)

    # Track whether the floating indicator is on (persists in config).
    def _floating_indicator_enabled() -> bool:
        return (config.get("SHOW_FLOATING_INDICATOR", "true") or "true").lower() == "true"

    # Swap tray icon image on status / model-state change. Two orthogonal axes
    # combined here: model "loading"/"failed" override the session dot (the model
    # isn't usable, so recording can't run anyway). On "ready" the model axis
    # steps aside and the session status shows through. Both signals reach us via
    # Qt::QueuedConnection, so these slots run on the GUI (main) thread.
    tray_state = {"session": "idle", "model": "ready"}

    def _repaint_icon():
        """Re-render the icon + tooltip from cached state.

        A pure function of `tray_state`, so it is also the language-switch hook:
        the tooltip is built HERE, not in `update_menu`, and would otherwise
        stay in the old language until the next status change — which on an idle
        machine may be a very long time, or never.
        """
        model = tray_state["model"]
        if model in ("loading", "failed"):
            effective = model
            tip = (t("tray.tooltip.loading") if model == "loading"
                   else t("tray.tooltip.failed"))
        else:
            effective = tray_state["session"]
            tip = t("app.title")
        try:
            icon.icon = _make_status_icon(base_icon, effective)
            icon.title = tip
        except Exception as e:
            logger.debug(f"Failed to swap tray icon for {effective!r}: {e}")

    def _on_status(status: str):
        tray_state["session"] = status
        _repaint_icon()

    def _on_model_state(state: str):
        tray_state["model"] = state
        _repaint_icon()

    ui_bridge.status_changed.connect(_on_status)
    ui_bridge.model_state_changed.connect(_on_model_state)

    def update_menu():
        """Updates the system tray menu with current settings.

        Rebuilt from scratch on every change, which is also what makes the tray
        free to re-render after a UI-language switch — `_on_settings_saved`
        already calls this. pystray is not Qt, so `QTranslator` could never
        reach these labels; they go through the same plain `t()` the windows do.

        Note the split between *canonical values* and *display labels*: every
        `enabled=` below compares a canonical value ('keyboard', 'cuda',
        'openai'), never a rendered label. Comparing labels used to work only
        because they happened to be English; under i18n it would silently break
        every submenu's enable/disable state.
        """
        is_keyboard = audio_writer.activation_mode == 'keyboard'
        activation_mode_label = t("tray.mode.keyboard") if is_keyboard else t("tray.mode.mouse")

        # Per-action hotkey submenu (keyboard mode). One sub-entry per action,
        # each showing its current key with a "Change" child that listens for a
        # new keypress and rebinds just that action.
        hotkey_items = []
        for aid, spec in HOTKEY_ACTIONS.items():
            cur = audio_writer.hotkeys.get(aid, spec["default"])
            hotkey_items.append(pystray.MenuItem(
                t("tray.hotkey.item", action=t(spec["label_key"]), key=cur),
                pystray.Menu(pystray.MenuItem(
                    t("tray.keys.change"),
                    (lambda a=aid: lambda icon=None, item=None: change_activation_key(a))(),
                    enabled=is_keyboard,
                )),
                enabled=is_keyboard,
            ))
        suppress_label = (
            t("tray.suppress.on") if audio_writer.suppress_hotkeys
            else t("tray.suppress.off")
        )
        mouse_activation_button = audio_writer.mouse_activation_button

        # Get current transcription model and backend
        current_model = audio_writer.whisper_model_name
        current_backend = audio_writer.transcription_backend

        # Build the unified Transcription model submenu. The model NAMES are
        # identifiers (gpt-4o-mini-transcribe, large-v3) and stay verbatim in
        # every locale — only the "which backend" prefix is translated.
        transcription_items = []
        for group_key, models in (
            ("tray.model.local", LOCAL_WHISPER_MODELS),
            ("tray.model.openai", OPENAI_TRANSCRIPTION_MODELS),
            ("tray.model.groq", GROQ_TRANSCRIPTION_MODELS),
        ):
            if transcription_items:
                transcription_items.append(pystray.Menu.SEPARATOR)
            for m in models:
                transcription_items.append(pystray.MenuItem(
                    t(group_key, model=m),
                    (lambda name=m: lambda icon=None, item=None: change_transcription_model(name))(),
                    enabled=(current_model != m)
                ))

        # Active transcription target, as a canonical value + its display label.
        # 'cuda'/'cpu' are hardware names and read the same everywhere; the two
        # cloud backends get a proper label.
        if current_backend in ("openai", "groq"):
            device_target = current_backend
            device_label = t(f"tray.device.{current_backend}")
        else:
            device_target = audio_writer.use_device
            device_label = device_target

        # Language pair (single source of truth for translation direction and
        # the Whisper transcription hint). These are English display names by
        # design — they are config VALUES, not chrome (see languages_page).
        primary_lang = config.get("PRIMARY_LANGUAGE") or "English"
        secondary_lang = config.get("SECONDARY_LANGUAGE") or "Russian"

        # Create menu with current settings
        floating_label = (
            t("tray.indicator.hide") if _floating_indicator_enabled()
            else t("tray.indicator.show")
        )

        menu_items = [
            pystray.MenuItem(t("tray.show_window"), lambda: ui_bridge.show_window_requested.emit(), default=True),
            pystray.MenuItem(floating_label, lambda: toggle_floating_indicator()),
            pystray.Menu.SEPARATOR,

            # Activation settings
            pystray.MenuItem(t("tray.mode", mode=activation_mode_label), pystray.Menu(
                pystray.MenuItem(t("tray.mode.keyboard"), lambda: change_activation_mode(None) if not is_keyboard else None, enabled=(not is_keyboard)),
                pystray.MenuItem(t("tray.mode.mouse"), lambda: change_activation_mode(None) if is_keyboard else None, enabled=is_keyboard)
            )),
            pystray.MenuItem(t("tray.keys"), pystray.Menu(*hotkey_items), enabled=is_keyboard),
            pystray.MenuItem(suppress_label, lambda: toggle_suppress_hotkeys(), enabled=is_keyboard),
            pystray.MenuItem(t("tray.mouse_button", button=t(f"general.mouse.{mouse_activation_button}")), pystray.Menu(
                pystray.MenuItem(t("general.mouse.middle"), lambda: change_mouse_activation_button(None) if mouse_activation_button != "middle" else None, enabled=(mouse_activation_button != "middle")),
                pystray.MenuItem(t("general.mouse.right"), lambda: change_mouse_activation_button(None) if mouse_activation_button != "right" else None, enabled=(mouse_activation_button != "right"))
            ), enabled=(not is_keyboard)),

            # Unified transcription model picker (local Whisper + OpenAI API)
            pystray.MenuItem(t("tray.model", model=current_model), pystray.Menu(*transcription_items)),

            pystray.MenuItem(t("tray.device", device=device_label), pystray.Menu(
                pystray.MenuItem('cuda', lambda: set_backend_device('cuda'), enabled=(device_target != 'cuda')),
                pystray.MenuItem('cpu', lambda: set_backend_device('cpu'), enabled=(device_target != 'cpu')),
                pystray.MenuItem(t("tray.device.openai"), lambda: set_backend_device('openai'), enabled=(device_target != 'openai')),
                pystray.MenuItem(t("tray.device.groq"), lambda: set_backend_device('groq'), enabled=(device_target != 'groq'))
            )),

            # Language submenu: the two languages the user configured in
            # Settings. Clicking the secondary swaps it with the primary, so
            # the pair stays intact. Drives both translation direction and
            # the Whisper transcription hint (unified setting).
            pystray.MenuItem(t("tray.language", language=primary_lang), pystray.Menu(
                pystray.MenuItem(primary_lang, lambda: None, enabled=False),
                pystray.MenuItem(secondary_lang, lambda sec=secondary_lang: set_primary_language(sec)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(t("tray.language.other"), lambda: ui_bridge.settings_requested.emit())
            )),

            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray.settings"), lambda: ui_bridge.settings_requested.emit()),
            pystray.MenuItem(t("tray.close"), lambda: on_exit(icon, ui_bridge))
        ]

        # Set the menu
        icon.menu = pystray.Menu(*menu_items)
    
    def toggle_floating_indicator():
        """Flip the SHOW_FLOATING_INDICATOR config flag and notify the indicator widget."""
        new_enabled = not _floating_indicator_enabled()
        config.set("SHOW_FLOATING_INDICATOR", "true" if new_enabled else "false")
        logger.info(f"Floating indicator: {new_enabled}")
        ui_bridge.floating_indicator_toggled.emit(new_enabled)
        update_menu()

    def change_activation_mode(item):
        """Changes activation mode between keyboard and mouse."""
        audio_writer.change_activation_mode()
        logger.info(f"Activation mode changed to: {audio_writer.activation_mode}")
        update_menu()
        
    def change_activation_key(action_id="transcribe"):
        """
        Starts listening for a new key for `action_id` in a separate thread.
        Updates the menu after a short delay.
        """
        # Start listening for new key in a separate thread to avoid blocking the UI
        threading.Thread(
            target=audio_writer.listen_for_new_activation_key,
            args=(action_id,),
            daemon=True,
        ).start()
        logger.info(f"Listening for new key for '{action_id}'...")
        # Wait briefly for the new key to be set
        time.sleep(1)
        update_menu()

    def toggle_suppress_hotkeys():
        """Toggle hard-capture (suppress) of hotkeys and re-register them."""
        audio_writer.toggle_suppress_hotkeys()
        logger.info(f"Hotkey hard-capture: {audio_writer.suppress_hotkeys}")
        update_menu()
        
    def change_mouse_activation_button(item):
        """Changes which mouse button activates the voice input."""
        audio_writer.change_mouse_activation_button()
        logger.info(f"Mouse activation button changed to: {audio_writer.mouse_activation_button}")
        update_menu()
        
    def change_transcription_model(model_name):
        """Changes the active transcription model (local Whisper or OpenAI API)."""
        try:
            audio_writer.change_transcription_model(model_name)
            logger.info(
                f"Transcription model changed to: {audio_writer.whisper_model_name} "
                f"(backend={audio_writer.transcription_backend})"
            )
        except Exception as e:
            logger.error(f"Failed to switch transcription model to {model_name}: {e}")
        update_menu()
        
    def toggle_use_device(item):
        """Toggles the device between CPU and CUDA."""
        audio_writer.toggle_use_device()
        logger.info(f"Device toggled to: {audio_writer.use_device}")
        update_menu()

    def set_backend_device(target):
        """Sets the active transcription target: 'cuda', 'cpu', or 'openai'."""
        try:
            audio_writer.set_backend_device(target)
            logger.info(
                f"Backend device set to: {target} "
                f"(backend={audio_writer.transcription_backend}, model={audio_writer.whisper_model_name})"
            )
        except Exception as e:
            logger.error(f"Failed to set backend device to {target}: {e}")
        update_menu()
        
    def _on_settings_saved():
        """Refresh tray state after the (in-process) settings window saves.

        Connected to ``ui_bridge.settings_saved``. The settings handler in
        OmniVerte.py already reloaded the shared Config before emitting,
        so we mainly rebuild the menu so the language pair and other
        config-driven labels reflect the new values without an app restart.
        The reload below is a redundant safety net (idempotent on the shared
        instance).

        This is also the tray's UI-language hook. OmniVerte's handler switches
        the catalog locale *before* emitting settings_saved, so the rebuild
        below simply picks the new language up — nothing here is
        language-specific. `_repaint_icon()` is called too because the tooltip
        is built there rather than in `update_menu`.
        """
        try:
            config.reload()
        except Exception as e:
            logger.warning(f"Config reload after settings save failed: {e}")
        try:
            # Live AudioWriter (voice path) — pick up edited glossary lists
            # without a restart, mirroring the config.reload() above.
            audio_writer.glossary.reload()
        except Exception as e:
            logger.warning(f"Glossary reload after settings save failed: {e}")
        try:
            update_menu()
            _repaint_icon()
        except Exception as e:
            logger.warning(f"Tray menu refresh after settings save failed: {e}")

    def set_primary_language(name):
        """Make `name` the primary language. If it was the secondary, swap so
        the pair stays intact. Drives both translation and Whisper hint."""
        current_primary = config.get("PRIMARY_LANGUAGE") or "English"
        current_secondary = config.get("SECONDARY_LANGUAGE") or "Russian"
        if name == current_primary:
            return
        config.set("PRIMARY_LANGUAGE", name)
        if name == current_secondary:
            config.set("SECONDARY_LANGUAGE", current_primary)
        logger.info(f"Primary language changed to: {name}")
        update_menu()
    
    # Rebuild the menu whenever the in-process settings window saves.
    ui_bridge.settings_saved.connect(_on_settings_saved)

    # Initialize menu
    update_menu()
    
    # Run the icon in a separate thread to avoid blocking the main application
    threading.Thread(target=icon.run, daemon=True).start()
    logger.info("System tray icon initialized")
    return icon
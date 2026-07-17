# file: OmniVerte.py

import argparse
import os
import sys

# Workaround for OMP: Error #15 — multiple OpenMP runtimes (MKL via numpy/torch
# + ctranslate2/onnxruntime) get linked into the process on Windows. Must be
# set before numpy/torch/sounddevice imports.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# Force UTF-8 for stdout/stderr so logging Cyrillic / non-ASCII transcripts
# doesn't blow up with UnicodeEncodeError on Windows (default cp1252).
for _stream in (sys.stdout, sys.stderr):
  try:
    _stream.reconfigure(encoding="utf-8")
  except Exception:
    pass

import ctypes
import logging

# Configure logger. Write the log into the per-user app data dir, not the CWD —
# launching from an arbitrary (or read-only) folder shouldn't litter it or fail.
_LOG_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~/.config"), "OmniVerte")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "OmniVerte.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Windows API functions for mutex handling
CreateMutex = ctypes.windll.kernel32.CreateMutexW
CloseHandle = ctypes.windll.kernel32.CloseHandle
GetLastError = ctypes.windll.kernel32.GetLastError

# Unique mutex name for single instance check
MUTEX_NAME = "omni_verte_mutex"

# Identifies us to the Windows shell — must be set in BOTH the main process and
# the `--settings` subprocess so they group as one app in the taskbar (and so
# the overlay icon attaches to the right HWND). Stable across versions.
APP_USER_MODEL_ID = "OmniVerte.App.1"


def _set_app_user_model_id():
  """Tag this process with our AppUserModelID. Safe to call multiple times."""
  try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
  except Exception as e:
    logger.warning(f"Failed to set AppUserModelID: {e}")


def check_cuda_availability():
  """Check if CUDA is available via ctranslate2 (avoids pulling in torch)."""
  try:
    import ctranslate2

    try:
      cuda_device_count = ctranslate2.get_cuda_device_count()
    except Exception:
      cuda_device_count = 0

    if cuda_device_count > 0:
      logger.info(f"CUDA is available (detected via ctranslate2). Device count: {cuda_device_count}")
      try:
        compute_types = ctranslate2.get_supported_compute_types("cuda")
        logger.info(f"Supported CUDA compute types: {compute_types}")
      except Exception:
        pass
      return True
    else:
      logger.warning("CUDA is not available. Models will run on CPU.")
      try:
        cpu_compute_types = ctranslate2.get_supported_compute_types("cpu")
        logger.info(f"Supported CPU compute types: {cpu_compute_types}")
      except Exception:
        pass
      return False

  except ImportError as e:
    logger.warning(f"ctranslate2 not available: {e}")
    return False
  except Exception as e:
    logger.warning(f"Error checking CUDA availability: {e}")
    return False


def _will_local_backend_be_used(config) -> bool:
  """
  Walk the priority list and decide whether the local backend will end up active.
  Used to gate the CUDA probe so cloud-only startups don't pay the cost.
  """
  for backend in config.backend_priority:
    if backend == "local":
      return True
    if backend == "openai" and config.has_secret("OPEN_AI_API_KEY"):
      return False
    if backend == "groq" and config.has_secret("GROQ_API_KEY"):
      return False
  return True  # nothing matched → AudioWriter falls back to local


def run_settings_dialog():
  """
  Standalone settings entry point — used both by `--settings` subprocess
  invocations (from the tray) and by the initial-startup onboarding path.
  Returns True if the user saved, False if they cancelled.
  """
  import i18n
  from services.config_store import Config
  from ui.onboarding_dialog import run_onboarding

  config = Config()
  # Separate process, so it has its own i18n module state — resolve the locale
  # before the dialog is built or it opens in English regardless of the setting.
  i18n.set_locale(
      (config.get("UI_LANGUAGE") or "").strip().lower() or i18n.detect_system_locale()
  )
  return run_onboarding(config, is_initial=not config.onboarding_done())


def main():
  """Main application: Qt event loop with tray + main window + hooks."""
  import i18n
  from services.config_store import Config

  config = Config()

  # Resolve the license entitlement once, up front (cached for the process).
  # No network — reads the dev override / cached token / FREE default. Every
  # gate downstream reads the same cached value via licensing.get_entitlement().
  from licensing import get_entitlement
  entitlement = get_entitlement()
  logger.info(f"License entitlement resolved: {entitlement}")

  # Create the QApplication early — onboarding (if needed) and the main window
  # both reuse this single instance. Without setting AUMID first, the taskbar
  # would group us with generic python.exe.
  _set_app_user_model_id()

  from PySide6.QtWidgets import QApplication
  app = QApplication.instance() or QApplication(sys.argv)
  app.setQuitOnLastWindowClosed(False)  # tray-only by default — closing the main window must NOT quit

  # Resolve the saved UI theme before any window/dialog is built so the very
  # first paint (including onboarding) is already in the right palette.
  from ui import style as _style
  _style.set_theme(config.get("THEME") or "light")

  # Same deal for the UI language, and for a sharper reason than the theme: page
  # titles and menu labels are resolved when their widget is BUILT, so this must
  # land before the first one exists — onboarding included, since a first-run
  # wizard is exactly when a user cannot yet go and change the setting.
  #
  # "" means auto: follow the OS on a fresh install. Existing installs were
  # pinned to an explicit "en" by Config._migrate_ui_language, so an update
  # never changes the language of a UI they already know. onboarding freezes
  # whatever we resolve here into config, so it stays put afterwards.
  _ui_lang = (config.get("UI_LANGUAGE") or "").strip().lower() or i18n.detect_system_locale()
  i18n.set_locale(_ui_lang)
  logger.info(f"UI language: {i18n.current_locale()}")

  # One-shot runtime patches to qfluentwidgets behaviours that have no public
  # configuration knob (e.g. the drop-shadow halo around ComboBox popups).
  from ui import qfluent_patches as _qf_patches
  _qf_patches.apply()

  # First-run onboarding. Inline; reuses the QApplication created above.
  just_onboarded = False
  if not config.onboarding_done():
    logger.info("No saved config found — running onboarding dialog")
    from ui.onboarding_dialog import run_onboarding
    if not run_onboarding(config, is_initial=True):
      logger.info("Onboarding cancelled — exiting")
      sys.exit(0)
    # Reload to pick up any values the dialog wrote
    config = Config()
    just_onboarded = True

  # Probe CUDA only when the local backend will actually be used.
  if _will_local_backend_be_used(config):
    cuda_available = check_cuda_availability()
    if not cuda_available:
      logger.info("CUDA is not available. Using CPU for transcription.")
  else:
    logger.info(
        f"Skipping CUDA probe — priority={config.backend_priority}, "
        "local backend will not be active."
    )

  from services.audio_writer import AudioWriter
  from services.ui_bridge import UIBridge
  from tray_preparing.tray_placing import setup_tray, get_resource_path
  from ui.history_manager import HistoryManager
  from ui.main_window import MainWindow
  from ui.rec_indicator import RecordingIndicator
  from ui.taskbar_overlay import TaskbarOverlay

  try:
    ui_bridge = UIBridge()
    history_manager = HistoryManager()

    audio_writer = AudioWriter(config, ui_bridge, history_manager)

    logger.info("Omni Verte application started.")
    logger.info(
        f"Active backend: {audio_writer.transcription_backend} "
        f"(model: {audio_writer.whisper_model_name})"
    )

    if audio_writer.activation_mode == 'keyboard':
      logger.info(f"Press the {audio_writer.activation_key} key for voice input.")
    else:
      logger.info(f"Press the {audio_writer.mouse_activation_button} mouse button for voice input.")

    # Floating indicator — session/model state pushed via UIBridge signals; the
    # live mic level is polled from ui_bridge.audio_level (a plain field written
    # by the audio callback), keeping the realtime audio thread off Qt.
    rec_indicator = RecordingIndicator(level_provider=lambda: ui_bridge.audio_level)
    show_floating = (config.get("SHOW_FLOATING_INDICATOR", "true") or "true").lower() == "true"
    rec_indicator.set_enabled(show_floating)
    ui_bridge.status_changed.connect(rec_indicator.on_status)
    ui_bridge.model_state_changed.connect(rec_indicator.on_model_state)
    ui_bridge.language_changed.connect(rec_indicator.on_language_changed)
    ui_bridge.floating_indicator_toggled.connect(rec_indicator.set_enabled)

    # Main window — hidden by default; user opens it from the tray.
    icon_path = get_resource_path("favicon.ico")
    main_window = MainWindow(
        ui_bridge=ui_bridge,
        history_manager=history_manager,
        openai_client=audio_writer.client,
        config=config,
        icon_path=icon_path,
    )

    # Taskbar overlay — only meaningful while main_window is visible (a hidden
    # window has no taskbar button). Silent no-op when window is hidden.
    overlay = TaskbarOverlay()

    def _on_status_for_overlay(status: str):
      try:
        hwnd = int(main_window.winId()) if main_window.isVisible() else 0
      except Exception:
        hwnd = 0
      overlay.set_overlay(hwnd, status if status in ("recording", "processing") else None)

    ui_bridge.status_changed.connect(_on_status_for_overlay)

    # Tray menu → main window. Connected via Qt signal so the show happens on
    # the GUI thread even though tray callbacks run on the pystray thread.
    ui_bridge.show_window_requested.connect(main_window.show_and_focus)

    # Tray / main-window gear → settings, opened IN-PROCESS in this same Qt
    # event loop. The old design spawned `OmniVerte --settings` as a
    # separate process; from the onefile PyInstaller build that re-extracted
    # the whole bundle (~30s) on every open. Here the modules are already warm
    # and the loop is already running, so the window appears instantly.
    #
    # `settings_holder` keeps the single live instance plus an optional pre-built
    # "spare" that waits in the wings. Requests from any source raise the live
    # window instead of creating a second — the hard single-window guarantee. The
    # slots run on the GUI thread because the signal is emitted from pystray's
    # thread via a queued connection.
    #
    # "Spare in the wings": constructing a SettingsWindow (7 pages + a per-page
    # load_from(), where the glossary page reads glossary.json off disk) is the
    # visible cost on open, not the module import. So we build a ready, hidden
    # instance during idle (see the prebuild scheduling near app.exec) and again
    # after each close — keeping the "fresh instance per open" semantics while
    # moving the build cost off the click. Opening then just shows the spare.
    from PySide6.QtCore import QMetaObject, Qt as _Qt, QTimer as _QTimer

    settings_holder: dict[str, object] = {"window": None, "spare": None}

    def _on_saved():
      try:
        config.reload()
      except Exception as e:
        logger.warning(f"Config reload after settings save failed: {e}")
      try:
        # Adopt the just-saved UI language BEFORE anything re-renders. Same
        # ordering rule as the transcription reload below: every sink reached by
        # settings_saved.emit() (notably the tray's full menu rebuild) must see
        # the new locale, so the catalog switch has to land first.
        #
        # set_locale returns True only on a real change, so an unrelated save
        # costs nothing and fires nothing. "" means auto — only a fresh install
        # still has it, and onboarding freezes it into an explicit value.
        lang = (config.get("UI_LANGUAGE") or "").strip().lower() or i18n.detect_system_locale()
        if i18n.set_locale(lang):
          logger.info(f"UI language switched to {lang!r}")
          ui_bridge.language_changed.emit(lang)
      except Exception as e:
        logger.warning(f"UI language switch after settings save failed: {e}")
      try:
        # Pick up edited glossary lists on the live voice path without a restart.
        audio_writer.glossary.reload()
        audio_writer.apply_entitlement()  # re-cap to the current tier
      except Exception as e:
        logger.warning(f"Glossary reload after settings save failed: {e}")
      try:
        # Re-register hotkeys / mouse hook so a changed activation key or mode
        # takes effect immediately instead of only on the next launch.
        audio_writer.reload_activation_settings()
      except Exception as e:
        logger.warning(f"Activation reload after settings save failed: {e}")
      try:
        # Re-resolve the transcription backend/model/clients from the just-saved
        # config so a changed priority, model or API key takes effect live.
        # Settings is the source of truth — this overrides any in-session tray
        # pick. Must run BEFORE settings_saved.emit() so the tray menu rebuild
        # reads the new active backend. Refresh the main window's OpenAI client
        # too (it holds its own reference) so the text buttons re-enable.
        audio_writer.reload_transcription_settings()
        main_window.set_openai_client(audio_writer.client)
      except Exception as e:
        logger.warning(f"Transcription reload after settings save failed: {e}")
      ui_bridge.settings_saved.emit()

    def _build_settings_window():
      """Construct a fully-wired but NOT-yet-shown SettingsWindow. Used both for
      the idle pre-build and as a fallback when a click beats the prebuild."""
      from PySide6.QtCore import Qt as _Qt
      from ui.settings_window import SettingsWindow

      # Pass the bridge so the license page can broadcast entitlement_changed
      # live (badge + glossary cap re-apply) without an app restart.
      window = SettingsWindow(config, is_initial=False, ui_bridge=ui_bridge)
      # Let Qt delete the window after close (the destroyed handler, wired at
      # open time, clears our handle and queues the next spare).
      window.setAttribute(_Qt.WA_DeleteOnClose, True)
      window.saved.connect(_on_saved)
      # Repaint the window live if the theme is toggled from the main window.
      # Qt auto-disconnects when the window is deleted. Connecting here means a
      # spare built before a theme toggle still repaints correctly.
      ui_bridge.theme_changed.connect(window.apply_theme)
      # Deliberately NOT connected to ui_bridge.language_changed, unlike the
      # theme above. A theme is pure styling and repaints in place; language
      # changes text, and the window's text is resolved once per page build. The
      # save path already destroys this window and builds a fresh spare under
      # the new locale (_on_save → saved.emit → close → _on_settings_closed →
      # prebuild), so it is REPLACED rather than retranslated. Wiring a
      # retranslate here would be a second, rottable copy of that truth.
      return window

    def _prebuild_settings_window():
      """Build a spare during idle if there isn't already one (and nothing open)."""
      if settings_holder["window"] is not None or settings_holder["spare"] is not None:
        return
      try:
        settings_holder["spare"] = _build_settings_window()
        logger.info("Settings window pre-built (spare ready).")
      except Exception as e:
        logger.warning(f"Settings pre-build failed (non-fatal): {e}")

    def _invalidate_settings_spare(_lang=""):
      """Discard a pre-built spare after a language change and re-arm the idle
      prebuild, so the next open is both fresh and instant.

      A spare resolved its labels at BUILD time; nothing re-reads them, so one
      built under the old locale would open visibly half-translated. Via the
      settings save this is a no-op — _open_settings_window already took the
      spare, so it is None while a window is open, and the replacement is built
      after the switch. It exists as a hard guarantee for any future
      non-settings language source (e.g. a tray language submenu), where a stale
      spare WOULD be sitting in the wings.
      """
      spare = settings_holder["spare"]
      if spare is None:
        return
      settings_holder["spare"] = None
      spare.deleteLater()
      logger.info("Discarded settings spare built under the previous UI language.")
      _QTimer.singleShot(0, _prebuild_settings_window)

    ui_bridge.language_changed.connect(_invalidate_settings_spare)

    def _on_settings_closed():
      settings_holder["window"] = None
      # Rebuild the spare once Qt has finished tearing down the closed window, so
      # the NEXT open is instant too. singleShot(0) keeps the close event snappy.
      _QTimer.singleShot(0, _prebuild_settings_window)

    def _refresh_settings_from_config(window):
      """Re-sync the (possibly pre-built / previously-opened) window's widgets
      from the live config so an in-session tray change is reflected before the
      user edits. Non-fatal: a refresh failure must never block opening."""
      try:
        window.reload_from_config()
      except Exception as e:
        logger.warning(f"Settings window refresh from config failed: {e}")

    def _open_settings_window(page_id=None):
      existing = settings_holder["window"]
      if existing is not None:
        _refresh_settings_from_config(existing)
        existing.show()
        existing.raise_()
        existing.activateWindow()
        if page_id:
          existing.show_page(page_id)
        return

      # Take the spare from the wings, or build one on the spot if a click beat
      # the idle prebuild.
      window = settings_holder["spare"]
      settings_holder["spare"] = None
      if window is None:
        window = _build_settings_window()

      settings_holder["window"] = window
      window.destroyed.connect(lambda *_: _on_settings_closed())
      _refresh_settings_from_config(window)
      window.show()
      window.raise_()
      window.activateWindow()
      if page_id:
        window.show_page(page_id)
      # Center the settings window over the main window so the two are aligned
      # to each other, regardless of where Windows would have cascaded it.
      # Deferred to the next event-loop tick: on Windows the OS emits its own
      # placement after show(), and a synchronous move() here would be silently
      # overwritten by it (the window just stays cascaded, no visible jump).
      # main_window is centred at construction, so this also keeps settings
      # roughly screen-centred.
      _QTimer.singleShot(0, lambda w=window: w.align_over(main_window))

    ui_bridge.settings_requested.connect(lambda: _open_settings_window())

    # Main-window tier badge → open Settings deep-linked to the License page.
    from ui.settings_pages import LicensePage
    ui_bridge.license_requested.connect(
        lambda: _open_settings_window(LicensePage.PAGE_ID)
    )

    # A license activation/clear (license settings page) refreshed the
    # entitlement cache — re-cap the glossary on the live voice path. The tray
    # callback thread is fine here; set_active_cap only touches in-memory state.
    ui_bridge.entitlement_changed.connect(audio_writer.apply_entitlement)

    # Tray menu → quit. Stop daemon threads gracefully where we can.
    def _on_quit():
      # Runs on the pystray thread (quit_requested is emitted from there and the
      # slot is a plain function → direct connection). That thread stays alive
      # even when the GUI thread wedges, which is exactly what we rely on below.
      #
      # The GUI thread can get stuck in a native modal/hook deadlock — observed
      # when Settings is open and focus is on another app: a global low-level
      # keyboard hook (hard-capture hotkeys) + cross-process window activation
      # can leave the main thread blocked in Win32 land, no longer pumping the Qt
      # event queue. When that happens NOTHING posted to the GUI thread runs
      # (neither app.quit() nor a queued meta-call), so exec() never returns and
      # the process hangs forever. We therefore (1) ask for a graceful quit, and
      # (2) arm a watchdog on this (live) thread that force-exits if the graceful
      # path doesn't complete promptly. On a clean shutdown the interpreter tears
      # down first and kills this daemon watchdog before it ever fires.
      logger.info("Quit requested — shutting down")

      import threading
      import time

      def _force_exit_watchdog():
        time.sleep(2.5)
        logger.warning("Graceful quit did not complete — forcing process exit")
        for stream in (sys.stdout, sys.stderr):
          try:
            stream.flush()
          except Exception:
            pass
        os._exit(0)

      threading.Thread(
          target=_force_exit_watchdog, name="quit-watchdog", daemon=True
      ).start()

      try:
        audio_writer.shutdown()
      except Exception as e:
        logger.warning(f"Input hook teardown failed (continuing): {e}")
      try:
        overlay.cleanup()
      except Exception:
        pass
      # Best-effort graceful exit. If the GUI thread is healthy this returns the
      # process cleanly within milliseconds (the watchdog never fires); if it's
      # wedged, the watchdog above guarantees termination.
      QMetaObject.invokeMethod(app, "quit", _Qt.QueuedConnection)

    ui_bridge.quit_requested.connect(_on_quit)

    # Pystray icon + menu (in its own thread).
    setup_tray(audio_writer, ui_bridge, config)

    # Install keyboard / mouse hooks. AudioWriter is now signal-driven, so all
    # UI interaction from the hook thread goes through ui_bridge.
    audio_writer.press_and_talk()

    # Now that every status/model-state sink (tray, floating indicator, main
    # window) is connected to ui_bridge, kick off backend initialization in the
    # background. For the local backend this downloads/loads the Whisper model —
    # the slow first-run step we deliberately moved off the constructor so the
    # window/tray appear instantly and the user sees a "Loading model…" cue
    # instead of a frozen, invisible app. Cloud backends report ready at once.
    audio_writer.init_backend_async()

    # Keep the cached license token fresh in the background. This is the only
    # licensing network activity: it re-validates against the Worker on startup
    # and then daily, dropping to Free if the license was revoked/refunded and
    # silently keeping the cached token if the server is unreachable. It's a
    # guarded daemon thread and a no-op unless a token exists and the API URL is
    # configured, so it can never block startup or crash the app. Started here,
    # after every entitlement_changed sink (tray, main-window badge, audio
    # writer) is connected, so a revoke is reflected everywhere live.
    try:
      from licensing import start_monitor
      start_monitor(ui_bridge)
    except Exception:
      logger.exception("could not start the license monitor (continuing)")

    # On the very first run (right after onboarding) show the main window so
    # the user actually sees the app — otherwise it lives in the tray and they
    # have to discover the icon themselves.
    if just_onboarded:
      main_window.show_and_focus()

    # Pre-build the settings window so the FIRST Settings open is instant. This
    # goes further than warming the import: it constructs the whole window (the
    # Fluent widget set imports cold at ~1.5-2s, then 7 pages + per-page
    # load_from() with the glossary page reading glossary.json off disk). All of
    # that would otherwise land on the first open as a visible stall. We pay it
    # here instead, shortly after startup while the user is idle, via a one-shot
    # timer; _on_settings_closed re-arms a spare after each close so every open
    # stays instant.
    #
    # Deliberately on the GUI thread (a QTimer callback), NOT a worker thread:
    # constructing Qt widgets creates QObjects, and those must take their
    # affinity from the GUI thread — building on a daemon thread that then exits
    # is a subtle source of cross-thread Qt bugs. The build is a one-time,
    # off-click cost; the tray menu stays responsive (pystray runs on its own
    # thread), and the small delay lets the main window paint first.
    _QTimer.singleShot(1000, _prebuild_settings_window)

    sys.exit(app.exec())

  except Exception as e:
    logger.error(f"Error initializing application: {e}", exc_info=True)
    sys.exit(1)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Omni Verte voice-to-text")
  parser.add_argument(
      "--settings",
      action="store_true",
      help="Open the settings dialog only and exit (used by tray)."
  )
  args = parser.parse_args()

  if args.settings:
    # No mutex / no main app — just the dialog. Used by tray subprocess.
    # Tag this process with the same AUMID so taskbar groups it with the main
    # app (and overlay icons attach to the same logical app).
    # Exit code: 0 = saved, 1 = cancelled — tray reads this to decide whether
    # to show the "restart to apply" notification.
    _set_app_user_model_id()
    saved = run_settings_dialog()
    sys.exit(0 if saved else 1)

  # Single-instance check via Windows Mutex.
  mutex = CreateMutex(None, False, MUTEX_NAME)
  last_error = GetLastError()
  if last_error == 183:  # ERROR_ALREADY_EXISTS
    logger.info("Application is already running. Exiting.")
    sys.exit(0)

  try:
    main()
  finally:
    CloseHandle(mutex)

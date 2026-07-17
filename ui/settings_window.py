# file: ui/settings_window.py

"""
Settings / onboarding window — light Fluent palette, left-sidebar navigation.

Replaces the old QDialog-based onboarding_dialog. Same launch contract:

    run_settings(config, is_initial) -> bool

is used by both the `--settings` subprocess (called from the tray) and the
first-run bootstrap in OmniVerte.py. Returns True on save, False on
cancel — exactly like the previous QDialog.exec() result.

Window size, palette, and titleBar match the main window so the two feel
like one cohesive app.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from PySide6.QtCore import QEventLoop, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    DotInfoBadge,
    FluentIcon as FIF,
    FluentWindow,
    InfoBadgePosition,
    InfoBar,
    InfoBarPosition,
    NavigationItemPosition,
    PrimaryPushButton,
    PushButton,
    Theme,
    setTheme,
)

from i18n import t
from services.config_store import Config
from ui import style
from ui.style import (
    SP_LG,
    SP_MD,
    settings_qss,
)
from ui.settings_pages import (
    AboutPage,
    BasePage,
    CustomStylePage,
    GeneralPage,
    GlossaryPage,
    LanguagesPage,
    LicensePage,
    TranscriptionPage,
)

logger = logging.getLogger(__name__)


class SettingsWindow(FluentWindow):
    """Settings window: sidebar nav, page area, persistent footer action bar."""

    saved = Signal()
    cancelled = Signal()

    def __init__(self, config: Config, is_initial: bool = False, ui_bridge=None):
        super().__init__()
        self._config = config
        self._is_initial = is_initial
        self._ui_bridge = ui_bridge
        self._result_saved = False

        # Match the saved palette (the app sets it at startup; honour it here too
        # in case the settings window is built before the main window).
        style.set_theme(config.get("THEME") or "light")
        setTheme(Theme.DARK if style.is_dark() else Theme.LIGHT)

        # Window basics — same footprint as the main window so the two feel
        # like one app.
        self.setWindowTitle(
            t("settingswindow.title.setup") if is_initial
            else t("settingswindow.title.settings")
        )
        self.resize(1040, 820)
        self.setMinimumSize(860, 680)

        icon_path = self._find_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        # Apply our QSS to all descendants. Setting on the window itself works
        # because Qt cascades stylesheet rules unless objectName-scoped.
        self.setObjectName("settingsRoot")
        self.setStyleSheet(settings_qss(style.palette()))

        self._pages: list[BasePage] = []
        self._build_pages()
        self._build_action_bar()
        self._load_all()

        # First-run onboarding: land on the keys page and cue the user once the
        # window is shown (see showEvent — the glow needs a painted widget).
        self._onboarding_page = None
        self._did_onboard_cue = False
        self._lang_badge = None
        if self._is_initial:
            self._onboarding_page = self._page_by_id[TranscriptionPage.PAGE_ID]
            self._switch_to(self._onboarding_page)
            # Clear the Languages attention dot the moment the user opens it.
            self.stackedWidget.currentChanged.connect(self._maybe_clear_lang_badge)

    def apply_theme(self, name: str | None = None):
        """Repaint live when the theme is toggled elsewhere (main window). The
        active palette is global, so re-reading it and re-applying our sheet +
        the Fluent theme is enough; Fluent widgets repaint themselves."""
        if name:
            style.set_theme(name)
        setTheme(Theme.DARK if style.is_dark() else Theme.LIGHT)
        self.setStyleSheet(settings_qss(style.palette()))

    # ---------- construction ----------

    def align_over(self, other):
        """Center this window over another window's frame, so the two sit
        concentric. Defer this to the event loop AFTER show() (e.g. via
        QTimer.singleShot(0, ...)) — on Windows the OS sends its own placement
        message after show(), which would otherwise overwrite a synchronous
        move()."""
        try:
            ref = other.frameGeometry()
        except Exception:
            return
        frame = self.frameGeometry()
        frame.moveCenter(ref.center())
        self.move(frame.topLeft())

    def _find_icon_path(self) -> Optional[str]:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(here, "favicon.ico")
        return path if os.path.exists(path) else None

    def _build_pages(self):
        general = GeneralPage()
        transcription = TranscriptionPage()
        languages = LanguagesPage()
        custom = CustomStylePage()
        glossary = GlossaryPage()
        license_page = LicensePage(ui_bridge=self._ui_bridge)
        about = AboutPage()

        # addSubInterface uses page.objectName() as the navigation key — the
        # base class sets it to PAGE_ID. The third argument is display text only,
        # so translating it cannot affect routing (`show_page`/`_switch_to` go
        # through PAGE_ID too).
        self.addSubInterface(general, FIF.SETTING, t("settingswindow.nav.general"))
        self.addSubInterface(transcription, FIF.MICROPHONE, t("settingswindow.nav.transcription"))
        self.addSubInterface(languages, FIF.LANGUAGE, t("settingswindow.nav.languages"))
        self.addSubInterface(custom, FIF.BRUSH, t("settingswindow.nav.custom_style"))
        self.addSubInterface(glossary, FIF.DICTIONARY, t("settingswindow.nav.glossary"))
        self.addSubInterface(
            license_page, FIF.CERTIFICATE, t("settingswindow.nav.license"),
            NavigationItemPosition.BOTTOM,
        )
        self.addSubInterface(
            about, FIF.INFO, t("settingswindow.nav.about"),
            NavigationItemPosition.BOTTOM,
        )

        self._pages = [general, transcription, languages, custom, glossary, license_page, about]
        self._page_by_id: dict[str, BasePage] = {p.PAGE_ID: p for p in self._pages}

    def _build_action_bar(self):
        """Persistent footer with Save / Cancel / Use Local Only buttons.

        The bar is a child of the FluentWindow and gets repositioned in
        resizeEvent so it floats over the content area's bottom edge. We don't
        re-layout FluentWindow's internal hBoxLayout because that interacts
        with the sidebar transitions in surprising ways — overlaying is the
        cleanest of the options I tried.
        """
        self._action_bar = QFrame(self)
        self._action_bar.setObjectName("actionBar")
        self._action_bar.setFixedHeight(72)

        layout = QHBoxLayout(self._action_bar)
        layout.setContentsMargins(SP_LG, SP_MD, SP_LG, SP_MD)
        layout.setSpacing(12)

        if self._is_initial:
            self._local_only_btn = PushButton(t("settingswindow.local_only"))
            self._local_only_btn.clicked.connect(self._on_use_local_only)
            layout.addWidget(self._local_only_btn)
        else:
            self._local_only_btn = None

        layout.addStretch(1)

        self._cancel_btn = PushButton(t("common.cancel"))
        self._cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self._cancel_btn)

        # Qt reads a lone "&" in a button label as a mnemonic marker, so a label
        # that wants a literal "&" has to double it — hence English's
        # "Save && Apply". That is a property of the TEXT, not of this call site:
        # a locale whose wording has no ampersand (Russian's "Сохранить и
        # применить") correctly carries none, and adding "&&" there would print
        # a stray "&". Translators write the label; Qt's escaping follows from it.
        save_label = (
            t("settingswindow.save_start") if self._is_initial
            else t("settingswindow.save_apply")
        )
        self._save_btn = PrimaryPushButton(save_label)
        self._save_btn.clicked.connect(self._on_save)
        layout.addWidget(self._save_btn)

        self._action_bar.raise_()
        self._position_action_bar()

    def _position_action_bar(self):
        # Anchor to bottom; span from end of nav sidebar to right edge.
        nav_w = self.navigationInterface.width() if hasattr(self, "navigationInterface") else 0
        bar_h = self._action_bar.height()
        self._action_bar.setGeometry(
            nav_w,
            self.height() - bar_h,
            max(0, self.width() - nav_w),
            bar_h,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_action_bar"):
            self._position_action_bar()

    def showEvent(self, event):
        super().showEvent(event)
        # Fire the onboarding cue once, after the window is actually visible —
        # the glow effect and nav badge need painted/laid-out widgets. Small
        # delay lets the page and sidebar finish their first layout.
        if self._is_initial and not self._did_onboard_cue:
            self._did_onboard_cue = True
            QTimer.singleShot(300, self._run_onboarding_cue)

    def _run_onboarding_cue(self):
        """Draw the eye to the API-key fields and to the Languages tab."""
        self._onboarding_page.enter_initial_setup()
        self._show_languages_badge()

    def _show_languages_badge(self):
        """Attention dot on the Languages sidebar item until the user visits it."""
        try:
            nav_item = self.navigationInterface.widget(LanguagesPage.PAGE_ID)
            if nav_item is not None:
                self._lang_badge = DotInfoBadge.attension(
                    parent=self.navigationInterface,
                    target=nav_item,
                    position=InfoBadgePosition.NAVIGATION_ITEM,
                )
                self._lang_badge.show()
        except Exception as e:
            logger.warning(f"Could not show Languages onboarding badge: {e}")

    def _maybe_clear_lang_badge(self, *_):
        if self._lang_badge is None:
            return
        if self.stackedWidget.currentWidget() is self._page_by_id.get(LanguagesPage.PAGE_ID):
            self._lang_badge.hide()
            self._lang_badge.deleteLater()
            self._lang_badge = None

    # ---------- data flow ----------

    def _load_all(self):
        for page in self._pages:
            try:
                page.load_from(self._config)
            except Exception as e:
                logger.warning(f"Page {page.PAGE_ID} failed to load: {e}", exc_info=True)

    def reload_from_config(self) -> None:
        """Re-read the shared live config into every page. Called on open so an
        in-session change made via the tray (which writes the same Config) is
        reflected before the user edits/saves — otherwise a pre-built spare
        window would show stale values and a save would revert the tray change."""
        self._load_all()

    def _switch_to(self, page: BasePage):
        # FluentWindow uses each page's objectName as its nav key — switchTo
        # is the documented way to activate it programmatically.
        self.switchTo(page)

    def show_page(self, page_id: str) -> None:
        """Activate the page with the given PAGE_ID (deep-link from elsewhere)."""
        page = self._page_by_id.get(page_id)
        if page is not None:
            self._switch_to(page)

    # ---------- actions ----------

    def _on_save(self):
        for page in self._pages:
            err = page.validate()
            if err:
                self._switch_to(page)
                self._show_error(err)
                return

        for page in self._pages:
            try:
                page.apply_to(self._config)
            except Exception as e:
                logger.error(f"Page {page.PAGE_ID} failed to apply: {e}", exc_info=True)
                self._show_error(t("settingswindow.error.apply_failed", page=page.PAGE_TITLE, error=e))
                return

        if self._is_initial:
            self._config.mark_onboarding_done()

        self._result_saved = True
        logger.info("Settings saved")
        self.saved.emit()
        self.close()

    def _on_use_local_only(self):
        # Skip-everything shortcut: force priority = ['local'] and save.
        # Other fields (custom style, hotkey, etc.) still get applied so the
        # user can pre-fill them before clicking this shortcut.
        for page in self._pages:
            try:
                page.apply_to(self._config)
            except Exception:
                pass
        self._config.set_backend_priority(["local"])
        if self._is_initial:
            self._config.mark_onboarding_done()
        self._result_saved = True
        logger.info("Onboarding skipped via Use Local Only")
        self.saved.emit()
        self.close()

    def _on_cancel(self):
        self._result_saved = False
        self.cancelled.emit()
        self.close()

    def closeEvent(self, event):
        # Window-frame close (X) follows the same path as the Cancel button
        # unless save already flipped the flag.
        if not self._result_saved:
            self.cancelled.emit()
        super().closeEvent(event)

    def _show_error(self, message: str):
        InfoBar.error(
            title=t("settingswindow.error.title"),
            content=message,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self,
        )


# ---------- module-level entry point ----------

def run_settings(config: Config, is_initial: bool = False, ui_bridge=None) -> bool:
    """
    Show the settings window modally. Returns True if the user saved.

    Used by:
      - OmniVerte.py initial-run bootstrap (`is_initial=True`)
      - OmniVerte.py `--settings` subprocess called from the tray

    ``ui_bridge`` is None on the subprocess path (no live main window to notify);
    a license activation there is picked up when the main process reloads.
    """
    app = QApplication.instance() or QApplication(sys.argv)

    window = SettingsWindow(config, is_initial=is_initial, ui_bridge=ui_bridge)

    # FluentWindow is not a QDialog, so we run a local QEventLoop and exit
    # when the window emits saved/cancelled (or closes via the X). This keeps
    # the bool-returning contract intact for the existing callers.
    loop = QEventLoop()

    def _finish():
        if loop.isRunning():
            loop.quit()

    window.saved.connect(_finish)
    window.cancelled.connect(_finish)

    window.show()
    window.raise_()
    window.activateWindow()
    loop.exec()

    return window._result_saved

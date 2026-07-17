# file: ui/settings_pages/license_page.py

"""
License page — two modes, selected by the build flag ``PRO_SALES_OPEN``
(``licensing/config.py``):

  - **Waitlist mode** (``PRO_SALES_OPEN = False``): Pro is visible but
    not for sale from inside the app (Paddle only approves a live public
    product). The page shows what Pro unlocks and a single **Join the Pro
    waitlist** button that opens the public landing page in the browser. There
    is NO token field, no email form, and no network call — lead capture lives
    only on the landing page (roadmap Phase 1C).

  - **Activation mode** (``PRO_SALES_OPEN = True``, current): the real
    key-activation UI. The user pastes the **license key** (``OVRT-…``); the app
    exchanges it for a signed token against the Worker (``activate_with_key`` →
    ``/activate``) on a background thread, so the window never freezes if the
    server is slow or down. The token lives in the Credential Manager via
    ``licensing`` (same vault as the API keys); we never write it to
    ``config.env``. Activation/clear take effect immediately
    (``refresh_entitlement`` + an ``entitlement_changed`` broadcast) so the tier
    badge and feature gates update without an app restart.

    The card has three states (``_apply_state``): **not activated** (key field +
    Activate), **activated** (no field at all — the key is in the vault and the
    Status card echoes it masked; offers "Use a different key" / "Deactivate"),
    and **editing** (field + Cancel/Activate). Leaving the field open and full
    of the accepted key after a successful activation reads as "nothing
    happened"; a settled card is the feedback.

The Pro benefit list (``pro_benefits``) is on whichever card the mode shows, in
every state — it is what the page hint's "see below" points at. Before
activation it is the pitch; after, it is the answer to "what did I pay for?",
which is otherwise nowhere in the app.

Testers don't need a key: ``OMNIVERTE_DEV_TIER=pro`` unlocks Pro locally.
"""

from __future__ import annotations

import platform
import threading
from typing import Optional

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qfluentwidgets import (
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PrimaryPushButton,
    PushButton,
)

from i18n import t
from licensing.config import PRO_SALES_OPEN, WAITLIST_URL
from services.config_store import Config
from .base import BasePage, make_section_card

# Bullet prefix for the benefit lines — layout, not language, so it stays out of
# the catalog and every locale gets the same indent.
_BULLET = "  –  "


def pro_benefits() -> list[str]:
    """What a Pro license unlocks, one line per benefit, in the active locale.

    Sourced from the Free/Pro boundary (licensing.features); shown on whichever
    card is the page's Pro pitch — the waitlist card, or the key card in
    activation mode. A function rather than the module-level constant this used
    to be: a tuple of `t()` results would be resolved once at import and pin the
    list to whatever locale was active then, which no rebuild of the page undoes.
    """
    return [
        _BULLET + t("license.benefit.glossary"),
        _BULLET + t("license.benefit.custom_styles"),
        _BULLET + t("license.benefit.presets"),
        _BULLET + t("license.benefit.history"),
        _BULLET + t("license.benefit.builds"),
    ]


def _benefits_text(lead: str) -> str:
    """The benefit list under a lead-in line ("Pro unlocks:" and friends)."""
    return lead + "\n" + "\n".join(pro_benefits())


def _benefits_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("cardSectionHint")
    lbl.setWordWrap(True)
    return lbl


def _mask_key(key: str) -> str:
    """Show only the last group of a license key in the status line."""
    key = key.strip()
    if len(key) <= 4:
        return "…"
    return "…" + key[-4:]


def _message_for(exc: Exception) -> str:
    """Turn an activation failure into a one-line, user-facing message.

    The error *kinds* and *codes* branched on here ("network", "empty_key",
    "seat_limit", the `license_` prefix, the HTTP statuses) are wire data from
    the Worker and are never translated — only the messages they resolve to are.
    """
    from licensing import LicenseApiError, LicenseError

    if isinstance(exc, LicenseApiError):
        if exc.kind == "network":
            return t("license.error.network")
        if exc.kind == "local":
            if exc.error == "empty_key":
                return t("license.error.empty_key")
            if exc.error == "no_fingerprint":
                return t("license.error.no_fingerprint")
            return t("license.error.local")
        # kind == "http"
        err = (exc.error or "").lower()
        if exc.status == 404 or err == "invalid_key":
            return t("license.error.invalid_key")
        if exc.status == 409 or err == "seat_limit":
            return t("license.error.seat_limit")
        if exc.status == 429:
            return t("license.error.rate_limit")
        if err.startswith("license_"):
            return t("license.error.inactive")
        # A 4xx with no error string of ours isn't a verdict on the license — it
        # comes from something between us and the Worker (a WAF, a proxy). Say so
        # instead of accusing the user's key.
        return t("license.error.refused")

    if isinstance(exc, LicenseError):
        return t("license.error.unverified")
    return t("license.error.generic")


class LicensePage(BasePage):
    PAGE_ID = "settings-license"
    PAGE_TITLE_KEY = "page.license.title"
    PAGE_HINT_KEY = "page.license.hint"

    # Carries the result of a background activation back to the UI thread.
    # Payload is the Entitlement on success or the Exception on failure.
    _activate_finished = Signal(object)

    def __init__(self, parent=None, ui_bridge=None):
        # Stash the bridge before BasePage.__init__ triggers build().
        self._ui_bridge = ui_bridge
        # Only the activation branch creates a key field; guard against the
        # waitlist branch touching it.
        self.key_edit = None
        # True while an activated user is typing a replacement key.
        self._editing = False
        super().__init__(parent)
        self._activate_finished.connect(self._on_activate_finished)

    def build(self, content_layout: QVBoxLayout) -> None:
        # --- current status (both modes) ---
        status_card, status_body = make_section_card(
            t("license.status.title"),
            t("license.status.hint"),
        )
        # An em-dash placeholder until _refresh_status fills it in — punctuation,
        # not copy, so it needs no catalog entry.
        self.status_label = QLabel("—")
        self.status_label.setObjectName("rowLabel")
        status_body.addWidget(self.status_label)
        content_layout.addWidget(status_card)

        if PRO_SALES_OPEN:
            self._build_activation(content_layout)
        else:
            self._build_waitlist(content_layout)

    # ---------- waitlist mode (PRO_SALES_OPEN = False) ----------

    def _build_waitlist(self, content_layout: QVBoxLayout) -> None:
        card, body = make_section_card(
            t("license.waitlist.title"),
            t("license.waitlist.hint"),
        )

        body.addWidget(_benefits_label(_benefits_text(t("license.waitlist.unlocks"))))

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        self.waitlist_btn = PrimaryPushButton(t("license.waitlist.button"))
        self.waitlist_btn.clicked.connect(self._on_waitlist)
        btn_row.addWidget(self.waitlist_btn)
        btn_row.addStretch(1)

        row_wrap = QWidget()
        row_wrap.setLayout(btn_row)
        body.addWidget(row_wrap)

        content_layout.addWidget(card)

    # ---------- activation mode (PRO_SALES_OPEN = True) ----------

    def _build_activation(self, content_layout: QVBoxLayout) -> None:
        # No hint passed to make_section_card: the card's description changes
        # with the state below, and the stock hint label isn't reachable once
        # built — so we own it here.
        card, body = make_section_card(t("license.key.title"))

        self.activation_hint = QLabel()
        self.activation_hint.setObjectName("cardSectionHint")
        self.activation_hint.setWordWrap(True)
        body.addWidget(self.activation_hint)

        # The Free/Pro boundary, spelled out on the only card this mode shows —
        # otherwise the page hint's "see below" points at nothing, and an
        # activated user never gets told what they bought. Text is state-
        # dependent (a pitch before activation, an inventory after), so
        # `_apply_state` owns it; here it just reserves the slot.
        self.benefits_label = _benefits_label("")
        body.addWidget(self.benefits_label)

        self.key_edit = LineEdit()
        # Not catalogued: this is the literal shape of a license key (product
        # prefix + hex groups), the same in every locale. Translating it would
        # show the user a pattern their key does not match.
        self.key_edit.setPlaceholderText("OVRT-XXXX-XXXX-XXXX-XXXX")
        self.key_edit.setClearButtonEnabled(True)
        self.key_edit.returnPressed.connect(self._on_activate)
        body.addWidget(self.key_edit)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(12)

        self.buy_btn = PushButton(t("license.button.buy"))
        self.buy_btn.clicked.connect(self._on_waitlist)
        btn_row.addWidget(self.buy_btn)

        self.change_btn = PushButton(t("license.button.change_key"))
        self.change_btn.clicked.connect(self._on_change_key)
        btn_row.addWidget(self.change_btn)

        self.cancel_btn = PushButton(t("common.cancel"))
        self.cancel_btn.clicked.connect(self._on_cancel_edit)
        btn_row.addWidget(self.cancel_btn)

        btn_row.addStretch(1)

        # Deliberately not a PrimaryPushButton: dropping to Free is the
        # destructive path, it shouldn't be the loudest thing on the card.
        self.clear_btn = PushButton(t("license.button.deactivate"))
        self.clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self.clear_btn)

        self.activate_btn = PrimaryPushButton(t("license.button.activate"))
        self.activate_btn.clicked.connect(self._on_activate)
        btn_row.addWidget(self.activate_btn)

        row_wrap = QWidget()
        row_wrap.setLayout(btn_row)
        body.addWidget(row_wrap)

        content_layout.addWidget(card)
        self._apply_state()

    # ---------- activation card state ----------

    def _has_key(self) -> bool:
        """True once a key is stored in the vault (i.e. this machine is activated).

        Keyed off the stored *key*, not the tier: ``OMNIVERTE_DEV_TIER=pro``
        makes a tester Pro with no key, and offering them "Deactivate" would be
        a lie — there'd be nothing to deactivate.
        """
        from licensing import get_license_key

        try:
            return bool(get_license_key())
        except Exception:
            return False

    def _apply_state(self, editing: bool = False) -> None:
        """Show one of three states on the activation card.

        Activated machines get a settled card (no dangling text field): the key
        already lives in the vault and is echoed, masked, in the Status card
        above. Entering another key is a deliberate step behind "Use a different
        key" rather than a field left permanently open.
        """
        if self.key_edit is None:  # waitlist mode — no activation card built
            return

        activated = self._has_key()
        self._editing = editing and activated
        show_entry = not activated or self._editing

        self.key_edit.setVisible(show_entry)
        self.activate_btn.setVisible(show_entry)
        self.buy_btn.setVisible(not activated)
        self.cancel_btn.setVisible(self._editing)
        self.change_btn.setVisible(activated and not self._editing)
        self.clear_btn.setVisible(activated and not self._editing)

        if self._editing:
            self.activation_hint.setText(t("license.hint.editing"))
        elif activated:
            self.activation_hint.setText(t("license.hint.activated"))
        else:
            self.activation_hint.setText(t("license.hint.enter"))

        # Keyed off `activated`, not the editing flag: someone swapping keys
        # still owns Pro, and telling them what it "unlocks" mid-swap would read
        # as if they'd lost it.
        self.benefits_label.setText(_benefits_text(
            t("license.benefits.included") if activated else t("license.benefits.unlocks")
        ))

    def _on_change_key(self) -> None:
        self.key_edit.clear()
        self._apply_state(editing=True)
        self.key_edit.setFocus()

    def _on_cancel_edit(self) -> None:
        self.key_edit.clear()
        self._apply_state(editing=False)

    # ---------- status ----------

    def _refresh_status(self) -> None:
        from licensing import get_entitlement, get_license_key

        try:
            tier = get_entitlement().tier.value
        except Exception:
            tier = "free"
        # The tier name itself is not translated — Free and Pro are what the
        # product is sold as, in every locale (same rule as `common.pro`).
        text = t("license.status.level", tier=tier.capitalize())
        try:
            key = get_license_key()
        except Exception:
            key = None
        if key:
            text += "   " + t("license.status.key", key=_mask_key(key))
        self.status_label.setText(text)

    # ---------- actions ----------

    def _on_waitlist(self) -> None:
        QDesktopServices.openUrl(QUrl(WAITLIST_URL))

    def _on_activate(self) -> None:
        if self.key_edit is None:
            return
        key = self.key_edit.text().strip()
        if not key:
            self._error(t("license.error.empty_key"))
            return

        # The /activate call hits the network — run it off the UI thread so the
        # settings window never freezes, even if the server is slow or down.
        self._set_busy(True)
        label = platform.node() or None

        def _work() -> None:
            from licensing import activate_with_key

            try:
                ent = activate_with_key(key, label)
                self._activate_finished.emit(ent)
            except Exception as exc:  # delivered to the UI thread below
                self._activate_finished.emit(exc)

        threading.Thread(target=_work, name="license-activate", daemon=True).start()

    def _on_activate_finished(self, result: object) -> None:
        self._set_busy(False)
        if isinstance(result, Exception):
            self._error(_message_for(result))
            return
        # Never leave the typed key sitting in the field afterwards: it's in the
        # vault now (or gone), and the Status card echoes it masked.
        if self.key_edit is not None:
            self.key_edit.clear()
        if result is None:
            # Clear path: deactivate_local already cleared + refreshed entitlement.
            self._broadcast()
            self._refresh_status()
            self._apply_state()
            self._success(t("license.toast.cleared"))
            return
        # Activation success: entitlement already refreshed in the worker.
        self._broadcast()
        self._refresh_status()
        self._apply_state()
        self._success(t("license.toast.activated"))

    def _on_clear(self) -> None:
        from licensing import deactivate_local

        # Best-effort seat release + local clear. The network part is swallowed
        # inside deactivate_local, but run it off-thread so a slow server can't
        # freeze the button.
        self._set_busy(True)

        def _work() -> None:
            try:
                deactivate_local()
            finally:
                # Reuse the activation-done channel to hop back to the UI thread;
                # None means "cleared", handled below.
                self._activate_finished.emit(None)

        threading.Thread(target=_work, name="license-clear", daemon=True).start()

    def _set_busy(self, busy: bool) -> None:
        for btn in ("activate_btn", "clear_btn", "buy_btn", "change_btn", "cancel_btn"):
            w = getattr(self, btn, None)
            if w is not None:
                w.setEnabled(not busy)
        if self.key_edit is not None:
            self.key_edit.setEnabled(not busy)

    def _broadcast(self) -> None:
        """Tell the live app (main window badge, glossary cap) to re-apply gates."""
        if self._ui_bridge is not None:
            try:
                self._ui_bridge.entitlement_changed.emit()
            except Exception:
                pass

    # ---------- toasts ----------

    def _success(self, message: str) -> None:
        InfoBar.success(
            title="",
            content=message,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

    def _error(self, message: str) -> None:
        InfoBar.error(
            title="",
            content=message,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self,
        )

    # ---------- Config interface (token lives in keyring, not config.env) ----------

    def load_from(self, config: Config) -> None:
        self._refresh_status()
        # Re-open on the settled state, even if the page was left mid-edit.
        self._apply_state()

    def apply_to(self, config: Config) -> None:
        # Activation/clear happen immediately via the buttons, not on Save.
        pass

    def validate(self) -> Optional[str]:
        return None

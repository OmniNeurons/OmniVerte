# file: ui/qfluent_patches.py

"""
Runtime monkey-patches for qfluentwidgets behaviours that don't expose a clean
configuration knob. Applied once at app startup from OmniVerte.main().

Patches
-------
flat_combo_box_popup
    Kill the drop-shadow halo around ComboBox dropdowns. qfluentwidgets'
    `RoundMenu` (popup base class of `ComboBoxMenu`) reserves 12/8/12/20 px
    of outer layout margin for a soft shadow + applies a QGraphicsDropShadowEffect
    on the inner list view. Combined with WA_TranslucentBackground, that margin
    reads as a large transparent frame around the actual dropdown. We strip the
    effect and collapse the margin so the popup hugs the list — a plain dropdown.
"""

from __future__ import annotations


_applied = False


def apply() -> None:
    """Idempotent. Safe to call multiple times — only the first call patches."""
    global _applied
    if _applied:
        return
    _applied = True
    _flat_combo_box_popup()


def _flat_combo_box_popup() -> None:
    from qfluentwidgets.components.widgets.combo_box import ComboBoxMenu

    _orig_init = ComboBoxMenu.__init__

    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        # Drop the soft shadow that the margin was reserved for.
        try:
            self.view.setGraphicsEffect(None)
        except Exception:
            pass
        # Collapse the outer layout margin so the popup window hugs the list
        # view; the list view paints its own border + rounded corners.
        try:
            self.hBoxLayout.setContentsMargins(1, 1, 1, 1)
        except Exception:
            pass

    ComboBoxMenu.__init__ = _patched_init

# file: ui/onboarding_dialog.py

"""
Thin compatibility shim — the old QDialog-based onboarding has been replaced
by a FluentWindow-based settings window in `ui/settings_window.py`. Callers
(OmniVerte.py bootstrap, --settings subprocess) still import
`run_onboarding` from here, so we re-export the new entry point under the
legacy name.
"""

from ui.settings_window import run_settings as run_onboarding

__all__ = ["run_onboarding"]

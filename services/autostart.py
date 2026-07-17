# file: services/autostart.py

"""
Windows "launch on sign-in" autostart, managed via the per-user registry Run key.

This is the *same* key + value name the installer writes (see
``installer/OmniVerte.iss`` — the ``autostart`` task), so the settings
toggle and the installer manage one shared entry: no duplicate autostart, no
desync. The registry is the single source of truth — there is no mirror in
config.env.

The module is Windows-specific. On other platforms (CI, tests) every function
degrades to a safe no-op so importing it never fails.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# HKCU Run key. Must match installer/OmniVerte.iss exactly.
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# Value name under the Run key. MUST stay in sync with the ValueName in
# OmniVerte.iss (currently "OmniVerte"), otherwise the installer and
# this toggle would create two competing autostart entries.
VALUE_NAME = "OmniVerte"

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import winreg


def _launch_command() -> str:
    """The command Windows runs at sign-in. Path(s) are quoted, like the installer."""
    if getattr(sys, "frozen", False):
        # PyInstaller build: sys.executable is OmniVerte.exe itself.
        return f'"{sys.executable}"'
    # Running from source: pythonw.exe (not python.exe — avoids a console
    # window flashing on every login) + absolute path to the entry script.
    pyw = Path(sys.executable).with_name("pythonw.exe")
    runner = str(pyw) if pyw.exists() else sys.executable
    script = Path(__file__).resolve().parent.parent / "OmniVerte.py"
    return f'"{runner}" "{script}"'


def is_enabled() -> bool:
    """True if the Run value exists (regardless of where it points).

    Reading the mere presence — not the path — means an entry created by the
    installer is correctly reflected as "on" even if the app later moved.
    """
    if not _IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        logger.error(f"autostart: failed to read Run value: {e}")
        return False


def enable() -> None:
    """Write (or refresh) the Run value with the current launch command.

    Always rewrites the value — this repairs a stale path if the app was
    reinstalled into a different folder.
    """
    if not _IS_WINDOWS:
        logger.info("autostart: not Windows — enable() is a no-op")
        return
    command = _launch_command()
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)
        logger.info(f"autostart: enabled → {command}")
    except OSError as e:
        logger.error(f"autostart: failed to enable: {e}")


def disable() -> None:
    """Remove the Run value. Silently ignores an already-absent value."""
    if not _IS_WINDOWS:
        logger.info("autostart: not Windows — disable() is a no-op")
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
        logger.info("autostart: disabled")
    except FileNotFoundError:
        pass  # key or value not present — nothing to remove
    except OSError as e:
        logger.error(f"autostart: failed to disable: {e}")


def set_enabled(flag: bool) -> None:
    """Convenience: enable() when flag is truthy, disable() otherwise."""
    if flag:
        enable()
    else:
        disable()

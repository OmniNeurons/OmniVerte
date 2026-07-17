# file: services/win_utils.py

"""
Small Windows-only utilities that don't fit anywhere else and are shared by
more than one caller (tray + main window).
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

logger = logging.getLogger(__name__)


def focus_pid_windows(pid: int) -> None:
    """Bring visible top-level windows of ``pid`` to the foreground (best-effort).

    Used to refocus an already-running ``--settings`` subprocess when the user
    clicks Settings a second time, instead of spawning a duplicate dialog.
    No-op on non-Windows; swallows any Win32 failures.
    """
    try:
        user32 = ctypes.windll.user32
        SW_RESTORE = 9
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def _cb(hwnd, _):
            proc_id = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
            if proc_id.value == pid and user32.IsWindowVisible(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(_cb), 0)
    except Exception as e:
        logger.debug(f"Failed to focus windows for pid {pid}: {e}")

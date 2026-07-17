# file: ui/taskbar_overlay.py

"""
Windows taskbar overlay icon (the little badge Teams/WhatsApp draw on top of
the app's taskbar button). Implemented via ITaskbarList3::SetOverlayIcon using
raw ctypes — no pywin32 dependency.

Overlay only renders when the host HWND has a real taskbar button. A hidden
QMainWindow has none, so set_overlay() is a silent no-op then. That is fine:
when the main window is closed-to-tray, status is conveyed via the tray icon
swap instead (see tray_preparing/tray_placing.py).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import logging
import os
import tempfile
from typing import Optional

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# ---------- COM / Windows constants ----------

# CLSID_TaskbarList = {56FDF344-FD6D-11d0-958A-006097C9A090}
# IID_ITaskbarList3 = {EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}

CLSCTX_INPROC_SERVER = 0x1
COINIT_APARTMENTTHREADED = 0x2

S_OK = 0

LR_LOADFROMFILE = 0x10
LR_DEFAULTSIZE = 0x40
IMAGE_ICON = 1

# ITaskbarList3 vtable layout (cumulative from IUnknown → ITaskbarList →
# ITaskbarList2 → ITaskbarList3). Indices we need:
VTBL_RELEASE = 2
VTBL_HRINIT = 3
VTBL_SET_OVERLAY_ICON = 18


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(s: str) -> GUID:
    g = GUID()
    ctypes.windll.ole32.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(g))
    return g


# ---------- icon generation ----------

# Map status → dot color (RGBA).
STATUS_COLORS = {
    "recording":  (220, 70, 70, 255),   # red
    "processing": (235, 200, 50, 255),  # yellow
}


def _build_status_icon(status: str) -> Image.Image:
    """
    Render a 32x32 RGBA image containing a solid colored dot for the overlay.
    Windows renders this anchored to the bottom-right of the taskbar button.
    """
    size = 32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dc = ImageDraw.Draw(img)
    color = STATUS_COLORS.get(status, (180, 180, 180, 255))
    # Small inset so the dot has breathing room from the border.
    margin = 4
    dc.ellipse([margin, margin, size - margin, size - margin], fill=color)
    # Subtle outline for contrast against any background.
    dc.ellipse(
        [margin, margin, size - margin, size - margin],
        outline=(20, 20, 20, 220),
        width=1,
    )
    return img


def _save_temp_ico(image: Image.Image) -> str:
    """Persist a PIL image as a .ico file in the temp dir and return its path."""
    fd, path = tempfile.mkstemp(prefix="vibe_overlay_", suffix=".ico")
    os.close(fd)
    image.save(path, format="ICO", sizes=[(16, 16), (32, 32)])
    return path


def _load_hicon(ico_path: str) -> int:
    """Load an HICON handle from a .ico file via LoadImageW."""
    h = ctypes.windll.user32.LoadImageW(
        None,
        ctypes.c_wchar_p(ico_path),
        IMAGE_ICON,
        0, 0,
        LR_LOADFROMFILE | LR_DEFAULTSIZE,
    )
    if not h:
        err = ctypes.windll.kernel32.GetLastError()
        raise OSError(f"LoadImageW failed for {ico_path}: GetLastError={err}")
    return h


# ---------- main wrapper ----------

class TaskbarOverlay:
    """
    Thin wrapper around ITaskbarList3::SetOverlayIcon. Holds a single interface
    pointer for the app's lifetime and a cache of HICON handles by status.
    Failures during init are swallowed — the rest of the app should never break
    because the taskbar overlay isn't available.
    """

    def __init__(self):
        self._taskbar_ptr: Optional[ctypes.c_void_p] = None
        self._set_overlay_fn = None
        self._release_fn = None
        self._icons: dict[str, int] = {}
        self._icon_paths: list[str] = []
        self._initialize()

    # ----- lifecycle -----

    def _initialize(self) -> None:
        try:
            # Qt has already initialized COM on this thread (apartment-threaded).
            # CoInitializeEx will return S_FALSE if already initialised, both OK.
            ctypes.windll.ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)

            clsid = _guid("{56FDF344-FD6D-11D0-958A-006097C9A090}")
            iid = _guid("{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}")

            ptr = ctypes.c_void_p()
            hr = ctypes.windll.ole32.CoCreateInstance(
                ctypes.byref(clsid),
                None,
                CLSCTX_INPROC_SERVER,
                ctypes.byref(iid),
                ctypes.byref(ptr),
            )
            if hr != S_OK or not ptr.value:
                logger.warning(f"CoCreateInstance(ITaskbarList3) failed: hr=0x{hr & 0xFFFFFFFF:08X}")
                return

            self._taskbar_ptr = ptr

            # vtable[0] points to the function-pointer table.
            vtable = ctypes.cast(
                ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0],
                ctypes.POINTER(ctypes.c_void_p),
            )

            # HrInit: HRESULT(this)
            hrinit_proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)
            hrinit_fn = hrinit_proto(vtable[VTBL_HRINIT])
            hr = hrinit_fn(ptr)
            if hr != S_OK:
                logger.warning(f"ITaskbarList3.HrInit failed: hr=0x{hr & 0xFFFFFFFF:08X}")
                self._taskbar_ptr = None
                return

            # SetOverlayIcon: HRESULT(this, HWND, HICON, LPCWSTR)
            set_overlay_proto = ctypes.WINFUNCTYPE(
                ctypes.c_long,
                ctypes.c_void_p,           # this
                wintypes.HWND,             # hwnd
                wintypes.HANDLE,           # hicon
                ctypes.c_wchar_p,          # description
            )
            self._set_overlay_fn = (set_overlay_proto(vtable[VTBL_SET_OVERLAY_ICON]), ptr)

            # Release: ULONG(this) — kept for cleanup().
            release_proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
            self._release_fn = (release_proto(vtable[VTBL_RELEASE]), ptr)

            self._preload_icons()
            logger.info("TaskbarOverlay initialised (ITaskbarList3).")

        except Exception as e:
            logger.warning(f"TaskbarOverlay init failed (overlay disabled): {e}")
            self._taskbar_ptr = None
            self._set_overlay_fn = None

    def _preload_icons(self) -> None:
        for status in STATUS_COLORS.keys():
            try:
                img = _build_status_icon(status)
                path = _save_temp_ico(img)
                self._icon_paths.append(path)
                self._icons[status] = _load_hicon(path)
            except Exception as e:
                logger.warning(f"Failed to build overlay icon for {status!r}: {e}")

    # ----- public API -----

    def set_overlay(self, hwnd: int, status: Optional[str]) -> None:
        """
        Attach the colored dot for `status` to the taskbar button of `hwnd`.
        status=None or unknown removes any overlay. Silent no-op if overlay
        isn't available or hwnd has no taskbar button.
        """
        if not self._set_overlay_fn or not hwnd:
            return

        fn, ptr = self._set_overlay_fn
        hicon = self._icons.get(status, 0) if status else 0
        desc = status or None

        try:
            hr = fn(ptr, wintypes.HWND(hwnd), wintypes.HANDLE(hicon), desc)
            if hr != S_OK:
                logger.debug(
                    f"SetOverlayIcon returned hr=0x{hr & 0xFFFFFFFF:08X} "
                    f"(hwnd={hwnd}, status={status!r}) — taskbar button likely absent"
                )
        except Exception as e:
            logger.debug(f"SetOverlayIcon raised: {e}")

    def cleanup(self) -> None:
        """Release the COM interface and destroy cached icons. Idempotent."""
        for hicon in self._icons.values():
            try:
                ctypes.windll.user32.DestroyIcon(hicon)
            except Exception:
                pass
        self._icons.clear()

        for path in self._icon_paths:
            try:
                os.remove(path)
            except Exception:
                pass
        self._icon_paths.clear()

        if self._release_fn and self._taskbar_ptr:
            try:
                fn, ptr = self._release_fn
                fn(ptr)
            except Exception:
                pass

        self._taskbar_ptr = None
        self._set_overlay_fn = None
        self._release_fn = None

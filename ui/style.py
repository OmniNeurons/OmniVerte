# file: ui/style.py

"""
Shared Qt styling for the app.

Theming model
-------------
A `Palette` dataclass holds every colour token. Two instances exist — `LIGHT`
and `DARK` — and a tiny module-level state (`_active`) tracks which one is in
effect. The three QSS sheets are built by *functions* of a palette rather than
baked at import time, so a live theme switch is just: `set_theme("dark")` then
re-apply the sheets.

  - main_window_qss(p) — main window
  - settings_qss(p)    — settings window (sidebar nav, form rows, action bar)
  - dialog_qss(p)      — small Custom-style quick dialog

Code that needs a colour outside QSS (QGraphicsDropShadowEffect, inline widget
tints, the status dot) reads it from `palette()` at apply-time, never via a
cached import — that's what keeps the switch live.

Spacing/radii tokens stay plain module constants; they don't depend on theme.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------- palette ----------

@dataclass(frozen=True)
class Palette:
    """All colour tokens for one theme. Field set is identical across themes."""

    BACKGROUND: str
    SURFACE: str
    SURFACE_SOFT: str
    SURFACE_HOVER: str

    ACCENT: str
    ACCENT_HOVER: str
    ACCENT_SOFT: str

    TEXT_PRIMARY: str
    TEXT_SECONDARY: str
    TEXT_MUTED: str

    BORDER_SUBTLE: str

    DANGER: str
    WARNING: str
    SUCCESS: str

    # Status-dot colours, named by canonical UIBridge status values.
    STATUS_DOT_IDLE: str
    STATUS_DOT_RECORDING: str
    STATUS_DOT_PROCESSING: str
    STATUS_DOT_ERROR: str
    STATUS_DOT_LOADING: str

    # Previously hard-coded inside QSS / widget code — tokenised so the dark
    # theme has no "holes".
    ERROR_BANNER_BG: str
    ERROR_BANNER_BORDER: str
    TEXT_ON_ACCENT: str
    SHADOW_RGBA: tuple[int, int, int, int]

    is_dark: bool


# Light Fluent palette (the app's original values, 1:1).
LIGHT = Palette(
    BACKGROUND="#F4F7F9",
    SURFACE="#FFFFFF",
    SURFACE_SOFT="#FAFCFD",
    SURFACE_HOVER="#F1F8F8",
    ACCENT="#14B8A6",
    ACCENT_HOVER="#0EA5A4",
    ACCENT_SOFT="#CCFBF1",
    TEXT_PRIMARY="#0F172A",
    TEXT_SECONDARY="#64748B",
    TEXT_MUTED="#94A3B8",
    BORDER_SUBTLE="#E2E8F0",
    DANGER="#EF4444",
    WARNING="#F59E0B",
    SUCCESS="#14B8A6",
    STATUS_DOT_IDLE="#1D9E75",
    STATUS_DOT_RECORDING="#EF9F27",
    STATUS_DOT_PROCESSING="#378ADD",
    STATUS_DOT_ERROR="#B91C1C",
    STATUS_DOT_LOADING="#8B5CF6",
    ERROR_BANNER_BG="#FEF2F2",
    ERROR_BANNER_BORDER="#FCA5A5",
    TEXT_ON_ACCENT="#FFFFFF",
    SHADOW_RGBA=(15, 23, 42, 16),
    is_dark=False,
)

# Dark Fluent palette (slate surfaces + brightened turquoise accent).
DARK = Palette(
    BACKGROUND="#0F1417",
    SURFACE="#1A2127",
    SURFACE_SOFT="#161D22",
    SURFACE_HOVER="#232C33",
    ACCENT="#2DD4BF",
    ACCENT_HOVER="#14B8A6",
    ACCENT_SOFT="#134E4A",
    TEXT_PRIMARY="#E6EDF3",
    TEXT_SECONDARY="#9AA7B2",
    TEXT_MUTED="#64748B",
    BORDER_SUBTLE="#2A343C",
    DANGER="#F87171",
    WARNING="#FBBF24",
    SUCCESS="#2DD4BF",
    STATUS_DOT_IDLE="#1D9E75",
    STATUS_DOT_RECORDING="#EF9F27",
    STATUS_DOT_PROCESSING="#378ADD",
    STATUS_DOT_ERROR="#DC2626",
    STATUS_DOT_LOADING="#A78BFA",
    ERROR_BANNER_BG="#2A1518",
    ERROR_BANNER_BORDER="#5B2626",
    TEXT_ON_ACCENT="#FFFFFF",
    SHADOW_RGBA=(0, 0, 0, 110),
    is_dark=True,
)


# ---------- active-theme state ----------

_active: Palette = LIGHT


def palette() -> Palette:
    """The palette currently in effect. Read this at apply-time, don't cache."""
    return _active


def is_dark() -> bool:
    return _active.is_dark


def set_theme(name: str) -> None:
    """Switch the active palette. `name` is "dark" / "light" (case-insensitive)."""
    global _active
    _active = DARK if str(name).strip().lower() == "dark" else LIGHT


# ---------- spacing scale (8px base) — theme-independent ----------

SP_XS = 4
SP_SM = 8
SP_MD = 16
SP_LG = 24
SP_XL = 32
SP_XXL = 48

# ---------- radii — theme-independent ----------

RADIUS_WINDOW = 18
RADIUS_CARD = 20
RADIUS_BUTTON = 12
RADIUS_PILL = 999
RADIUS_FEED_ITEM = 14


# ---------- QSS builders ----------

def main_window_qss(p: Palette | None = None) -> str:
    """Sheet for the redesigned main window."""
    p = p or _active
    return f"""
QWidget#mainRoot {{
    background-color: {p.BACKGROUND};
    color: {p.TEXT_PRIMARY};
    font-family: "Segoe UI Variable", "Segoe UI", "Inter", sans-serif;
}}

/* --- header --- */
QWidget#headerBar {{
    background-color: transparent;
}}
QLabel#appTitle {{
    color: {p.TEXT_PRIMARY};
    font-size: 15px;
    font-weight: 600;
}}
QLabel#statusText {{
    color: {p.TEXT_SECONDARY};
    font-size: 13px;
}}
QLabel#headerTagline {{
    color: {p.TEXT_SECONDARY};
    font-size: 13px;
}}

/* --- tier chip (Free / Pro) — flat, borderless; matches the header icon
   buttons (no outline). Subtle hover band; accent text + soft hover when Pro. */
QPushButton#tierChip {{
    color: {p.TEXT_SECONDARY};
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#tierChip:hover {{
    background-color: {p.SURFACE_HOVER};
    color: {p.TEXT_PRIMARY};
}}
QPushButton#tierChip:pressed {{
    background-color: {p.BORDER_SUBTLE};
}}
QPushButton#tierChip[pro="true"] {{
    color: {p.ACCENT_HOVER};
}}
QPushButton#tierChip[pro="true"]:hover {{
    background-color: {p.ACCENT_SOFT};
    color: {p.ACCENT_HOVER};
}}

/* --- cards --- */
QFrame#card {{
    background-color: {p.SURFACE};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: {RADIUS_CARD}px;
}}
QFrame#card[interactive="true"]:hover {{
    border-color: {p.ACCENT_SOFT};
}}

QLabel#cardTitle {{
    color: {p.TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 600;
}}
QLabel#cardSubtitle {{
    color: {p.TEXT_MUTED};
    font-size: 12px;
}}
QLabel#historyCount {{
    color: {p.TEXT_MUTED};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#historyCount[warn="true"] {{
    color: {p.ACCENT_HOVER};
}}

/* --- text views inside cards --- */
QTextEdit#docView, QPlainTextEdit#docView {{
    background-color: transparent;
    border: none;
    color: {p.TEXT_PRIMARY};
    font-size: 15px;
    selection-background-color: {p.ACCENT_SOFT};
    selection-color: {p.TEXT_PRIMARY};
}}

/* --- ghost toolbar buttons (Copy / Insert again / Clear) --- */
QPushButton#ghost {{
    background-color: transparent;
    color: {p.TEXT_SECONDARY};
    border: none;
    border-radius: {RADIUS_BUTTON}px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#ghost:hover {{
    background-color: {p.SURFACE_HOVER};
    color: {p.TEXT_PRIMARY};
}}
QPushButton#ghost:pressed {{
    background-color: {p.BORDER_SUBTLE};
}}
QPushButton#ghost:disabled {{
    color: {p.TEXT_MUTED};
    background-color: transparent;
}}

/* --- segmented rewrite buttons --- */
QPushButton#segment {{
    background-color: {p.SURFACE};
    color: {p.TEXT_SECONDARY};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: {RADIUS_BUTTON}px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton#segment:hover {{
    background-color: {p.SURFACE_HOVER};
    color: {p.TEXT_PRIMARY};
    border-color: {p.ACCENT_SOFT};
}}
QPushButton#segment:pressed {{
    background-color: {p.BORDER_SUBTLE};
}}
QPushButton#segment:disabled {{
    color: {p.TEXT_MUTED};
    background-color: {p.SURFACE};
}}
QPushButton#segment[active="true"] {{
    background-color: {p.ACCENT_SOFT};
    color: {p.ACCENT_HOVER};
    border-color: {p.ACCENT_SOFT};
}}

/* --- translation pill (matches the segment buttons; turquoise globe icon) --- */
QPushButton#translatePill {{
    background-color: {p.SURFACE};
    color: {p.TEXT_SECONDARY};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: {RADIUS_BUTTON}px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
}}
QPushButton#translatePill:hover {{
    background-color: {p.SURFACE_HOVER};
    color: {p.TEXT_PRIMARY};
    border-color: {p.ACCENT_SOFT};
}}
QPushButton#translatePill:pressed {{
    background-color: {p.BORDER_SUBTLE};
}}
QPushButton#translatePill:disabled {{
    color: {p.TEXT_MUTED};
    background-color: {p.SURFACE};
}}

/* --- activity feed --- */
QFrame#feedItem {{
    background-color: transparent;
    border: none;
    border-radius: {RADIUS_FEED_ITEM}px;
}}
QFrame#feedItem:hover {{
    background-color: {p.SURFACE};
}}
QLabel#feedKind {{
    color: {p.TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#feedTime {{
    color: {p.TEXT_MUTED};
    font-size: 11px;
}}
QLabel#feedPreview {{
    color: {p.TEXT_SECONDARY};
    font-size: 12px;
}}

QScrollArea#feedScroll {{
    background-color: transparent;
    border: none;
}}
QScrollArea#feedScroll > QWidget > QWidget {{
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 4px 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {p.BORDER_SUBTLE};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {p.TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0;
}}

/* --- status dot wrapper (filled in code) --- */
QLabel#statusDot {{
    border-radius: 5px;
}}
"""


def settings_qss(p: Palette | None = None) -> str:
    """Sheet for the redesigned settings window."""
    p = p or _active
    return f"""
QWidget#settingsRoot {{
    background-color: {p.BACKGROUND};
    color: {p.TEXT_PRIMARY};
    font-family: "Segoe UI Variable", "Segoe UI", "Inter", sans-serif;
}}

QWidget#settingsPage {{
    background-color: transparent;
}}

QScrollArea#settingsScroll {{
    background-color: transparent;
    border: none;
}}
QScrollArea#settingsScroll > QWidget > QWidget {{
    background-color: transparent;
}}

/* --- page header --- */
QLabel#pageTitle {{
    color: {p.TEXT_PRIMARY};
    font-size: 22px;
    font-weight: 600;
}}
QLabel#pageHint {{
    color: {p.TEXT_SECONDARY};
    font-size: 13px;
}}

/* --- section cards --- */
QFrame#settingsCard {{
    background-color: {p.SURFACE};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: {RADIUS_CARD}px;
}}
QLabel#cardSectionTitle {{
    color: {p.TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 600;
}}
QLabel#cardSectionHint {{
    color: {p.TEXT_SECONDARY};
    font-size: 12px;
}}

/* --- form rows --- */
QWidget#settingsRow {{
    border-radius: 8px;
    padding: 3px 8px;
}}
QWidget#settingsRow:hover {{
    background-color: {p.SURFACE_HOVER};
}}
QLabel#rowLabel {{
    color: {p.TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 500;
}}
QLabel#rowValue {{
    color: {p.TEXT_PRIMARY};
    font-size: 13px;
}}
QLabel#rowHint {{
    color: {p.TEXT_MUTED};
    font-size: 11px;
}}
QLabel#onboardingHint {{
    color: {p.ACCENT};
    font-size: 12px;
    font-weight: 600;
}}
/* --- "Get a key ↗" link beside an API-key field (anchor colour is inline
   accent from make_link_label; this just keeps it quiet/small) --- */
QLabel#getKeyLink {{
    font-size: 11px;
}}

/* --- 'Pro' tag-link on locked (Pro) features → opens the waitlist (Phase 1A).
   A small accent pill, deliberately quiet; never a nag popup. */
QPushButton#proTag {{
    color: {p.ACCENT_HOVER};
    background-color: {p.ACCENT_SOFT};
    border: none;
    border-radius: 6px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 700;
}}
QPushButton#proTag:hover {{
    background-color: {p.ACCENT};
    color: #ffffff;
}}

/* --- glossary live term counter — neutral, accented when the cap is hit --- */
QLabel#termCounter {{
    color: {p.TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#termCounter[warn="true"] {{
    color: {p.ACCENT_HOVER};
}}

/* --- hotkey↔style pairing panel (General page) --- */
QFrame#stylePairPanel {{
    background-color: {p.ACCENT_SOFT};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: {RADIUS_BUTTON}px;
}}
QLabel#hotkeyBadge {{
    background-color: {p.SURFACE};
    color: {p.TEXT_PRIMARY};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: 6px;
    padding: 2px 10px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#stylePairName {{
    color: {p.TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 600;
}}
QLabel#stylePairArrow {{
    color: {p.TEXT_SECONDARY};
    font-size: 15px;
    font-weight: 600;
}}

/* --- backend priority drag-list --- */
QListWidget#priorityList {{
    background-color: {p.SURFACE_SOFT};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: {RADIUS_BUTTON}px;
    padding: 4px;
    color: {p.TEXT_PRIMARY};
}}
QListWidget#priorityList::item {{
    padding: 10px 14px;
    border-radius: 8px;
    color: {p.TEXT_PRIMARY};
}}
QListWidget#priorityList::item:hover {{
    background-color: {p.SURFACE_HOVER};
}}
QListWidget#priorityList::item:selected {{
    background-color: {p.ACCENT_SOFT};
    color: {p.ACCENT_HOVER};
}}

/* --- footer action bar --- */
QFrame#actionBar {{
    background-color: {p.SURFACE};
    border-top: 1px solid {p.BORDER_SUBTLE};
}}

/* --- inline error banner --- */
QFrame#errorBanner {{
    background-color: {p.ERROR_BANNER_BG};
    border: 1px solid {p.ERROR_BANNER_BORDER};
    border-radius: {RADIUS_BUTTON}px;
}}
QLabel#errorBannerText {{
    color: {p.DANGER};
    font-size: 12px;
    font-weight: 500;
}}

/* --- scrollbar --- */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 4px 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {p.BORDER_SUBTLE};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {p.TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0;
}}
"""


def dialog_qss(p: Palette | None = None) -> str:
    """Sheet for the small Custom-style quick dialog."""
    p = p or _active
    return f"""
QDialog {{
    background-color: {p.BACKGROUND};
    color: {p.TEXT_PRIMARY};
    font-family: "Segoe UI Variable", "Segoe UI", "Inter", sans-serif;
}}
QLabel {{
    color: {p.TEXT_PRIMARY};
}}
QLabel#sectionTitle {{
    font-size: 15px;
    font-weight: 600;
    color: {p.TEXT_PRIMARY};
}}
QLabel#sectionHint {{
    color: {p.TEXT_SECONDARY};
    font-size: 12px;
}}
QLabel#fieldLabel {{
    color: {p.TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 500;
}}
QFrame#card {{
    background-color: {p.SURFACE};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: {RADIUS_CARD}px;
}}
QLineEdit, QPlainTextEdit {{
    background-color: {p.SURFACE_SOFT};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: {RADIUS_BUTTON}px;
    padding: 8px 10px;
    color: {p.TEXT_PRIMARY};
    selection-background-color: {p.ACCENT_SOFT};
    selection-color: {p.TEXT_PRIMARY};
    font-size: 13px;
}}
QLineEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {p.ACCENT};
    background-color: {p.SURFACE};
}}
QLineEdit:disabled, QPlainTextEdit:disabled {{
    color: {p.TEXT_MUTED};
    background-color: {p.BACKGROUND};
}}
QPushButton {{
    background-color: {p.SURFACE};
    color: {p.TEXT_PRIMARY};
    border: 1px solid {p.BORDER_SUBTLE};
    border-radius: {RADIUS_BUTTON}px;
    padding: 8px 18px;
    font-weight: 500;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {p.SURFACE_HOVER};
    border-color: {p.ACCENT_SOFT};
}}
QPushButton:pressed {{
    background-color: {p.BORDER_SUBTLE};
}}
QPushButton:disabled {{
    color: {p.TEXT_MUTED};
    background-color: {p.SURFACE};
}}
QPushButton#primary {{
    background-color: {p.ACCENT};
    color: {p.TEXT_ON_ACCENT};
    border: 1px solid {p.ACCENT};
}}
QPushButton#primary:hover {{
    background-color: {p.ACCENT_HOVER};
    border-color: {p.ACCENT_HOVER};
}}
QPushButton#primary:pressed {{
    background-color: {p.ACCENT_HOVER};
    border-color: {p.ACCENT_HOVER};
}}
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 4px 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {p.BORDER_SUBTLE};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {p.TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0;
}}
"""

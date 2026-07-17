# file: ui/settings_pages/__init__.py

"""
Settings sub-pages for the redesigned settings window.

Each page subclasses _BasePage (defined in `.base`) and exposes:

  load_from(config)  → populate widgets from the current Config state
  apply_to(config)   → persist widget values back to Config (+ keyring)
  validate()         → return an error string if the page's inputs are invalid

The settings window iterates over pages on Save: validate first, abort on the
first failure (and switch to that page); apply each in sequence on success.
"""

from .base import BasePage
from .general_page import GeneralPage
from .transcription_page import TranscriptionPage
from .languages_page import LanguagesPage
from .custom_style_page import CustomStylePage
from .glossary_page import GlossaryPage
from .license_page import LicensePage
from .about_page import AboutPage

__all__ = [
    "BasePage",
    "GeneralPage",
    "TranscriptionPage",
    "LanguagesPage",
    "CustomStylePage",
    "GlossaryPage",
    "LicensePage",
    "AboutPage",
]

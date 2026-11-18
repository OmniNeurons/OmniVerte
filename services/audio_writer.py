# file: services/audio_writer.py

import ctypes
import difflib
import logging
import os
import re
import tempfile
import time
import threading
import queue

import numpy as np
import openai
import sounddevice as sd
import scipy.io.wavfile as wav
import pyperclip
import keyboard
import mouse  # for handling mouse events

try:  # Seam dedup's mangled-final-word fallback only; exact matching without it.
    from rapidfuzz import fuzz as _rf_fuzz
    from rapidfuzz.distance import JaroWinkler as _rf_jaro
except ImportError:  # pragma: no cover - exercised via the missing-module test
    _rf_fuzz = None
    _rf_jaro = None

# faster_whisper is imported lazily inside _initialize_transcription_backend so
# that running with TRANSCRIPTION_BACKEND='openai' doesn't pull in ctranslate2
# and allocate a CUDA context / VRAM at startup.

# Settings
SEGMENT_DURATION = 20  # Duration of segment in seconds
OVERLAP_DURATION = 1   # Overlap between segments in seconds
MAX_SEGMENTS = 50      # Max segments per transcription (protection against hallucinations)
TRANSCRIPTION_THREAD_TIMEOUT = 60.0  # Timeout for waiting transcription thread (seconds)
# How long _announce_recording waits for the first mic frame before showing
# "recording" anyway (a dead mic then reads as flat bars, not as a hung start).
FIRST_FRAME_TIMEOUT = 1.0
# A held hotkey auto-repeats at most ~1s apart (Windows' longest repeat delay);
# a key-down after a longer silence is a new press even if its key-up was missed.
HOTKEY_REPEAT_GAP = 1.5
# Keep the input stream OPENED BUT NOT STARTED between dictations. Opening the
# device was ~80-100ms (300ms+ cold) of the hotkey→first-frame gap; starting an
# already-open stream is ~1ms, which took that gap from ~125ms to ~40ms. An
# unstarted stream captures no audio and does not light Windows' "microphone
# in use" indicator (checked on Win11 / MME). False = old open-on-press.
PREOPEN_INPUT_STREAM = True

# Cloud request resilience. Without an explicit timeout the openai SDK waits up
# to 600s per request — a single stalled request froze the whole app for minutes.
CLOUD_REQUEST_TIMEOUT = 30.0  # seconds, hard cap on ONE cloud request
CLOUD_MAX_RETRIES = 1         # SDK-level retries of the SAME provider (1 retry = 2 attempts)

# Available transcription models. Re-exported from services.transcription_models
# so the settings UI can pull just the constants without dragging in numpy/
# openai/sounddevice/etc.
from services.transcription_models import (
    GROQ_BASE_URL,
    GEMINI_TRANSCRIPTION_MODELS,
    GROQ_TRANSCRIPTION_MODELS,
    LOCAL_WHISPER_MODELS,
    OPENAI_TRANSCRIPTION_MODELS,
)
from services.api_errors import CloudApiError, classify_api_error
from services import elevenlabs_realtime, gemini_live, gemini_transcribe
from services.config_store import choose_quick_engine
from services.glossary import Glossary
from services.audio_prep import (
    normalize_enhance_profile,
    prepare_for_transcription,
    resolve_input_device,
)

# Backends in canonical order. UI / priority lists use these names.
ALL_BACKENDS = ("groq", "openai", "gemini", "local")
# The subset that talks to the network — no local model to load, and eligible
# for the cross-provider fallback in _cloud_fallback_order.
CLOUD_BACKENDS = ("openai", "groq", "gemini")
# Display labels for provider-facing log lines / error toasts.
CLOUD_BACKEND_LABELS = {"openai": "OpenAI", "groq": "Groq", "gemini": "Gemini"}
# Display labels for the quick hotkey's live engines (same role as above).
QUICK_ENGINE_LABELS = {"gemini": "Gemini", "elevenlabs": "ElevenLabs"}
# Failure kinds (services.api_errors.classify_api_error) a retry cannot cure:
# the account is out of credits or the key is rejected. A live engine that
# fails this way is skipped for the rest of the session instead of costing
# every quick dictation a doomed session plus a batch replay.
STICKY_FAILURE_KINDS = ("quota", "auth")

# Global hotkey actions (keyboard mode). Each entry maps an internal action id
# to its display label, the config key holding its key, and a default key.
# Adding a new hotkey = one entry here + a default in config_store.DEFAULTS +
# a branch in AudioWriter.process_text. The order is the registration order.
# `label_key` is an i18n catalog KEY, not text: this table is built at import,
# before the UI language is known, and the tray menu that renders it is rebuilt
# on every change. Resolving the label here would freeze it in the boot locale.
HOTKEY_ACTIONS = {
    "translate":  {"label_key": "tray.action.translate",  "config_key": "HOTKEY_TRANSLATE",  "default": "F10"},
    "custom":     {"label_key": "tray.action.custom",     "config_key": "HOTKEY_CUSTOM",     "default": "F11"},
    "quick":      {"label_key": "tray.action.quick",      "config_key": "HOTKEY_QUICK",      "default": "F9"},
}


# Actions whose audio streams to the quick engine (Gemini Live / ElevenLabs)
# while the user speaks, when that engine has a key — i.e. every action (the
# mouse button starts dictation, "quick", too). Translate/custom then run
# their LLM pass on that transcript.
REALTIME_ACTIONS = ("quick", "translate", "custom")


def resolve_hotkey(config, action_id):
  """The key bound to `action_id`; "" means the action is deliberately unbound.

  An empty value on file is the user's choice (Settings lets an action go
  without a key), so only a key that is missing altogether falls back to the
  default.
  """
  spec = HOTKEY_ACTIONS[action_id]
  value = config.get(spec["config_key"])
  return spec["default"] if value is None else value.strip()

# Whisper-family models commonly hallucinate these phrases on silent/noisy
# input. Compared lowercase with trailing punctuation stripped.
WHISPER_HALLUCINATIONS = frozenset({
    "thanks for watching",
    "thank you for watching",
    "thank you",
    "subscribe to my channel",
    "like and subscribe",
    "спасибо за просмотр",
    "спасибо за внимание",
    "продолжение следует",
    "субтитры",
    "субтитры сделал dimatorzok",
    "редактор субтитров",
    "корректор",
})

logger = logging.getLogger(__name__)

# Scratch dir for the short-lived WAV files handed to the transcription
# backends. Lives under the OS temp dir (not the CWD), so launching the app
# from anywhere doesn't litter that folder with recordings — and a stray
# `git add` can never commit a clip of the user's voice into the repo again.
_TEMP_DIR = os.path.join(tempfile.gettempdir(), "OmniVerte")
os.makedirs(_TEMP_DIR, exist_ok=True)


# Opening punctuation a dictated text may start with, skipped to reach the
# first word.
_LEADING_PUNCT = "\"'«„“‘([{¿¡—–-…"


def capitalize_first(text: str) -> str:
  """Start the text with a capital letter, as a sentence would.

  The quick key has no LLM pass, and the streaming engines start a take in
  lower case whenever they read it as a continuation ("после сохранения…").
  Only a plain lower-case first word is touched: one that already carries a
  capital (iPhone, eBay), starts with a digit (2G), or looks like a link, path
  or address stays exactly as transcribed.
  """
  i = 0
  while i < len(text) and (text[i].isspace() or text[i] in _LEADING_PUNCT):
    i += 1
  word = text[i:].split(None, 1)[0] if text[i:].strip() else ""
  if (not word or not word[0].isalpha() or not word[0].islower()
      or any(c.isupper() for c in word)
      or any(m in word for m in ("://", "@", "/", "\\"))
      or word.lower().startswith("www.")):
    return text
  return text[:i] + text[i].upper() + text[i + 1:]


def _model_key_for_backend(backend: str) -> str:
  return f"MODEL_{backend.upper()}"


def _backend_for_model(model_name: str) -> str | None:
  if model_name in LOCAL_WHISPER_MODELS:
    return "local"
  if model_name in OPENAI_TRANSCRIPTION_MODELS:
    return "openai"
  if model_name in GROQ_TRANSCRIPTION_MODELS:
    return "groq"
  if model_name in GEMINI_TRANSCRIPTION_MODELS:
    return "gemini"
  return None


# Cross-segment overlap dedup (see _dedup_overlap_join). Each streaming segment
# is transcribed from audio that begins with the last OVERLAP_DURATION second(s)
# of the previous segment, so that shared window is transcribed twice — once at
# the tail of segment N, once at the head of segment N+1. We cap the boundary
# search a few words above what ~1s of speech can hold: wide enough to catch a
# slow-boundary overlap, narrow enough that a genuinely repeated phrase far from
# the seam is never swallowed.
_MAX_OVERLAP_WORDS = 12
_WORD_RE = re.compile(r"\w+", re.UNICODE)

# Fuzzy-seam guards. Whisper does NOT re-transcribe the shared 1s window
# identically on both sides of a boundary — it inserts/drops leading filler
# ("А …") and substitutes words ("он" -> "она"). So an exact suffix==prefix
# match misses real duplications. We align the two edges with difflib instead,
# then accept the overlap only when it looks like a genuine seam re-transcription
# (not a coincidental word match that would eat real new speech):
#   TRAIL_SLACK — the matched run must reach within this many words of prev's END.
#                 The overlap is prev's LAST ~1s, so a real seam always re-utters
#                 prev's final word; requiring the match to include it (0) cleanly
#                 rejects coincidental mid-tail word matches ("…is on Friday" /
#                 "the report is ready", "…the feature" / "and the team"). The
#                 cost is a rare miss if Whisper mangles that final word — a
#                 leftover duplicate, which is far less harmful than eating speech.
#   HEAD_SLACK  — ...and begin within this many words of nxt's START (allowing a
#                 couple of inserted leading fillers, e.g. "А …", "So …").
#   MATCH_FRAC  — ...and at least this fraction of the dropped head must actually
#                 be matched words (rejects a lone stopword coincidence).
_SEAM_TRAIL_SLACK = 0
_SEAM_HEAD_SLACK = 3
_SEAM_MATCH_FRAC = 0.5

# Mangled-final-word fallback. difflib compares words as atoms: equal or not,
# no partial credit. So when Whisper re-transcribes the overlap's last word
# imperfectly ("…внешнего сервера?" / "Сервиса.") there is no match at all, the
# TRAIL_SLACK anchor never forms, and the duplicate survives — the exact miss
# predicted above, observed in the wild. We give that ONE word a fuzzy second
# chance before alignment: prev's final word is the word the overlap is
# guaranteed to re-utter, so a near-match there is far likelier to be the same
# audio twice than a coincidence. Every other word stays exact, and all the
# guards above still apply to the run this produces.
#
# The thresholds cannot be tuned by similarity alone: "сервера"/"сервиса" (the
# true pair) scores BELOW lookalikes like "кода"/"когда" on ratio and on
# JaroWinkler alike, so no cutoff separates them — position is what carries the
# signal, and the cutoffs only fence off the far field ("может"/"можно",
# "сервера"/"северный"). Both metrics must pass: ratio tolerates the substituted
# tail, JaroWinkler demands the shared prefix that a mishearing keeps.
# MIN_LEN keeps short function words ("он"/"она", "the"/"they") exact-only,
# where a coincidence is cheap to make and costly to swallow.
_SEAM_FUZZY_MIN_LEN = 4
_SEAM_FUZZY_RATIO = 65
_SEAM_FUZZY_JARO = 85


def _seam_words_alike(a: str, b: str) -> bool:
  """True if `a` and `b` are plausibly one word Whisper transcribed two ways.

  Only ever asked about prev's FINAL word (see the thresholds above) — this is
  deliberately not a general "are these words similar" test and does not
  separate near-homophones on its own.
  """
  if a == b:
    return True
  if _rf_fuzz is None or _rf_jaro is None:
    return False
  if len(a) < _SEAM_FUZZY_MIN_LEN or len(b) < _SEAM_FUZZY_MIN_LEN:
    return False
  return (
      _rf_fuzz.ratio(a, b) >= _SEAM_FUZZY_RATIO
      and _rf_jaro.similarity(a, b) * 100 >= _SEAM_FUZZY_JARO
  )


def _overlap_word_count(prev: str, nxt: str) -> tuple[int, int]:
  """Fuzzy boundary overlap between `prev`'s tail and `nxt`'s head.

  Returns ``(word_count, char_cut)`` where ``word_count`` is how many words of
  ``nxt``'s head re-transcribe ``prev``'s tail (0 = no overlap) and ``char_cut``
  is the index in ``nxt`` just past that run. Alignment is on normalized
  (lowercased) words via difflib, so it survives the word insertions /
  substitutions / punctuation Whisper introduces when it re-transcribes the same
  audio in a different chunk (e.g. ``"…что он делает."`` vs ``"А что она
  делает?"``). Prev's final word additionally gets a fuzzy chance
  (`_seam_words_alike`), since difflib alone gives a mangled word no partial
  credit. The guards above keep all of this from swallowing genuine new speech
  when the seam words only coincidentally overlap.
  """
  prev_words = [(m.group(0).lower(), m.start(), m.end()) for m in _WORD_RE.finditer(prev)]
  next_words = [(m.group(0).lower(), m.start(), m.end()) for m in _WORD_RE.finditer(nxt)]
  if not prev_words or not next_words:
    return 0, 0

  # Window to the seam: prev's last N words, nxt's first N.
  prev_tail = prev_words[-_MAX_OVERLAP_WORDS:]
  next_head = next_words[:_MAX_OVERLAP_WORDS]
  prev_norm = [w for w, _, _ in prev_tail]
  next_norm = [w for w, _, _ in next_head]

  # Give a near-miss of prev's final word difflib's notion of equality, so the
  # TRAIL_SLACK anchor can form on it. Rewriting rather than special-casing the
  # anchor keeps every guard below operating on one consistent word sequence.
  # Which nxt word it lands on is left to the alignment; `fuzzy_idx` remembers
  # the rewrites so the corroboration guard below can tell a fuzzy anchor from
  # an exact one.
  final = prev_norm[-1]
  fuzzy_idx = set()
  for i, w in enumerate(next_norm):
    if w != final and _seam_words_alike(final, w):
      next_norm[i] = final
      fuzzy_idx.add(i)

  # The overlap must include prev's final word (TRAIL_SLACK = 0: it is prev's
  # last ~1s of audio), so pin that word to each of its occurrences in nxt's
  # head and align only what lies before both. A single global alignment of the
  # two windows cannot do this: difflib's blocks never cross, so a coincidental
  # earlier match ("…и поэтому модель" / "модель сама … не было" — "было")
  # claimed the alignment and the real seam word, crossing it, was dropped —
  # leaving "модель… модель" in the paste. Of the occurrences that pass the
  # guards, the best-corroborated one wins (a seam repeating its own last word,
  # "…либо на промпт, либо на" / "либо на промпт, либо на …", must cut at the
  # second "на"); a tie goes to the smaller, conservative cut. An exact anchor
  # outranks a fuzzy one ("…сервер телефон?" / "сервер телефон, или в
  # телефоне" — "телефоне" would eat "или в").
  best = None
  for j, w in enumerate(next_norm):
    if w != final:
      continue
    cut_words = j + 1  # words of nxt's head to drop
    matcher = difflib.SequenceMatcher(None, prev_norm[:-1], next_norm[:j], autojunk=False)
    blocks = [b for b in matcher.get_matching_blocks() if b.size > 0]
    first_b = min([b.b for b in blocks] + [j])
    if first_b > _SEAM_HEAD_SLACK:
      continue
    matched = 1 + sum(b.size for b in blocks)
    if matched / cut_words < _SEAM_MATCH_FRAC:
      continue
    # An uncorroborated fuzzy rewrite may drop ITSELF and nothing more. With no
    # exact word backing the seam, a near-miss sitting past nxt's first word is
    # as easily two different words as one word twice, and cutting to it
    # swallows the real speech in front ("…А здесь нужно" / "подсвечивать
    # нужный набор" — "нужно"~"нужный" ate "подсвечивать"). Replaying the log's
    # 447 real multi-segment joins, this is the only place the fallback
    # overreached.
    if matched == 1 and cut_words > 1 and j in fuzzy_idx:
      continue
    rank = (j not in fuzzy_idx, matched)
    if best is None or rank > best[0]:
      best = (rank, j)
  if best is None:
    return 0, 0
  j = best[1]
  return j + 1, next_head[j][2]


def _dedup_overlap_join(segments) -> str:
  """Join streaming transcription segments, stripping the re-transcribed overlap.

  Consecutive segments share the OVERLAP_DURATION audio window, so joining them
  raw duplicates whatever words fell on each segment boundary. For every seam we
  fuzzily align the end of the accumulated text with the start of the incoming
  segment (`_overlap_word_count`) and drop the re-transcribed run (plus any
  punctuation bridging it) from the incoming head, keeping the previous segment's
  copy. A segment that is entirely overlap contributes nothing.
  """
  result = ""
  for seg in segments:
    seg = (seg or "").strip()
    if not seg:
      continue
    if not result:
      result = seg
      continue
    k, cut = _overlap_word_count(result, seg)
    tail = seg[cut:].lstrip(" \t\r\n,.;:!?…-—") if k else seg
    tail = tail.strip()
    if tail:
      result = f"{result} {tail}"
  return result.strip()


_LANG_SHORT = {
    "English": "EN", "Russian": "RU", "Spanish": "ES", "German": "DE",
    "French": "FR", "Italian": "IT", "Chinese": "ZH", "Japanese": "JA",
}


def _lang_short(name: str) -> str:
  """Short label for a history row's direction ("→ RU"). Same table the main
  window's translate pill uses, for the 8 app languages."""
  return _LANG_SHORT.get(name, (name or "")[:2].upper())


class AudioWriter:
  """
  Class for audio recording, transcription and processing using OpenAI and WhisperModel.
  Handles both keyboard and mouse activation for recording control.
  """

  # Quick-mode state, also set in __init__/_build_cloud_clients. Class-level
  # defaults keep partially-built instances (tests, early hotkeys) on the
  # ordinary batch path.
  _session_source = "batch"
  _quick_engine = "elevenlabs"
  elevenlabs_api_key = None
  gemini_api_key = None
  # Provider-health state (see _reset_provider_health). Class-level defaults
  # for the same reason as above; the set is a frozenset so a partially-built
  # instance can never mutate a shared one.
  _degraded_batch = None
  _degraded_quick = None
  _quick_engine_down = frozenset()

  def __init__(self, config, ui_bridge, history_manager):
    """
    Initialize the AudioWriter.

    Args:
        config: Config instance (services.config_store.Config) — single source
            of truth for settings (AppData) and secrets (Windows Credentials).
        ui_bridge: services.ui_bridge.UIBridge — receives status/transcript
            signals, marshals them to the Qt main thread.
        history_manager: ui.history_manager.HistoryManager — receives final
            corrected transcripts for the session history.
    """
    self.config = config
    self.ui_bridge = ui_bridge
    self.history_manager = history_manager

    # Corporate glossary (own names / counterparties / services / replacements).
    # Loaded from glossary.json; empty + inert unless the user fills it in and
    # enables the feature. Reloaded after a settings save (see tray wiring).
    self.glossary = Glossary()
    # Apply the Free-tier term cap (Pro lifts it). Re-applied on reload and on
    # an in-session license change via apply_entitlement().
    self.apply_entitlement()

    # OpenAI + Groq clients, built from the stored secrets. Factored into a
    # helper so a settings save can rebuild them live (a just-added/-removed key
    # takes effect without a restart).
    self._build_cloud_clients()

    # Pick the initial backend by walking the configured priority list.
    self.transcription_backend = self._pick_initial_backend()
    self.whisper_model_name = config.get(_model_key_for_backend(self.transcription_backend))
    self.use_device = config.get("USE_DEVICE", "cpu")  # "cpu" or "cuda"
    self.whisper_model = None

    # Backend init runs in the background (see init_backend_async / the worker)
    # so a slow first-run model download never blocks the UI from appearing.
    #   _model_state: "loading" | "ready" | "failed" — mirrors what the UI shows
    #     and is the source of truth for the start_recording guard.
    #   _init_gen: bumped on every (re)init request; a worker only commits its
    #     result if its captured gen is still current, so a model switch that
    #     lands mid-download supersedes the stale load instead of racing it.
    #   _load_lock: serializes the heavy WhisperModel build so two inits never
    #     construct/free the model concurrently.
    self._model_state = "loading"
    self._init_gen = 0
    self._gen_lock = threading.Lock()
    self._load_lock = threading.Lock()

    self.fs = 16000  # Sample rate
    # Capture / prep settings — re-read on settings save and at each start.
    # INPUT_DEVICE: "" → system default; else "name::<PortAudio name>".
    # AUDIO_ENHANCE: off|light (default light). Applied only at WAV write time.
    self._input_device_config = config.get("INPUT_DEVICE", "") or ""
    self._audio_enhance_profile = normalize_enhance_profile(
        config.get("AUDIO_ENHANCE", "light")
    )
    self.is_recording = False
    self.audio_queue = queue.Queue()
    self.stream = None
    # Pre-opened, unstarted stream for the next dictation (PREOPEN_INPUT_STREAM)
    # as (stream, INPUT_DEVICE value it was opened for). The lock also covers
    # the open itself, so a press landing mid-open waits for that stream
    # instead of opening a second one.
    self._standby = None
    self._standby_lock = threading.Lock()
    self.recording_timer = 10  # Auto-stop timer (e.g., 10 minutes)
    # HWND of the window that had focus when recording started — used to
    # restore focus before pasting so Ctrl+V lands in the user's editor and
    # not in our own main window if they opened it during processing.
    self._prev_foreground_hwnd = 0
    # True when the window focused at recording start belonged to our OWN
    # process (the user had the main window active, e.g. cursor in the text
    # card). In that case auto-paste is skipped: the transcript is already
    # delivered into the card via transcript_ready, and Ctrl+V would land in the
    # same field and duplicate it.
    self._foreground_was_own = False
    # Set when the user double-taps during a session. Tells the auto-paste flow
    # to skip Ctrl+V regardless of whether the main window has finished showing
    # by then (Qt signal delivery is async, so checking main_window_visible
    # alone races against fast transcription).
    self._skip_next_paste = False
    # When the user single-taps to stop, we defer the actual stop_recording
    # call so the keyboard thread isn't blocked (stop joins the transcription
    # thread, which can take seconds). If a second tap arrives within the
    # double-tap window, we cancel this timer and treat the pair as a
    # "double-tap stop + open window" gesture.
    self._pending_stop_timer: threading.Timer | None = None
    # One user-facing API-error notification per recording session: a dead
    # quota fails every 20s streaming segment AND the final pass AND the LLM
    # correction — one toast carries the news, the rest would be spam.
    self._api_error_notified = False
    # For streaming transcription
    self.streaming = False
    self.transcription_thread = None
    # Monotonic session counter. Bumped on every start_recording. The streaming
    # thread and the deferred process_text() each capture the gen of the session
    # they belong to and refuse to touch shared state / the UI once a newer
    # session has started — otherwise a previous session's post-processing tail
    # (drop_all/idle/press_and_talk) clobbers the live session, orphaning its
    # streaming thread and leaving the indicator stuck on "processing".
    self._session_gen = 0
    self.segment_duration = SEGMENT_DURATION  # Duration of segment in seconds
    self.overlap_duration = OVERLAP_DURATION  # Overlap in seconds
    self.mouse_hook = None
    self.transcribed_segments = []
    # Where this session's transcript comes from, fixed by the key that STARTED
    # it: "realtime" (quick hotkey + ElevenLabs key: PCM streamed over a
    # WebSocket while speaking) or "batch" (the 20s-segment backend chain).
    # The key that STOPS the session still picks the post-processing.
    self._session_source = "batch"

    self.activation_mode = config.get("ACTIVATION_MODE", 'keyboard')  # or 'mouse'
    self.mouse_activation_button = config.get("MOUSE_ACTIVATION_BUTTON", 'middle')  # 'left'|'middle'|'right'
    self.double_tap_opens_window = (
        config.get("DOUBLE_TAP_OPENS_WINDOW", "true") or "true"
    ).lower() == "true"

    # Per-action hotkeys; "" = unbound.
    self.hotkeys = {aid: resolve_hotkey(config, aid) for aid in HOTKEY_ACTIONS}
    # Hard-capture (swallow) hotkeys via a low-level keyboard hook.
    self.suppress_hotkeys = (
        config.get("HOTKEYS_SUPPRESS", "true") or "true"
    ).lower() == "true"
    # action id -> keyboard.add_hotkey handle, so we can remove them on rebind.
    self.activation_hooks: dict[str, object] = {}
    # The action the *current* recording was started with (locked at start).
    self.active_action = "quick"
    # Set by the hotkey callback just before toggling, consumed on start.
    self._pending_action = "quick"
    # Hotkeys fire on key-DOWN (see press_and_talk), so a held key auto-repeats
    # into the callback. _hotkey_held swallows those repeats until the release
    # watcher (_arm_release_watch) sees the key go up; _hotkey_last_down is the
    # self-heal clock for a key-up we never got to see.
    self._hotkey_held = False
    self._hotkey_last_down = 0.0
    self._release_watch = None

    self.last_toggle_time = 0

    # Persist the (possibly changed) active backend back to config so the tray
    # menu / next launch reflect what we actually picked.
    config.set("TRANSCRIPTION_BACKEND", self.transcription_backend)
    config.set("WHISPER_MODEL", self.whisper_model_name)

    # NOTE: the active backend is initialized LATER, off the constructor, via
    # init_backend_async() — main() calls it once all UI sinks are wired so the
    # "loading" signal isn't emitted into the void. Constructing AudioWriter no
    # longer downloads/loads a model (and no longer blocks).

  # ---------- backend selection ----------

  def _build_cloud_clients(self):
    """(Re)build the OpenAI + Groq clients from the current stored secrets.

    Called from __init__ and from reload_transcription_settings (after a save),
    so a just-added/-removed key takes effect live. ``self.client`` also serves
    grammar correction and the on-demand text_operations, so rebuilding it
    refreshes those paths too. timeout/max_retries apply to every call made
    through each client. Groq uses an OpenAI-compatible API — same SDK, custom
    base_url; it's transcription-only (grammar correction stays on OpenAI)."""
    openai_api_key = self.config.get_secret("OPEN_AI_API_KEY")
    self.client = (
        openai.OpenAI(api_key=openai_api_key,
                      timeout=CLOUD_REQUEST_TIMEOUT,
                      max_retries=CLOUD_MAX_RETRIES)
        if openai_api_key else None
    )
    groq_api_key = self.config.get_secret("GROQ_API_KEY")
    self.groq_client = (
        openai.OpenAI(api_key=groq_api_key, base_url=GROQ_BASE_URL,
                      timeout=CLOUD_REQUEST_TIMEOUT,
                      max_retries=CLOUD_MAX_RETRIES)
        if groq_api_key else None
    )
    # Gemini is not OpenAI-compatible — services.gemini_transcribe talks to the
    # Interactions API directly, so there is no client object to build; the key
    # itself is the "client" (None = no credentials, same contract as above).
    self.gemini_api_key = self.config.get_secret("GEMINI_API_KEY") or None
    # ElevenLabs serves only the quick hotkey's realtime session — it is not a
    # member of the backend chain (see realtime_transcribe).
    self.elevenlabs_api_key = self.config.get_secret("ELEVENLABS_API_KEY") or None
    # Keys may have just changed (a topped-up account, a replaced key) — a
    # provider written off earlier deserves a fresh chance.
    self._reset_provider_health()

  def _reset_provider_health(self):
    """Forget every "this provider is down" verdict of the session.

    Three pieces of state, all session-only (never persisted — the provider
    may recover by next launch):
      _degraded_batch    (failed label, fallback label) once the batch chain
                         failed over (sticky, see _transcribe_audio_file)
      _degraded_quick    same pair for the quick hotkey's live engine
      _quick_engine_down live engines skipped after a STICKY_FAILURE_KINDS error
    Called wherever the user re-decides the backend: settings save / key
    rebuild (_build_cloud_clients) and a model pick from the tray. The
    indicator's banner follows on the next recording via provider_degraded.
    """
    self._degraded_batch = None
    self._degraded_quick = None
    self._quick_engine_down = frozenset()

  def _note_batch_failover(self, failed_label, exc, fallback_label):
    """Record + announce a sticky batch failover. Never raises — this runs on
    a transcription worker thread right before the text is returned."""
    self._degraded_batch = (failed_label, fallback_label)
    try:
      self.ui_bridge.provider_failover.emit(
          failed_label, classify_api_error(exc), fallback_label
      )
    except Exception as e:  # defensive: the notice is best-effort
      logger.warning(f"Failed to emit provider_failover: {e}")

  def _notify_quick_fallback(self, exc, engine_label):
    """The live session failed but the batch replay delivered: say so, naming
    the provider that actually transcribed (the active batch backend — the
    replay has already made any failover of its own sticky by now).

    Shares _notify_api_error's once-per-session gate, so it also replaces a
    later "pasted without correction" for the same recording, as before.
    Never raises — worker thread, mid-failure.
    """
    if self._api_error_notified:
      return
    self._api_error_notified = True
    try:
      serving = CLOUD_BACKEND_LABELS.get(
          getattr(self, "transcription_backend", None), "Local Whisper")
      self.ui_bridge.quick_fallback.emit(
          engine_label, classify_api_error(exc), serving
      )
    except Exception as e:  # defensive: the notice is best-effort
      logger.warning(f"Failed to emit quick_fallback: {e}")

  def _note_quick_engine_failure(self, engine, label, exc):
    """A live session failed: write the engine off for the session when a
    retry cannot help (STICKY_FAILURE_KINDS), and remember what serves instead
    so the next quick recording can say so. Transient failures (network, rate
    limit) change nothing — the engine is tried again next time."""
    if classify_api_error(exc) not in STICKY_FAILURE_KINDS:
      return
    self._quick_engine_down = self._quick_engine_down | {engine}
    nxt = self._pick_quick_engine()
    fallback = (QUICK_ENGINE_LABELS[nxt] if nxt else
                CLOUD_BACKEND_LABELS.get(
                    getattr(self, "transcription_backend", None), "Local Whisper"))
    logger.warning(
        f"Quick engine {label} written off for this session ({classify_api_error(exc)}); "
        f"quick dictation now goes via {fallback}"
    )
    # Same provider on both sides (Gemini Live down, Gemini batch still
    # answering) would read as nonsense in the banner — stay silent then.
    self._degraded_quick = (label, fallback) if fallback != label else None

  def _emit_provider_degraded(self):
    """Tell the indicator which degradation, if any, applies to the recording
    that is starting. Quick sessions care about the live engine; everything
    that runs on the batch chain cares about the batch failover. A healthy
    live session shows nothing even if the batch chain is degraded — it does
    not touch that chain. Never raises (hook thread)."""
    try:
      if self.active_action in REALTIME_ACTIONS and self._degraded_quick:
        state = self._degraded_quick
      elif self._session_source == "batch":
        state = self._degraded_batch
      else:
        state = None
      failed, fallback = state or ("", "")
      self.ui_bridge.provider_degraded.emit(failed, fallback)
    except Exception as e:  # defensive: the banner is best-effort
      logger.warning(f"Failed to emit provider_degraded: {e}")

  def _backend_has_creds(self, backend: str) -> bool:
    if backend == "local":
      return True
    if backend == "openai":
      return self.client is not None
    if backend == "groq":
      return self.groq_client is not None
    if backend == "gemini":
      return self.gemini_api_key is not None
    return False

  def _pick_initial_backend(self) -> str:
    """
    Walk the configured priority list. First backend with valid credentials
    becomes active. If nothing in the list works, fall back to 'local'.
    """
    priority = self.config.backend_priority
    for backend in priority:
      if backend not in ALL_BACKENDS:
        logger.warning(f"Unknown backend in priority list: {backend!r}, skipping")
        continue
      if self._backend_has_creds(backend):
        logger.info(f"Active transcription backend: {backend} (from priority {priority})")
        return backend
      logger.info(f"Skipping {backend}: no credentials available")
    logger.warning("No backend in priority list is usable, defaulting to 'local'")
    return "local"

  def _initialize_transcription_backend(self):
    """Initialize the active transcription backend (local Whisper or OpenAI API)."""
    self._unload_local_model()  # free VRAM/RAM if previously loaded

    if self.transcription_backend == "openai":
      if not self.client:
        logger.error("OpenAI backend selected but no API key — falling back to local")
        self.transcription_backend = "local"
        self.whisper_model_name = self.config.get("MODEL_LOCAL", "small")
        self.config.set("TRANSCRIPTION_BACKEND", "local")
        self.config.set("WHISPER_MODEL", self.whisper_model_name)
      else:
        logger.info(f"Using OpenAI transcription model: {self.whisper_model_name}")
        return

    if self.transcription_backend == "groq":
      if not self.groq_client:
        logger.error("Groq backend selected but no API key — falling back to local")
        self.transcription_backend = "local"
        self.whisper_model_name = self.config.get("MODEL_LOCAL", "small")
        self.config.set("TRANSCRIPTION_BACKEND", "local")
        self.config.set("WHISPER_MODEL", self.whisper_model_name)
      else:
        logger.info(f"Using Groq transcription model: {self.whisper_model_name}")
        return

    if self.transcription_backend == "gemini":
      if not self.gemini_api_key:
        logger.error("Gemini backend selected but no API key — falling back to local")
        self.transcription_backend = "local"
        self.whisper_model_name = self.config.get("MODEL_LOCAL", "small")
        self.config.set("TRANSCRIPTION_BACKEND", "local")
        self.config.set("WHISPER_MODEL", self.whisper_model_name)
      else:
        logger.info(f"Using Gemini transcription model: {self.whisper_model_name}")
        return

    # Lazy import — avoids loading ctranslate2 / CUDA when the user is running
    # cloud-only.
    from faster_whisper import WhisperModel

    # Pick the compute type explicitly so ctranslate2 doesn't infer float16 from
    # the model and then noisily auto-convert it. On CPU float16 isn't supported
    # efficiently — "int8" is the faster-whisper-recommended type (much faster,
    # far less RAM, especially for large-v3) and silences the conversion warning.
    # On CUDA "float16" matches how the weights are stored (no conversion).
    compute_type = "int8" if self.use_device == "cpu" else "float16"
    logger.info(
        f"Initializing local Whisper model: {self.whisper_model_name} "
        f"on {self.use_device} ({compute_type})"
    )
    try:
      self.whisper_model = WhisperModel(
          self.whisper_model_name,
          device=self.use_device,
          compute_type=compute_type,
      )
    except Exception as e:
      logger.error(f"Error initializing Whisper model: {e}")
      self.whisper_model = None
      raise e

  def _unload_local_model(self):
    """Drop reference to the local Whisper model and free GPU/CPU memory."""
    if getattr(self, "whisper_model", None) is None:
      return
    self.whisper_model = None
    import gc
    gc.collect()
    try:
      import torch
      if torch.cuda.is_available():
        torch.cuda.empty_cache()
    except Exception:
      pass

  # ---------- async backend init ----------

  def init_backend_async(self):
    """
    Kick off backend initialization in the background. Call this from main()
    AFTER every UI sink is connected to ui_bridge.model_state_changed — a worker
    emits "loading" almost immediately, and a Qt queued signal sent before the
    slots exist would be dropped (the indicator would never light up).
    """
    self._reinit_backend_async()

  def _reinit_backend_async(self):
    """Bump the init generation and spawn a daemon worker to (re)load the active
    backend. Used both for the first load and for every live model/device switch
    so the tray/settings thread never blocks on a model download."""
    with self._gen_lock:
      self._init_gen += 1
      gen = self._init_gen
    threading.Thread(
        target=self._load_backend_worker, args=(gen,), daemon=True
    ).start()

  def _current_gen(self) -> int:
    with self._gen_lock:
      return self._init_gen

  def _set_model_state(self, state: str, gen: int, force: bool = False) -> None:
    """Commit a model state, but only if this worker's generation is still the
    current one — a superseded load must not overwrite a newer request's state."""
    if gen != self._current_gen():
      return
    self._model_state = state
    self.ui_bridge.safe_emit_model_state(state, force=force)

  def _load_backend_worker(self, gen: int):
    """Background worker: bring the active backend up and report state.

    Cloud backends need no local model, so they report "ready" at once. The
    local backend announces "loading", builds the faster-whisper model under
    _load_lock (downloading it from HuggingFace on first use — the slow part we
    moved off the main thread), and reports "ready"/"failed". A CUDA build
    failure retries once on CPU, mirroring the old synchronous fallback."""
    if gen != self._current_gen():
      return

    if self.transcription_backend in CLOUD_BACKENDS:
      # No local model to construct; the cloud client was built in __init__.
      self._set_model_state("ready", gen)
      return

    self._set_model_state("loading", gen)
    with self._load_lock:
      if gen != self._current_gen():
        return  # a newer request arrived while we waited for the lock
      try:
        self._initialize_transcription_backend()
      except Exception as e:
        logger.error(f"Local model init failed: {e}", exc_info=True)
        # CUDA fallback: retry once on CPU before giving up.
        if self.use_device == "cuda":
          logger.warning("Local model init on CUDA failed — retrying on CPU")
          self.use_device = "cpu"
          self.config.set("USE_DEVICE", "cpu")
          try:
            self._initialize_transcription_backend()
          except Exception as e2:
            logger.error(f"Local model init on CPU also failed: {e2}", exc_info=True)
            self._set_model_state("failed", gen)
            return
        else:
          self._set_model_state("failed", gen)
          return
      self._set_model_state("ready", gen)

  def change_transcription_model(self, model_name):
    """
    Switch the active transcription model. The backend (local vs OpenAI API vs Groq)
    is auto-detected from the model name. Updates config and (re)initializes the backend.
    """
    new_backend = _backend_for_model(model_name)
    if new_backend is None:
      logger.error(f"Unknown transcription model: {model_name}")
      return

    self.whisper_model_name = model_name
    self.transcription_backend = new_backend
    # An explicit pick is a fresh start: drop the "primary is down" verdicts.
    self._reset_provider_health()
    logger.info(f"Transcription model changed to: {model_name} (backend={new_backend})")

    # Save BOTH the per-backend preference and the currently-active model.
    self.config.set(_model_key_for_backend(new_backend), model_name)
    self.config.set("TRANSCRIPTION_BACKEND", new_backend)
    self.config.set("WHISPER_MODEL", model_name)

    # An explicit tray pick is also a priority statement: make this backend the
    # head of BACKEND_PRIORITY so the Settings priority block + next launch agree
    # with the choice (and a later Settings save, which re-picks by priority,
    # doesn't revert it).
    self._promote_backend_priority(new_backend)

    # Re-init in the background so the tray/settings thread doesn't block on a
    # model (re)load. _init_gen makes this switch supersede any in-flight load.
    self._reinit_backend_async()

  def _promote_backend_priority(self, backend):
    """Move ``backend`` to the front of BACKEND_PRIORITY (preserving the relative
    order of the rest) and persist. Keeps an explicit tray model/backend pick
    consistent with the Settings priority block and across restarts. The
    defensive top-up keeps every backend reachable even if the stored list was
    truncated."""
    current = self.config.backend_priority
    reordered = [backend] + [b for b in current if b != backend]
    for b in ALL_BACKENDS:
      if b not in reordered:
        reordered.append(b)
    self.config.set_backend_priority(reordered)

  def change_activation_mode(self):
    """Toggle between keyboard and mouse activation modes and persist."""
    self.activation_mode = 'keyboard' if self.activation_mode == 'mouse' else 'mouse'
    logger.info(f"Activation mode changed to: {self.activation_mode}")
    self.config.set("ACTIVATION_MODE", self.activation_mode)
    # Rebuild hooks for the new mode: tear down both, then install what the new
    # mode needs. Otherwise the keyboard hotkeys would keep suppressing
    # F9/F10/F11 after switching to mouse mode (and vice versa).
    self._unhook_all()
    if self.mouse_hook:
      try:
        mouse.unhook(self.mouse_hook)
      except Exception as e:
        logger.debug(f"mouse.unhook failed (continuing): {e}")
      self.mouse_hook = None
    self.press_and_talk()

  def change_mouse_activation_button(self):
    """Toggle between mouse activation buttons and persist."""
    self.mouse_activation_button = 'middle' if self.mouse_activation_button == 'right' else 'right'
    logger.info(f"Activation button changed to: {self.mouse_activation_button}")
    self.config.set("MOUSE_ACTIVATION_BUTTON", self.mouse_activation_button)

  def toggle_suppress_hotkeys(self):
    """Toggle hard-capture (suppression) of hotkeys, persist, and re-register."""
    self.suppress_hotkeys = not self.suppress_hotkeys
    self.config.set("HOTKEYS_SUPPRESS", "true" if self.suppress_hotkeys else "false")
    logger.info(f"Hotkey hard-capture set to: {self.suppress_hotkeys}")
    if self.activation_mode == 'keyboard':
      self._unhook_all()
      self.press_and_talk()

  def reload_activation_settings(self):
    """Re-sync activation config from disk and rebuild the input hooks live.

    The Settings window only writes config.env; it never touches the live
    AudioWriter. Without this the engine keeps the activation mode, hotkeys and
    suppression flag it captured at launch, so a changed hotkey (e.g. F9 -> F1)
    didn't take effect until restart. Mirrors the field reads in __init__, then
    tears down BOTH keyboard and mouse hooks and reinstalls whatever the current
    mode needs — the same rebuild change_activation_mode does for the tray.
    """
    config = self.config
    self.activation_mode = config.get("ACTIVATION_MODE", 'keyboard')
    self.mouse_activation_button = config.get("MOUSE_ACTIVATION_BUTTON", 'middle')
    self.double_tap_opens_window = (
        config.get("DOUBLE_TAP_OPENS_WINDOW", "true") or "true"
    ).lower() == "true"
    for aid in HOTKEY_ACTIONS:
      self.hotkeys[aid] = resolve_hotkey(config, aid)
    self.suppress_hotkeys = (
        config.get("HOTKEYS_SUPPRESS", "true") or "true"
    ).lower() == "true"

    self._unhook_all()
    if self.mouse_hook:
      try:
        mouse.unhook(self.mouse_hook)
      except Exception as e:
        logger.debug(f"mouse.unhook failed (continuing): {e}")
      self.mouse_hook = None
    self.press_and_talk()

  def reload_transcription_settings(self):
    """Re-resolve the live transcription backend from config after a settings
    save — Settings is the final source of truth.

    The Transcription page only writes config (backend priority, API keys,
    per-backend model); without this the engine keeps the backend/model/clients
    captured at launch. We rebuild the cloud clients from the (possibly new)
    keys, re-pick the active backend by priority (now credentials-aware), update
    the model/device, mirror the choice into config, and reload the model in the
    background via the same generation-guarded machinery the tray uses. This
    intentionally overrides any manual backend/model pick made via the tray
    earlier in the session.
    """
    config = self.config
    self._build_cloud_clients()                                # live key add/remove
    self.transcription_backend = self._pick_initial_backend()  # re-pick by priority
    self.whisper_model_name = config.get(_model_key_for_backend(self.transcription_backend))
    self.use_device = config.get("USE_DEVICE", "cpu")
    self._input_device_config = config.get("INPUT_DEVICE", "") or ""
    self._audio_enhance_profile = normalize_enhance_profile(
        config.get("AUDIO_ENHANCE", "light")
    )
    # Mirror the resolved choice so the tray menu / next launch agree (the page
    # writes MODEL_* + BACKEND_PRIORITY but not TRANSCRIPTION_BACKEND/WHISPER_MODEL).
    config.set("TRANSCRIPTION_BACKEND", self.transcription_backend)
    config.set("WHISPER_MODEL", self.whisper_model_name)
    logger.info(
        f"Transcription settings reloaded: backend={self.transcription_backend}, "
        f"model={self.whisper_model_name}, device={self.use_device}, "
        f"enhance={self._audio_enhance_profile}, "
        f"input_device={self._input_device_config!r}"
    )
    self._reinit_backend_async()
    # INPUT_DEVICE may have changed — swap the pre-opened stream to match.
    self._prepare_standby_stream()

  def toggle_use_device(self):
    """
    Toggle between CPU and CUDA devices and persist.
    No-op when a cloud backend is active.
    """
    if self.transcription_backend in CLOUD_BACKENDS:
      logger.info("Device toggle ignored: cloud transcription is active")
      return

    self.use_device = 'cuda' if self.use_device == 'cpu' else 'cpu'
    logger.info(f"Device toggled to: {self.use_device}")
    self.config.set("USE_DEVICE", self.use_device)

    # Re-initialize the model with the new device in the background. The
    # CUDA->CPU fallback now lives in the worker (_load_backend_worker).
    self._reinit_backend_async()

  def set_backend_device(self, target):
    """
    Set the active transcription target. ``target`` is one of:
      - 'cuda'    — local Whisper on CUDA
      - 'cpu'     — local Whisper on CPU
      - 'openai'  — OpenAI cloud transcription
      - 'groq'    — Groq cloud transcription
      - 'gemini'  — Google Gemini cloud transcription
    """
    if target == 'openai':
      self.change_transcription_model(
          self.config.get("MODEL_OPENAI", "gpt-transcribe")
      )
      return

    if target == 'groq':
      self.change_transcription_model(
          self.config.get("MODEL_GROQ", "whisper-large-v3-turbo")
      )
      return

    if target == 'gemini':
      self.change_transcription_model(
          self.config.get("MODEL_GEMINI", "gemini-3.5-transcribe")
      )
      return

    if target not in ('cuda', 'cpu'):
      logger.error(f"Unknown backend device target: {target}")
      return

    self.use_device = target
    self.config.set("USE_DEVICE", self.use_device)

    if self.transcription_backend in CLOUD_BACKENDS:
      # Coming back from cloud — pick the configured local model
      self.change_transcription_model(self.config.get("MODEL_LOCAL", "small"))
      return

    # Already on local backend, just re-init with the new device in the
    # background. The CUDA->CPU fallback lives in the worker.
    self._reinit_backend_async()

  def listen_for_new_activation_key(self, action_id="quick"):
    """Wait for the user to press a key and bind it to `action_id`."""
    spec = HOTKEY_ACTIONS.get(action_id)
    if spec is None:
      logger.error(f"Unknown hotkey action: {action_id}")
      return
    # Logs name the action by its canonical id, not its display label: the
    # label is now translated, and a Russian log line helps nobody reading a
    # bug report. (Same id the next line already logs.)
    logger.info(f"Waiting for new key for '{action_id}'. Please press the desired key...")
    new_key = keyboard.read_key()
    self.change_activation_key(new_key, action_id)
    logger.info(f"New key for '{action_id}' set: {self.hotkeys[action_id]}")

  def change_activation_key(self, new_key, action_id="quick"):
    """Rebind `action_id` to `new_key`, persist it, and re-register all hotkeys."""
    spec = HOTKEY_ACTIONS.get(action_id)
    if spec is None:
      logger.error(f"Unknown hotkey action: {action_id}")
      return
    # A key belongs to one action: taking it from another leaves that one
    # unbound (same rule as "Catch the key" in Settings).
    for other_id, other_key in self.hotkeys.items():
      if other_id != action_id and other_key and other_key.lower() == new_key.lower():
        self.hotkeys[other_id] = ""
        self.config.set(HOTKEY_ACTIONS[other_id]["config_key"], "")
        logger.info(f"Key {new_key} moved from '{other_id}' to '{action_id}'")
    self.hotkeys[action_id] = new_key
    self.config.set(spec["config_key"], new_key)
    # Re-register everything so the new binding takes effect immediately and
    # the old hook is removed (no double-firing).
    self._unhook_all()
    time.sleep(0.5)  # let the just-pressed key settle before re-hooking
    self.press_and_talk()

  def _whisper_language_hint(self):
    """Derive the Whisper language hint from PRIMARY_LANGUAGE via the shared map.

    Returns the BCP-47 short code (e.g. "en", "ru") or None if no mapping
    exists — in which case the transcription API auto-detects.
    """
    from services.text_operations import LANGUAGE_TO_WHISPER_CODE
    return LANGUAGE_TO_WHISPER_CODE.get(self.config.get("PRIMARY_LANGUAGE") or "")

  def _notify_api_error(self, context, exc, provider=None):
    """Surface a user-actionable API failure via UIBridge.api_error.

    At most once per recording session (see _api_error_notified) — the same
    dead quota otherwise fires from every streaming segment, the final pass
    and the LLM correction. ``context`` is "transcribe" (no text produced) or
    "postprocess" (raw text pasted uncorrected). Provider comes from the
    CloudApiError wrapper when present, else from ``provider``/the active
    backend. Never raises — this runs on worker threads mid-failure.
    """
    if self._api_error_notified:
      return
    self._api_error_notified = True
    try:
      if isinstance(exc, CloudApiError):
        provider = exc.provider
      if provider is None:
        provider = CLOUD_BACKEND_LABELS.get(
            self.transcription_backend, "Local Whisper"
        )
      self.ui_bridge.api_error.emit(context, classify_api_error(exc), provider)
    except Exception as e:  # pragma: no cover - defensive, notification is best-effort
      logger.warning(f"Failed to emit api_error notification: {e}")

  def drop_all(self):
    """Reset all recording and transcription state variables."""
    logger.info("Resetting all recording and transcription states")
    self.transcribed_segments = []
    self.transcription_thread = None
    self.recording_timer = None
    self.mouse_hook = None

  def _hwnd_is_own_process(self, hwnd) -> bool:
    """Return True if `hwnd` belongs to our own process (i.e. the user had an
    Omni Verte window focused when recording started).

    Windows-only; any failure (non-Windows, invalid hwnd) is treated as "not
    ours" so the normal auto-paste path is preserved.
    """
    if not hwnd:
      return False
    try:
      pid = ctypes.c_ulong(0)
      ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
      return pid.value == os.getpid()
    except Exception as e:
      logger.debug(f"_hwnd_is_own_process check failed: {e}")
      return False

  def start_recording(self):
    """
    Starts audio recording from the microphone and initiates streaming transcription.
    Sets up the audio stream, starts the transcription thread, and sets a safety timer.
    """
    logger.info("Starting audio recording...")

    # Guard: the local backend's model may still be downloading/loading (or have
    # failed) since init now runs in the background. Cloud backends need no local
    # model, so they're never blocked here. Re-assert the model state (force, to
    # bypass the dedup) so the user sees WHY the hotkey did nothing.
    realtime = self._session_source == "realtime"
    if not realtime and self.transcription_backend == "local" and self._model_state != "ready":
      logger.info(f"Recording blocked: local model not ready ({self._model_state})")
      self.ui_bridge.safe_emit_model_state(self._model_state, force=True)
      return

    self.audio_queue = queue.Queue()  # Reset the queue
    # New session — clear any "skip paste" intent left over from a previous one.
    self._skip_next_paste = False
    # New session — the once-per-session API-error notification re-arms.
    self._api_error_notified = False
    # New session — tell the indicator whether this recording runs on a
    # fallback provider (also clears a banner/notice left by the previous one).
    self._emit_provider_degraded()
    # Defensive: cancel any stale deferred-stop timer (e.g. if it fired racey
    # with this start). The guard in _deferred_stop is the primary defence.
    if self._pending_stop_timer is not None:
      self._pending_stop_timer.cancel()
      self._pending_stop_timer = None
    try:
      # Capture whichever window the user was working in — we'll restore it
      # before pasting so Ctrl+V doesn't accidentally land in our own window.
      try:
        self._prev_foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
        self._foreground_was_own = self._hwnd_is_own_process(
            self._prev_foreground_hwnd
        )
      except Exception:
        self._prev_foreground_hwnd = 0
        self._foreground_was_own = False

      # NOT "recording" yet: opening the device takes 0.1–0.5s (more on slow
      # laptops) and nothing said in that window is captured. The indicator is
      # the user's "speak now" cue, so it flips only once the first frame has
      # actually arrived — see _announce_recording below.
      self._capture_announced = False
      self._capture_live = threading.Event()
      self.ui_bridge.audio_level = 0.0  # start the equalizer flat until first frame
      # Re-read capture settings so a settings save mid-session applies on the
      # next press without requiring a full backend reinit.
      self._input_device_config = self.config.get("INPUT_DEVICE", "") or ""
      self._audio_enhance_profile = normalize_enhance_profile(
          self.config.get("AUDIO_ENHANCE", "light")
      )
      # Set up the audio input stream. device=None → PortAudio system default.
      # Fast path: the stream pre-opened after the previous dictation. If it
      # went stale (device unplugged since) start() raises and we fall through
      # to a fresh open, exactly as before the pre-open existed.
      stream = self._take_standby(self._input_device_config)
      if stream is not None:
        try:
          stream.start()
          logger.info("Started pre-opened input stream")
        except Exception as e:
          logger.warning(f"Pre-opened input stream failed to start ({e}); reopening")
          self._close_quietly(stream)
          stream = None
      if stream is None:
        device_index = resolve_input_device(self._input_device_config)
        stream = self._open_input_stream(device_index)
        stream.start()
      self.stream = stream
      self.is_recording = True

      # Start streaming transcription. Bump the session gen first so this
      # session owns the shared state and any still-finishing tail of the
      # previous one (its process_text) sees a newer gen and bows out.
      self._session_gen += 1
      self.streaming = True
      self.transcription_thread = threading.Thread(
          target=self.realtime_transcribe if realtime else self.streaming_transcribe,
          args=(self._session_gen,),
      )
      self.transcription_thread.start()

      # Flip the indicator to "recording" once the mic really delivers audio.
      # Off this thread: we may be inside the low-level keyboard hook, which
      # must return promptly.
      threading.Thread(
          target=self._announce_recording,
          args=(self._session_gen, self._capture_live),
          daemon=True,
      ).start()

      # Set a 10-minute (600 seconds) safety timer for auto-stop
      self.recording_timer = threading.Timer(600, self.stop_recording)
      self.recording_timer.start()

      logger.info("Recording started. Press the activation key/button again to stop recording.")
    except Exception as e:
      logger.error(f"Error starting recording: {e}")

  # Bare instances (tests drive streaming_transcribe without start_recording)
  # behave as "already announced"; start_recording resets it per session.
  _capture_announced = True
  # Same for the hotkey release-watch state (set per instance in __init__).
  _hotkey_held = False
  _hotkey_last_down = 0.0
  _release_watch = None

  def _announce_recording(self, session_gen, live):
    """Emit "recording" when the first audio frame of this session arrives.

    ``live`` is the session's own Event, set by audio_callback. If no frame
    shows up within the timeout the status flips anyway: the stream is open,
    and the indicator's flat bars are how a dead/switched mic is surfaced.
    """
    started = time.monotonic()
    if live.wait(timeout=FIRST_FRAME_TIMEOUT):
      logger.info(
          f"First audio frame {time.monotonic() - started:.3f}s after stream start"
      )
    else:
      logger.warning(
          f"No audio frame within {FIRST_FRAME_TIMEOUT}s of stream start"
      )
    # A stop (or a newer session) may have won the race while we waited.
    if session_gen != self._session_gen or not self.is_recording:
      return
    self._capture_announced = True
    self.ui_bridge.safe_emit_status("recording")

  def stop_recording(self):
    """
    Stops recording, halts streaming transcription, and initiates final processing.
    Collects remaining audio data and processes it for transcription.
    """
    if not self.is_recording:
      return

    # The session being stopped is the current one; capture its gen so the
    # deferred process_text() can tell whether a newer session started while it
    # was busy and avoid clobbering it.
    session_gen = self._session_gen

    logger.info("Stopping recording...")

    # IMMEDIATELY show user that stop command was received
    self.ui_bridge.safe_emit_status("processing")

    # Set flags to signal threads to stop
    self.is_recording = False
    self.streaming = False  # Signal the transcription thread to stop

    # Stop audio stream IMMEDIATELY to prevent more data accumulation
    try:
      self.stream.stop()
      self.stream.close()
    except Exception as e:
      logger.error(f"Error stopping audio stream: {e}")
    # Re-arm the pre-opened stream now, not after processing: the next press
    # may come while this dictation is still being transcribed.
    self._prepare_standby_stream()

    # Remove mouse handler to prevent duplicate calls
    if self.mouse_hook:
      mouse.unhook(self.mouse_hook)
      self.mouse_hook = None

    # Wait for transcription thread with timeout (don't block indefinitely).
    # Capture the handle into a local: a racing reset (a concurrent
    # _deferred_stop / drop_all) can null self.transcription_thread mid-method,
    # which previously turned the is_alive() check into an AttributeError. The
    # local is reused for the no-data wait below so both reads see one object.
    transcription_thread = self.transcription_thread
    if transcription_thread:
      transcription_thread.join(timeout=TRANSCRIPTION_THREAD_TIMEOUT)
      if transcription_thread.is_alive():
        logger.warning("Transcription thread timeout - proceeding without waiting")

    # Cancel the safety timer
    if self.recording_timer:
      self.recording_timer.cancel()

    logger.info("Recording finished.")

    # Collect remaining audio data
    audio_frames = []
    while not self.audio_queue.empty():
      audio_frames.append(self.audio_queue.get())

    # Handle case with no recorded data
    if len(audio_frames) == 0:
      logger.info("No recorded data available.")
      # The streaming thread drained the queue. If it timed out above, its
      # final segment hasn't been appended to transcribed_segments yet — wait
      # for it now (streaming flag is already False, so it will exit soon).
      if transcription_thread and transcription_thread.is_alive():
        logger.info("Waiting for streaming transcription to complete...")
        transcription_thread.join(timeout=60.0)
      # Use transcribed segments if available
      if self.transcribed_segments:
        # Diagnostics: the full per-segment list makes segment-boundary
        # duplications (overlap re-transcribed in two consecutive segments)
        # reconstructable from the log.
        logger.info(
            f"Joining {len(self.transcribed_segments)} segment(s): "
            f"{self.transcribed_segments!r}"
        )
        # Dedup the re-transcribed audio-overlap at each segment seam (a raw
        # " ".join doubles whatever words landed on a 20s boundary — the classic
        # "…две недели. Две недели, и…" duplication).
        final_transcript = _dedup_overlap_join(self.transcribed_segments)
        self.process_text(final_transcript, session_gen=session_gen)
      else:
        # Nothing to paste — but we still must reset UI/state, otherwise the
        # indicator stays green and the user thinks the app froze.
        logger.info("Nothing to transcribe — resetting state.")
        self.ui_bridge.safe_emit_status("idle")
        self.drop_all()
        self.press_and_talk()
      self.transcribed_segments = []
      return

    # Process recorded audio data
    audio_data = np.concatenate(audio_frames, axis=0)
    temp_audio_file = os.path.join(_TEMP_DIR, "temp_audio.wav")
    self._write_transcription_wav(temp_audio_file, audio_data)
    logger.info("Audio saved to temporary file.")
    try:
      self.process_audio_file(temp_audio_file, session_gen=session_gen)
    except Exception as e:
      # Transcription failed outright (dead quota, revoked key, no network).
      # Without this catch the exception kills the timer/hook thread that
      # called us, the reset tail never runs, and the indicator hangs on
      # "processing" forever — the user reads it as a freeze. Tell them what
      # happened, flip the window status to "error", and restore the hooks so
      # the next hotkey press works.
      logger.error(f"Final transcription failed: {e}", exc_info=True)
      if session_gen == self._session_gen:
        self._notify_api_error("transcribe", e)
        self.ui_bridge.safe_emit_status("error")
        self.drop_all()
        self.press_and_talk()

  def _open_input_stream(self, device_index):
    """Open a mono int16 InputStream; fall back to default if device is gone."""
    kwargs = dict(
        samplerate=self.fs,
        channels=1,
        dtype="int16",
        callback=self.audio_callback,
    )
    if device_index is not None:
      kwargs["device"] = device_index
      try:
        logger.info(f"Opening input stream on device index {device_index}")
        return sd.InputStream(**kwargs)
      except Exception as e:
        logger.warning(
            f"Failed to open input device index {device_index} ({e}); "
            f"falling back to system default"
        )
        kwargs.pop("device", None)
    return sd.InputStream(**kwargs)

  # Bare instances (tests build AudioWriter via __new__) share these defaults.
  _standby = None
  _standby_lock = threading.Lock()

  @staticmethod
  def _close_quietly(stream):
    try:
      stream.close()
    except Exception as e:
      logger.debug(f"input stream close failed: {e}")

  def _prepare_standby_stream(self):
    """Pre-open (never start) the input stream for the next dictation.

    Runs on its own thread: opening the device blocks for ~100ms+ and callers
    are the keyboard hook thread, the GUI thread or stop_recording. Idempotent:
    a standby already open for the current INPUT_DEVICE is kept.
    """
    if not PREOPEN_INPUT_STREAM:
      return
    threading.Thread(target=self._open_standby, daemon=True).start()

  def _open_standby(self):
    try:
      cfg = self.config.get("INPUT_DEVICE", "") or ""
      with self._standby_lock:
        # A session that started meanwhile opened its own stream; its stop
        # will re-arm us. Don't hold a second handle on the device.
        if self.is_recording:
          return
        if self._standby is not None:
          if self._standby[1] == cfg:
            return
          self._close_quietly(self._standby[0])  # device changed in Settings
          self._standby = None
        started = time.monotonic()
        stream = self._open_input_stream(resolve_input_device(cfg))
        self._standby = (stream, cfg)
        logger.info(
            f"Input stream pre-opened in {time.monotonic() - started:.3f}s (not started)"
        )
    except Exception as e:
      # Purely an optimisation: start_recording opens on demand without it.
      logger.debug(f"pre-open of input stream failed: {e}")

  def _take_standby(self, cfg):
    """Hand over the pre-opened stream if it matches ``cfg``, else None."""
    with self._standby_lock:
      standby, self._standby = self._standby, None
    if standby is None:
      return None
    stream, standby_cfg = standby
    if standby_cfg != cfg:
      self._close_quietly(stream)
      return None
    return stream

  def _drop_standby(self):
    with self._standby_lock:
      standby, self._standby = self._standby, None
    if standby is not None:
      self._close_quietly(standby[0])

  def _write_transcription_wav(self, path, pcm):
    """Apply AUDIO_ENHANCE profile and write int16 mono WAV for the ASR backends.

    Overlap / queue buffers stay raw; only the array about to be transcribed is
    enhanced, so streaming seam logic is unchanged and off is byte-stable.
    """
    prepared = prepare_for_transcription(
        pcm, self.fs, profile=self._audio_enhance_profile
    )
    if logger.isEnabledFor(logging.DEBUG):
      # Cheap diagnostics when users report "garbage ASR" after capture changes.
      def _rms(a):
        x = np.asarray(a, dtype=np.float64).reshape(-1)
        if x.size == 0:
          return 0.0
        return float(np.sqrt(np.mean((x / 32768.0) ** 2)))

      logger.debug(
          "WAV prep profile=%s shape_in=%s dtype_in=%s rms_in=%.4f "
          "shape_out=%s rms_out=%.4f peak_out=%s",
          self._audio_enhance_profile,
          getattr(pcm, "shape", None),
          getattr(pcm, "dtype", None),
          _rms(pcm),
          prepared.shape,
          _rms(prepared),
          int(np.max(np.abs(prepared))) if prepared.size else 0,
      )
    wav.write(path, self.fs, prepared)

  def audio_callback(self, indata, frames, time_info, status):
    """Callback function for the audio stream — pushes incoming data to the queue."""
    if status:
      logger.warning(f"Audio stream status: {status}")

    if not self.is_recording:
      return

    # First frame of the session → wake _announce_recording (the indicator's
    # "speak now" flip). Checked first so the steady state is a lock-free read.
    live = self._capture_live
    if not live.is_set():
      live.set()

    # Live level for the floating indicator's equalizer. int16 → normalized RMS
    # in [0, 1], stored in a plain field polled by the widget's animation timer.
    # NO Qt here: this runs on the realtime PortAudio thread, and emitting a
    # cross-thread Qt signal ~25×/sec starved the keyboard hook past the OS
    # LowLevelHooks timeout and dropped hotkeys. A bare store is GIL-atomic and
    # allocation-free. A sustained near-zero level is how the indicator surfaces
    # a dead/switched mic (flat bars → "no signal").
    # Level is RAW capture (pre-enhance) — enhance runs only at WAV write time.
    x = indata.astype(np.float32) / 32768.0
    self.ui_bridge.audio_level = float(np.sqrt(np.mean(x * x)))

    self.audio_queue.put(indata.copy())

  def streaming_transcribe(self, session_gen=None):
    """
    Performs streaming transcription with overlapping audio segments.
    Each segment lasts 20 seconds with a 1-second overlap between segments.
    Processes audio in chunks to provide real-time feedback.

    ``session_gen`` is the session this thread belongs to. If a newer session
    has started, this thread is stale — it stops appending to the shared
    transcript and stops driving the status indicator, so it can't fight the
    live session for the UI or pollute its segments.
    """
    def _current():
      return session_gen is None or session_gen == self._session_gen
    buffer = []  # Temporary audio data buffer
    frames_overlap = int(self.overlap_duration * self.fs)
    segment_start_time = time.time()
    overlap_data = None
    segment_index = 0  # 1-based; only for diagnostics (segment-boundary dup analysis)

    while True:
      try:
        data = self.audio_queue.get(timeout=0.1)
        buffer.append(data)
      except queue.Empty:
        pass

      elapsed = time.time() - segment_start_time
      finalizing = not self.streaming
      # Process segment if enough time has elapsed or recording has stopped
      if elapsed >= self.segment_duration or (finalizing and buffer):
        # On finalize, drain ALL remaining queue data into the buffer up front,
        # so we process the leftover as a single segment and exit cleanly —
        # otherwise tiny residual chunks from sounddevice keep arriving and
        # each gets re-transcribed together with the 1s overlap_data, producing
        # duplicate / hallucinated output.
        if finalizing:
          try:
            while True:
              buffer.append(self.audio_queue.get_nowait())
          except queue.Empty:
            pass

        if buffer:
          segment_data = np.concatenate(buffer, axis=0)
          overlap_frames_used = 0
          if overlap_data is not None:
            overlap_frames_used = overlap_data.shape[0]
            segment_data = np.concatenate((overlap_data, segment_data), axis=0)

          segment_index += 1
          seg_seconds = segment_data.shape[0] / self.fs
          overlap_seconds = overlap_frames_used / self.fs

          temp_segment_file = os.path.join(_TEMP_DIR, "temp_segment.wav")
          self._write_transcription_wav(temp_segment_file, segment_data)
          logger.info(
              f"Transcribing segment #{segment_index} "
              f"(audio {seg_seconds:.1f}s, overlap {overlap_seconds:.1f}s, "
              f"finalizing={finalizing})..."
          )
          # Only surface "processing" once recording has actually STOPPED.
          # Mid-stream segments are cut and transcribed WHILE the user is still
          # dictating; flipping the indicator to "processing" then reads as "it
          # stopped listening" and confuses users who are still talking. The mic
          # is open and audio_callback keeps feeding the equalizer, so
          # "recording" stays the honest state until stop_recording. The tail
          # block below re-asserts "recording" every iteration while live.
          if _current() and finalizing:
            self.ui_bridge.safe_emit_status("processing")

          try:
            segment_text = self._transcribe_audio_file(temp_segment_file, streaming=True)
            logger.info(f"Segment #{segment_index} raw text: {segment_text!r}")

            stripped = segment_text.strip()
            normalized = stripped.lower().rstrip(".!?…").strip()

            if not stripped:
              logger.info(f"Segment #{segment_index} skipped (empty).")
            elif normalized in WHISPER_HALLUCINATIONS:
              logger.info(f"Segment #{segment_index} skipped (known hallucination: {stripped!r}).")
            elif not _current():
              logger.info(f"Segment #{segment_index} dropped (stale session — newer recording started).")
            else:
              self.transcribed_segments.append(segment_text)
          except Exception as e:
            logger.error(f"Error transcribing segment: {e}")
            # Words were lost — tell the user why (quota/key/network), once
            # per session. Only the live session may notify: a stale thread's
            # failure is not news about the current recording.
            if _current():
              self._notify_api_error("transcribe", e)

          # Save the last frames for overlap (only while continuing to stream)
          if not finalizing:
            total_frames = segment_data.shape[0]
            if total_frames > frames_overlap:
              overlap_data = segment_data[-frames_overlap:]
            else:
              overlap_data = segment_data

          buffer = []
          segment_start_time = time.time()

      # safe_emit_status dedupes on the bridge side, so flipping these every
      # loop iteration costs nothing if nothing actually changed. Only the
      # current session drives the indicator — a stale thread leaves the UI to
      # whoever owns the live session (and to stop_recording's finalize).
      if _current():
        if self.is_recording:
          # Until the first frame lands the indicator must not claim
          # "recording" — _announce_recording owns that first flip.
          if self._capture_announced:
            self.ui_bridge.safe_emit_status("recording")
        else:
          self.ui_bridge.safe_emit_status("processing")

      if not self.streaming and self.audio_queue.empty() and not buffer:
        break

    logger.info("Streaming transcription completed.")

  def realtime_transcribe(self, session_gen=None):
    """Quick-hotkey counterpart of streaming_transcribe: stream PCM to the
    quick engine (Gemini Live or ElevenLabs Scribe v2 Realtime, see
    _pick_quick_engine) while the user speaks.

    The server transcribes as the audio arrives, so at stop only the tail is
    left to finalize — the transcript is ready almost the moment speech ends.
    A local copy of every frame is kept: if the session fails (no network,
    bad key, quota, session limit) the audio is replayed through the ordinary
    batch chain, so a failure costs latency, never the words. The result lands
    in transcribed_segments like a single batch segment — stop_recording's
    join/process path is shared.
    """
    def _current():
      return session_gen is None or session_gen == self._session_gen

    # Captured now: a newer recording may re-pick _quick_engine before this
    # session's failure is handled below.
    engine = self._quick_engine
    session, provider = self._open_quick_session()
    session.start()
    frames = []
    while True:
      try:
        data = self.audio_queue.get(timeout=0.05)
      except queue.Empty:
        if not self.streaming and self.audio_queue.empty():
          break
        continue
      frames.append(data)
      session.send_pcm(data.tobytes())

    if _current():
      self.ui_bridge.safe_emit_status("processing")
    finish_started = time.monotonic()
    try:
      text = session.finish()
      logger.info(
          f"{provider} realtime transcript ({time.monotonic() - finish_started:.2f}s "
          f"after stop): {text!r}"
      )
    except Exception as e:
      logger.warning(f"Realtime session failed, replaying audio via batch chain: {e}")
      text = self._transcribe_frames_batch(frames)
      # After the replay, so the remembered fallback names the batch provider
      # that actually answered (the replay itself may have failed over).
      self._note_quick_engine_failure(engine, provider, e)
      # Told only once the replay worked: the text did arrive, just the slow
      # way. A failed replay reports itself ("not transcribed") instead.
      if text and _current():
        self._notify_quick_fallback(e, provider)

    text = self._scrub_glossary_echo(text or "")
    if not text.strip():
      logger.info("Realtime session produced no text.")
    elif not _current():
      logger.info("Realtime transcript dropped (stale session — newer recording started).")
    else:
      self.transcribed_segments.append(text)
    logger.info("Realtime transcription completed.")

  def _pick_quick_engine(self):
    """Engine for a live session: "gemini" | "elevenlabs" | None (no key → batch).

    Same rule as the settings pages (config_store.choose_quick_engine), on the
    keys this engine instance holds.
    """
    config = getattr(self, "config", None)    # absent on partially-built instances
    # An engine written off this session (_note_quick_engine_failure) is
    # treated as keyless, so the existing rule falls through to the other
    # engine or, with none left, to the batch chain.
    down = self._quick_engine_down
    return choose_quick_engine(
        config.get("QUICK_ENGINE") if config else None,
        bool(self.gemini_api_key) and "gemini" not in down,
        bool(self.elevenlabs_api_key) and "elevenlabs" not in down,
    )

  def _open_quick_session(self):
    """(session, provider label) for _quick_engine."""
    if self._quick_engine == "gemini":
      setup = self._gemini_live_setup()
      logger.info(f"Transcribing via Gemini Live ({gemini_live.MODEL_ID})")
      session = gemini_live.LiveSession(self.gemini_api_key, setup)
      return session, "Gemini"
    url = self._realtime_url()
    logger.info(f"Transcribing via ElevenLabs realtime ({elevenlabs_realtime.MODEL_ID})")
    session = elevenlabs_realtime.RealtimeSession(self.elevenlabs_api_key, url)
    return session, "ElevenLabs"

  def _gemini_live_setup(self):
    """Live setup: PRIMARY (+SECONDARY for code-switching) and layer B."""
    from services.text_operations import LANGUAGE_TO_WHISPER_CODE
    secondary = LANGUAGE_TO_WHISPER_CODE.get(self.config.get("SECONDARY_LANGUAGE") or "")
    vocabulary = None
    if self._glossary_asr_active():
      vocabulary = self.glossary.canonical_terms() or None
    return gemini_live.build_setup(
        language=self._whisper_language_hint(),
        secondary_languages=[secondary] if secondary else None,
        vocabulary=vocabulary,
    )

  def _realtime_url(self):
    """Session URL: PRIMARY (+SECONDARY for code-switching) and layer B."""
    from services.text_operations import LANGUAGE_TO_WHISPER_CODE
    secondary = LANGUAGE_TO_WHISPER_CODE.get(self.config.get("SECONDARY_LANGUAGE") or "")
    keyterms = None
    if self._glossary_asr_active():
      keyterms = self.glossary.canonical_terms() or None
    return elevenlabs_realtime.build_url(
        language=self._whisper_language_hint(),
        secondary_languages=[secondary] if secondary else None,
        keyterms=keyterms,
        no_verbatim=self._flag_on("QUICK_CLEAN_FILLERS"),
    )

  def _transcribe_frames_batch(self, frames):
    """Fallback for a failed realtime session: one WAV through the chain.

    Returns "" (never raises) when there is no audio or the chain fails too;
    the chain's own failure is reported like any other transcription error.
    """
    if not frames:
      return ""
    path = os.path.join(_TEMP_DIR, "temp_realtime_fallback.wav")
    try:
      self._write_transcription_wav(path, np.concatenate(frames, axis=0))
      return self._transcribe_audio_file(path)
    except Exception as e:
      logger.error(f"Batch fallback for realtime session failed: {e}")
      self._notify_api_error("transcribe", e)
      return ""

  def _cloud_fallback_order(self):
    """
    Ordered cloud backends to attempt: the active one first, then every other
    cloud provider with credentials (in CLOUD_BACKENDS order). Local is
    deliberately not part of the chain — it's offline, never hangs on the
    network, and loading it would cost VRAM/time mid-session.
    """
    if self.transcription_backend not in CLOUD_BACKENDS:
      return []
    order = [self.transcription_backend]
    for other in CLOUD_BACKENDS:
      if other != self.transcription_backend and self._backend_has_creds(other):
        order.append(other)
    return order

  def _transcribe_audio_file(self, audio_file_path, streaming=False):
    """
    Dispatch transcription to the active backend. For cloud backends, fall back
    to the other cloud provider if the active one fails (timeout/outage/etc).
    """
    # local is not a network call — no timeout/fallback concern.
    if self.transcription_backend == "local":
      text = self._transcribe_via_local_whisper(audio_file_path, streaming=streaming)
      return self._scrub_glossary_echo(text)

    last_err = None
    last_label = None
    # The chain starts with the active backend, so the first failure is the
    # primary's — that is the reason the user needs to hear on a failover.
    primary_err = None
    for backend in self._cloud_fallback_order():
      label = CLOUD_BACKEND_LABELS[backend]
      model = self.config.get(_model_key_for_backend(backend))
      try:
        if backend == "gemini":
          text = self._transcribe_via_gemini(audio_file_path, model)
        else:
          client = self.client if backend == "openai" else self.groq_client
          text = self._transcribe_via_cloud(audio_file_path, client, label, model)
        if backend != self.transcription_backend:
          # Sticky failover: stay on the provider that worked for the rest of
          # this session so we don't re-hit the dead primary on every segment.
          # Not persisted to config — the primary may recover by next launch.
          logger.warning(
              f"Transcription failover: {self.transcription_backend} -> {backend} "
              f"(sticky for this session)"
          )
          # No longer silent: the indicator shows why the primary was dropped
          # and keeps a banner up while recordings run on the fallback.
          self._note_batch_failover(
              CLOUD_BACKEND_LABELS[self.transcription_backend], primary_err, label
          )
          self.transcription_backend = backend
          self.whisper_model_name = model
        return self._scrub_glossary_echo(text)
      except Exception as e:
        last_err = e
        last_label = label
        if primary_err is None:
          primary_err = e
        logger.error(f"Transcription via {label} failed: {e}")
        continue

    # Every cloud provider failed. Raise so the caller degrades as before
    # (streaming: skip segment; final: surface the error) — never hang. The
    # CloudApiError wrapper carries the provider label so _notify_api_error can
    # name who is out of quota / rejecting the key.
    if last_err:
      raise CloudApiError(last_label, last_err)
    raise RuntimeError("No cloud transcription backend available")

  def _transcribe_via_local_whisper(self, audio_file_path, streaming=False):
    """Transcribe audio file using the local faster-whisper model."""
    # Defensive: with async init the model may not be loaded yet. start_recording
    # guards the normal path, but a model switch mid-session could land here with
    # no model — raise a clear error instead of an AttributeError on None.
    if self.whisper_model is None:
      raise RuntimeError("Local Whisper model is not loaded yet")
    try:
      logger.info("Transcribing with local Whisper model")
      hint = self._whisper_language_hint()
      # Layer B (local): faster-whisper 1.1.1 supports hotwords=. Empty dict when
      # the layer is off/empty, so the call is unchanged for the no-glossary path.
      glossary_kwargs = self._whisper_glossary_kwargs()
      if hint:
        segments, info = self.whisper_model.transcribe(
            audio_file_path,
            beam_size=5,
            language=hint,
            **glossary_kwargs
        )
      else:
        segments, info = self.whisper_model.transcribe(
            audio_file_path,
            beam_size=5,
            **glossary_kwargs
        )

      # Iterate Whisper output. We intentionally do NOT interrupt mid-segment
      # on stop — the in-flight transcription represents the user's speech and
      # interrupting it just loses words. The streaming flag stops the OUTER
      # loop only after the current segment finishes.
      transcript_parts = []
      for i, segment in enumerate(segments):
        # Protection against Whisper hallucinations (endless repetition)
        if i >= MAX_SEGMENTS:
          logger.warning(f"Max segments ({MAX_SEGMENTS}) reached - possible hallucination, stopping")
          break

        transcript_parts.append(segment.text)

      transcript = " ".join(transcript_parts)
      return transcript

    except Exception as e:
      logger.error(f"Error transcribing with Whisper: {e}")
      raise e

  def _transcribe_via_cloud(self, audio_file_path, client, label, model):
    """Transcribe audio file via an OpenAI-compatible API (OpenAI or Groq).

    `model` is passed explicitly because OpenAI and Groq use different model
    names — during failover we must send the fallback provider's own model.
    """
    try:
      logger.info(f"Transcribing via {label} ({model})")
      with open(audio_file_path, "rb") as f:
        kwargs = {"model": model, "file": f}
        hint = self._whisper_language_hint()
        if hint:
          kwargs["language"] = hint
        # Layer B (cloud): soft-bias the decoder toward company terms. Works for
        # both OpenAI and Groq (shared OpenAI-compatible API); asr_prompt() is
        # already budget-trimmed to Whisper's ~224-token prompt window.
        if self._glossary_asr_active():
          prompt = self.glossary.asr_prompt()
          if prompt:
            kwargs["prompt"] = prompt
        response = client.audio.transcriptions.create(**kwargs)
      return response.text
    except Exception as e:
      logger.error(f"Error transcribing via {label}: {e}")
      raise e

  def _transcribe_via_gemini(self, audio_file_path, model):
    """Transcribe via Google's Gemini Interactions API (services.gemini_transcribe).

    Gemini is not OpenAI-compatible, so it bypasses _transcribe_via_cloud.
    Layer B rides the API's first-class ``custom_vocabulary`` field instead of
    the Whisper prompt hack — terms bias recognition without being treated as
    preceding speech, so the _scrub_glossary_echo pass downstream simply has
    nothing to strip.
    """
    logger.info(f"Transcribing via Gemini ({model})")
    vocabulary = None
    if self._glossary_asr_active():
      vocabulary = self.glossary.canonical_terms() or None
    return gemini_transcribe.transcribe_file(
        self.gemini_api_key,
        audio_file_path,
        model or "gemini-3.5-transcribe",
        language_hint=self._whisper_language_hint(),
        vocabulary=vocabulary,
        timeout=CLOUD_REQUEST_TIMEOUT,
    )

  def process_audio_file(self, temp_audio_file, session_gen=None):
    """Process the final audio file after recording stops."""
    logger.info("Starting final audio transcription...")

    transcript = self._transcribe_audio_file(temp_audio_file)
    logger.info(f"Final transcription result: {transcript}")
    self.process_text(transcript, session_gen=session_gen)

  # ---------- corporate glossary (layer A wiring) ----------

  def apply_entitlement(self):
    """Cap the glossary's active term set to the current tier (Free = 5,
    Pro/Enterprise = 200). Centralised gate: asks ``ent.limit()``, never the tier
    directly. Call after construction, after a glossary reload, and after an
    in-session license change."""
    from licensing import get_entitlement

    self.glossary.set_active_cap(get_entitlement().limit("glossary_terms"))

  def _glossary_block(self, layer_flag):
    """Canonical-terms block for an LLM prompt, or None when the layer is off.

    Gated by the master switch, the per-layer flag (`layer_flag`), and a
    non-empty glossary — so a disabled/empty glossary adds nothing to any prompt
    and behavior stays identical to the no-glossary build.
    """
    if not self._flag_on("GLOSSARY_ENABLED"):
      return None
    if not self._flag_on(layer_flag):
      return None
    if self.glossary.is_empty:
      return None
    return self.glossary.llm_block() or None

  def _flag_on(self, key):
    """True iff the config flag `key` is the string ``"true"`` (case-insensitive)."""
    return (self.config.get(key) or "false").strip().lower() == "true"

  def _glossary_asr_active(self):
    """Layer B gate: master switch + ASR-bias flag + a non-empty glossary."""
    return (
        self._flag_on("GLOSSARY_ENABLED")
        and self._flag_on("GLOSSARY_ASR_BIAS")
        and not self.glossary.is_empty
    )

  def _scrub_glossary_echo(self, text):
    """Layer B safety net: strip the bias prompt if the ASR echoed it.

    Whisper conditions on the glossary prompt/hotwords as if it were preceding
    speech; on a low-information tail (trailing silence, a near-silent chunk)
    it can emit the term list itself verbatim at an edge of the result. Runs
    on every ASR result (each streaming chunk and the final pass). No-op when
    layer B is off — no prompt was sent, so there is nothing to echo.
    """
    if not text or not self._glossary_asr_active():
      return text
    cleaned = self.glossary.strip_asr_echo(text)
    if cleaned != text:
      logger.warning(
          "Glossary ASR-prompt echo stripped from the transcript edge "
          f"({len(text) - len(cleaned)} chars removed)"
      )
    return cleaned

  def _glossary_fuzzy_active(self):
    """Layer C gate: master switch + fuzzy-replace flag + a non-empty glossary."""
    return (
        self._flag_on("GLOSSARY_ENABLED")
        and self._flag_on("GLOSSARY_FUZZY_REPLACE")
        and not self.glossary.is_empty
    )

  def _glossary_fuzzy_threshold(self):
    """`GLOSSARY_FUZZY_THRESHOLD` as a number, clamped to a sane 70–100 band."""
    try:
      value = float(self.config.get("GLOSSARY_FUZZY_THRESHOLD") or 88)
    except (TypeError, ValueError):
      value = 88.0
    return max(70.0, min(100.0, value))

  def _glossary_fuzzy_max_terms(self):
    """`GLOSSARY_FUZZY_MAX_TERMS` as a positive int (default 200)."""
    try:
      value = int(self.config.get("GLOSSARY_FUZZY_MAX_TERMS") or 200)
    except (TypeError, ValueError):
      value = 200
    return value if value > 0 else 200

  def _whisper_glossary_kwargs(self):
    """``{"hotwords": ...}`` for the local model when layer B is active, else ``{}``.

    Returns an empty dict (no kwargs) whenever the layer is off or the glossary
    has no usable hotword string, so the local `.transcribe()` calls are
    byte-identical to the no-glossary path.
    """
    if not self._glossary_asr_active():
      return {}
    hotwords = self.glossary.hotwords()
    return {"hotwords": hotwords} if hotwords else {}

  def _normalize_to_primary(self, raw):
    """Grammar-correct the transcript and ensure it ends up in PRIMARY language.

    Dictation's optional AI pass (DICTATION_AI_CORRECTION). It guarantees the
    output language without
    over-correcting mixed-language speech: foreign words, brand/product names,
    proper nouns, technical terms, code, and URLs that are embedded in
    otherwise-primary text are kept verbatim — only prose that is wholly in
    another language gets translated.
    """
    primary = self.config.get("PRIMARY_LANGUAGE") or "English"
    # Layer A: if a glossary term is close to a word in the text, normalize it to
    # the canonical form. Appended as an extra rule so the six base rules and the
    # brand-preservation rule (#2) are untouched when the glossary is off/empty.
    glossary_block = self._glossary_block("GLOSSARY_LLM_CORRECTION")
    glossary_rule = (
        f"\n7. Company canonical terms — if a word in the text is phonetically or "
        f"orthographically close to one of these, normalize it to the canonical "
        f"form (do not add terms that were not spoken):\n{glossary_block}"
        if glossary_block else ""
    )
    user_content = (
        f"""You are a text correction assistant. The output must read naturally in {primary}.

1. The overall text must be in {primary}. If the text as a whole is in another language, translate it into {primary}.
2. Do NOT translate or transliterate individual foreign words, brand or product names, proper nouns, technical terms, code identifiers, inline code, or URLs that are embedded in the text — keep them exactly as dictated (e.g. a product name like "MasterDrive" stays "MasterDrive").
3. Fix spelling, grammar, and punctuation.
4. Return only the resulting text — no additional comments, greetings, or explanations.
5. If the text contains profanity, leave it unchanged.
6. If the text should be split into parts, start each part from a new line.{glossary_rule}

Text to process:
<text>{raw}</text>"""
    )
    logger.debug(f"Normalizing transcript to {primary}")
    response = self.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a text correction assistant."},
            {"role": "user", "content": user_content}
        ],
        temperature=0.3,
        max_tokens=self.config.llm_max_tokens
    )
    result = response.choices[0].message.content or raw
    logger.info("Received response from OpenAI")
    logger.debug(f"OpenAI response: {result[:100]}...")
    return result

  def _dictation_text(self, raw):
    """Dictation's cleanup after layer C: hesitation sounds, then the optional
    AI correction. Speed first — both are local/cheap unless the user turned
    the AI pass on, and a failed AI pass falls back to the cleaned text."""
    if self._flag_on("QUICK_CLEAN_FILLERS"):
      # Gemini VERBATIM and the batch chain keep "э-э"; ElevenLabs drops them
      # server-side already (no_verbatim) — stripping again is a no-op there.
      raw = gemini_live.strip_hesitations(raw)
    if not raw.strip() or not self._flag_on("DICTATION_AI_CORRECTION"):
      return raw
    if not self.client:
      logger.info("AI correction is on but there is no OpenAI client — pasting as is")
      return raw
    try:
      return self._normalize_to_primary(raw) or raw
    except Exception as e:
      logger.warning(f"AI correction failed, pasting uncorrected text: {e}")
      self._notify_api_error("postprocess", e, provider="OpenAI")
      return raw

  def _apply_action_transform(self, raw):
    """Turn the raw transcript into the final text based on the active action.

    quick      -> dictation: layer C, filler strip (QUICK_CLEAN_FILLERS), the
                  optional AI correction (DICTATION_AI_CORRECTION: grammar +
                  PRIMARY language), then a capital first letter
    translate  -> always translate into SECONDARY language (fixed target)
    custom     -> rewrite using the style picked for the custom hotkey
                  (HOTKEY_CUSTOM_STYLE): casual / professional preset, or the
                  user's CUSTOM_STYLE_PROMPT

    Always degrades gracefully to the raw transcript: on a missing OpenAI
    client, missing custom prompt, or any API failure, the user still gets
    their words inserted rather than an error string.
    """
    raw = raw or ""
    action = self.active_action
    # What the history should call the result. Stays "transcription" unless an
    # LLM step actually produced the text (a failed/skipped one pastes raw).
    self._last_history = ("transcription", {})

    # Layer C: deterministic glossary replacements, dictation only. Applied up
    # front (before the client check / LLM call) so the canonical forms survive
    # even with no client or a failed correction — both of those fall back to
    # `raw`. translate/custom never get layer C (they keep the source meaning).
    if action == "quick" and self._glossary_fuzzy_active():
      raw = self.glossary.apply_replacements(
          raw,
          threshold=self._glossary_fuzzy_threshold(),
          max_terms=self._glossary_fuzzy_max_terms(),
      )

    if action == "quick":
      return capitalize_first(self._dictation_text(raw))

    if not self.client:
      logger.info(f"No OpenAI client — pasting raw transcript (action='{action}')")
      return raw

    # Layer A for translate/rewrite (separate flag from transcribe correction).
    # None unless enabled + non-empty, so the cloud calls below are unchanged for
    # users without a glossary.
    rewrite_glossary = self._glossary_block("GLOSSARY_LLM_REWRITE")
    # User-configured completion budget for every LLM call on this path.
    max_tokens = self.config.llm_max_tokens

    try:
      if action == "translate":
        from services.text_operations import translate_to_language
        secondary = self.config.get("SECONDARY_LANGUAGE") or "Russian"
        logger.info(f"Translating transcript -> {secondary}")
        out = translate_to_language(
            self.client, raw, secondary, glossary_block=rewrite_glossary,
            max_tokens=max_tokens,
        )
        if out:
          self._last_history = ("translation", {"direction": f"→ {_lang_short(secondary)}"})
        return out or raw

      if action == "custom":
        from services.text_operations import (
          BUSINESS_STYLE,
          CONVERSATIONAL_STYLE,
          rewrite_text,
        )
        style = (self.config.get("HOTKEY_CUSTOM_STYLE") or "custom").strip().lower()
        if style == "casual":
          logger.info("Rewriting transcript in casual style")
          out = rewrite_text(
              self.client, raw, CONVERSATIONAL_STYLE, glossary_block=rewrite_glossary,
              max_tokens=max_tokens,
          )
          if out:
            self._last_history = ("casual", {})
          return out or raw
        if style == "professional":
          logger.info("Rewriting transcript in professional style")
          out = rewrite_text(
              self.client, raw, BUSINESS_STYLE, glossary_block=rewrite_glossary,
              max_tokens=max_tokens,
          )
          if out:
            self._last_history = ("professional", {})
          return out or raw
        # "custom" (or any unknown value): use the user's own prompt.
        prompt = (self.config.get("CUSTOM_STYLE_PROMPT") or "").strip()
        if not prompt:
          logger.info("Custom-style hotkey but no CUSTOM_STYLE_PROMPT set — pasting raw")
          return raw
        logger.info("Rewriting transcript in custom style")
        out = rewrite_text(
            self.client, raw, prompt, glossary_block=rewrite_glossary,
            max_tokens=max_tokens,
        )
        if out:
          self._last_history = ("custom", {})
        return out or raw

      logger.warning(f"Unknown action '{action}' — pasting raw transcript")
      return raw
    except Exception as e:
      # Post-processing is a nice-to-have. On failure (network, timeout,
      # rate-limit) fall back to the raw transcript so the user still gets
      # their words inserted instead of an error string. Still tell them WHY
      # the text arrived uncorrected/untranslated — the LLM always runs on the
      # OpenAI client, hence the fixed provider label.
      logger.warning(f"Post-processing (action='{action}') failed, pasting raw transcript: {e}")
      self._notify_api_error("postprocess", e, provider="OpenAI")
      return raw

  def process_text(self, input_text, session_gen=None):
    """Post-process the transcript per the active action and insert via clipboard.

    ``session_gen`` is the recording session this transcript came from. If a
    newer session has already started (e.g. the user pressed the hotkey again
    while we were waiting on the LLM), we still deliver this text — paste it and
    hand it to the window — but we must NOT run the post-process reset tail
    (idle / drop_all / press_and_talk): that state now belongs to the live
    session, and clobbering it orphans its streaming thread and freezes the
    indicator on "processing".
    """
    logger.info(f"Processing text (action='{self.active_action}')")

    def _current():
      return session_gen is None or session_gen == self._session_gen

    if _current():
      self.ui_bridge.safe_emit_status("processing")

    corrected_text = self._apply_action_transform(input_text)
    history_kind, history_meta = getattr(self, "_last_history", ("transcription", {}))
    # Reset to the default action so any subsequent stray start (mouse mode, a
    # race, the safety-timer auto-stop) defaults to dictation — but only if we
    # still own the session, else we'd wipe the new session's action.
    if _current():
      self.active_action = "quick"

    # Hand off to the main window + session history before the paste, so the
    # user sees it appear in the GUI even if Ctrl+V fails for some reason.
    try:
      self.ui_bridge.transcript_ready.emit(corrected_text or "")
      if corrected_text:
        self.history_manager.add(corrected_text, kind=history_kind, meta=history_meta)
    except Exception as e:
      logger.warning(f"Failed to forward transcript to UI: {e}")

    logger.info("Applying corrected text via clipboard")
    pyperclip.copy(corrected_text)
    time.sleep(0.2)

    # Skip auto-paste in two cases:
    #   1. The user explicitly double-tapped during this session.
    #   2. The window focused at start belonged to us (cursor in our own text
    #      card). transcript_ready already put the text in the card, so Ctrl+V
    #      here would land in the same field and duplicate it.
    # Otherwise paste runs normally — even if the main window is open somewhere
    # on the side, Ctrl+V should still deliver text to whatever external editor
    # the user was working in. The transcript is also handed to the window via
    # transcript_ready, so they get it there regardless.
    if self._skip_next_paste:
      logger.info("Skipping auto-paste (double-tap intent) — text is in clipboard + window")
    elif self._foreground_was_own:
      logger.info("Skipping auto-paste (own window was focused) — text is in clipboard + window")
    else:
      if self._prev_foreground_hwnd:
        try:
          ctypes.windll.user32.SetForegroundWindow(self._prev_foreground_hwnd)
          time.sleep(0.05)
        except Exception as e:
          logger.debug(f"SetForegroundWindow failed (continuing): {e}")

      keyboard.send("ctrl+v")
      time.sleep(0.2)

    # Finalize the session state only if we still own it. If a newer recording
    # started while we were processing, it owns is_recording / streaming /
    # transcription_thread / the indicator — leave all of it alone.
    if not _current():
      logger.info(
          "Post-process reset skipped — a newer session is active "
          f"(gen {session_gen} != {self._session_gen})."
      )
      return

    self.ui_bridge.safe_emit_status("idle")
    logger.debug("Resetting system state")
    time.sleep(0.3)  # Small delay to let the activation button event settle
    self.drop_all()
    self.press_and_talk()

  def toggle_recording(self):
    """Toggle the recording state.

    Three zones based on time since the previous activation event:
      - <50ms   : mechanical bounce / double-event from the hook lib — ignore.
      - 50–300ms: double-tap — open the main window. If the first tap of the
                  pair scheduled a deferred stop, execute it now (and skip the
                  auto-paste). Otherwise just open the window — recording
                  continues.
      - >300ms  : normal single press. Start immediately on idle; on stop,
                  *defer* the actual stop_recording by 300ms so a follow-up
                  tap can convert it into a double-tap. Without this deferral
                  the keyboard thread blocks inside stop_recording (it joins
                  the transcription thread) and the second tap arrives too
                  late to be recognised as a double-tap.
    """
    current_time = time.time()
    elapsed = current_time - self.last_toggle_time
    self.last_toggle_time = current_time

    if elapsed < 0.05:
      logger.debug("Toggle ignored: mechanical bounce")
      return

    if elapsed < 0.3:
      # Double-tap: cancel any pending deferred stop. If a stop was pending,
      # the first tap of this pair was a "stop request" and we now execute it
      # synchronously together with opening the window.
      stop_was_pending = self._pending_stop_timer is not None
      if stop_was_pending:
        self._pending_stop_timer.cancel()
        self._pending_stop_timer = None

      if self.double_tap_opens_window:
        logger.debug("Double-tap detected — opening main window, skipping next paste")
        self._skip_next_paste = True
        self.ui_bridge.show_window_requested.emit()
      else:
        logger.debug("Double-tap detected but disabled in settings — ignoring open")

      if stop_was_pending:
        # _skip_next_paste is already True if the user enabled the feature,
        # which is the whole point of the gesture.
        # Honour "closing key wins" — the second tap's action becomes the mode.
        if self.active_action != self._pending_action:
          logger.debug(
              f"Action switched at double-tap stop: "
              f"{self.active_action} -> {self._pending_action}"
          )
          self.active_action = self._pending_action
        self.stop_recording()
      return

    # Normal single press.
    if not self.is_recording:
      # Lock the action for this session at start. Pressing a *different*
      # hotkey while recording won't change it — it just stops the session.
      self.active_action = self._pending_action
      engine = (self._pick_quick_engine()
                if self.active_action in REALTIME_ACTIONS else None)
      self._session_source = "realtime" if engine else "batch"
      if engine:
        self._quick_engine = engine
      elif self.active_action in REALTIME_ACTIONS:
        logger.info(
            f"'{self.active_action}' has no usable live engine (no GEMINI_API_KEY / "
            "ELEVENLABS_API_KEY, or it failed earlier this session): "
            "using the batch chain"
        )
      logger.debug(
          f"Recording started in '{self.active_action}' mode "
          f"(source: {self._session_source})"
      )
      self.start_recording()
    else:
      # Closing key wins: the hotkey that triggers the stop determines the
      # post-processing mode, even if recording was started with a different
      # one. Lets the user start dictating with F8 and finish with F10 to get
      # the translate result without a separate round-trip.
      if self.active_action != self._pending_action:
        logger.debug(
            f"Action switched mid-recording by closing key: "
            f"{self.active_action} -> {self._pending_action}"
        )
        self.active_action = self._pending_action
      # A realtime quick session stops at once: the whole point is zero wait,
      # and the 300ms double-tap window would be the single largest delay
      # left. Translate/custom keep the window — their LLM pass dwarfs it.
      # Still off the hook thread — stop_recording joins the session thread.
      if self._session_source == "realtime" and self.active_action == "quick":
        threading.Thread(target=self._deferred_stop, daemon=True).start()
        return
      # Defer the stop to give a possible double-tap a chance to land.
      if self._pending_stop_timer is not None:
        self._pending_stop_timer.cancel()
      timer = threading.Timer(0.3, self._deferred_stop)
      timer.daemon = True
      self._pending_stop_timer = timer
      timer.start()

  def _deferred_stop(self):
    """Run on the timer thread after 300ms with no follow-up tap."""
    self._pending_stop_timer = None
    if self.is_recording:
      self.stop_recording()

  def _on_hotkey(self, action_id):
    """Hotkey callback — record which action fired, then toggle.

    Kept deliberately trivial: a low-level keyboard hook (suppress=True) must
    return quickly or Windows skips it past its ~300ms timeout and the key
    leaks through. All heavy work happens later off the hook thread.

    Fires on key-DOWN, so a held key keeps calling us via auto-repeat. Only
    the first down of a physical press may toggle; repeats are dropped until
    the release watcher clears _hotkey_held. If the key-up was never seen
    (lock screen / UAC desktop ate it) the flag would stick and kill the
    hotkey — auto-repeat never pauses this long, so a down arriving after a
    HOTKEY_REPEAT_GAP of silence is a fresh press.
    """
    now = time.monotonic()
    repeat = self._hotkey_held and now - self._hotkey_last_down < HOTKEY_REPEAT_GAP
    self._hotkey_last_down = now
    if repeat:
      return
    self._arm_release_watch(action_id)
    self._pending_action = action_id
    self.toggle_recording()

  def _arm_release_watch(self, action_id):
    """Mark the hotkey as held and watch for its release.

    The watcher is a plain (non-suppressing) keyboard hook, so it runs on the
    keyboard lib's queue thread, not inside the low-level hook. It only clears
    the flag; the hook itself is removed here on the *next* press — unhooking
    from inside the handler would mutate the lib's handler list mid-iteration.
    """
    self._disarm_release_watch()
    key = self.hotkeys.get(action_id, "")
    self._hotkey_held = True

    def _watch(event):
      if not self._hotkey_held or getattr(event, "event_type", None) != "up":
        return
      try:
        still_down = keyboard.is_pressed(key)
      except Exception:
        still_down = False
      if not still_down:
        self._hotkey_held = False

    try:
      self._release_watch = keyboard.hook(_watch)
    except Exception as e:
      # No watcher → no way to see the release; fail open (repeats may toggle)
      # rather than leave the hotkey dead.
      logger.debug(f"release watch failed: {e}")
      self._hotkey_held = False

  def _disarm_release_watch(self):
    """Remove the release watcher hook, if any."""
    watch, self._release_watch = self._release_watch, None
    if watch is not None:
      try:
        keyboard.unhook(watch)
      except (KeyError, ValueError) as e:
        logger.debug(f"release watch unhook failed (already gone?): {e}")

  def _unhook_all(self):
    """Remove every registered keyboard hotkey handle."""
    for handle in self.activation_hooks.values():
      try:
        keyboard.remove_hotkey(handle)
      except (KeyError, ValueError) as e:
        logger.debug(f"remove_hotkey failed (already gone?): {e}")
    self.activation_hooks.clear()
    self._disarm_release_watch()
    self._hotkey_held = False

  def shutdown(self):
    """Tear down every input hook for a clean process exit.

    The hard-capture keyboard hook (``suppress=True``) installs a global
    low-level ``WH_KEYBOARD_LL`` hook; together with the mouse hook these hold
    OS-level handles that the system services on our hook threads. If the app
    tears down while the foreground window belongs to another process, leaving
    those hooks installed can deadlock shutdown. Remove them up front. Safe to
    call more than once and from any thread (the ``keyboard``/``mouse`` libs
    guard their state with locks)."""
    logger.info("AudioWriter shutdown — removing input hooks")
    self._drop_standby()
    try:
      self._unhook_all()
    except Exception as e:
      logger.debug(f"keyboard hotkey teardown failed: {e}")
    try:
      keyboard.unhook_all()  # drop the global WH_KEYBOARD_LL hook + any handlers
    except Exception as e:
      logger.debug(f"keyboard.unhook_all failed: {e}")
    if self.mouse_hook:
      try:
        mouse.unhook(self.mouse_hook)
      except Exception as e:
        logger.debug(f"mouse.unhook failed: {e}")
      self.mouse_hook = None
    try:
      mouse.unhook_all()
    except Exception as e:
      logger.debug(f"mouse.unhook_all failed: {e}")

  def press_and_talk(self):
    """Activate voice input mode and set up the activation hook(s)."""
    logger.info("Voice input activated")
    # First arming at startup (later ones come from stop_recording); a no-op
    # when a matching standby is already open.
    self._prepare_standby_stream()

    if self.activation_mode == 'keyboard':
      # Already registered (we keep hooks alive across recordings) — nothing to do.
      if self.activation_hooks:
        return
      for aid in HOTKEY_ACTIONS:
        key = self.hotkeys.get(aid, "")
        if not key:
          logger.info(f"Hotkey for {aid}: not assigned")
          continue
        try:
          # suppress=True swallows BOTH key edges so the focused app never sees
          # it. The callback fires on key-DOWN: waiting for the release cost
          # ~100ms of the user's first word on every dictation. _on_hotkey
          # filters the auto-repeat of a held key, so it is still once per
          # tap and the double-tap logic is unchanged.
          self.activation_hooks[aid] = keyboard.add_hotkey(
              key,
              (lambda a=aid: self._on_hotkey(a)),
              suppress=self.suppress_hotkeys,
              trigger_on_release=False,
          )
          logger.info(
              f"Hotkey [{key.upper()}] -> {aid}"
              f"{' (hard-capture)' if self.suppress_hotkeys else ''}"
          )
        except Exception as e:
          logger.error(f"Failed to register hotkey {key} for {aid}: {e}")
    else:
      if self.mouse_hook:
        mouse.unhook(self.mouse_hook)

      def mouse_handler(event):
        """Handle mouse events for recording activation (dictation only)."""
        if hasattr(event, 'event_type') and event.event_type == 'down':
          if getattr(event, 'button', None) == self.mouse_activation_button:
            self._pending_action = "quick"
            self.toggle_recording()

      self.mouse_hook = mouse.hook(mouse_handler)

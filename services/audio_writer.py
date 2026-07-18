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

# Cloud request resilience. Without an explicit timeout the openai SDK waits up
# to 600s per request — a single stalled request froze the whole app for minutes.
CLOUD_REQUEST_TIMEOUT = 30.0  # seconds, hard cap on ONE cloud request
CLOUD_MAX_RETRIES = 1         # SDK-level retries of the SAME provider (1 retry = 2 attempts)

# Available transcription models. Re-exported from services.transcription_models
# so the settings UI can pull just the constants without dragging in numpy/
# openai/sounddevice/etc.
from services.transcription_models import (
    GROQ_TRANSCRIPTION_MODELS,
    LOCAL_WHISPER_MODELS,
    OPENAI_TRANSCRIPTION_MODELS,
)
from services.glossary import Glossary
from services.audio_prep import (
    normalize_enhance_profile,
    prepare_for_transcription,
    resolve_input_device,
)
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Backends in canonical order. UI / priority lists use these names.
ALL_BACKENDS = ("groq", "openai", "local")

# Global hotkey actions (keyboard mode). Each entry maps an internal action id
# to its display label, the config key holding its key, and a default key.
# Adding a new hotkey = one entry here + a default in config_store.DEFAULTS +
# a branch in AudioWriter.process_text. The order is the registration order.
# `label_key` is an i18n catalog KEY, not text: this table is built at import,
# before the UI language is known, and the tray menu that renders it is rebuilt
# on every change. Resolving the label here would freeze it in the boot locale.
HOTKEY_ACTIONS = {
    "transcribe": {"label_key": "tray.action.transcribe", "config_key": "HOTKEY_TRANSCRIBE", "default": "F9"},
    "translate":  {"label_key": "tray.action.translate",  "config_key": "HOTKEY_TRANSLATE",  "default": "F10"},
    "custom":     {"label_key": "tray.action.custom",     "config_key": "HOTKEY_CUSTOM",     "default": "F11"},
}

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


def _model_key_for_backend(backend: str) -> str:
  return f"MODEL_{backend.upper()}"


def _backend_for_model(model_name: str) -> str | None:
  if model_name in LOCAL_WHISPER_MODELS:
    return "local"
  if model_name in OPENAI_TRANSCRIPTION_MODELS:
    return "openai"
  if model_name in GROQ_TRANSCRIPTION_MODELS:
    return "groq"
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

  matcher = difflib.SequenceMatcher(None, prev_norm, next_norm, autojunk=False)
  blocks = [b for b in matcher.get_matching_blocks() if b.size > 0]
  if not blocks:
    return 0, 0

  # Anchor = the matched run reaching FURTHEST into prev's tail; the overlap must
  # include prev's final words, since it is prev's last ~1s of audio.
  anchor = max(blocks, key=lambda b: b.a + b.size)
  if anchor.a + anchor.size < len(prev_tail) - _SEAM_TRAIL_SLACK:
    return 0, 0
  if min(b.b for b in blocks) > _SEAM_HEAD_SLACK:
    return 0, 0

  cut_words = anchor.b + anchor.size  # words of nxt's head to drop
  matched = sum(b.size for b in blocks if b.b < cut_words)
  if cut_words <= 0 or matched / cut_words < _SEAM_MATCH_FRAC:
    return 0, 0

  # An uncorroborated fuzzy rewrite may drop ITSELF and nothing more. With no
  # exact word backing the seam, a near-miss sitting past nxt's first word is as
  # easily two different words as one word twice, and cutting to it swallows the
  # real speech in front ("…А здесь нужно" / "подсвечивать нужный набор" —
  # "нужно"~"нужный" ate "подсвечивать"). Replaying the log's 447 real
  # multi-segment joins, this is the only place the fallback overreached.
  if matched == 1 and cut_words > 1 and (cut_words - 1) in fuzzy_idx:
    return 0, 0

  return cut_words, next_head[cut_words - 1][2]


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


class AudioWriter:
  """
  Class for audio recording, transcription and processing using OpenAI and WhisperModel.
  Handles both keyboard and mouse activation for recording control.
  """

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

    self.activation_mode = config.get("ACTIVATION_MODE", 'keyboard')  # or 'mouse'
    self.activation_key = config.get("ACTIVATION_KEY", 'F9')  # legacy; mouse-mode + migration only
    self.mouse_activation_button = config.get("MOUSE_ACTIVATION_BUTTON", 'middle')  # 'left'|'middle'|'right'
    self.double_tap_opens_window = (
        config.get("DOUBLE_TAP_OPENS_WINDOW", "true") or "true"
    ).lower() == "true"

    # Per-action hotkeys. For "transcribe" we fall back to the legacy
    # ACTIVATION_KEY so a user who customised it keeps their key.
    self.hotkeys = {}
    for aid, spec in HOTKEY_ACTIONS.items():
      value = config.get(spec["config_key"])
      if not value and aid == "transcribe":
        value = config.get("ACTIVATION_KEY")
      self.hotkeys[aid] = value or spec["default"]
    # Hard-capture (swallow) hotkeys via a low-level keyboard hook.
    self.suppress_hotkeys = (
        config.get("HOTKEYS_SUPPRESS", "true") or "true"
    ).lower() == "true"
    # action id -> keyboard.add_hotkey handle, so we can remove them on rebind.
    self.activation_hooks: dict[str, object] = {}
    # The action the *current* recording was started with (locked at start).
    self.active_action = "transcribe"
    # Set by the hotkey callback just before toggling, consumed on start.
    self._pending_action = "transcribe"

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

  def _backend_has_creds(self, backend: str) -> bool:
    if backend == "local":
      return True
    if backend == "openai":
      return self.client is not None
    if backend == "groq":
      return self.groq_client is not None
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

    if self.transcription_backend in ("openai", "groq"):
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
    self.activation_key = config.get("ACTIVATION_KEY", 'F9')
    self.mouse_activation_button = config.get("MOUSE_ACTIVATION_BUTTON", 'middle')
    self.double_tap_opens_window = (
        config.get("DOUBLE_TAP_OPENS_WINDOW", "true") or "true"
    ).lower() == "true"
    for aid, spec in HOTKEY_ACTIONS.items():
      value = config.get(spec["config_key"])
      if not value and aid == "transcribe":
        value = config.get("ACTIVATION_KEY")
      self.hotkeys[aid] = value or spec["default"]
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

  def toggle_use_device(self):
    """
    Toggle between CPU and CUDA devices and persist.
    No-op when a cloud backend is active.
    """
    if self.transcription_backend in ("openai", "groq"):
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
    """
    if target == 'openai':
      self.change_transcription_model(
          self.config.get("MODEL_OPENAI", "gpt-4o-mini-transcribe")
      )
      return

    if target == 'groq':
      self.change_transcription_model(
          self.config.get("MODEL_GROQ", "whisper-large-v3-turbo")
      )
      return

    if target not in ('cuda', 'cpu'):
      logger.error(f"Unknown backend device target: {target}")
      return

    self.use_device = target
    self.config.set("USE_DEVICE", self.use_device)

    if self.transcription_backend in ('openai', 'groq'):
      # Coming back from cloud — pick the configured local model
      self.change_transcription_model(self.config.get("MODEL_LOCAL", "small"))
      return

    # Already on local backend, just re-init with the new device in the
    # background. The CUDA->CPU fallback lives in the worker.
    self._reinit_backend_async()

  def listen_for_new_activation_key(self, action_id="transcribe"):
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

  def change_activation_key(self, new_key, action_id="transcribe"):
    """Rebind `action_id` to `new_key`, persist it, and re-register all hotkeys."""
    spec = HOTKEY_ACTIONS.get(action_id)
    if spec is None:
      logger.error(f"Unknown hotkey action: {action_id}")
      return
    self.hotkeys[action_id] = new_key
    self.config.set(spec["config_key"], new_key)
    if action_id == "transcribe":
      # Keep the legacy key in sync for migration / back-compat.
      self.activation_key = new_key
      self.config.set("ACTIVATION_KEY", new_key)
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
    if self.transcription_backend == "local" and self._model_state != "ready":
      logger.info(f"Recording blocked: local model not ready ({self._model_state})")
      self.ui_bridge.safe_emit_model_state(self._model_state, force=True)
      return

    self.audio_queue = queue.Queue()  # Reset the queue
    # New session — clear any "skip paste" intent left over from a previous one.
    self._skip_next_paste = False
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

      self.ui_bridge.safe_emit_status("recording")
      self.ui_bridge.audio_level = 0.0  # start the equalizer flat until first frame
      # Re-read capture settings so a settings save mid-session applies on the
      # next press without requiring a full backend reinit.
      self._input_device_config = self.config.get("INPUT_DEVICE", "") or ""
      self._audio_enhance_profile = normalize_enhance_profile(
          self.config.get("AUDIO_ENHANCE", "light")
      )
      # Set up the audio input stream. device=None → PortAudio system default.
      device_index = resolve_input_device(self._input_device_config)
      self.stream = self._open_input_stream(device_index)
      self.stream.start()
      self.is_recording = True

      # Start streaming transcription. Bump the session gen first so this
      # session owns the shared state and any still-finishing tail of the
      # previous one (its process_text) sees a newer gen and bows out.
      self._session_gen += 1
      self.streaming = True
      self.transcription_thread = threading.Thread(
          target=self.streaming_transcribe, args=(self._session_gen,)
      )
      self.transcription_thread.start()

      # Set a 10-minute (600 seconds) safety timer for auto-stop
      self.recording_timer = threading.Timer(600, self.stop_recording)
      self.recording_timer.start()

      logger.info("Recording started. Press the activation key/button again to stop recording.")
    except Exception as e:
      logger.error(f"Error starting recording: {e}")

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
    self.process_audio_file(temp_audio_file, session_gen=session_gen)

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
          self.ui_bridge.safe_emit_status("recording")
        else:
          self.ui_bridge.safe_emit_status("processing")

      if not self.streaming and self.audio_queue.empty() and not buffer:
        break

    logger.info("Streaming transcription completed.")

  def _cloud_fallback_order(self):
    """
    Ordered cloud backends to attempt: the active one first, then the other
    cloud provider if it has credentials. Local is deliberately not part of the
    chain — it's offline, never hangs on the network, and loading it would cost
    VRAM/time mid-session.
    """
    if self.transcription_backend not in ("openai", "groq"):
      return []
    order = [self.transcription_backend]
    other = "groq" if self.transcription_backend == "openai" else "openai"
    if self._backend_has_creds(other):
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
    for backend in self._cloud_fallback_order():
      client = self.client if backend == "openai" else self.groq_client
      label = "OpenAI" if backend == "openai" else "Groq"
      model = self.config.get(_model_key_for_backend(backend))
      try:
        text = self._transcribe_via_cloud(audio_file_path, client, label, model)
        if backend != self.transcription_backend:
          # Sticky failover: stay on the provider that worked for the rest of
          # this session so we don't re-hit the dead primary on every segment.
          # Not persisted to config — the primary may recover by next launch.
          logger.warning(
              f"Transcription failover: {self.transcription_backend} -> {backend} "
              f"(sticky for this session)"
          )
          self.transcription_backend = backend
          self.whisper_model_name = model
        return self._scrub_glossary_echo(text)
      except Exception as e:
        last_err = e
        logger.error(f"Transcription via {label} failed: {e}")
        continue

    # Every cloud provider failed. Raise so the caller degrades as before
    # (streaming: skip segment; final: surface the error) — never hang.
    if last_err:
      raise last_err
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

    This is the F9 (default) action. It guarantees the output language without
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
        max_tokens=1500
    )
    result = response.choices[0].message.content or raw
    logger.info("Received response from OpenAI")
    logger.debug(f"OpenAI response: {result[:100]}...")
    return result

  def _apply_action_transform(self, raw):
    """Turn the raw transcript into the final text based on the active action.

    transcribe -> grammar-correct, always output in PRIMARY language
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

    # Layer C: deterministic glossary replacements, transcribe only. Applied up
    # front (before the client check / LLM call) so the canonical forms survive
    # even with no client or a failed correction — both of those fall back to
    # `raw`. translate/custom never get layer C (they keep the source meaning).
    if action == "transcribe" and self._glossary_fuzzy_active():
      raw = self.glossary.apply_replacements(
          raw,
          threshold=self._glossary_fuzzy_threshold(),
          max_terms=self._glossary_fuzzy_max_terms(),
      )

    if not self.client:
      logger.info(f"No OpenAI client — pasting raw transcript (action='{action}')")
      return raw

    # Layer A for translate/rewrite (separate flag from transcribe correction).
    # None unless enabled + non-empty, so the cloud calls below are unchanged for
    # users without a glossary.
    rewrite_glossary = self._glossary_block("GLOSSARY_LLM_REWRITE")

    try:
      if action == "translate":
        from services.text_operations import translate_to_language
        secondary = self.config.get("SECONDARY_LANGUAGE") or "Russian"
        logger.info(f"Translating transcript -> {secondary}")
        return translate_to_language(
            self.client, raw, secondary, glossary_block=rewrite_glossary
        ) or raw

      if action == "custom":
        from services.text_operations import (
          BUSINESS_STYLE,
          CONVERSATIONAL_STYLE,
          rewrite_text,
        )
        style = (self.config.get("HOTKEY_CUSTOM_STYLE") or "custom").strip().lower()
        if style == "casual":
          logger.info("Rewriting transcript in casual style")
          return rewrite_text(
              self.client, raw, CONVERSATIONAL_STYLE, glossary_block=rewrite_glossary
          ) or raw
        if style == "professional":
          logger.info("Rewriting transcript in professional style")
          return rewrite_text(
              self.client, raw, BUSINESS_STYLE, glossary_block=rewrite_glossary
          ) or raw
        # "custom" (or any unknown value): use the user's own prompt.
        prompt = (self.config.get("CUSTOM_STYLE_PROMPT") or "").strip()
        if not prompt:
          logger.info("Custom-style hotkey but no CUSTOM_STYLE_PROMPT set — pasting raw")
          return raw
        logger.info("Rewriting transcript in custom style")
        return rewrite_text(
            self.client, raw, prompt, glossary_block=rewrite_glossary
        ) or raw

      # Default action: grammar-correct + normalize to PRIMARY language.
      return self._normalize_to_primary(raw)
    except Exception as e:
      # Post-processing is a nice-to-have. On failure (network, timeout,
      # rate-limit) fall back to the raw transcript so the user still gets
      # their words inserted instead of an error string.
      logger.warning(f"Post-processing (action='{action}') failed, pasting raw transcript: {e}")
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
    # Reset to the default action so any subsequent stray start (mouse mode, a
    # race, the safety-timer auto-stop) defaults to plain transcription — but
    # only if we still own the session, else we'd wipe the new session's action.
    if _current():
      self.active_action = "transcribe"

    # Hand off to the main window + session history before the paste, so the
    # user sees it appear in the GUI even if Ctrl+V fails for some reason.
    try:
      self.ui_bridge.transcript_ready.emit(corrected_text or "")
      if corrected_text:
        self.history_manager.add(corrected_text)
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
      logger.debug(f"Recording started in '{self.active_action}' mode")
      self.start_recording()
    else:
      # Closing key wins: the hotkey that triggers the stop determines the
      # post-processing mode, even if recording was started with a different
      # one. Lets the user start dictating with F9 and finish with F10 to get
      # the translate result without a separate round-trip.
      if self.active_action != self._pending_action:
        logger.debug(
            f"Action switched mid-recording by closing key: "
            f"{self.active_action} -> {self._pending_action}"
        )
        self.active_action = self._pending_action
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
    """
    self._pending_action = action_id
    self.toggle_recording()

  def _unhook_all(self):
    """Remove every registered keyboard hotkey handle."""
    for handle in self.activation_hooks.values():
      try:
        keyboard.remove_hotkey(handle)
      except (KeyError, ValueError) as e:
        logger.debug(f"remove_hotkey failed (already gone?): {e}")
    self.activation_hooks.clear()

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

    if self.activation_mode == 'keyboard':
      # Already registered (we keep hooks alive across recordings) — nothing to do.
      if self.activation_hooks:
        return
      for aid in HOTKEY_ACTIONS:
        key = self.hotkeys[aid]
        try:
          # suppress=True swallows BOTH key edges so the focused app never sees
          # it; trigger_on_release fires the callback once per tap (matching the
          # previous on_release_key semantics, so the double-tap logic still works).
          self.activation_hooks[aid] = keyboard.add_hotkey(
              key,
              (lambda a=aid: self._on_hotkey(a)),
              suppress=self.suppress_hotkeys,
              trigger_on_release=True,
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
        """Handle mouse events for recording activation (transcribe only)."""
        if hasattr(event, 'event_type') and event.event_type == 'down':
          if getattr(event, 'button', None) == self.mouse_activation_button:
            self._pending_action = "transcribe"
            self.toggle_recording()

      self.mouse_hook = mouse.hook(mouse_handler)

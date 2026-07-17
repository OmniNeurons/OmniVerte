"""Async backend initialization and the model-state axis.

Backend init (which, for the local backend, downloads/loads a faster-whisper
model) was moved off ``AudioWriter.__init__`` onto a background worker so a slow
first-run download never blocks the UI. These tests exercise the worker's state
reporting, the generation guard that lets a model switch supersede an in-flight
load, and the ``start_recording`` guard that refuses to record on a not-yet-ready
local model.

AudioWriter is built with ``__new__`` so the real (now UI-less) ``__init__``
isn't run; only the attributes each path touches are set up.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services import audio_writer as aw
from services.audio_writer import AudioWriter


def _worker_writer(monkeypatch, *, backend="local", use_device="cpu"):
    """Bare writer wired for _load_backend_worker / _reinit_backend_async."""
    w = AudioWriter.__new__(AudioWriter)
    w.transcription_backend = backend
    w.use_device = use_device
    w.whisper_model = None
    w._model_state = "loading"
    w._init_gen = 1
    w._gen_lock = threading.Lock()
    w._load_lock = threading.Lock()
    w.ui_bridge = MagicMock()
    w.config = MagicMock()
    return w


# ---------- _load_backend_worker: state reporting ----------

def test_worker_local_success_reports_loading_then_ready(monkeypatch):
    w = _worker_writer(monkeypatch, backend="local")
    init = MagicMock()
    monkeypatch.setattr(w, "_initialize_transcription_backend", init)

    w._load_backend_worker(gen=1)

    init.assert_called_once()
    assert w._model_state == "ready"
    states = [c.args[0] for c in w.ui_bridge.safe_emit_model_state.call_args_list]
    assert states == ["loading", "ready"]


def test_worker_local_failure_reports_failed(monkeypatch):
    w = _worker_writer(monkeypatch, backend="local", use_device="cpu")
    monkeypatch.setattr(
        w, "_initialize_transcription_backend",
        MagicMock(side_effect=RuntimeError("no network")),
    )

    w._load_backend_worker(gen=1)

    assert w._model_state == "failed"
    states = [c.args[0] for c in w.ui_bridge.safe_emit_model_state.call_args_list]
    assert states == ["loading", "failed"]


def test_worker_cuda_failure_retries_on_cpu(monkeypatch):
    w = _worker_writer(monkeypatch, backend="local", use_device="cuda")
    # First call (CUDA) raises; second call (after CPU fallback) succeeds.
    init = MagicMock(side_effect=[RuntimeError("cuda oom"), None])
    monkeypatch.setattr(w, "_initialize_transcription_backend", init)

    w._load_backend_worker(gen=1)

    assert init.call_count == 2
    assert w.use_device == "cpu"
    assert w._model_state == "ready"


def test_worker_cloud_reports_ready_without_loading_model(monkeypatch):
    w = _worker_writer(monkeypatch, backend="groq")
    init = MagicMock()
    monkeypatch.setattr(w, "_initialize_transcription_backend", init)

    w._load_backend_worker(gen=1)

    init.assert_not_called()  # no local model to build
    assert w._model_state == "ready"
    states = [c.args[0] for c in w.ui_bridge.safe_emit_model_state.call_args_list]
    assert states == ["ready"]  # never announces "loading"


# ---------- generation guard ----------

def test_stale_generation_does_not_commit(monkeypatch):
    w = _worker_writer(monkeypatch, backend="local")
    w._init_gen = 2  # a newer request already arrived
    init = MagicMock()
    monkeypatch.setattr(w, "_initialize_transcription_backend", init)

    w._load_backend_worker(gen=1)  # stale worker

    init.assert_not_called()
    w.ui_bridge.safe_emit_model_state.assert_not_called()
    assert w._model_state == "loading"  # untouched


def test_set_model_state_ignores_stale_generation(monkeypatch):
    w = _worker_writer(monkeypatch, backend="local")
    w._init_gen = 5
    w._set_model_state("ready", gen=4)  # stale
    assert w._model_state == "loading"
    w.ui_bridge.safe_emit_model_state.assert_not_called()


def test_reinit_bumps_generation(monkeypatch):
    w = _worker_writer(monkeypatch, backend="local")
    # Don't actually spawn a thread — capture the target instead.
    spawned = {}

    class _FakeThread:
        def __init__(self, target, args, daemon):
            spawned["args"] = args
            spawned["daemon"] = daemon

        def start(self):
            spawned["started"] = True

    monkeypatch.setattr(aw.threading, "Thread", _FakeThread)

    w._reinit_backend_async()

    assert w._init_gen == 2  # bumped from 1
    assert spawned["args"] == (2,)
    assert spawned["daemon"] is True
    assert spawned["started"] is True


# ---------- start_recording guard ----------

def test_start_recording_blocked_while_local_model_loading(monkeypatch):
    w = AudioWriter.__new__(AudioWriter)
    w.transcription_backend = "local"
    w._model_state = "loading"
    w.is_recording = False
    w.ui_bridge = MagicMock()
    # Make any accidental fall-through blow up loudly rather than silently record.
    monkeypatch.setattr(aw, "sd", None)

    w.start_recording()

    assert w.is_recording is False
    w.ui_bridge.safe_emit_model_state.assert_called_once_with("loading", force=True)


def test_start_recording_not_blocked_for_cloud_backend(monkeypatch):
    w = AudioWriter.__new__(AudioWriter)
    w.transcription_backend = "openai"
    w._model_state = "loading"  # irrelevant for cloud
    w.is_recording = False
    w._skip_next_paste = False
    w._pending_stop_timer = None
    w._session_gen = 0
    w.streaming = False
    w.fs = 16000
    w.ui_bridge = MagicMock()
    # Stub the OS/audio surfaces start_recording touches past the guard.
    monkeypatch.setattr(aw, "ctypes", SimpleNamespace(
        windll=SimpleNamespace(user32=SimpleNamespace(
            GetForegroundWindow=lambda: 0))))
    monkeypatch.setattr(w, "_hwnd_is_own_process", lambda hwnd: False)
    monkeypatch.setattr(aw, "sd", SimpleNamespace(InputStream=MagicMock()))
    monkeypatch.setattr(aw.threading, "Thread", MagicMock())
    monkeypatch.setattr(aw.threading, "Timer", MagicMock())

    w.start_recording()

    # Proceeded past the guard: the loading nudge was NOT emitted, recording began.
    w.ui_bridge.safe_emit_model_state.assert_not_called()
    assert w.is_recording is True

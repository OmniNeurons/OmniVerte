"""Regression: the status indicator must stay "recording" until recording
actually stops, even though `streaming_transcribe` cuts and transcribes 20 s
segments WHILE the user is still dictating.

Before the fix, each mid-stream segment emitted "processing" the moment it was
cut, so a long dictation flashed "transcribing" while the user was still
talking — reading as "it stopped listening". The mic is open and audio frames
keep arriving, so "recording" is the honest state until stop_recording.

`streaming_transcribe` is thread/queue driven, so we drive it directly with a
bare writer: one queued chunk, `segment_duration=0` to force an immediate
segment boundary, and a stubbed transcribe that finalizes the loop after the
first (mid-recording) segment. Every status emit is captured together with the
`is_recording` flag at emit time; the assertion is simply that no "processing"
is ever emitted while still recording.
"""

from __future__ import annotations

import queue

import numpy as np

from services import audio_writer as aw
from services.audio_writer import AudioWriter


def test_no_processing_status_while_still_recording(monkeypatch):
    monkeypatch.setattr(aw.wav, "write", lambda *a, **k: None)  # no disk IO

    w = AudioWriter.__new__(AudioWriter)
    w.fs = 16000
    w.overlap_duration = 1
    w.segment_duration = 0  # force a segment boundary on the first iteration
    w.streaming = True
    w.is_recording = True
    w._session_gen = 0
    w.transcribed_segments = []

    w.audio_queue = queue.Queue()
    w.audio_queue.put(np.zeros((100, 1), dtype=np.int16))

    emits: list[tuple[str, bool]] = []

    class _Bridge:
        def safe_emit_status(self, status):
            emits.append((status, w.is_recording))

    w.ui_bridge = _Bridge()

    calls = {"n": 0}

    def _fake_transcribe(path, streaming=False):
        calls["n"] += 1
        # First (mid-recording) segment done — now simulate the user stopping so
        # the loop finalizes and exits instead of spinning forever.
        w.streaming = False
        w.is_recording = False
        return ""  # empty → segment skipped, keeps the trace clean

    w._transcribe_audio_file = _fake_transcribe

    w.streaming_transcribe(session_gen=0)

    assert calls["n"] == 1  # exactly one segment was processed
    # The core guarantee: "processing" never shows while the mic is still open.
    assert ("processing", True) not in emits
    # And once recording has stopped, "processing" is allowed (and expected).
    assert any(status == "processing" for status, _ in emits)

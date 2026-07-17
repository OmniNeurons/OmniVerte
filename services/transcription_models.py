# file: services/transcription_models.py

"""
Lightweight transcription-model name tuples — kept in their own module so the
settings window can import them without triggering the audio_writer import
chain (numpy, openai, sounddevice, scipy, pyperclip, keyboard, mouse), which
adds ~2.5s to settings-window startup.
"""

from __future__ import annotations

LOCAL_WHISPER_MODELS: tuple[str, ...] = ("tiny", "base", "small", "medium", "large-v3")
OPENAI_TRANSCRIPTION_MODELS: tuple[str, ...] = (
    "gpt-4o-mini-transcribe",
    "gpt-4o-transcribe",
    "whisper-1",
)
GROQ_TRANSCRIPTION_MODELS: tuple[str, ...] = (
    "whisper-large-v3-turbo",
    "whisper-large-v3",
    "distil-whisper-large-v3-en",
)

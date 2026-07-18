# file: tests/test_audio_prep.py

"""Unit tests for services.audio_prep — pure DSP + device resolve (no mic)."""

from __future__ import annotations

import numpy as np
import pytest

from services import audio_prep as ap


def _sine(freq_hz: float, seconds: float, sr: int = 16000, amp: float = 0.1) -> np.ndarray:
    t = np.arange(int(sr * seconds), dtype=np.float64) / sr
    x = amp * np.sin(2 * np.pi * freq_hz * t)
    return np.clip(x * 32767.0, -32768, 32767).astype(np.int16)


def _rms_i16(x: np.ndarray) -> float:
    f = x.astype(np.float64) / 32768.0
    return float(np.sqrt(np.mean(f * f))) if f.size else 0.0


# ----- profile normalization --------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("off", "off"),
        ("OFF", "off"),
        ("none", "off"),
        ("light", "light"),
        ("strong", "light"),  # reserved alias
        ("on", "light"),
        ("", "light"),
        (None, "light"),
        ("weird", "light"),
    ],
)
def test_normalize_enhance_profile(raw, expected):
    assert ap.normalize_enhance_profile(raw) == expected


# ----- prepare_for_transcription ----------------------------------------------


def test_off_is_byte_identical_int16_mono():
    src = _sine(440, 0.2, amp=0.05)
    out = ap.prepare_for_transcription(src, 16000, profile="off")
    assert out.dtype == np.int16
    assert out.shape == src.shape
    np.testing.assert_array_equal(out, src)


def test_off_sounddevice_shape_n1_not_rescaled():
    """Regression: (frames, 1) int16 from sounddevice must NOT be treated as float.

    A prior bug averaged channels to float64 (still in PCM counts) then did
    ``* 32767``, clipping speech to ±full-scale and wrecking ASR for both
    Light and Off.
    """
    flat = _sine(440, 0.25, amp=0.1)  # peak ~±3276
    src = flat.reshape(-1, 1)
    assert src.dtype == np.int16
    assert int(np.max(np.abs(src))) < 10000

    off = ap.prepare_for_transcription(src, 16000, profile="off")
    np.testing.assert_array_equal(off, flat)
    assert int(np.max(np.abs(off))) < 10000
    # Not a near-square-wave (the failure mode was ~2–3 unique extreme values).
    assert len(np.unique(off)) > 100

    light = ap.prepare_for_transcription(src, 16000, profile="light")
    assert light.dtype == np.int16
    assert int(np.max(np.abs(light))) < 32767  # soft-limited, not hard brickwall all samples
    # Still looks like a sine, not clipped rails.
    assert len(np.unique(light)) > 100


def test_off_does_not_mutate_input():
    src = _sine(440, 0.1, amp=0.05)
    copy = src.copy()
    ap.prepare_for_transcription(src, 16000, profile="off")
    np.testing.assert_array_equal(src, copy)


def test_empty_returns_empty_int16():
    out = ap.prepare_for_transcription(np.zeros(0, dtype=np.int16), 16000, profile="light")
    assert out.dtype == np.int16
    assert out.size == 0


def test_shape_n1_accepted():
    src = _sine(440, 0.15, amp=0.05).reshape(-1, 1)
    out = ap.prepare_for_transcription(src, 16000, profile="off")
    assert out.ndim == 1
    assert out.size == src.shape[0]


def test_near_silence_not_blown_up():
    # Tiny noise well under SILENCE_RMS after float conversion.
    rng = np.random.default_rng(0)
    quiet = (rng.normal(0, 20, size=16000)).astype(np.int16)  # ~very quiet
    rms_in = _rms_i16(quiet)
    assert rms_in < ap.SILENCE_RMS
    out = ap.prepare_for_transcription(quiet, 16000, profile="light")
    rms_out = _rms_i16(out)
    # Must not approach TARGET_RMS — silence guard holds gain ≈ 1 (HPF may
    # change energy slightly).
    assert rms_out < ap.SILENCE_RMS * 3


def test_quiet_speech_gain_toward_target():
    # 440 Hz at low amplitude — above silence floor after measure.
    quiet = _sine(440, 0.5, amp=0.02)
    rms_in = _rms_i16(quiet)
    assert rms_in >= ap.SILENCE_RMS
    assert rms_in < ap.TARGET_RMS * 0.5
    out = ap.prepare_for_transcription(quiet, 16000, profile="light")
    rms_out = _rms_i16(out)
    assert rms_out > rms_in
    # Soft limiter + HPF prevent exact target; should move closer.
    assert rms_out > rms_in * 1.5
    assert int(out.max()) <= 32767
    assert int(out.min()) >= -32768


def test_loud_speech_not_hard_clip_overflow():
    loud = _sine(440, 0.3, amp=0.9)
    out = ap.prepare_for_transcription(loud, 16000, profile="light")
    assert out.dtype == np.int16
    # Soft limiter keeps peaks under full-scale int16 extremes in practice.
    assert abs(int(out.max())) <= 32767
    assert abs(int(out.min())) <= 32768


def test_highpass_reduces_low_frequency_energy():
    # Isolate the IIR (AGC would re-boost residual and muddy the assertion).
    sr = 16000
    rumble = _sine(40, 0.5, sr=sr, amp=0.2).astype(np.float64) / 32768.0
    tone = _sine(1000, 0.5, sr=sr, amp=0.2).astype(np.float64) / 32768.0
    filt_r = ap._highpass(rumble, sr)
    filt_t = ap._highpass(tone, sr)
    rms = lambda x: float(np.sqrt(np.mean(x * x)))
    assert rms(filt_r) < rms(rumble) * 0.35
    # Mid-band speech tone should survive mostly intact.
    assert rms(filt_t) > rms(tone) * 0.85


def test_float_input_accepted():
    f = (0.05 * np.sin(2 * np.pi * 440 * np.arange(8000) / 16000)).astype(np.float32)
    out = ap.prepare_for_transcription(f, 16000, profile="light")
    assert out.dtype == np.int16
    assert out.size == f.size


# ----- device encode / resolve ------------------------------------------------


def test_encode_decode_device_name():
    assert ap.encode_device_name("Mic USB") == "name::Mic USB"
    assert ap.decode_device_name("name::Mic USB") == "Mic USB"
    assert ap.decode_device_name("") is None
    assert ap.decode_device_name(None) is None
    assert ap.decode_device_name("Bare Name") == "Bare Name"


def test_list_input_devices_filters_outputs_raw():
    devices = [
        {"name": "Speakers", "max_input_channels": 0, "hostapi": 0},
        {"name": "Headset Mic", "max_input_channels": 1, "hostapi": 0},
        {"name": "Line In", "max_input_channels": 2, "hostapi": 1},
    ]
    hostapis = [{"name": "MME"}, {"name": "Windows WASAPI"}]
    infos = ap.list_input_devices(
        devices=devices, hostapis=hostapis, dedupe_by_name=False
    )
    assert [i.name for i in infos] == ["Headset Mic", "Line In"]
    assert infos[0].index == 1
    assert infos[0].hostapi_name == "MME"
    assert infos[1].config_value == "name::Line In"


def test_list_input_devices_wasapi_only_hides_mappers_and_other_hosts():
    """UI list: only WASAPI rows when present; no MME/DS/WDM duplicates or mappers."""
    devices = [
        {"name": "Microsoft Sound Mapper - Input", "max_input_channels": 1, "hostapi": 0},
        {"name": "Microphone (4- Trust GXT 232 Mi", "max_input_channels": 1, "hostapi": 0},
        {"name": "Primary Sound Capture Driver", "max_input_channels": 1, "hostapi": 1},
        {"name": "Microphone (4- Trust GXT 232 Microphone)", "max_input_channels": 1, "hostapi": 1},
        {"name": "Microphone (4- Trust GXT 232 Microphone)", "max_input_channels": 1, "hostapi": 2},
        {"name": "Microphone (Virtual Desktop Audio)", "max_input_channels": 1, "hostapi": 2},
        {"name": "Microphone (Trust GXT 232 Microphone)", "max_input_channels": 1, "hostapi": 3},
        {"name": "Headset Microphone (OCULUSVAD Wave)", "max_input_channels": 1, "hostapi": 3},
    ]
    hostapis = [
        {"name": "MME"},
        {"name": "Windows DirectSound"},
        {"name": "Windows WASAPI"},
        {"name": "Windows WDM-KS"},
    ]
    infos = ap.list_input_devices(devices=devices, hostapis=hostapis)
    assert len(infos) == 2
    assert all(i.hostapi_name == "Windows WASAPI" for i in infos)
    assert {i.name for i in infos} == {
        "Microphone (4- Trust GXT 232 Microphone)",
        "Microphone (Virtual Desktop Audio)",
    }
    # Labels are clean names — no "(Windows WASAPI)" suffix.
    assert infos[0].display_label == infos[0].name


def test_list_input_devices_falls_back_to_mme_without_wasapi():
    devices = [
        {"name": "Microsoft Sound Mapper - Input", "max_input_channels": 1, "hostapi": 0},
        {"name": "Desk Mic", "max_input_channels": 1, "hostapi": 0},
        {"name": "Other Mic", "max_input_channels": 1, "hostapi": 0},
    ]
    hostapis = [{"name": "MME"}]
    infos = ap.list_input_devices(devices=devices, hostapis=hostapis)
    assert [i.name for i in infos] == ["Desk Mic", "Other Mic"]


def test_resolve_input_device_default_and_match():
    devices = [
        {"name": "Speakers", "max_input_channels": 0, "hostapi": 0},
        {"name": "Desk Mic", "max_input_channels": 1, "hostapi": 0},
    ]
    hostapis = [{"name": "MME"}]
    assert ap.resolve_input_device("", devices=devices, hostapis=hostapis) is None
    assert ap.resolve_input_device(None, devices=devices, hostapis=hostapis) is None
    assert ap.resolve_input_device("name::Desk Mic", devices=devices, hostapis=hostapis) == 1
    assert ap.resolve_input_device("Desk Mic", devices=devices, hostapis=hostapis) == 1
    # Missing → default
    assert ap.resolve_input_device("name::Gone", devices=devices, hostapis=hostapis) is None


def test_resolve_prefers_wasapi_when_name_collides():
    # indices follow enumerate of the full device table
    devices = [
        {"name": "Speakers", "max_input_channels": 0, "hostapi": 0},
        {"name": "Desk Mic", "max_input_channels": 1, "hostapi": 0},  # MME → 1
        {"name": "Desk Mic", "max_input_channels": 1, "hostapi": 2},  # WASAPI → 2
    ]
    hostapis = [
        {"name": "MME"},
        {"name": "Windows DirectSound"},
        {"name": "Windows WASAPI"},
    ]
    assert ap.resolve_input_device(
        "name::Desk Mic", devices=devices, hostapis=hostapis
    ) == 2


def test_input_device_info_config_value():
    info = ap.InputDeviceInfo(index=2, name="Foo", hostapi_name="WASAPI")
    assert info.config_value == "name::Foo"
    assert info.display_label == "Foo"

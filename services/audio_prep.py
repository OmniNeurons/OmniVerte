# file: services/audio_prep.py

"""Audio capture helpers: light speech enhance + input-device resolution.

Pure DSP and PortAudio bookkeeping — no Qt, no network. Called by AudioWriter
immediately before writing a WAV for transcription (not in the realtime
callback). When the enhance profile is ``off``, samples pass through unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)

# ----- enhance profiles -------------------------------------------------------

ENHANCE_PROFILES = ("off", "light")
DEFAULT_ENHANCE_PROFILE = "light"

# Light-profile DSP constants (code-tuned; not user-facing yet).
HPF_CUTOFF_HZ = 100.0
HPF_ORDER = 2
TARGET_RMS = 0.12
MAX_GAIN = 10 ** (15.0 / 20.0)  # ~15 dB
SILENCE_RMS = 0.005
LIMITER_CEILING = 0.95

# Stored form for a non-default mic: "name::<PortAudio device name>".
# Empty string / missing → system default.
_DEVICE_NAME_PREFIX = "name::"

# Minimum samples for a meaningful high-pass (filter pad). Below this we still
# run gain/limit when profile is light, but skip the IIR if the buffer is tiny.
_MIN_HPF_SAMPLES = 32


def normalize_enhance_profile(value: Optional[str]) -> str:
    """Map config text to a known profile. Unknown / empty → default (light)."""
    raw = (value or "").strip().lower()
    if raw in ("off", "none", "false", "0"):
        return "off"
    # Reserved alias: strong maps to light until a real strong profile exists.
    if raw in ("light", "on", "true", "1", "strong"):
        return "light"
    if raw == "":
        return DEFAULT_ENHANCE_PROFILE
    logger.warning("Unknown AUDIO_ENHANCE=%r — using %s", value, DEFAULT_ENHANCE_PROFILE)
    return DEFAULT_ENHANCE_PROFILE


def prepare_for_transcription(
    samples: np.ndarray,
    sample_rate: int,
    profile: str = DEFAULT_ENHANCE_PROFILE,
) -> np.ndarray:
    """Return mono int16 PCM suitable for ``wav.write`` / Whisper APIs.

    Parameters
    ----------
    samples:
        int16 or floating PCM, shape ``(N,)`` or ``(N, 1)`` (or multi-channel —
        channels are averaged to mono).
    sample_rate:
        Hz; must be positive. Used for the high-pass design.
    profile:
        ``off`` — byte-identical int16 mono copy of the input (no DSP).
        ``light`` / ``strong`` — high-pass + capped AGC + soft limiter.

    Returns
    -------
    np.ndarray
        dtype int16, shape ``(N,)``. Empty input yields empty int16 array.
    """
    mono_i16 = _to_mono_int16(samples)
    if mono_i16.size == 0:
        return mono_i16

    prof = normalize_enhance_profile(profile)
    if prof == "off":
        return mono_i16

    if sample_rate is None or sample_rate <= 0:
        logger.warning("Invalid sample_rate=%r — skipping enhance", sample_rate)
        return mono_i16

    return _enhance_light(mono_i16, int(sample_rate))


def _to_mono_int16(samples: np.ndarray) -> np.ndarray:
    """Flatten channel dim and coerce to int16 mono without DSP.

    Critical: sounddevice delivers ``(frames, channels)`` **int16**. Averaging
    channels yields float64 values still in the *integer PCM range* (e.g. ±3000),
    not in [-1, 1]. Re-scaling those as if they were unit floats (*32767) clips
    every sample to full scale and destroys the speech signal — that was the
    bug behind unusable Light/Off transcription after the enhance path landed.
    """
    if samples is None:
        return np.zeros(0, dtype=np.int16)
    arr = np.asarray(samples)
    if arr.size == 0:
        return np.zeros(0, dtype=np.int16)

    # Remember the *input* scale before any mean() promotes int → float64.
    input_dtype = arr.dtype
    input_is_float = np.issubdtype(input_dtype, np.floating)
    input_is_int16 = input_dtype == np.int16

    if arr.ndim == 1 and input_is_int16:
        return arr.copy()

    if arr.ndim == 2 and arr.shape[1] == 1 and input_is_int16:
        # Fast path: mono int16 from sounddevice — no rescale, no mean loss.
        return np.ascontiguousarray(arr[:, 0])

    if arr.ndim == 2:
        # sounddevice / wav convention: (frames, channels). Average channels.
        arr = np.mean(arr.astype(np.float64), axis=1)
    elif arr.ndim > 2:
        arr = arr.reshape(arr.shape[0], -1).mean(axis=1)
    else:
        arr = arr.astype(np.float64, copy=False).reshape(-1)

    arr = np.asarray(arr, dtype=np.float64).reshape(-1)

    if input_is_float:
        # Caller handed unit-scale float PCM in [-1, 1].
        return np.clip(arr * 32767.0, -32768, 32767).astype(np.int16)

    if input_dtype == np.int32:
        scaled = (arr / 2147483648.0) * 32767.0
        return np.clip(scaled, -32768, 32767).astype(np.int16)

    # Integer PCM (typically int16): sample counts, not unit floats. Clip only.
    return np.clip(arr, -32768, 32767).astype(np.int16)


def _enhance_light(mono_i16: np.ndarray, sample_rate: int) -> np.ndarray:
    """High-pass → silence-aware AGC → soft limiter → int16."""
    x = mono_i16.astype(np.float64) / 32768.0

    x = _highpass(x, sample_rate)

    rms = float(np.sqrt(np.mean(x * x))) if x.size else 0.0
    if rms >= SILENCE_RMS:
        gain = min(TARGET_RMS / rms, MAX_GAIN)
        x = x * gain
    # else: leave level alone so we don't inflate near-silent chunks

    x = _soft_limit(x, LIMITER_CEILING)

    return np.clip(x * 32768.0, -32768, 32767).astype(np.int16)


def _highpass(x: np.ndarray, sample_rate: int) -> np.ndarray:
    """2nd-order Butterworth high-pass. No-op on tiny buffers or bad Nyquist."""
    if x.size < _MIN_HPF_SAMPLES:
        return x
    nyq = sample_rate * 0.5
    if HPF_CUTOFF_HZ >= nyq * 0.9:
        return x
    try:
        from scipy.signal import butter, sosfilt
    except ImportError:  # pragma: no cover
        logger.warning("scipy.signal unavailable — skipping high-pass")
        return x

    sos = butter(HPF_ORDER, HPF_CUTOFF_HZ / nyq, btype="highpass", output="sos")
    return sosfilt(sos, x).astype(np.float64, copy=False)


def _soft_limit(x: np.ndarray, ceiling: float) -> np.ndarray:
    """Soft knee into ±ceiling so peaks don't hard-clip after gain."""
    if ceiling <= 0:
        return x
    # tanh compression scaled so small signals stay ~linear and peaks approach ceiling.
    # y = ceiling * tanh(x / ceiling)
    return ceiling * np.tanh(x / ceiling)


# ----- input devices ----------------------------------------------------------


@dataclass(frozen=True)
class InputDeviceInfo:
    """One PortAudio input-capable device, for UI and resolve."""

    index: int
    name: str
    hostapi_name: str = ""
    max_input_channels: int = 1

    @property
    def config_value(self) -> str:
        """Stable-ish value stored in config.env."""
        return f"{_DEVICE_NAME_PREFIX}{self.name}"

    @property
    def display_label(self) -> str:
        # Host API is an implementation detail after we pick a preferred path
        # (WASAPI when present). Showing "(MME)" / "(WASAPI)" for every row
        # made the picker look like 3–4 copies of each mic.
        return self.name


def encode_device_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    return f"{_DEVICE_NAME_PREFIX}{name}"


def decode_device_name(config_value: Optional[str]) -> Optional[str]:
    """Return the bare device name, or None when config means system default."""
    raw = (config_value or "").strip()
    if not raw:
        return None
    if raw.startswith(_DEVICE_NAME_PREFIX):
        name = raw[len(_DEVICE_NAME_PREFIX) :].strip()
        return name or None
    # Legacy / bare name without prefix — still accept.
    return raw


# Prefer modern Windows host APIs. Exact name match across APIs fails on Windows
# because MME truncates names and WDM-KS renames devices ("… Wave", driver paths).
_HOSTAPI_PREFERENCE = (
    "windows wasapi",
    "windows directsound",
    "mme",
    "windows wdm-ks",
)

# PortAudio "virtual" capture endpoints — not real mics; confuse the picker.
_MAPPER_NAME_PREFIXES = (
    "microsoft sound mapper",
    "primary sound capture driver",
)


def _hostapi_rank(hostapi_name: str) -> int:
    key = (hostapi_name or "").strip().lower()
    try:
        return _HOSTAPI_PREFERENCE.index(key)
    except ValueError:
        return len(_HOSTAPI_PREFERENCE)


def _is_mapper_alias(name: str) -> bool:
    n = (name or "").strip().lower()
    return any(n.startswith(p) for p in _MAPPER_NAME_PREFIXES)


def _hostapi_key(hostapi_name: str) -> str:
    return (hostapi_name or "").strip().lower()


def _collect_input_devices(
    devices: Optional[Sequence[dict]] = None,
    hostapis: Optional[Sequence[dict]] = None,
) -> list[InputDeviceInfo]:
    """All input-capable PortAudio devices (no filtering / host preference)."""
    if devices is None:
        import sounddevice as sd

        devices = list(sd.query_devices())
        if hostapis is None:
            try:
                hostapis = list(sd.query_hostapis())
            except Exception:
                hostapis = []
    hostapis = hostapis or []
    hostapi_names = {
        i: (ha.get("name") or "") for i, ha in enumerate(hostapis)
    }

    out: list[InputDeviceInfo] = []
    for idx, dev in enumerate(devices):
        try:
            max_in = int(dev.get("max_input_channels") or 0)
        except (TypeError, ValueError):
            max_in = 0
        if max_in <= 0:
            continue
        name = (dev.get("name") or "").strip() or f"Device {idx}"
        ha_idx = dev.get("hostapi", 0)
        try:
            ha_idx_int = int(ha_idx)
        except (TypeError, ValueError):
            ha_idx_int = 0
        out.append(
            InputDeviceInfo(
                index=idx,
                name=name,
                hostapi_name=hostapi_names.get(ha_idx_int, ""),
                max_input_channels=max_in,
            )
        )
    return out


def list_input_devices(
    devices: Optional[Sequence[dict]] = None,
    hostapis: Optional[Sequence[dict]] = None,
    *,
    dedupe_by_name: bool = True,
) -> list[InputDeviceInfo]:
    """Return input devices for the Settings picker.

    Windows exposes the same physical mic via MME / DirectSound / WASAPI /
    WDM-KS, often with *different* strings (MME truncates, WDM-KS uses Wave /
    driver paths). Exact-name dedupe barely helps.

    Strategy when ``dedupe_by_name`` is True (default, UI path):

    1. Drop mapper aliases (Sound Mapper, Primary Sound Capture Driver).
    2. If any **WASAPI** inputs remain, show **only WASAPI** (best default on
       modern Windows — typically one clean row per real mic).
    3. Else DirectSound (minus mappers), else MME, else whatever is left
       (including WDM-KS).
    4. Within the chosen host API, still collapse exact duplicate names.

    Pass ``dedupe_by_name=False`` to get the raw input list (tests / diagnostics).
    """
    raw = _collect_input_devices(devices=devices, hostapis=hostapis)
    if not dedupe_by_name:
        return raw

    usable = [d for d in raw if not _is_mapper_alias(d.name)]
    if not usable:
        return []

    by_host: dict[str, list[InputDeviceInfo]] = {}
    for info in usable:
        by_host.setdefault(_hostapi_key(info.hostapi_name), []).append(info)

    chosen: list[InputDeviceInfo]
    if by_host.get("windows wasapi"):
        chosen = by_host["windows wasapi"]
    elif by_host.get("windows directsound"):
        chosen = by_host["windows directsound"]
    elif by_host.get("mme"):
        chosen = by_host["mme"]
    else:
        # WDM-KS or unknown host — last resort (ugly names, but better than empty).
        chosen = usable

    # Exact-name collapse inside the chosen host API (rare duplicates).
    best: dict[str, InputDeviceInfo] = {}
    for info in chosen:
        prev = best.get(info.name)
        if prev is None or info.index < prev.index:
            best[info.name] = info
    seen: set[str] = set()
    out: list[InputDeviceInfo] = []
    for info in chosen:
        if info.name in seen:
            continue
        seen.add(info.name)
        out.append(best[info.name])
    return out


def resolve_input_device(
    config_value: Optional[str],
    devices: Optional[Sequence[dict]] = None,
    hostapis: Optional[Sequence[dict]] = None,
) -> Optional[int]:
    """Map config string → PortAudio device index, or None for system default.

    Searches **all** host APIs (not only the UI-filtered list) so a saved name
    still resolves if the preferred API set changes. When several entries share
    the same name, prefer WASAPI → DirectSound → MME → WDM-KS.

    If the stored name is not found, logs a warning and returns None (caller
    opens the default device).
    """
    name = decode_device_name(config_value)
    if name is None:
        return None

    all_inputs = _collect_input_devices(devices=devices, hostapis=hostapis)
    matches = [info for info in all_inputs if info.name == name]
    if matches:
        matches.sort(key=lambda i: (_hostapi_rank(i.hostapi_name), i.index))
        return matches[0].index

    logger.warning(
        "Configured input device %r not found — using system default",
        name,
    )
    return None


def prepare_and_describe(
    samples: np.ndarray,
    sample_rate: int,
    profile: str = DEFAULT_ENHANCE_PROFILE,
) -> tuple[np.ndarray, dict]:
    """Like ``prepare_for_transcription`` but also returns a small debug dict.

    Useful for tests and optional logging (RMS in/out, gain applied).
    """
    mono = _to_mono_int16(samples)
    prof = normalize_enhance_profile(profile)
    if mono.size == 0 or prof == "off":
        return mono if prof == "off" else prepare_for_transcription(samples, sample_rate, profile), {
            "profile": prof,
            "rms_in": 0.0,
            "rms_out": 0.0,
            "gain": 1.0,
            "silent": True,
        }

    x_in = mono.astype(np.float64) / 32768.0
    rms_in = float(np.sqrt(np.mean(x_in * x_in)))
    silent = rms_in < SILENCE_RMS
    gain = 1.0 if silent else min(TARGET_RMS / max(rms_in, 1e-12), MAX_GAIN)
    out = prepare_for_transcription(samples, sample_rate, profile)
    x_out = out.astype(np.float64) / 32768.0
    rms_out = float(np.sqrt(np.mean(x_out * x_out))) if out.size else 0.0
    return out, {
        "profile": prof,
        "rms_in": rms_in,
        "rms_out": rms_out,
        "gain": gain,
        "silent": silent,
    }

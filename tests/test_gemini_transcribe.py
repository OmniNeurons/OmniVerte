"""services.gemini_transcribe: payload building, response parsing, error wrapping.

The module is pure stdlib, so the network layer is faked by monkeypatching
urllib.request.urlopen — no google SDK, no sockets.
"""

from __future__ import annotations

import base64
import io
import json
import urllib.error

import pytest

from services import gemini_transcribe as gt
from services.api_errors import classify_api_error
from services.gemini_transcribe import (
    GeminiApiError,
    build_transcription_payload,
    extract_transcript,
    transcribe_file,
)


# ---------- payload building ----------

def test_payload_embeds_audio_as_base64_wav():
    payload = build_transcription_payload("gemini-3.5-transcribe", b"RIFFxxxx")
    (part,) = payload["input"]
    assert part["type"] == "audio"
    assert part["mime_type"] == "audio/wav"
    assert base64.b64decode(part["data"]) == b"RIFFxxxx"
    assert payload["model"] == "gemini-3.5-transcribe"
    # No hint, no vocabulary → no transcription_config at all: auto-detect.
    assert "generation_config" not in payload


def test_payload_widens_whisper_hint_to_bcp47():
    payload = build_transcription_payload("m", b"x", language_hint="ru")
    config = payload["generation_config"]["transcription_config"]
    assert config["language_codes"] == ["ru-RU"]


def test_payload_omits_unmapped_hint():
    payload = build_transcription_payload("m", b"x", language_hint="tlh")
    assert "generation_config" not in payload


def test_payload_caps_vocabulary_preserving_head_priority():
    terms = [f"term{i}" for i in range(150)]
    payload = build_transcription_payload("m", b"x", vocabulary=terms)
    vocab = payload["generation_config"]["transcription_config"]["custom_vocabulary"]
    assert len(vocab) == gt.MAX_VOCABULARY_TERMS
    assert vocab[0] == "term0"  # head (own_names first) survives the trim


# ---------- response parsing ----------

def test_extract_prefers_output_text():
    assert extract_transcript({"output_text": "hello"}) == "hello"


def test_extract_falls_back_to_steps_content():
    response = {
        "steps": [{
            "type": "model_output",
            "content": [{"type": "text", "text": "hello "},
                        {"type": "text", "text": "world"}],
        }],
    }
    assert extract_transcript(response) == "hello world"


def test_extract_empty_transcript_is_valid():
    # Silence in → empty text out is a real result, not a protocol error.
    assert extract_transcript({"output_text": ""}) == ""


def test_extract_raises_on_unknown_shape():
    with pytest.raises(GeminiApiError) as exc_info:
        extract_transcript({"weird": True})
    assert exc_info.value.kind == "response"


# ---------- transcribe_file ----------

class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_transcribe_file_round_trip(monkeypatch, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"RIFF-fake-wav")
    seen = {}

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["api_key"] = request.get_header("X-goog-api-key")
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"output_text": "привет мир"}).encode())

    monkeypatch.setattr(gt.urllib.request, "urlopen", fake_urlopen)
    text = transcribe_file(
        "gm-key", str(wav), "gemini-3.5-transcribe",
        language_hint="ru", vocabulary=["OmniVerte"], timeout=17.0,
    )

    assert text == "привет мир"
    assert seen["url"] == gt.INTERACTIONS_URL
    assert seen["timeout"] == 17.0
    assert seen["api_key"] == "gm-key"
    body = seen["body"]
    assert body["model"] == "gemini-3.5-transcribe"
    config = body["generation_config"]["transcription_config"]
    assert config["language_codes"] == ["ru-RU"]
    assert config["custom_vocabulary"] == ["OmniVerte"]


def test_transcribe_file_rejects_oversize_audio(monkeypatch, tmp_path):
    wav = tmp_path / "huge.wav"
    wav.write_bytes(b"x")
    monkeypatch.setattr(gt, "MAX_INLINE_AUDIO_BYTES", 0)
    with pytest.raises(GeminiApiError):
        transcribe_file("k", str(wav), "m")


def _raise_http(code, body=b"{}"):
    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            gt.INTERACTIONS_URL, code, "err", hdrs=None, fp=io.BytesIO(body)
        )
    return fake_urlopen


def test_http_error_carries_status_and_classifies(monkeypatch, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"RIFF")
    monkeypatch.setattr(gt.urllib.request, "urlopen", _raise_http(403))
    with pytest.raises(GeminiApiError) as exc_info:
        transcribe_file("bad-key", str(wav), "m")
    err = exc_info.value
    assert err.kind == "http" and err.status == 403
    assert classify_api_error(err) == "auth"


@pytest.mark.parametrize(
    "code,body,expected",
    [
        (401, b"{}", "auth"),
        (429, b'{"error": {"message": "quota exceeded for today"}}', "quota"),
        (429, b'{"error": {"message": "slow down"}}', "rate"),
        (500, b"{}", "unknown"),
    ],
)
def test_gemini_error_classification(monkeypatch, tmp_path, code, body, expected):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"RIFF")
    monkeypatch.setattr(gt.urllib.request, "urlopen", _raise_http(code, body))
    with pytest.raises(GeminiApiError) as exc_info:
        transcribe_file("k", str(wav), "m")
    assert classify_api_error(exc_info.value) == expected


def test_network_error_classifies_as_network(monkeypatch, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"RIFF")

    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError("dns is down")

    monkeypatch.setattr(gt.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(GeminiApiError) as exc_info:
        transcribe_file("k", str(wav), "m")
    assert exc_info.value.kind == "network"
    assert classify_api_error(exc_info.value) == "network"


def test_non_json_body_raises_response_error(monkeypatch, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"RIFF")

    def fake_urlopen(request, timeout=None):
        return _FakeResponse(b"<html>edge proxy said no</html>")

    monkeypatch.setattr(gt.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(GeminiApiError) as exc_info:
        transcribe_file("k", str(wav), "m")
    assert exc_info.value.kind == "response"

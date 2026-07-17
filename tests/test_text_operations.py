"""text_operations: empty-input short-circuits, output stripping, prompt wiring."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services import text_operations
from services.text_operations import (
    CORRECTION_MODEL,
    _chat_with_watchdog,
    fix_text,
    rewrite_text,
    translate_text,
    translate_to_language,
)


def make_client(reply: str = "OK") -> MagicMock:
    """Fake OpenAI client whose chat.completions.create returns `reply`."""
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=reply))]
    )
    return client


def test_translate_empty_returns_empty_without_calling_api():
    client = make_client()
    assert translate_text(client, "   ", "English", "Russian") == ""
    client.chat.completions.create.assert_not_called()


def test_translate_strips_output_and_passes_both_languages():
    client = make_client("  Привет  ")
    out = translate_text(client, "Hello", "English", "Russian")
    assert out == "Привет"
    system_msg = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "English" in system_msg and "Russian" in system_msg


def test_translate_to_language_targets_fixed_language():
    client = make_client("Bonjour")
    out = translate_to_language(client, "Hello", "French")
    assert out == "Bonjour"
    system_msg = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "French" in system_msg


def test_fix_text_uses_correction_model():
    client = make_client("fixed")
    assert fix_text(client, "raw text") == "fixed"
    assert client.chat.completions.create.call_args.kwargs["model"] == CORRECTION_MODEL


def test_rewrite_requires_both_text_and_instruction():
    client = make_client("x")
    assert rewrite_text(client, "text", "   ") == ""
    assert rewrite_text(client, "   ", "make it formal") == ""
    client.chat.completions.create.assert_not_called()


def test_rewrite_embeds_style_instruction_in_prompt():
    client = make_client("done")
    rewrite_text(client, "hi", "Make it sound like a pirate.")
    system_msg = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "pirate" in system_msg


def test_glossary_block_appended_to_system_prompt():
    client = make_client("done")
    translate_to_language(client, "Hi", "French", glossary_block="- Acme Corp\n- Z-tuning")
    system_msg = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "Acme Corp" in system_msg
    assert "Z-tuning" in system_msg
    assert "canonical" in system_msg.lower()


def test_glossary_block_omitted_leaves_prompt_unchanged():
    client = make_client("done")
    rewrite_text(client, "Hi", "Make it formal.")  # no glossary_block
    system_msg = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "canonical" not in system_msg.lower()


def test_glossary_block_empty_string_is_noop():
    client = make_client("fixed")
    fix_text(client, "raw", glossary_block="   ")
    system_msg = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "canonical" not in system_msg.lower()


def test_chat_watchdog_retries_after_transient_error():
    """First attempt raises, second succeeds — caller sees the second result."""
    ok_reply = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="recovered"))]
    )
    client = MagicMock()
    client.chat.completions.create.side_effect = [RuntimeError("flake"), ok_reply]

    response = _chat_with_watchdog(client, "test", model="x", messages=[])
    assert response is ok_reply
    assert client.chat.completions.create.call_count == 2


def test_chat_watchdog_gives_up_after_max_attempts():
    """All attempts fail → last error is re-raised, exactly _CHAT_MAX_ATTEMPTS calls."""
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("dead")

    with pytest.raises(RuntimeError, match="dead"):
        _chat_with_watchdog(client, "test", model="x", messages=[])
    assert client.chat.completions.create.call_count == text_operations._CHAT_MAX_ATTEMPTS


def test_chat_watchdog_fires_on_hung_call():
    """A stalled call is abandoned by the wall-clock watchdog and retried."""
    # Hang the first attempt past the watchdog deadline, then succeed.
    ok_reply = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )

    def hang_then_ok(*_args, **_kwargs):
        if not hang_then_ok.tripped:
            hang_then_ok.tripped = True
            time.sleep(1.0)  # > watchdog
        return ok_reply
    hang_then_ok.tripped = False

    client = MagicMock()
    client.chat.completions.create.side_effect = hang_then_ok

    with patch.object(text_operations, "_CHAT_ATTEMPT_TIMEOUT", 0.2):
        response = _chat_with_watchdog(client, "test", model="x", messages=[])

    assert response is ok_reply
    # First attempt hung (counted), second returned cleanly.
    assert client.chat.completions.create.call_count == 2


def test_attempt_deadline_scales_with_payload():
    """Longer payloads get a longer per-attempt deadline, capped at the ceiling."""
    base = text_operations._CHAT_ATTEMPT_TIMEOUT
    per_1k = text_operations._CHAT_ATTEMPT_TIMEOUT_PER_1K
    ceiling = text_operations._CHAT_ATTEMPT_TIMEOUT_MAX

    # Empty/short input → exactly the base (keeps the hung-socket test's 0-char
    # patch semantics intact).
    assert text_operations._attempt_deadline(0) == base
    # 1000 chars → base + one full surcharge.
    assert text_operations._attempt_deadline(1000) == pytest.approx(base + per_1k)
    # A huge payload is clamped to the ceiling, never unbounded.
    assert text_operations._attempt_deadline(1_000_000) == ceiling


def test_payload_chars_sums_string_message_contents():
    """_payload_chars counts only string contents and tolerates odd shapes."""
    kwargs = {
        "messages": [
            {"role": "system", "content": "abc"},
            {"role": "user", "content": "defg"},
            {"role": "tool", "content": None},          # ignored
            {"role": "user", "content": [{"type": "x"}]},  # non-str, ignored
        ]
    }
    assert text_operations._payload_chars(kwargs) == 7
    assert text_operations._payload_chars({}) == 0


def test_long_payload_survives_a_slow_but_valid_response():
    """The regression: a long input whose response lands just after the OLD
    fixed 15s deadline but well within the scaled one must NOT be abandoned."""
    ok_reply = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="translated"))]
    )

    def slow_ok(*_args, **_kwargs):
        time.sleep(0.3)  # would trip a 0.2s base deadline, not the scaled one
        return ok_reply

    client = MagicMock()
    client.chat.completions.create.side_effect = slow_ok

    long_text = "word " * 400  # 2000 chars
    # base 0.2s + (2000/1000)*0.5s = 1.2s deadline → 0.3s response fits.
    with patch.object(text_operations, "_CHAT_ATTEMPT_TIMEOUT", 0.2), \
         patch.object(text_operations, "_CHAT_ATTEMPT_TIMEOUT_PER_1K", 0.5):
        response = _chat_with_watchdog(
            client, "test", model="x",
            messages=[{"role": "user", "content": long_text}],
        )

    assert response is ok_reply
    assert client.chat.completions.create.call_count == 1

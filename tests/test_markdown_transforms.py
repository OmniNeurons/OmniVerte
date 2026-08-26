# file: tests/test_markdown_transforms.py

"""Guards around the markdown-preserving LLM round-trip.

Covers the pure-string helpers (fence unwrapping, the block-level structure
signature) and the `_run_transform` retry ladder via a canned fake client —
no network, no Qt. Plus the Config.llm_max_tokens clamp.
"""

from __future__ import annotations

from types import SimpleNamespace

from services.config_store import Config
from services.text_operations import (
    _inline_marks_balanced,
    _markdown_signature,
    _run_transform,
    markdown_structure_ok,
    strip_wrapping_fence,
)


# ---------- strip_wrapping_fence ----------

def test_fence_bare_wrap_is_unwrapped():
    assert strip_wrapping_fence("```\n**Bold** text\n```") == "**Bold** text"


def test_fence_language_tag_wrap_is_unwrapped():
    assert strip_wrapping_fence("```markdown\n# Title\nBody\n```") == "# Title\nBody"


def test_fence_unwrapped_text_untouched():
    text = "# Title\n\nplain paragraph"
    assert strip_wrapping_fence(text) == text


def test_fence_with_inner_code_block_untouched():
    # Ambiguous: the wrapper may be content. Leave it for the structure check.
    text = "```\nintro\n```python\nx = 1\n```\noutro\n```"
    assert strip_wrapping_fence(text) == text


def test_fence_single_line_untouched():
    assert strip_wrapping_fence("```") == "```"


# ---------- structure signature ----------

def test_signature_counts_block_elements():
    md = (
        "# Title\n"
        "## Sub\n"
        "- one\n"
        "- two\n"
        "* three\n"
        "1. first\n"
        "2) second\n"
        "| a | b |\n"
        "|---|---|\n"
        "plain line\n"
    )
    assert _markdown_signature(md) == (2, 3, 2, 2)


def test_signature_ignores_fenced_code():
    md = "# Real\n```\n# not a heading\n- not a bullet\n```\n"
    assert _markdown_signature(md) == (1, 0, 0, 0)


def test_inline_marks_balance():
    assert _inline_marks_balanced("**bold** and `code`")
    assert not _inline_marks_balanced("**bold and `code`")   # ** unclosed
    assert not _inline_marks_balanced("only `one backtick")  # ` unclosed


def test_structure_ok_tolerates_word_order_changes():
    src = "# Титул\n- **первый** пункт\n- второй\n"
    out = "# Title\n- the **first** item\n- the second\n"
    assert markdown_structure_ok(src, out)


def test_structure_not_ok_on_lost_list_item():
    src = "- one\n- two\n- three\n"
    out = "- one\n- two\n"
    assert not markdown_structure_ok(src, out)


# ---------- _run_transform retry ladder ----------

class _FakeClient:
    """Returns canned (content, finish_reason) replies and records each call."""

    def __init__(self, replies: list[tuple[str, str]]):
        self._replies = list(replies)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        content, finish = self._replies.pop(0)
        choice = SimpleNamespace(
            message=SimpleNamespace(content=content), finish_reason=finish
        )
        return SimpleNamespace(choices=[choice])


def _transform(client, *, markdown, source, max_tokens=1000):
    return _run_transform(
        client,
        "test",
        system_msg="sys",
        user_msg=source,
        temperature=0.2,
        max_tokens=max_tokens,
        markdown=markdown,
        source_text=source,
    )


def test_plain_mode_is_a_single_call():
    client = _FakeClient([("result", "stop")])
    assert _transform(client, markdown=False, source="hello") == "result"
    assert len(client.calls) == 1
    # Plain mode must not leak the markdown clause into the prompt.
    assert "Markdown" not in client.calls[0]["messages"][0]["content"]


def test_markdown_mode_appends_clause_and_unwraps_fence():
    client = _FakeClient([("```markdown\n- uno\n```", "stop")])
    assert _transform(client, markdown=True, source="- one\n") == "- uno"
    assert "Markdown" in client.calls[0]["messages"][0]["content"]


def test_truncation_retries_once_with_doubled_budget():
    client = _FakeClient([("cut off resu", "length"), ("full result", "stop")])
    assert _transform(client, markdown=False, source="hello", max_tokens=1000) == "full result"
    assert [c["max_tokens"] for c in client.calls] == [1000, 2000]


def test_structure_mismatch_retries_with_reminder_and_takes_good_retry():
    src = "- one\n- two\n"
    client = _FakeClient([("- uno\n", "stop"), ("- uno\n- dos\n", "stop")])
    assert _transform(client, markdown=True, source=src) == "- uno\n- dos"
    assert len(client.calls) == 2
    assert "STRICT" in client.calls[1]["messages"][0]["content"]


def test_structure_mismatch_keeps_first_result_when_retry_no_better():
    src = "- one\n- two\n"
    client = _FakeClient([("- uno\n", "stop"), ("- solo\n", "stop")])
    # Both attempts diverge → best-effort: the first reply, no third call.
    assert _transform(client, markdown=True, source=src) == "- uno"
    assert len(client.calls) == 2


def test_matching_structure_needs_no_retry():
    src = "# T\n- a\n- b\n"
    client = _FakeClient([("# Т\n- а\n- б\n", "stop")])
    assert _transform(client, markdown=True, source=src) == "# Т\n- а\n- б"
    assert len(client.calls) == 1


# ---------- Config.llm_max_tokens ----------

def test_llm_max_tokens_default(appdata):
    assert Config().llm_max_tokens == 4000


def test_llm_max_tokens_round_trip(appdata):
    Config().set("LLM_MAX_TOKENS", "6000")
    assert Config().llm_max_tokens == 6000


def test_llm_max_tokens_clamps_and_survives_garbage(appdata):
    c = Config()
    c.set("LLM_MAX_TOKENS", "50")
    assert c.llm_max_tokens == 500
    c.set("LLM_MAX_TOKENS", "999999")
    assert c.llm_max_tokens == 16000
    c.set("LLM_MAX_TOKENS", "not-a-number")
    assert c.llm_max_tokens == 4000

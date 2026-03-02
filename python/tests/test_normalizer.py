"""Tests for input normalizer."""

from omnimind_backend.infra.normalizer import normalize_message
from omnimind_backend.schemas.normalization import NormalizationConfig


def test_collapse_excessive_punctuation() -> None:
    assert normalize_message("Hello!!!!!!") == "Hello!"
    assert normalize_message("What???") == "What?"
    assert normalize_message("Wow.......") == "Wow..."


def test_collapse_whitespace() -> None:
    assert normalize_message("Hello    world") == "Hello world"
    assert normalize_message("Hello\n\n\n\nworld") == "Hello\n\nworld"


def test_preserve_code_blocks() -> None:
    msg = "Check this:\n```python\nprint('Hello!!!!!!')\n```\nDone!!!!!!"
    result = normalize_message(msg)
    assert "print('Hello!!!!!!')" in result  # Code block preserved
    assert result.endswith("Done!")  # Outside code block normalized


def test_disabled_returns_original() -> None:
    cfg = NormalizationConfig(enabled=False)
    msg = "Hello!!!!!!"
    assert normalize_message(msg, config=cfg) == msg


def test_strip_filler_phrases() -> None:
    result = normalize_message("Well, basically, I just want to, you know, fix the bug")
    assert "basically" not in result
    assert "you know" not in result
    assert "fix the bug" in result


def test_collapse_repeated_sentences() -> None:
    msg = "Fix the login bug. Fix the login bug. Fix the login bug."
    result = normalize_message(msg)
    assert result.count("Fix the login bug") == 1
    assert "[repeated 3 times]" in result


def test_no_collapse_for_unique_sentences() -> None:
    msg = "Fix the login bug. Then update the docs. Finally run tests."
    result = normalize_message(msg)
    assert "Fix the login bug" in result
    assert "update the docs" in result
    assert "run tests" in result

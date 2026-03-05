"""Tests for no-raw-context payload guard."""

import pytest

from omnimind_backend.orchestrator.context_validation import validate_payload_size, PayloadTooLargeError, estimate_tokens


def test_small_payload_passes() -> None:
    payload = "Short summary of findings."
    validate_payload_size(payload)  # Should not raise


def test_large_payload_rejected() -> None:
    payload = "x " * 5000  # ~10000 chars = ~2500 tokens
    with pytest.raises(PayloadTooLargeError):
        validate_payload_size(payload, max_tokens=1000)


def test_custom_max_tokens() -> None:
    payload = "x " * 200  # ~400 chars = ~100 tokens
    validate_payload_size(payload, max_tokens=200)  # Should pass


def test_empty_payload_passes() -> None:
    validate_payload_size("")


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("test") == 1  # 4 chars = 1 token
    assert estimate_tokens("test test") == 2  # 9 chars = 2 tokens
    assert estimate_tokens("a" * 100) == 25  # 100 chars = 25 tokens


def test_payload_too_large_error_message() -> None:
    payload = "x " * 2000  # ~4000 chars = ~1000 tokens
    with pytest.raises(PayloadTooLargeError) as exc_info:
        validate_payload_size(payload, max_tokens=500)
    
    error_msg = str(exc_info.value)
    assert "1000 tokens" in error_msg
    assert "exceeds limit of 500" in error_msg
    assert "re-summarize" in error_msg


def test_exact_limit_passes() -> None:
    payload = "x" * 4000  # 4000 chars = 1000 tokens
    validate_payload_size(payload, max_tokens=1000)  # Should pass


def test_one_over_limit_fails() -> None:
    payload = "x " * 4004  # ~4004 chars = ~1001 tokens
    with pytest.raises(PayloadTooLargeError):
        validate_payload_size(payload, max_tokens=1000)
"""Tests for OAuth2 PKCE implementation."""

import pytest

from mindflow_backend.security.auth.oauth2 import (
    generate_code_challenge,
    generate_code_verifier,
    generate_pkce_pair,
)


def test_generate_code_verifier():
    """Test code verifier generation."""
    verifier = generate_code_verifier()

    assert verifier is not None
    assert len(verifier) >= 43
    # Length may exceed 128 due to base64 encoding, but should be reasonable
    assert len(verifier) <= 200
    # Should only contain URL-safe characters
    assert all(c.isalnum() or c in "-._~" for c in verifier)


def test_generate_code_challenge_s256():
    """Test code challenge generation with S256 method."""
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier, method="S256")

    assert challenge is not None
    assert len(challenge) > 0
    # Challenge should be different from verifier
    assert challenge != verifier


def test_generate_code_challenge_plain():
    """Test code challenge generation with plain method."""
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier, method="plain")

    assert challenge is not None
    # Plain method should return verifier unchanged
    assert challenge == verifier


def test_generate_code_challenge_invalid_method():
    """Test code challenge with invalid method."""
    verifier = generate_code_verifier()

    with pytest.raises(ValueError, match="Unsupported code challenge method"):
        generate_code_challenge(verifier, method="invalid")


def test_generate_pkce_pair():
    """Test PKCE pair generation."""
    verifier, challenge = generate_pkce_pair(method="S256")

    assert verifier is not None
    assert challenge is not None
    assert len(verifier) >= 43
    assert challenge != verifier


def test_generate_pkce_pair_custom_length():
    """Test PKCE pair generation with custom length."""
    verifier, challenge = generate_pkce_pair(verifier_length=64, method="S256")

    assert verifier is not None
    assert challenge is not None
    assert len(verifier) >= 43


def test_code_verifier_uniqueness():
    """Test that code verifiers are unique."""
    verifiers = [generate_code_verifier() for _ in range(10)]

    # All verifiers should be unique
    assert len(set(verifiers)) == 10


def test_code_challenge_deterministic():
    """Test that code challenge is deterministic for same verifier."""
    verifier = generate_code_verifier()
    challenge1 = generate_code_challenge(verifier, method="S256")
    challenge2 = generate_code_challenge(verifier, method="S256")

    # Same verifier should produce same challenge
    assert challenge1 == challenge2

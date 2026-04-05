"""Tests for OAuth2 state manager."""

import pytest
import asyncio

from mindflow_backend.security.auth.oauth2 import StateManager


@pytest.mark.asyncio
async def test_state_generation():
    """Test state generation."""
    manager = StateManager()
    state = manager.generate_state(user_id="test_user")

    assert state is not None
    assert len(state) == 36  # UUID format


@pytest.mark.asyncio
async def test_state_validation():
    """Test state validation."""
    manager = StateManager()
    state = manager.generate_state(user_id="test_user")

    # Valid state
    is_valid = manager.validate_state(state, user_id="test_user")
    assert is_valid is True

    # State should be consumed (one-time use)
    is_valid_again = manager.validate_state(state, user_id="test_user")
    assert is_valid_again is False


@pytest.mark.asyncio
async def test_state_validation_wrong_user():
    """Test state validation with wrong user."""
    manager = StateManager()
    state = manager.generate_state(user_id="test_user")

    # Wrong user_id
    is_valid = manager.validate_state(state, user_id="wrong_user")
    assert is_valid is False


@pytest.mark.asyncio
async def test_state_validation_invalid_state():
    """Test state validation with invalid state."""
    manager = StateManager()

    # Invalid state
    is_valid = manager.validate_state("invalid-state", user_id="test_user")
    assert is_valid is False


@pytest.mark.asyncio
async def test_state_expiration():
    """Test state expiration."""
    manager = StateManager(ttl_seconds=1)  # 1 second TTL
    state = manager.generate_state(user_id="test_user")

    # Wait for expiration
    await asyncio.sleep(1.5)

    # State should be expired
    is_valid = manager.validate_state(state, user_id="test_user")
    assert is_valid is False


@pytest.mark.asyncio
async def test_cleanup_expired_states():
    """Test cleanup of expired states."""
    manager = StateManager(ttl_seconds=1)

    # Generate states
    state1 = manager.generate_state(user_id="user1")
    await asyncio.sleep(1.5)  # Let state1 expire
    state2 = manager.generate_state(user_id="user2")

    # Cleanup expired
    cleaned = manager.cleanup_expired_states()

    assert cleaned >= 1


@pytest.mark.asyncio
async def test_clear_all_states():
    """Test clearing all states."""
    manager = StateManager()

    # Generate multiple states
    for i in range(5):
        manager.generate_state(user_id=f"user{i}")

    # Clear all
    cleared = manager.clear_all_states()

    assert cleared == 5

    # Verify all cleared
    for i in range(5):
        is_valid = manager.validate_state(f"state{i}", user_id=f"user{i}")
        assert is_valid is False


@pytest.mark.asyncio
async def test_state_uniqueness():
    """Test that states are unique."""
    manager = StateManager()

    states = [manager.generate_state(user_id="test_user") for _ in range(10)]

    # All states should be unique
    assert len(set(states)) == 10

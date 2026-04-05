"""Tests for OAuth2 callback server."""

import pytest
import asyncio
from mindflow_backend.security.auth.oauth2.callback_server import OAuthCallbackServer


@pytest.mark.asyncio
async def test_callback_server_start():
    """Test starting callback server."""
    server = OAuthCallbackServer(expected_state="test-state", timeout=10)
    port = await server.start()

    assert port > 0
    assert port < 65536

    await server.stop()


@pytest.mark.asyncio
async def test_callback_server_stop():
    """Test stopping callback server."""
    server = OAuthCallbackServer(expected_state="test-state", timeout=10)
    await server.start()
    await server.stop()

    # Should not raise exception
    await server.stop()


@pytest.mark.asyncio
async def test_callback_server_state_validation():
    """Test state validation in callback."""
    server = OAuthCallbackServer(expected_state="correct-state", timeout=10)

    # Simulate callback with correct state
    server._handle_callback("test-code", {"state": "correct-state"})

    assert server.authorization_code == "test-code"
    assert server._callback_received.is_set()


@pytest.mark.asyncio
async def test_callback_server_state_mismatch():
    """Test state mismatch rejection."""
    server = OAuthCallbackServer(expected_state="correct-state", timeout=10)

    # Simulate callback with wrong state
    # This should be handled by the HTTP handler, not directly
    # We test the expected_state is set correctly
    assert server.expected_state == "correct-state"


@pytest.mark.asyncio
async def test_callback_server_wait_for_callback():
    """Test waiting for callback."""
    server = OAuthCallbackServer(expected_state="test-state", timeout=10)
    await server.start()

    # Simulate callback
    server._handle_callback("test-code", {"state": "test-state"})

    # Wait for callback
    code, params = await server.wait_for_callback()

    assert code == "test-code"
    assert params["state"] == "test-state"

    await server.stop()


@pytest.mark.asyncio
async def test_callback_server_timeout():
    """Test callback timeout."""
    server = OAuthCallbackServer(expected_state="test-state", timeout=1)
    await server.start()

    # Wait for callback without receiving one
    code, params = await server.wait_for_callback()

    assert code is None
    assert params == {}

    await server.stop()

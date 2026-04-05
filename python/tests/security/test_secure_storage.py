"""Tests for secure storage backends."""

import json
import pytest
from pathlib import Path

from mindflow_backend.security.secrets import (
    SecureStorageData,
    get_secure_storage,
)


@pytest.mark.asyncio
async def test_secure_storage_write_read():
    """Test writing and reading secrets."""
    storage = get_secure_storage(use_fallback=True)

    # Write secret
    data = SecureStorageData()
    data.add_secret(
        user_id="test_user",
        service="github",
        secret_data={"token": "ghp_test_token"},
    )

    success = storage.write(data)
    assert success is True

    # Read secret
    secret = storage.get_secret("github", "test_user")
    assert secret is not None
    assert secret["token"] == "ghp_test_token"

    # Cleanup
    storage.delete("github", "test_user")


@pytest.mark.asyncio
async def test_secure_storage_delete():
    """Test deleting secrets."""
    storage = get_secure_storage(use_fallback=True)

    # Write secret
    data = SecureStorageData()
    data.add_secret(
        user_id="test_user",
        service="openai",
        secret_data={"api_key": "sk_test_key"},
    )

    storage.write(data)

    # Delete secret
    success = storage.delete("openai", "test_user")
    assert success is True

    # Verify deletion
    secret = storage.get_secret("openai", "test_user")
    assert secret is None


@pytest.mark.asyncio
async def test_secure_storage_multiple_services():
    """Test storing secrets for multiple services."""
    storage = get_secure_storage(use_fallback=True)

    # Write github secret
    github_data = SecureStorageData()
    github_data.add_secret(
        user_id="test_user",
        service="github",
        secret_data={"token": "ghp_test"},
    )

    storage.write(github_data)

    # Read github secret
    github_secret = storage.get_secret("github", "test_user")
    assert github_secret is not None
    assert github_secret["token"] == "ghp_test"

    # Write openai secret (will now coexist with github)
    # Read existing data first
    existing_data = storage.read()
    if existing_data is None:
        existing_data = SecureStorageData()

    existing_data.add_secret(
        user_id="test_user",
        service="openai",
        secret_data={"api_key": "sk_test"},
    )

    storage.write(existing_data)

    # Read openai secret
    openai_secret = storage.get_secret("openai", "test_user")
    assert openai_secret is not None
    assert openai_secret["api_key"] == "sk_test"

    # Now github secret should still exist
    github_secret_after = storage.get_secret("github", "test_user")
    assert github_secret_after is not None
    assert github_secret_after["token"] == "ghp_test"

    # Cleanup
    storage.delete("github", "test_user")
    storage.delete("openai", "test_user")


@pytest.mark.asyncio
async def test_secure_storage_update():
    """Test updating existing secret."""
    storage = get_secure_storage(use_fallback=True)

    # Write initial secret
    data = SecureStorageData()
    data.add_secret(
        user_id="test_user",
        service="anthropic",
        secret_data={"api_key": "sk-ant-old"},
    )

    storage.write(data)

    # Update secret
    updated_data = SecureStorageData()
    updated_data.add_secret(
        user_id="test_user",
        service="anthropic",
        secret_data={"api_key": "sk-ant-new"},
    )

    storage.write(updated_data)

    # Verify update
    secret = storage.get_secret("anthropic", "test_user")
    assert secret is not None
    assert secret["api_key"] == "sk-ant-new"

    # Cleanup
    storage.delete("anthropic", "test_user")


@pytest.mark.asyncio
async def test_secure_storage_clear():
    """Test clearing all secrets."""
    storage = get_secure_storage(use_fallback=True)

    # Write secret
    data = SecureStorageData()
    data.add_secret(
        user_id="test_user",
        service="test_service",
        secret_data={"secret": "test_value"},
    )

    storage.write(data)

    # Clear all
    success = storage.clear()
    assert success is True

    # Verify clear
    secret = storage.get_secret("test_service", "test_user")
    assert secret is None


@pytest.mark.asyncio
async def test_secure_storage_metadata():
    """Test storing metadata with secrets."""
    storage = get_secure_storage(use_fallback=True)

    # Write secret with metadata
    data = SecureStorageData()
    data.add_secret(
        user_id="test_user",
        service="github",
        secret_data={"token": "ghp_test"},
        metadata={"type": "oauth_token", "expires": "2025-12-31"},
    )

    storage.write(data)

    # Note: Metadata is stored but not returned by get_secret
    # This is by design to keep the API simple
    secret = storage.get_secret("github", "test_user")
    assert secret is not None
    assert secret["token"] == "ghp_test"

    # Cleanup
    storage.delete("github", "test_user")


@pytest.mark.asyncio
async def test_secure_storage_nonexistent_secret():
    """Test reading non-existent secret."""
    storage = get_secure_storage(use_fallback=True)

    # Try to read non-existent secret
    secret = storage.get_secret("nonexistent", "nonexistent_user")
    assert secret is None


@pytest.mark.asyncio
async def test_secure_storage_complex_data():
    """Test storing complex secret data structures."""
    storage = get_secure_storage(use_fallback=True)

    # Write complex data
    complex_data = {
        "access_token": "test_token",
        "refresh_token": "refresh_token",
        "expires_at": 1234567890,
        "scopes": ["read", "write", "admin"],
        "user_info": {
            "id": "user_id",
            "name": "Test User",
            "email": "test@example.com",
        },
    }

    data = SecureStorageData()
    data.add_secret(
        user_id="test_user",
        service="oauth_provider",
        secret_data=complex_data,
    )

    storage.write(data)

    # Read and verify
    secret = storage.get_secret("oauth_provider", "test_user")
    assert secret is not None
    assert secret["access_token"] == "test_token"
    assert secret["scopes"] == ["read", "write", "admin"]
    assert secret["user_info"]["email"] == "test@example.com"

    # Cleanup
    storage.delete("oauth_provider", "test_user")

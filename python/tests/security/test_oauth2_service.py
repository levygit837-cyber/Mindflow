"""Tests for OAuth2 service integration."""

import pytest
from mindflow_backend.security.auth import OAuth2Service, StateManager


@pytest.mark.asyncio
async def test_oauth2_service_init():
    """Test OAuth2 service initialization."""
    service = OAuth2Service()

    assert service is not None
    assert service.state_manager is not None


@pytest.mark.asyncio
async def test_oauth2_service_start_flow():
    """Test starting OAuth2 flow."""
    service = OAuth2Service()

    auth_url, state = await service.start_oauth_flow(
        provider_name="github",
        user_id="test_user",
    )

    assert auth_url is not None
    assert state is not None
    assert "github.com" in auth_url
    assert "client_id" in auth_url


@pytest.mark.asyncio
async def test_oauth2_service_invalid_provider():
    """Test OAuth2 service with invalid provider."""
    service = OAuth2Service()

    with pytest.raises(ValueError, match="Unknown OAuth2 provider"):
        await service.start_oauth_flow(
            provider_name="invalid_provider",
            user_id="test_user",
        )


@pytest.mark.asyncio
async def test_oauth2_service_state_generation():
    """Test state generation in OAuth2 flow."""
    service = OAuth2Service()

    auth_url, state = await service.start_oauth_flow(
        provider_name="github",
        user_id="test_user",
    )

    # State should be generated
    assert state is not None
    assert len(state) == 36  # UUID format


@pytest.mark.asyncio
async def test_oauth2_service_pkce_parameters():
    """Test PKCE parameters in authorization URL."""
    service = OAuth2Service()

    auth_url, state = await service.start_oauth_flow(
        provider_name="github",
        user_id="test_user",
    )

    # Check for PKCE parameters
    assert "code_challenge" in auth_url
    assert "code_challenge_method=S256" in auth_url


@pytest.mark.asyncio
async def test_oauth2_service_tokens_dataclass():
    """Test OAuth2Tokens dataclass."""
    from mindflow_backend.security.auth.oauth2.service import OAuth2Tokens

    tokens = OAuth2Tokens(
        access_token="test_token",
        token_type="Bearer",
        expires_in=3600,
    )

    assert tokens.access_token == "test_token"
    assert tokens.token_type == "Bearer"
    assert tokens.expires_in == 3600
    assert tokens.received_at is not None


@pytest.mark.asyncio
async def test_oauth2_tokens_not_expired():
    """Test token expiration check (not expired)."""
    from mindflow_backend.security.auth.oauth2.service import OAuth2Tokens

    tokens = OAuth2Tokens(
        access_token="test_token",
        token_type="Bearer",
        expires_in=3600,  # 1 hour
    )

    # Should not be expired
    assert tokens.is_expired() is False


@pytest.mark.asyncio
async def test_oauth2_tokens_expired():
    """Test token expiration check (expired)."""
    from mindflow_backend.security.auth.oauth2.service import OAuth2Tokens
    from datetime import UTC, datetime, timedelta

    tokens = OAuth2Tokens(
        access_token="test_token",
        token_type="Bearer",
        expires_in=3600,
    )

    # Manually set received_at to 2 hours ago
    tokens.received_at = (datetime.now(UTC) - timedelta(hours=2)).isoformat()

    # Should be expired
    assert tokens.is_expired() is True


@pytest.mark.asyncio
async def test_oauth2_service_custom_state_manager():
    """Test OAuth2 service with custom state manager."""
    custom_manager = StateManager(ttl_seconds=600)
    service = OAuth2Service(state_manager=custom_manager)

    assert service.state_manager is custom_manager


@pytest.mark.asyncio
async def test_oauth2_config_get_provider():
    """Test getting provider configuration."""
    from mindflow_backend.security.auth.oauth2.config import get_provider_config

    config = get_provider_config("github")

    assert config is not None
    assert config.name == "GitHub"
    assert "github.com" in config.authorization_url


@pytest.mark.asyncio
async def test_oauth2_config_invalid_provider():
    """Test getting invalid provider configuration."""
    from mindflow_backend.security.auth.oauth2.config import get_provider_config

    config = get_provider_config("invalid_provider")

    assert config is None


@pytest.mark.asyncio
async def test_oauth2_config_base_url_allowed():
    """Test base URL validation."""
    from mindflow_backend.security.auth.oauth2.config import is_base_url_allowed

    assert is_base_url_allowed("https://github.com/user/repo") is True
    assert is_base_url_allowed("https://api.github.com/repos") is True
    assert is_base_url_allowed("https://evil.com") is False


@pytest.mark.asyncio
async def test_oauth2_tokens_expired_with_buffer():
    """Test token expiration check with buffer."""
    from mindflow_backend.security.auth.oauth2.service import OAuth2Tokens
    from datetime import UTC, datetime, timedelta

    tokens = OAuth2Tokens(
        access_token="test_token",
        token_type="Bearer",
        expires_in=3600,  # 1 hour
    )

    # Set received_at to 59 minutes ago (within 60 second buffer)
    tokens.received_at = (datetime.now(UTC) - timedelta(minutes=59)).isoformat()

    # Should be expired with 60 second buffer
    assert tokens.is_expired(buffer_seconds=60) is True

    # Should not be expired with 30 second buffer
    assert tokens.is_expired(buffer_seconds=30) is False

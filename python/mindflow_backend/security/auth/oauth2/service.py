"""OAuth2 service for authentication flow.

Main service for OAuth2 authentication with PKCE, CSRF protection,
and token management.

TODO: Integrate with CLI
- CLI should support device code flow for OAuth2
- CLI should enforce same timeout policies as backend

TODO: Integrate with Desktop
- Desktop should support custom scheme OAuth2 flow
- Desktop should enforce same timeout policies as backend
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.security.secrets import get_secure_storage, SecureStorageData

from .callback_server import OAuthCallbackServer
from .config import (
    get_provider_config,
    is_base_url_allowed,
    SENSITIVE_OAUTH_PARAMS,
)
from .pkce import generate_code_verifier, generate_code_challenge
from .state_manager import StateManager

_logger = get_logger(__name__)


@dataclass
class OAuth2Tokens:
    """OAuth2 tokens response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    received_at: str | None = None

    def __post_init__(self) -> None:
        """Set received timestamp."""
        if self.received_at is None:
            self.received_at = datetime.now(UTC).isoformat()

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if access token is expired.

        Args:
            buffer_seconds: Buffer time before actual expiration (default: 60 seconds)

        Returns:
            True if token is expired, False otherwise
        """
        if self.expires_in is None:
            return False  # No expiration info, assume not expired

        received_at = datetime.fromisoformat(self.received_at)
        expires_at = received_at + timedelta(seconds=self.expires_in)
        now = datetime.now(UTC) + timedelta(seconds=buffer_seconds)

        return now >= expires_at


class OAuth2Service:
    """OAuth2 authentication service.

    Features:
    - PKCE (Proof Key for Code Exchange)
    - CSRF protection via state parameter
    - Token storage in secure storage
    - Token refresh
    - Multiple provider support
    """

    def __init__(self, state_manager: StateManager | None = None):
        """Initialize OAuth2 service.

        Args:
            state_manager: Optional custom state manager (default: create new)
        """
        self.state_manager = state_manager or StateManager()
        self._code_verifier: str | None = None
        self._code_challenge: str | None = None
        self._state: str | None = None

    async def start_oauth_flow(
        self,
        provider_name: str,
        user_id: str,
        redirect_uri: str | None = None,
    ) -> tuple[str, str]:
        """Start OAuth2 authorization flow.

        Args:
            provider_name: Name of OAuth2 provider (e.g., "github", "google")
            user_id: User identifier
            redirect_uri: Optional custom redirect URI (default: localhost callback)

        Returns:
            Tuple of (authorization_url, state)
        """
        # Get provider configuration
        provider_config = get_provider_config(provider_name)
        if not provider_config:
            raise ValueError(f"Unknown OAuth2 provider: {provider_name}")

        # Generate PKCE pair
        self._code_verifier = generate_code_verifier()
        self._code_challenge = generate_code_challenge(
            self._code_verifier, provider_config.pkce_method
        )

        # Generate state for CSRF protection
        self._state = self.state_manager.generate_state(user_id)

        # Build authorization URL
        auth_params = {
            "client_id": provider_config.client_id,
            "response_type": "code",
            "scope": " ".join(provider_config.scopes),
            "redirect_uri": redirect_uri or f"http://localhost:8080/oauth/callback",
            "code_challenge": self._code_challenge,
            "code_challenge_method": provider_config.pkce_method,
            "state": self._state,
        }

        # Build URL
        from urllib.parse import urlencode, urlparse, urlunparse

        parsed_url = urlparse(provider_config.authorization_url)
        query = urlencode(auth_params)
        auth_url = urlunparse(parsed_url._replace(query=query))

        _logger.info(
            "oauth_flow_started",
            provider=provider_name,
            user_id=user_id,
        )

        return auth_url, self._state

    async def complete_oauth_flow(
        self,
        provider_name: str,
        user_id: str,
        timeout: int = 300,
    ) -> OAuth2Tokens | None:
        """Complete OAuth2 flow by waiting for callback.

        Args:
            provider_name: Name of OAuth2 provider
            user_id: User identifier
            timeout: Timeout in seconds (default: 5 minutes)

        Returns:
            OAuth2Tokens or None if failed
        """
        if self._state is None:
            raise RuntimeError("OAuth2 flow not started. Call start_oauth_flow first.")

        # Start callback server
        callback_server = OAuthCallbackServer(expected_state=self._state, timeout=timeout)
        port = await callback_server.start()

        # Wait for callback
        authorization_code, params = await callback_server.wait_for_callback()

        # Stop callback server
        await callback_server.stop()

        if authorization_code is None:
            _logger.error("oauth_callback_failed", user_id=user_id)
            return None

        # Validate state
        if not self.state_manager.validate_state(self._state, user_id):
            _logger.error("oauth_state_validation_failed", user_id=user_id)
            return None

        # Exchange authorization code for tokens
        tokens = await self._exchange_code_for_tokens(
            provider_name,
            authorization_code,
        )

        if tokens:
            # Store tokens securely
            await self._store_tokens(provider_name, user_id, tokens)

        return tokens

    async def _exchange_code_for_tokens(
        self,
        provider_name: str,
        authorization_code: str,
    ) -> OAuth2Tokens | None:
        """Exchange authorization code for access tokens.

        Args:
            provider_name: Name of OAuth2 provider
            authorization_code: Authorization code from callback

        Returns:
            OAuth2Tokens or None if failed
        """
        provider_config = get_provider_config(provider_name)
        if not provider_config:
            raise ValueError(f"Unknown OAuth2 provider: {provider_name}")

        # Get client secret from environment or secure storage
        client_secret = os.getenv(f"{provider_name.upper()}_CLIENT_SECRET")
        if not client_secret:
            _logger.warning(
                "client_secret_not_set",
                provider=provider_name,
            )

        # Prepare token request
        token_data = {
            "client_id": provider_config.client_id,
            "code": authorization_code,
            "redirect_uri": "http://localhost:8080/oauth/callback",
        }

        if client_secret:
            token_data["client_secret"] = client_secret

        if self._code_verifier:
            token_data["code_verifier"] = self._code_verifier

        token_data["grant_type"] = "authorization_code"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    provider_config.token_url,
                    data=token_data,
                    headers={"Accept": "application/json"},
                )

                response.raise_for_status()
                token_data = response.json()

                tokens = OAuth2Tokens(
                    access_token=token_data.get("access_token", ""),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in"),
                    refresh_token=token_data.get("refresh_token"),
                    scope=token_data.get("scope"),
                )

                _logger.info(
                    "token_exchange_success",
                    provider=provider_name,
                )

                return tokens

        except httpx.HTTPStatusError as e:
            _logger.error(
                "token_exchange_http_error",
                provider=provider_name,
                status_code=e.response.status_code,
                error=str(e),
            )
            return None
        except Exception as e:
            _logger.error(
                "token_exchange_failed",
                provider=provider_name,
                error=str(e),
            )
            return None

    async def _store_tokens(
        self,
        provider_name: str,
        user_id: str,
        tokens: OAuth2Tokens,
    ) -> bool:
        """Store OAuth2 tokens securely.

        Args:
            provider_name: Name of OAuth2 provider
            user_id: User identifier
            tokens: OAuth2 tokens to store

        Returns:
            True if storage succeeded, False otherwise
        """
        storage = get_secure_storage()

        # Prepare token data (exclude sensitive params from logs)
        token_data = {
            "access_token": tokens.access_token,
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
            "refresh_token": tokens.refresh_token,
            "scope": tokens.scope,
            "received_at": tokens.received_at,
        }

        data = SecureStorageData()
        data.add_secret(
            user_id=user_id,
            service=f"oauth2_{provider_name}",
            secret_data=token_data,
            metadata={"type": "oauth_tokens", "provider": provider_name},
        )

        success = storage.write(data)

        if success:
            _logger.info(
                "tokens_stored_successfully",
                provider=provider_name,
                user_id=user_id,
            )
        else:
            _logger.error(
                "token_storage_failed",
                provider=provider_name,
                user_id=user_id,
            )

        return success

    async def get_stored_tokens(
        self,
        provider_name: str,
        user_id: str,
    ) -> OAuth2Tokens | None:
        """Get stored OAuth2 tokens.

        Args:
            provider_name: Name of OAuth2 provider
            user_id: User identifier

        Returns:
            OAuth2Tokens or None if not found
        """
        storage = get_secure_storage()

        token_data = storage.get_secret(f"oauth2_{provider_name}", user_id)
        if not token_data:
            return None

        return OAuth2Tokens(
            access_token=token_data.get("access_token", ""),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in"),
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope"),
            received_at=token_data.get("received_at"),
        )

    async def refresh_tokens(
        self,
        provider_name: str,
        user_id: str,
    ) -> OAuth2Tokens | None:
        """Refresh OAuth2 tokens.

        Args:
            provider_name: Name of OAuth2 provider
            user_id: User identifier

        Returns:
            OAuth2Tokens or None if failed
        """
        # Get current tokens
        current_tokens = await self.get_stored_tokens(provider_name, user_id)
        if not current_tokens or not current_tokens.refresh_token:
            _logger.error(
                "no_refresh_token",
                provider=provider_name,
                user_id=user_id,
            )
            return None

        provider_config = get_provider_config(provider_name)
        if not provider_config:
            raise ValueError(f"Unknown OAuth2 provider: {provider_name}")

        # Get client secret
        client_secret = os.getenv(f"{provider_name.upper()}_CLIENT_SECRET")

        # Prepare refresh request
        refresh_data = {
            "client_id": provider_config.client_id,
            "refresh_token": current_tokens.refresh_token,
            "grant_type": "refresh_token",
        }

        if client_secret:
            refresh_data["client_secret"] = client_secret

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    provider_config.token_url,
                    data=refresh_data,
                    headers={"Accept": "application/json"},
                )

                response.raise_for_status()
                token_data = response.json()

                new_tokens = OAuth2Tokens(
                    access_token=token_data.get("access_token", ""),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in"),
                    refresh_token=token_data.get("refresh_token", current_tokens.refresh_token),
                    scope=token_data.get("scope"),
                )

                # Store new tokens
                await self._store_tokens(provider_name, user_id, new_tokens)

                _logger.info(
                    "token_refresh_success",
                    provider=provider_name,
                    user_id=user_id,
                )

                return new_tokens

        except httpx.HTTPStatusError as e:
            _logger.error(
                "token_refresh_http_error",
                provider=provider_name,
                status_code=e.response.status_code,
                error=str(e),
            )
            return None
        except Exception as e:
            _logger.error(
                "token_refresh_failed",
                provider=provider_name,
                user_id=user_id,
                error=str(e),
            )
            return None

    async def get_valid_tokens(
        self,
        provider_name: str,
        user_id: str,
        buffer_seconds: int = 60,
    ) -> OAuth2Tokens | None:
        """Get valid OAuth2 tokens, refreshing automatically if expired.

        Args:
            provider_name: Name of OAuth2 provider
            user_id: User identifier
            buffer_seconds: Buffer time before actual expiration (default: 60 seconds)

        Returns:
            OAuth2Tokens or None if failed
        """
        tokens = await self.get_stored_tokens(provider_name, user_id)
        if not tokens:
            return None

        # Check if token is expired
        if tokens.is_expired(buffer_seconds=buffer_seconds):
            _logger.info(
                "token_expired_refreshing",
                provider=provider_name,
                user_id=user_id,
            )
            # Try to refresh
            new_tokens = await self.refresh_tokens(provider_name, user_id)
            if new_tokens:
                return new_tokens
            else:
                _logger.error(
                    "token_refresh_failed",
                    provider=provider_name,
                    user_id=user_id,
                )
                return None

        return tokens

    async def revoke_tokens(
        self,
        provider_name: str,
        user_id: str,
    ) -> bool:
        """Revoke OAuth2 tokens.

        Args:
            provider_name: Name of OAuth2 provider
            user_id: User identifier

        Returns:
            True if revocation succeeded, False otherwise
        """
        storage = get_secure_storage()

        success = storage.delete(f"oauth2_{provider_name}", user_id)

        if success:
            _logger.info(
                "tokens_revoked",
                provider=provider_name,
                user_id=user_id,
            )
        else:
            _logger.error(
                "token_revocation_failed",
                provider=provider_name,
                user_id=user_id,
            )

        return success

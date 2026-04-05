"""OAuth2 configuration.

Configuration for OAuth2 providers and settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OAuth2ProviderConfig:
    """Configuration for an OAuth2 provider."""

    name: str
    authorization_url: str
    token_url: str
    client_id: str
    scopes: list[str]
    redirect_uri: str | None = None
    pkce_method: str = "S256"  # S256 or plain


# OAuth2 provider configurations
PROVIDER_CONFIGS = {
    "github": OAuth2ProviderConfig(
        name="GitHub",
        authorization_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        client_id="",  # Set via environment variable: GITHUB_CLIENT_ID
        scopes=["read:user", "repo"],
        pkce_method="S256",
    ),
    "google": OAuth2ProviderConfig(
        name="Google",
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        client_id="",  # Set via environment variable: GOOGLE_CLIENT_ID
        scopes=["openid", "profile", "email"],
        pkce_method="S256",
    ),
    # MindFlow OAuth2 (future integration)
    "mindflow": OAuth2ProviderConfig(
        name="MindFlow",
        authorization_url="",  # To be configured
        token_url="",  # To be configured
        client_id="",  # Set via environment variable: MINDFLOW_CLIENT_ID
        scopes=["openid", "profile", "email"],
        pkce_method="S256",
    ),
}

# Allowed OAuth2 base URLs for security
ALLOWED_OAUTH_BASE_URLS = [
    "github.com",
    "api.github.com",
    "accounts.google.com",
    "oauth2.googleapis.com",
]

# Sensitive OAuth parameters to redact from logs
SENSITIVE_OAUTH_PARAMS = [
    "state",
    "nonce",
    "code_challenge",
    "code_verifier",
    "code",
    "access_token",
    "refresh_token",
    "client_secret",
]


def get_provider_config(provider_name: str) -> OAuth2ProviderConfig | None:
    """Get OAuth2 provider configuration.

    Args:
        provider_name: Name of the provider (e.g., "github", "google")

    Returns:
        OAuth2ProviderConfig or None if provider not found
    """
    return PROVIDER_CONFIGS.get(provider_name)


def is_base_url_allowed(url: str) -> bool:
    """Check if a URL base is in the allowed list.

    Args:
        url: URL to check

    Returns:
        True if URL base is allowed, False otherwise
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    base_url = parsed.netloc

    # Remove port if present
    base_url = base_url.split(":")[0]

    return base_url in ALLOWED_OAUTH_BASE_URLS

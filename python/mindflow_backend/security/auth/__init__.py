"""Authentication module.

Provides OAuth2 authentication with PKCE and CSRF protection,
plus JWT secret key management.
"""

from .jwt_secret import generate_jwt_secret, get_jwt_secret_key
from .oauth2 import (
    OAuth2Service,
    StateManager,
    generate_code_challenge,
    generate_code_verifier,
)

__all__ = [
    "OAuth2Service",
    "StateManager",
    "generate_code_challenge",
    "generate_code_verifier",
    "generate_jwt_secret",
    "get_jwt_secret_key",
]

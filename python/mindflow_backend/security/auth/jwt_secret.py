"""JWT secret key management.

Provides secure JWT secret key loading from environment variables
with fallback to secure random generation.
"""

import os
import secrets

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def get_jwt_secret_key() -> str:
    """Get JWT secret key from environment or generate secure one.

    Priority:
    1. JWT_SECRET_KEY environment variable
    2. Generate secure random key (logged as warning)

    Returns:
        JWT secret key string

    Warning:
        If JWT_SECRET_KEY is not set, a temporary key is generated.
        This key will change on restart, invalidating all tokens.
        Set JWT_SECRET_KEY environment variable for production.
    """
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        # Generate secure random key
        secret_key = secrets.token_urlsafe(32)
        _logger.warning(
            "JWT_SECRET_KEY not set in environment. "
            "Generated temporary key. "
            "Set JWT_SECRET_KEY environment variable for production. "
            "All tokens will be invalidated on restart."
        )

    return secret_key


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret key.

    Returns:
        Secure random JWT secret key (32 bytes, URL-safe base64)

    Example:
        >>> secret = generate_jwt_secret()
        >>> print(f"JWT_SECRET_KEY={secret}")
    """
    return secrets.token_urlsafe(32)

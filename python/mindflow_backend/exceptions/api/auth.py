"""API authentication and authorization exceptions.

Exceptions for authentication failures, authorization issues,
and security-related API errors.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.business import (
    AuthenticationError as BaseAuthenticationError,
    AuthorizationError as BaseAuthorizationError,
)


class AuthenticationError(BaseAuthenticationError):
    """API authentication failure."""
    
    def __init__(
        self,
        message: str = "API authentication failed",
        *,
        auth_scheme: str | None = None,
        token_type: str | None = None,
        endpoint: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            auth_method=auth_scheme,
            user_identifier=None,
            component="api",
            **kwargs
        )
        self.auth_scheme = auth_scheme
        self.token_type = token_type
        self.endpoint = endpoint


class AuthorizationError(BaseAuthorizationError):
    """API authorization failure."""
    
    def __init__(
        self,
        message: str = "API access denied",
        *,
        endpoint: str | None = None,
        method: str | None = None,
        required_scope: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            required_permission=required_scope,
            resource=endpoint,
            component="api",
            **kwargs
        )
        self.endpoint = endpoint
        self.method = method
        self.required_scope = required_scope

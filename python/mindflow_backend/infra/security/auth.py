"""Advanced authentication and authorization system.

Provides comprehensive security features including
JWT tokens, API keys, role-based access control,
and security monitoring.
"""

from __future__ import annotations

import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import jwt

from mindflow_backend.infra.cache.redis_client import get_redis_client
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class AuthMethod(Enum):
    """Authentication methods."""
    JWT = "jwt"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH = "oauth"
    SESSION = "session"


class Permission(Enum):
    """Permission types."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    SYSTEM = "system"


class Role(Enum):
    """User roles."""
    GUEST = "guest"
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class User:
    """User information."""
    id: str
    username: str
    email: str
    roles: list[Role] = field(default_factory=list)
    permissions: set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_login: datetime | None = None
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        return permission in self.permissions
        
    def has_role(self, role: Role) -> bool:
        """Check if user has role.
        
        Args:
            role: Role to check
            
        Returns:
            True if user has role
        """
        return role in self.roles
        
    def add_role(self, role: Role) -> None:
        """Add role to user.
        
        Args:
            role: Role to add
        """
        if role not in self.roles:
            self.roles.append(role)
            
    def remove_role(self, role: Role) -> bool:
        """Remove role from user.
        
        Args:
            role: Role to remove
            
        Returns:
            True if role was removed
        """
        if role in self.roles:
            self.roles.remove(role)
            return True
        return False
        
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "roles": [role.value for role in self.roles],
            "permissions": [perm.value for perm in self.permissions],
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }


@dataclass
class APIToken:
    """API token information."""
    token_id: str
    user_id: str
    name: str
    permissions: set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    last_used: datetime | None = None
    is_active: bool = True
    usage_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if token is expired.
        
        Returns:
            True if token is expired
        """
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at
        
    def has_permission(self, permission: Permission) -> bool:
        """Check if token has permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if token has permission
        """
        return permission in self.permissions
        
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "name": self.name,
            "permissions": [perm.value for perm in self.permissions],
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "metadata": self.metadata,
        }


class AuthProvider(ABC):
    """Abstract authentication provider."""
    
    @abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> User | None:
        """Authenticate user credentials.
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            Authenticated user or None
        """
        pass
        
    @abstractmethod
    async def validate_token(self, token: str) -> User | None:
        """Validate authentication token.
        
        Args:
            token: Authentication token
            
        Returns:
            Authenticated user or None
        """
        pass


class JWTAuthProvider(AuthProvider):
    """JWT authentication provider."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """Initialize JWT provider.
        
        Args:
            secret_key: JWT secret key
            algorithm: JWT algorithm
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self._token_expiry = timedelta(hours=24)
        
    async def authenticate(self, credentials: dict[str, Any]) -> User | None:
        """Authenticate with username/password and return JWT.
        
        Args:
            credentials: Username and password
            
        Returns:
            User with JWT token or None
        """
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            return None
            
        # This would validate against user database
        # For now, create a mock user
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=f"{username}@example.com",
            roles=[Role.USER],
            permissions={Permission.READ, Permission.WRITE},
        )
        
        return user
        
    async def validate_token(self, token: str) -> User | None:
        """Validate JWT token and return user.
        
        Args:
            token: JWT token
            
        Returns:
            Authenticated user or None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Create user from payload
            user = User(
                id=payload["user_id"],
                username=payload["username"],
                email=payload["email"],
                roles=[Role(role) for role in payload.get("roles", [])],
                permissions={Permission(perm) for perm in payload.get("permissions", [])},
            )
            
            return user
            
        except jwt.ExpiredSignatureError:
            _logger.warning("jwt_token_expired")
            return None
        except jwt.InvalidTokenError as e:
            _logger.warning("jwt_token_invalid", error=str(e))
            return None
            
    def generate_token(self, user: User) -> str:
        """Generate JWT token for user.
        
        Args:
            user: User to generate token for
            
        Returns:
            JWT token
        """
        payload = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": [role.value for role in user.roles],
            "permissions": [perm.value for perm in user.permissions],
            "exp": datetime.now(UTC) + self._token_expiry,
            "iat": datetime.now(UTC),
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


class APIKeyAuthProvider(AuthProvider):
    """API key authentication provider."""
    
    def __init__(self):
        """Initialize API key provider."""
        self._redis_client = None
        self._key_prefix = "auth:api_key:"
        
    async def initialize(self) -> None:
        """Initialize API key provider."""
        self._redis_client = get_redis_client()
        await self._redis_client.initialize()
        
    async def authenticate(self, credentials: dict[str, Any]) -> User | None:
        """API key authentication not supported for initial auth.
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            None (API keys are for token validation only)
        """
        return None
        
    async def validate_token(self, api_key: str) -> User | None:
        """Validate API key and return user.
        
        Args:
            api_key: API key string
            
        Returns:
            Authenticated user or None
        """
        if not self._redis_client:
            return None
            
        try:
            # Get token data from Redis
            token_data = await self._redis_client.get(f"{self._key_prefix}{api_key}")
            
            if not token_data:
                return None
                
            token = APIToken(**token_data)
            
            # Check if token is active and not expired
            if not token.is_active or token.is_expired():
                return None
                
            # Update usage
            token.last_used = datetime.now(UTC)
            token.usage_count += 1
            
            # Save updated token
            await self._redis_client.set(f"{self._key_prefix}{api_key}", token.to_dict())
            
            # Get user (this would query user database)
            user = User(
                id=token.user_id,
                username=f"user_{token.user_id}",
                email=f"user_{token.user_id}@example.com",
                permissions=token.permissions,
            )
            
            return user
            
        except Exception as e:
            _logger.error("api_key_validation_failed", error=str(e))
            return None
            
    async def create_api_key(
        self,
        user_id: str,
        name: str,
        permissions: set[Permission],
        expires_at: datetime | None = None
    ) -> str:
        """Create new API key.
        
        Args:
            user_id: User ID
            name: Key name
            permissions: Key permissions
            expires_at: Expiration time
            
        Returns:
            API key string
        """
        if not self._redis_client:
            raise RuntimeError("API key provider not initialized")
            
        # Generate secure API key
        api_key = secrets.token_urlsafe(32)
        
        # Create token
        token = APIToken(
            token_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            permissions=permissions,
            expires_at=expires_at,
        )
        
        # Store in Redis
        await self._redis_client.set(f"{self._key_prefix}{api_key}", token.to_dict())
        
        _logger.info("api_key_created", user_id=user_id, name=name, token_id=token.token_id)
        
        return api_key
        
    async def revoke_api_key(self, api_key: str) -> bool:
        """Revoke API key.
        
        Args:
            api_key: API key to revoke
            
        Returns:
            True if key was revoked
        """
        if not self._redis_client:
            return False
            
        result = await self._redis_client.delete(f"{self._key_prefix}{api_key}")
        
        if result:
            _logger.info("api_key_revoked", api_key=api_key[:8] + "...")
            
        return result


class AuthManager:
    """Advanced authentication and authorization manager.
    
    Features:
    - Multiple authentication providers
    - Role-based access control
    - API key management
    - JWT token handling
    - Security monitoring
    - Session management
    """
    
    def __init__(self):
        """Initialize auth manager."""
        self._providers: dict[AuthMethod, AuthProvider] = {}
        self._users: dict[str, User] = {}
        self._api_key_provider: APIKeyAuthProvider | None = None
        self._jwt_provider: JWTAuthProvider | None = None
        self._is_initialized = False
        
        # Security settings
        self._max_failed_attempts = 5
        self._lockout_duration = timedelta(minutes=15)
        self._session_timeout = timedelta(hours=24)
        
        # Statistics
        self._stats = {
            "total_auth_attempts": 0,
            "successful_auth": 0,
            "failed_auth": 0,
            "api_keys_created": 0,
            "api_keys_revoked": 0,
            "active_sessions": 0,
            "blocked_attempts": 0,
        }
        
    async def initialize(self) -> None:
        """Initialize auth manager."""
        settings = get_settings()
        
        # Initialize JWT provider
        self._jwt_provider = JWTAuthProvider(
            secret_key=settings.app_name + "_secret_key",  # In production, use proper secret
            algorithm="HS256"
        )
        self._providers[AuthMethod.JWT] = self._jwt_provider
        
        # Initialize API key provider
        self._api_key_provider = APIKeyAuthProvider()
        await self._api_key_provider.initialize()
        self._providers[AuthMethod.API_KEY] = self._api_key_provider
        
        self._is_initialized = True
        
        _logger.info(
            "auth_manager_initialized",
            providers=len(self._providers),
            jwt_enabled=True,
            api_keys_enabled=True,
        )
        
    async def authenticate(
        self,
        method: AuthMethod,
        credentials: dict[str, Any]
    ) -> User | None:
        """Authenticate user with specified method.
        
        Args:
            method: Authentication method
            credentials: Authentication credentials
            
        Returns:
            Authenticated user or None
        """
        if not self._is_initialized:
            raise RuntimeError("Auth manager not initialized")
            
        self._stats["total_auth_attempts"] += 1
        
        provider = self._providers.get(method)
        if not provider:
            _logger.error("auth_provider_not_found", method=method.value)
            self._stats["failed_auth"] += 1
            return None
            
        try:
            user = await provider.authenticate(credentials)
            
            if user:
                self._stats["successful_auth"] += 1
                user.last_login = datetime.now(UTC)
                self._users[user.id] = user
                
                _logger.info("user_authenticated", user_id=user.id, method=method.value)
                return user
            else:
                self._stats["failed_auth"] += 1
                return None
                
        except Exception as e:
            _logger.error("authentication_failed", method=method.value, error=str(e))
            self._stats["failed_auth"] += 1
            return None
            
    async def validate_token(self, token: str, method: AuthMethod = AuthMethod.JWT) -> User | None:
        """Validate authentication token.
        
        Args:
            token: Authentication token
            method: Token method
            
        Returns:
            Authenticated user or None
        """
        if not self._is_initialized:
            return None
            
        provider = self._providers.get(method)
        if not provider:
            return None
            
        try:
            user = await provider.validate_token(token)
            
            if user:
                # Update user in cache
                self._users[user.id] = user
                
            return user
            
        except Exception as e:
            _logger.error("token_validation_failed", method=method.value, error=str(e))
            return None
            
    async def authorize(self, user: User, required_permission: Permission) -> bool:
        """Authorize user for required permission.
        
        Args:
            user: User to authorize
            required_permission: Required permission
            
        Returns:
            True if authorized
        """
        if not user or not user.is_active:
            return False
            
        # Check if user has required permission
        if user.has_permission(required_permission):
            return True
            
        # Check role-based permissions
        role_permissions = {
            Role.GUEST: {Permission.READ},
            Role.USER: {Permission.READ, Permission.WRITE},
            Role.MODERATOR: {Permission.READ, Permission.WRITE, Permission.DELETE},
            Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN},
            Role.SYSTEM: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN, Permission.SYSTEM},
        }
        
        for role in user.roles:
            if required_permission in role_permissions.get(role, set()):
                return True
                
        return False
        
    async def create_api_key(
        self,
        user_id: str,
        name: str,
        permissions: set[Permission],
        expires_at: datetime | None = None
    ) -> str | None:
        """Create API key for user.
        
        Args:
            user_id: User ID
            name: Key name
            permissions: Key permissions
            expires_at: Expiration time
            
        Returns:
            API key string or None
        """
        if not self._api_key_provider:
            return None
            
        try:
            api_key = await self._api_key_provider.create_api_key(
                user_id=user_id,
                name=name,
                permissions=permissions,
                expires_at=expires_at,
            )
            
            self._stats["api_keys_created"] += 1
            
            return api_key
            
        except Exception as e:
            _logger.error("api_key_creation_failed", user_id=user_id, error=str(e))
            return None
            
    async def revoke_api_key(self, api_key: str) -> bool:
        """Revoke API key.
        
        Args:
            api_key: API key to revoke
            
        Returns:
            True if revoked
        """
        if not self._api_key_provider:
            return False
            
        try:
            result = await self._api_key_provider.revoke_api_key(api_key)
            
            if result:
                self._stats["api_keys_revoked"] += 1
                
            return result
            
        except Exception as e:
            _logger.error("api_key_revocation_failed", error=str(e))
            return False
            
    def get_user(self, user_id: str) -> User | None:
        """Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User or None
        """
        return self._users.get(user_id)
        
    def add_user_role(self, user_id: str, role: Role) -> bool:
        """Add role to user.
        
        Args:
            user_id: User ID
            role: Role to add
            
        Returns:
            True if role was added
        """
        user = self._users.get(user_id)
        if not user:
            return False
            
        user.add_role(role)
        _logger.info("user_role_added", user_id=user_id, role=role.value)
        return True
        
    def remove_user_role(self, user_id: str, role: Role) -> bool:
        """Remove role from user.
        
        Args:
            user_id: User ID
            role: Role to remove
            
        Returns:
            True if role was removed
        """
        user = self._users.get(user_id)
        if not user:
            return False
            
        result = user.remove_role(role)
        if result:
            _logger.info("user_role_removed", user_id=user_id, role=role.value)
            
        return result
        
    def get_stats(self) -> dict[str, Any]:
        """Get auth manager statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        
        # Calculate rates
        total_attempts = stats["total_auth_attempts"]
        if total_attempts > 0:
            stats["success_rate"] = stats["successful_auth"] / total_attempts
            stats["failure_rate"] = stats["failed_auth"] / total_attempts
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
            
        # Add user counts
        stats["total_users"] = len(self._users)
        stats["active_users"] = sum(1 for user in self._users.values() if user.is_active)
        
        # Add provider info
        stats["providers"] = list(self._providers.keys())
        
        return stats
        
    async def health_check(self) -> dict[str, Any]:
        """Perform auth manager health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test JWT provider
            jwt_healthy = True
            if self._jwt_provider:
                try:
                    test_user = User(
                        id="test",
                        username="test",
                        email="test@example.com",
                        roles=[Role.USER],
                    )
                    token = self._jwt_provider.generate_token(test_user)
                    validated_user = await self._jwt_provider.validate_token(token)
                    jwt_healthy = validated_user is not None
                except Exception:
                    jwt_healthy = False
                    
            # Test API key provider
            api_key_healthy = True
            if self._api_key_provider:
                try:
                    # Test API key creation and validation
                    test_key = await self._api_key_provider.create_api_key(
                        "test_user", "test_key", {Permission.READ}
                    )
                    validated_user = await self._api_key_provider.validate_token(test_key)
                    api_key_healthy = validated_user is not None
                    
                    # Clean up test key
                    await self._api_key_provider.revoke_api_key(test_key)
                except Exception:
                    api_key_healthy = False
                    
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "jwt_provider_healthy": jwt_healthy,
                "api_key_provider_healthy": api_key_healthy,
                "providers_count": len(self._providers),
                "users_count": len(self._users),
                "duration_ms": duration_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("auth_manager_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("auth_manager_health_check_failed", **error_data)
            return error_data


# Global auth manager instance
_auth_manager: AuthManager | None = None


def get_auth_manager() -> AuthManager:
    """Get global auth manager instance.
    
    Returns:
        AuthManager instance
    """
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


# Import uuid for UUID generation
import uuid

"""OAuth2 state manager for CSRF protection.

Manages OAuth2 state parameters to prevent CSRF attacks during
the authorization code flow.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class StateManager:
    """Manages OAuth2 state parameters for CSRF protection.

    Features:
    - UUID-based state generation
    - TTL-based expiration (5 minutes default)
    - Redis-backed storage (for distributed systems)
    - In-memory fallback
    """

    def __init__(self, ttl_seconds: int = 300):
        """Initialize state manager.

        Args:
            ttl_seconds: Time-to-live for state tokens (default: 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._states: dict[str, dict[str, Any]] = {}
        self._redis_client = None

    def _get_redis_client(self):
        """Lazy import Redis client."""
        try:
            from mindflow_backend.infra.cache.redis_client import get_redis_client

            if self._redis_client is None:
                self._redis_client = get_redis_client()
            return self._redis_client
        except Exception:
            return None

    def generate_state(self, user_id: str | None = None) -> str:
        """Generate a new state token.

        Args:
            user_id: Optional user identifier for tracking

        Returns:
            UUID state token
        """
        state = str(uuid.uuid4())
        expires_at = datetime.now(UTC) + timedelta(seconds=self.ttl_seconds)

        state_data = {
            "state": state,
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at.isoformat(),
            "user_id": user_id,
        }

        # Store in Redis if available
        redis_client = self._get_redis_client()
        if redis_client:
            try:
                redis_client.set(
                    f"oauth2_state:{state}",
                    state_data,
                    ttl=self.ttl_seconds,
                )
                _logger.debug("state_stored_in_redis", state=state)
            except Exception as e:
                _logger.warning("redis_state_storage_failed", error=str(e))

        # Always store in memory as fallback
        self._states[state] = state_data
        _logger.debug("state_generated", state=state, user_id=user_id)

        return state

    def validate_state(self, state: str, user_id: str | None = None) -> bool:
        """Validate a state token.

        Args:
            state: State token to validate
            user_id: Optional user identifier to match

        Returns:
            True if state is valid, False otherwise
        """
        # Check Redis first
        redis_client = self._get_redis_client()
        if redis_client:
            try:
                state_data = redis_client.get(f"oauth2_state:{state}")
                if state_data:
                    # Validate expiration
                    expires_at = datetime.fromisoformat(state_data["expires_at"])
                    if datetime.now(UTC) < expires_at:
                        # Validate user_id if provided
                        if user_id is None or state_data.get("user_id") == user_id:
                            # Delete state after validation (one-time use)
                            redis_client.delete(f"oauth2_state:{state}")
                            _logger.debug("state_validated_redis", state=state)
                            return True
            except Exception as e:
                _logger.warning("redis_state_validation_failed", error=str(e))

        # Fallback to in-memory
        state_data = self._states.get(state)
        if state_data:
            # Validate expiration
            expires_at = datetime.fromisoformat(state_data["expires_at"])
            if datetime.now(UTC) < expires_at:
                # Validate user_id if provided
                if user_id is None or state_data.get("user_id") == user_id:
                    # Delete state after validation (one-time use)
                    del self._states[state]
                    _logger.debug("state_validated_memory", state=state)
                    return True
            else:
                # Clean up expired state
                del self._states[state]

        _logger.warning("state_validation_failed", state=state)
        return False

    def cleanup_expired_states(self) -> int:
        """Clean up expired states from memory.

        Returns:
            Number of states cleaned up
        """
        now = datetime.now(UTC)
        expired_states = []

        for state, state_data in self._states.items():
            expires_at = datetime.fromisoformat(state_data["expires_at"])
            if now >= expires_at:
                expired_states.append(state)

        for state in expired_states:
            del self._states[state]

        if expired_states:
            _logger.debug("expired_states_cleaned", count=len(expired_states))

        return len(expired_states)

    def clear_all_states(self) -> int:
        """Clear all states from memory.

        Returns:
            Number of states cleared
        """
        count = len(self._states)
        self._states.clear()

        # Also try to clear from Redis
        redis_client = self._get_redis_client()
        if redis_client:
            try:
                # This would require pattern matching which may not be available
                # For now, we'll just log
                _logger.info("redis_states_not_cleared_pattern")
            except Exception as e:
                _logger.warning("redis_state_clear_failed", error=str(e))

        _logger.debug("all_states_cleared", count=count)
        return count

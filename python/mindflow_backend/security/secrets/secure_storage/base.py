"""Abstract base class for secure storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class SecureStorageData:
    """Structured data for secure storage.

    Schema:
    - secrets: Dictionary of secrets with key as f"{user_id}:{service}"
    - Each entry contains secret_data and metadata

    Example:
    {
        "user1:github": {"secret_data": {"token": "xyz"}, "metadata": {...}},
        "user1:openai": {"secret_data": {"api_key": "abc"}, "metadata": {...}},
    }
    """

    secrets: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize empty secrets dict if not provided."""
        if not isinstance(self.secrets, dict):
            self.secrets = {}

    def add_secret(
        self,
        user_id: str,
        service: str,
        secret_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a secret entry.

        Args:
            user_id: User identifier
            service: Service name
            secret_data: Secret data
            metadata: Optional metadata
        """
        key = f"{user_id}:{service}"
        if metadata is None:
            metadata = {}

        if "created_at" not in metadata:
            metadata["created_at"] = datetime.now(UTC).isoformat()
        if "type" not in metadata:
            metadata["type"] = "secret"

        self.secrets[key] = {
            "user_id": user_id,
            "service": service,
            "secret_data": secret_data,
            "metadata": metadata,
        }

    def get_secret(self, user_id: str, service: str) -> dict[str, Any] | None:
        """Get secret for specific service and user.

        Args:
            user_id: User identifier
            service: Service name

        Returns:
            Secret data or None if not found
        """
        key = f"{user_id}:{service}"
        entry = self.secrets.get(key)
        if entry:
            return entry["secret_data"]
        return None

    def remove_secret(self, user_id: str, service: str) -> bool:
        """Remove a secret entry.

        Args:
            user_id: User identifier
            service: Service name

        Returns:
            True if removed, False if not found
        """
        key = f"{user_id}:{service}"
        if key in self.secrets:
            del self.secrets[key]
            return True
        return False


class SecureStorage(ABC):
    """Abstract base class for secure storage backends.

    All storage backends must implement these methods:
    - read(): Read all stored data
    - write(data): Write data to storage
    - delete(service, user_id): Delete specific secret
    - clear(): Clear all stored data
    """

    @abstractmethod
    def read(self) -> SecureStorageData | None:
        """Read all stored data.

        Returns:
            SecureStorageData or None if no data exists
        """
        pass

    @abstractmethod
    def write(self, data: SecureStorageData) -> bool:
        """Write data to storage.

        Args:
            data: SecureStorageData to write

        Returns:
            True if write succeeded, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, service: str, user_id: str) -> bool:
        """Delete specific secret.

        Args:
            service: Service name
            user_id: User identifier

        Returns:
            True if deletion succeeded, False otherwise
        """
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear all stored data.

        Returns:
            True if clear succeeded, False otherwise
        """
        pass

    def get_secret(self, service: str, user_id: str) -> dict[str, Any] | None:
        """Get secret for specific service and user.

        Args:
            service: Service name
            user_id: User identifier

        Returns:
            Secret data or None if not found
        """
        data = self.read()
        if not data:
            return None

        return data.get_secret(user_id, service)

    def set_secret(
        self, service: str, user_id: str, secret_data: dict[str, Any]
    ) -> bool:
        """Set secret for specific service and user.

        Args:
            service: Service name
            user_id: User identifier
            secret_data: Secret data to store

        Returns:
            True if write succeeded, False otherwise
        """
        # Read existing data
        existing = self.read()
        if not existing:
            existing = SecureStorageData()

        # Add or update the secret
        existing.add_secret(user_id, service, secret_data)

        return self.write(existing)

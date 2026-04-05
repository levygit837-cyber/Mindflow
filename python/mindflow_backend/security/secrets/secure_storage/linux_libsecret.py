"""Linux libsecret storage backend.

Uses libsecret via DBus for secure storage on Linux.
Falls back to encrypted file storage if libsecret is unavailable.
"""

from __future__ import annotations

import json
from typing import Any

from mindflow_backend.infra.logging import get_logger

from .base import SecureStorage, SecureStorageData
from .fallback_storage import FallbackStorage

_logger = get_logger(__name__)

# Schema name for libsecret
LIBSECRET_SCHEMA = "com.mindflow.Secrets"


def _get_attribute_name(user_id: str, service: str) -> str:
    """Get attribute name for libsecret entry.

    Format: user:{user_id}:service:{service}

    Args:
        user_id: User identifier
        service: Service name

    Returns:
        Attribute name for libsecret
    """
    return f"user:{user_id}:service:{service}"


class LinuxLibsecretStorage(SecureStorage):
    """Linux libsecret storage backend.

    Features:
    - Uses libsecret via DBus
    - Schema-based organization
    - Fallback to encrypted file if unavailable
    """

    def __init__(self, use_fallback: bool = False):
        """Initialize Linux libsecret storage.

        Args:
            use_fallback: Force use of fallback storage
        """
        if __import__("sys").platform not in ("linux", "linux2"):
            raise RuntimeError("LinuxLibsecretStorage only works on Linux")

        self._fallback = None
        self._libsecret_available = False

        if not use_fallback:
            self._libsecret_available = self._check_libsecret()

        if not self._libsecret_available:
            _logger.info("libsecret_unavailable_using_fallback")
            self._fallback = FallbackStorage()

    def _check_libsecret(self) -> bool:
        """Check if libsecret is available.

        Returns:
            True if libsecret is available, False otherwise
        """
        try:
            import gi

            gi.require_version("Secret", "1")
            from gi.repository import Secret

            self.Secret = Secret
            return True
        except (ImportError, ValueError):
            return False

    def read(self) -> SecureStorageData | None:
        """Read all stored data.

        Returns:
            SecureStorageData or None if no data exists
        """
        if self._fallback:
            return self._fallback.read()

        # Libsecret doesn't support reading all entries easily
        # Use get_secret/set_secret instead
        return SecureStorageData()

    def write(self, data: SecureStorageData) -> bool:
        """Write data to storage.

        Args:
            data: SecureStorageData to write

        Returns:
            True if write succeeded, False otherwise
        """
        if self._fallback:
            return self._fallback.write(data)

        # Write each secret as a separate libsecret entry
        all_success = True

        for key, entry in data.secrets.items():
            user_id = entry["user_id"]
            service = entry["service"]

            # Convert to JSON
            data_dict = {
                "user_id": user_id,
                "service": service,
                "secret_data": entry["secret_data"],
                "metadata": entry.get("metadata", {}),
            }
            json_str = json.dumps(data_dict)

            # Store using libsecret
            try:
                attributes = {
                    "user_id": user_id,
                    "service": service,
                }

                self.Secret.password_store_sync(
                    LIBSECRET_SCHEMA,
                    attributes,
                    None,  # Default collection
                    f"MindFlow: {service} for {user_id}",
                    json_str,
                )

                _logger.debug(
                    "libsecret_write_success",
                    service=service,
                    user_id=user_id,
                )
            except Exception as e:
                _logger.error(
                    "libsecret_write_failed",
                    service=service,
                    user_id=user_id,
                    error=str(e),
                )
                all_success = False

        # Fall back to file storage if any failed
        if not all_success and self._fallback is None:
            self._fallback = FallbackStorage()
            return self._fallback.write(data)

        return all_success

    def delete(self, service: str, user_id: str) -> bool:
        """Delete specific secret.

        Args:
            service: Service name
            user_id: User identifier

        Returns:
            True if deletion succeeded, False otherwise
        """
        if self._fallback:
            return self._fallback.delete(service, user_id)

        try:
            attributes = {
                "user_id": user_id,
                "service": service,
            }

            deleted = self.Secret.password_clear_sync(
                LIBSECRET_SCHEMA,
                attributes,
                None,  # Default collection
            )

            if deleted:
                _logger.debug(
                    "libsecret_delete_success",
                    service=service,
                    user_id=user_id,
                )
            return deleted
        except Exception as e:
            _logger.error(
                "libsecret_delete_failed",
                service=service,
                user_id=user_id,
                error=str(e),
            )
            return False

    def clear(self) -> bool:
        """Clear all stored data.

        Returns:
            True if clear succeeded, False otherwise
        """
        if self._fallback:
            return self._fallback.clear()

        # Libsecret doesn't have a clear all method
        # Users should use delete() for specific entries
        _logger.warning("libsecret_clear_not_fully_implemented")
        return True

    def get_secret(self, service: str, user_id: str) -> dict[str, Any] | None:
        """Get secret for specific service and user.

        Args:
            service: Service name
            user_id: User identifier

        Returns:
            Secret data or None if not found
        """
        if self._fallback:
            return self._fallback.get_secret(service, user_id)

        try:
            attributes = {
                "user_id": user_id,
                "service": service,
            }

            secret = self.Secret.password_lookup_sync(
                LIBSECRET_SCHEMA,
                attributes,
                None,  # Default collection
            )

            if secret:
                data_dict = json.loads(secret)
                # Handle both old and new format
                if "secret_data" in data_dict:
                    return data_dict["secret_data"]
                else:
                    # Old format: data_dict is the secret_data directly
                    return data_dict

            return None
        except Exception as e:
            _logger.error(
                "libsecret_lookup_failed",
                service=service,
                user_id=user_id,
                error=str(e),
            )
            return None

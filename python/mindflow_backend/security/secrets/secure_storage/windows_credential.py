"""Windows Credential Manager storage backend.

Uses Windows Credential Manager via pywin32 for secure storage.
"""

from __future__ import annotations

import json
from typing import Any

from mindflow_backend.infra.logging import get_logger

from .base import SecureStorage, SecureStorageData
from .fallback_storage import FallbackStorage

_logger = get_logger(__name__)

# Credential Manager target name format
CREDENTIAL_PREFIX = "MindFlow:"


def _get_target_name(user_id: str, service: str) -> str:
    """Get target name for credential.

    Format: MindFlow:{service}:{user_id}

    Args:
        user_id: User identifier
        service: Service name

    Returns:
        Target name for credential
    """
    return f"{CREDENTIAL_PREFIX}{service}:{user_id}"


class WindowsCredentialStorage(SecureStorage):
    """Windows Credential Manager storage backend.

    Features:
    - Uses Windows Credential Manager via pywin32
    - Target name format: MindFlow:{service}:{user_id}
    - Fallback to encrypted file if unavailable
    """

    def __init__(self, use_fallback: bool = False):
        """Initialize Windows credential storage.

        Args:
            use_fallback: Force use of fallback storage
        """
        if __import__("sys").platform != "win32":
            raise RuntimeError("WindowsCredentialStorage only works on Windows")

        self._fallback = None
        self._win32_available = False

        if not use_fallback:
            self._win32_available = self._check_win32()

        if not self._win32_available:
            _logger.info("win32_unavailable_using_fallback")
            self._fallback = FallbackStorage()

    def _check_win32(self) -> bool:
        """Check if pywin32 is available.

        Returns:
            True if pywin32 is available, False otherwise
        """
        try:
            import win32cred

            self.win32cred = win32cred
            return True
        except ImportError:
            return False

    def read(self) -> SecureStorageData | None:
        """Read all stored data.

        Returns:
            SecureStorageData or None if no data exists
        """
        if self._fallback:
            return self._fallback.read()

        # Credential Manager doesn't support listing all credentials easily
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

        # Write each secret as a separate credential
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

            # Store using Credential Manager
            try:
                target = _get_target_name(user_id, service)

                credential = {
                    "Type": self.win32cred.CRED_TYPE_GENERIC,
                    "TargetName": target,
                    "UserName": user_id,
                    "Secret": json_str.encode("utf-16-le"),  # Windows expects UTF-16-LE
                    "Comment": f"MindFlow secret for {service}",
                    "Persist": self.win32cred.CRED_PERSIST_LOCAL_MACHINE,
                }

                self.win32cred.CredWrite(credential, 0)

                _logger.debug(
                    "credential_write_success",
                    service=service,
                    user_id=user_id,
                )
            except Exception as e:
                _logger.error(
                    "credential_write_failed",
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
            target = _get_target_name(user_id, service)

            deleted = self.win32cred.CredDelete(
                {
                    "Type": self.win32cred.CRED_TYPE_GENERIC,
                    "TargetName": target,
                },
                0,
            )

            if deleted:
                _logger.debug(
                    "credential_delete_success",
                    service=service,
                    user_id=user_id,
                )
            return deleted
        except Exception as e:
            _logger.error(
                "credential_delete_failed",
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

        # Credential Manager doesn't have a clear all method
        # Users should use delete() for specific entries
        _logger.warning("credential_clear_not_fully_implemented")
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
            target = _get_target_name(user_id, service)

            credential = self.win32cred.CredRead(
                {
                    "Type": self.win32cred.CRED_TYPE_GENERIC,
                    "TargetName": target,
                },
                0,
            )

            if credential:
                # Decode from UTF-16-LE
                secret_str = credential["Secret"].decode("utf-16-le")
                data_dict = json.loads(secret_str)
                # Handle both old and new format
                if "secret_data" in data_dict:
                    return data_dict["secret_data"]
                else:
                    # Old format: data_dict is the secret_data directly
                    return data_dict

            return None
        except Exception as e:
            _logger.error(
                "credential_read_failed",
                service=service,
                user_id=user_id,
                error=str(e),
            )
            return None

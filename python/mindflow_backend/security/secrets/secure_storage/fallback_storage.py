"""Fallback encrypted file storage for secure secrets.

Uses PBKDF2-HMAC-SHA256 with salt for key derivation and Fernet (AES-128) encryption.
Used when platform-specific storage (keychain, libsecret) is unavailable.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from mindflow_backend.infra.config.settings import Settings
from mindflow_backend.infra.logging import get_logger

from .base import SecureStorage, SecureStorageData

_logger = get_logger(__name__)


class FallbackStorage(SecureStorage):
    """Encrypted file-based secure storage fallback.

    Features:
    - PBKDF2-HMAC-SHA256 key derivation with random salt
    - AES-128 encryption via Fernet
    - User-specific key derivation with pepper from config
    - File permissions: 600 (Unix) / ACL (Windows)
    - Location: ~/.mindflow/secrets.enc
    - Supports multiple secrets per user
    """

    def __init__(self, storage_path: str | None = None):
        """Initialize fallback storage.

        Args:
            storage_path: Custom storage path (default: ~/.mindflow/secrets.enc)
        """
        if storage_path is None:
            home_dir = Path.home()
            storage_path = str(home_dir / ".mindflow" / "secrets.enc")

        self.storage_path = Path(storage_path)
        self._ensure_storage_dir()
        self._salt = self._load_or_generate_salt()
        self._key = self._derive_key()
        self._fernet = Fernet(self._key)

    def _ensure_storage_dir(self) -> None:
        """Ensure storage directory exists with proper permissions."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions on directory (Unix)
        if os.name != "nt":  # Unix-like
            try:
                os.chmod(self.storage_path.parent, 0o700)
            except OSError as e:
                _logger.warning(
                    "failed_to_set_dir_permissions",
                    path=str(self.storage_path.parent),
                    error=str(e),
                )

    def _load_or_generate_salt(self) -> bytes:
        """Load existing salt or generate new one.

        Returns:
            16-byte salt
        """
        salt_path = self.storage_path.with_suffix(".salt")

        if salt_path.exists():
            try:
                with open(salt_path, "rb") as f:
                    salt = f.read()
                    if len(salt) == 16:
                        return salt
            except OSError as e:
                _logger.warning("failed_to_load_salt", error=str(e))

        # Generate new salt
        salt = os.urandom(16)

        try:
            with open(salt_path, "wb") as f:
                f.write(salt)
            # Set restrictive permissions
            if os.name != "nt":
                os.chmod(salt_path, 0o600)
            _logger.debug("generated_new_salt")
        except OSError as e:
            _logger.error("failed_to_save_salt", error=str(e))

        return salt

    def _derive_key(self) -> bytes:
        """Derive encryption key using PBKDF2-HMAC-SHA256.

        Uses:
        - Random salt (16 bytes)
        - User-specific data (home directory, username)
        - Pepper from SecurityConfig

        Returns:
            Fernet-compatible encryption key (32 bytes)
        """
        import getpass

        # Get pepper from settings
        settings = Settings()
        pepper = settings.security.secret_pepper or "default_development_pepper_change_in_production"

        # Combine user-specific data with pepper
        user_data = f"{Path.home()}:{getpass.getuser()}:{pepper}"

        # Derive key using PBKDF2-HMAC-SHA256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=480000,  # OWASP recommended as of 2023
        )
        key = kdf.derive(user_data.encode())

        # Fernet requires base64-encoded 32-byte key
        return base64.urlsafe_b64encode(key)

    def _encrypt(self, data: str) -> str:
        """Encrypt data.

        Args:
            data: Plaintext data

        Returns:
            Encrypted data (base64-encoded)
        """
        encrypted = self._fernet.encrypt(data.encode())
        return encrypted.decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt data.

        Args:
            encrypted_data: Encrypted data (base64-encoded)

        Returns:
            Plaintext data

        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        try:
            decrypted = self._fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except InvalidToken as e:
            _logger.error("decryption_failed", error=str(e))
            raise

    def _set_file_permissions(self) -> None:
        """Set restrictive file permissions.

        Unix: 600 (owner read/write only)
        Windows: ACL via pywin32security (if available)
        """
        if not self.storage_path.exists():
            return

        if os.name != "nt":  # Unix-like
            try:
                os.chmod(self.storage_path, 0o600)
            except OSError as e:
                _logger.warning(
                    "failed_to_set_file_permissions",
                    path=str(self.storage_path),
                    error=str(e),
                )
        else:  # Windows
            try:
                import win32security
                import ntsecuritycon

                # Get current user
                user = win32security.LookupAccountName("", os.environ.get("USERNAME", "USER"))[0]

                # Create DACL with only user having full access
                dacl = win32security.ACL()
                dacl.AddAccessAllowedAce(
                    win32security.ACL_REVISION,
                    ntsecuritycon.FILE_ALL_ACCESS,
                    user
                )

                # Apply security descriptor
                sd = win32security.SECURITY_DESCRIPTOR()
                sd.SetSecurityDescriptorDacl(1, dacl, 0)

                # Set security on file
                win32security.SetFileSecurity(str(self.storage_path), win32security.DACL_SECURITY_INFORMATION, sd)

                _logger.debug("set_windows_acl_success", path=str(self.storage_path))
            except (ImportError, OSError, Exception) as e:
                _logger.warning(
                    "failed_to_set_windows_acl",
                    path=str(self.storage_path),
                    error=str(e),
                )

    def read(self) -> SecureStorageData | None:
        """Read all stored data.

        Returns:
            SecureStorageData or None if no data exists
        """
        if not self.storage_path.exists():
            return None

        try:
            with open(self.storage_path, "r") as f:
                encrypted_data = f.read().strip()

            if not encrypted_data:
                return None

            decrypted_json = self._decrypt(encrypted_data)
            data_dict = json.loads(decrypted_json)

            # Handle both old format (single entry) and new format (dictionary)
            if "secrets" in data_dict:
                # New format: dictionary of secrets
                return SecureStorageData(secrets=data_dict["secrets"])
            elif "user_id" in data_dict and "service" in data_dict:
                # Old format: single entry - migrate to new format
                old_data = data_dict
                new_data = SecureStorageData()
                new_data.add_secret(
                    old_data["user_id"],
                    old_data["service"],
                    old_data["secret_data"],
                    old_data.get("metadata", {}),
                )
                # Write back in new format
                self.write(new_data)
                return new_data
            else:
                # Unknown format
                _logger.warning("unknown_storage_format")
                return None
        except (InvalidToken, json.JSONDecodeError, KeyError, OSError) as e:
            _logger.error(
                "read_failed",
                path=str(self.storage_path),
                error=str(e),
            )
            return None

    def write(self, data: SecureStorageData) -> bool:
        """Write data to storage.

        Args:
            data: SecureStorageData to write

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            # Convert to JSON
            data_dict = {"secrets": data.secrets}
            json_str = json.dumps(data_dict)

            # Encrypt
            encrypted = self._encrypt(json_str)

            # Write to file (atomic write)
            temp_path = self.storage_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                f.write(encrypted)

            # Set permissions before moving
            self._set_file_permissions()

            # Atomic move
            temp_path.replace(self.storage_path)

            _logger.debug(
                "write_success",
                secrets_count=len(data.secrets),
            )

            return True
        except (OSError, TypeError) as e:
            _logger.error(
                "write_failed",
                path=str(self.storage_path),
                error=str(e),
            )
            return False

    def delete(self, service: str, user_id: str) -> bool:
        """Delete specific secret.

        Args:
            service: Service name
            user_id: User identifier

        Returns:
            True if deletion succeeded, False otherwise
        """
        data = self.read()
        if not data:
            return False

        # Remove the secret
        if data.remove_secret(user_id, service):
            # Write back updated data
            return self.write(data)

        return False

    def clear(self) -> bool:
        """Clear all stored data.

        Returns:
            True if clear succeeded, False otherwise
        """
        try:
            if self.storage_path.exists():
                self.storage_path.unlink()
                _logger.debug("clear_success", path=str(self.storage_path))

            # Also remove salt file
            salt_path = self.storage_path.with_suffix(".salt")
            if salt_path.exists():
                salt_path.unlink()
                _logger.debug("clear_salt_success", path=str(salt_path))

            return True
        except OSError as e:
            _logger.error(
                "clear_failed",
                path=str(self.storage_path),
                error=str(e),
            )
            return False

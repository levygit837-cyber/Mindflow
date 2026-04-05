"""Unified secure storage manager.

Provides platform-specific secure storage with fallback to encrypted file.

TODO: Integrate with CLI
- CLI should use same secure storage backend
- CLI should support device code flow for OAuth2

TODO: Integrate with Desktop
- Desktop should use same secure storage backend
- Desktop should support custom scheme OAuth2 flow
"""

from __future__ import annotations

import sys

from mindflow_backend.infra.logging import get_logger

from .base import SecureStorage
from .fallback_storage import FallbackStorage

# Platform-specific imports (lazy loaded)
_macos_storage = None
_linux_storage = None
_windows_storage = None

_logger = get_logger(__name__)


def get_secure_storage(use_fallback: bool = False) -> SecureStorage:
    """Get appropriate secure storage for current platform.

    Priority:
    1. macOS Keychain (darwin)
    2. Linux libsecret (linux)
    3. Windows Credential Manager (win32)
    4. Encrypted file fallback (all platforms)

    Args:
        use_fallback: Force use of fallback storage

    Returns:
        SecureStorage instance
    """
    global _macos_storage, _linux_storage, _windows_storage

    if use_fallback:
        _logger.info("using_fallback_storage")
        return FallbackStorage()

    platform = sys.platform

    # macOS
    if platform == "darwin":
        if _macos_storage is None:
            try:
                from .macos_keychain import MacOSKeychainStorage

                _macos_storage = MacOSKeychainStorage()
                _logger.info("using_macos_keychain")
            except Exception as e:
                _logger.warning("macos_keychain_failed", error=str(e))
                _macos_storage = FallbackStorage()
        return _macos_storage

    # Linux
    elif platform in ("linux", "linux2"):
        if _linux_storage is None:
            try:
                from .linux_libsecret import LinuxLibsecretStorage

                _linux_storage = LinuxLibsecretStorage()
                _logger.info("using_linux_libsecret")
            except Exception as e:
                _logger.warning("linux_libsecret_failed", error=str(e))
                _linux_storage = FallbackStorage()
        return _linux_storage

    # Windows
    elif platform == "win32":
        if _windows_storage is None:
            try:
                from .windows_credential import WindowsCredentialStorage

                _windows_storage = WindowsCredentialStorage()
                _logger.info("using_windows_credential")
            except Exception as e:
                _logger.warning("windows_credential_failed", error=str(e))
                _windows_storage = FallbackStorage()
        return _windows_storage

    # Unknown platform - use fallback
    else:
        _logger.warning("unknown_platform_using_fallback", platform=platform)
        return FallbackStorage()


def migrate_to_backend(
    from_storage: SecureStorage,
    to_storage: SecureStorage,
) -> bool:
    """Migrate secrets from one backend to another.

    Args:
        from_storage: Source storage backend
        to_storage: Destination storage backend

    Returns:
        True if migration succeeded, False otherwise
    """
    try:
        # Read all data from source
        data = from_storage.read()

        if data:
            # Write to destination
            success = to_storage.write(data)

            if success:
                # Clear source
                from_storage.clear()
                _logger.info("migration_success")
                return True
            else:
                _logger.error("migration_write_failed")
                return False
        else:
            _logger.info("no_data_to_migrate")
            return True
    except Exception as e:
        _logger.error("migration_failed", error=str(e))
        return False

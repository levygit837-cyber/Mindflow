"""Secure storage for user secrets with multi-platform support.

Provides secure storage backend abstraction supporting:
- macOS: Keychain via security command
- Linux: libsecret via DBus
- Windows: Credential Manager via pywin32
- Fallback: Encrypted file storage
"""

from .base import SecureStorage, SecureStorageData
from .manager import get_secure_storage

__all__ = [
    "SecureStorage",
    "SecureStorageData",
    "get_secure_storage",
]

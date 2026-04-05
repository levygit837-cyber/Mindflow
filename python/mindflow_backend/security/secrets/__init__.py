"""Secret management module.

Provides secure storage for user secrets with multi-platform support:
- macOS Keychain
- Linux libsecret
- Windows Credential Manager
- Encrypted file fallback

Also includes secret scanner for detecting exposed credentials in code.
"""

from .secure_storage import (
    SecureStorage,
    SecureStorageData,
    get_secure_storage,
)
from .scanner import SecretScanner, SecretMatch

__all__ = [
    "SecureStorage",
    "SecureStorageData",
    "get_secure_storage",
    "SecretScanner",
    "SecretMatch",
]

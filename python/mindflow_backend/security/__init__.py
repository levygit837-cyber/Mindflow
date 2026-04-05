"""Security module for MindFlow.

Provides comprehensive security features including:
- Docker sandbox isolation
- Secret detection and scanning
- Secure multi-platform secret storage
- Bash command validation
- Network access control
- Security audit logging
- JWT authentication
- OAuth2 authentication with PKCE
- Timeout enforcement
- XSS sanitization
- Penetration testing framework
"""

# Lazy imports to avoid requiring docker at import time
__all__ = [
    "DockerSandbox",
    "DockerSandboxConfig",
    "SecretScanner",
    "SecretMatch",
    "SecureStorage",
    "SecureStorageData",
    "get_secure_storage",
    "validate_bash_command",
    "SecurityDecision",
    "NetworkPolicy",
    "NetworkAction",
    "get_security_logger",
    "SecurityLogger",
    "get_jwt_secret_key",
    "generate_jwt_secret",
    "OAuth2Service",
    "StateManager",
    "generate_code_challenge",
    "generate_code_verifier",
    "generate_pkce_pair",
    "TimeoutManager",
    "get_timeout_manager",
    "XSSSanitizer",
    "sanitize_html",
    "sanitize_json",
    "sanitize_url",
    "PenTestFramework",
    "PenTestResult",
    "PenTestSeverity",
]


def __getattr__(name):
    """Lazy import security components."""
    if name == "DockerSandbox" or name == "DockerSandboxConfig":
        from mindflow_backend.security.sandbox.docker_sandbox import DockerSandbox, DockerSandboxConfig
        return DockerSandbox if name == "DockerSandbox" else DockerSandboxConfig

    elif name == "SecretScanner" or name == "SecretMatch":
        from mindflow_backend.security.secrets.scanner import SecretScanner, SecretMatch
        return SecretScanner if name == "SecretScanner" else SecretMatch

    elif name == "validate_bash_command" or name == "SecurityDecision":
        from mindflow_backend.security.validators.bash_validators import validate_bash_command, SecurityDecision
        return validate_bash_command if name == "validate_bash_command" else SecurityDecision

    elif name == "NetworkPolicy" or name == "NetworkAction":
        from mindflow_backend.security.policies.network_policy import NetworkPolicy, NetworkAction
        return NetworkPolicy if name == "NetworkPolicy" else NetworkAction

    elif name == "get_security_logger" or name == "SecurityLogger":
        from mindflow_backend.security.audit.security_logger import get_security_logger, SecurityLogger
        return get_security_logger if name == "get_security_logger" else SecurityLogger

    elif name == "get_jwt_secret_key" or name == "generate_jwt_secret":
        from mindflow_backend.security.auth.jwt_secret import get_jwt_secret_key, generate_jwt_secret
        return get_jwt_secret_key if name == "get_jwt_secret_key" else generate_jwt_secret

    elif name == "SecureStorage" or name == "SecureStorageData" or name == "get_secure_storage":
        from mindflow_backend.security.secrets import SecureStorage, SecureStorageData, get_secure_storage
        if name == "SecureStorage":
            return SecureStorage
        elif name == "SecureStorageData":
            return SecureStorageData
        else:
            return get_secure_storage

    elif name == "OAuth2Service" or name == "StateManager" or name == "generate_code_challenge" or name == "generate_code_verifier" or name == "generate_pkce_pair":
        from mindflow_backend.security.auth import OAuth2Service, StateManager, generate_code_challenge, generate_code_verifier, generate_pkce_pair
        if name == "OAuth2Service":
            return OAuth2Service
        elif name == "StateManager":
            return StateManager
        elif name == "generate_code_challenge":
            return generate_code_challenge
        elif name == "generate_code_verifier":
            return generate_code_verifier
        else:
            return generate_pkce_pair

    elif name == "TimeoutManager" or name == "get_timeout_manager":
        from mindflow_backend.security.timeout import TimeoutManager, get_timeout_manager
        return TimeoutManager if name == "TimeoutManager" else get_timeout_manager

    elif name == "XSSSanitizer" or name == "sanitize_html" or name == "sanitize_json" or name == "sanitize_url":
        from mindflow_backend.security.xss import XSSSanitizer, sanitize_html, sanitize_json, sanitize_url
        if name == "XSSSanitizer":
            return XSSSanitizer
        elif name == "sanitize_html":
            return sanitize_html
        elif name == "sanitize_json":
            return sanitize_json
        else:
            return sanitize_url

    elif name == "PenTestFramework" or name == "PenTestResult" or name == "PenTestSeverity":
        from mindflow_backend.security.pen_test import PenTestFramework, PenTestResult, PenTestSeverity
        if name == "PenTestFramework":
            return PenTestFramework
        elif name == "PenTestResult":
            return PenTestResult
        else:
            return PenTestSeverity

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

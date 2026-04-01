"""Security module for MindFlow.

Provides comprehensive security features including:
- Docker sandbox isolation
- Secret detection and scanning
- Bash command validation
- Network access control
- Security audit logging
- JWT authentication
"""

# Lazy imports to avoid requiring docker at import time
__all__ = [
    "DockerSandbox",
    "DockerSandboxConfig",
    "SecretScanner",
    "SecretMatch",
    "validate_bash_command",
    "SecurityDecision",
    "NetworkPolicy",
    "NetworkAction",
    "get_security_logger",
    "SecurityLogger",
    "get_jwt_secret_key",
    "generate_jwt_secret",
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

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

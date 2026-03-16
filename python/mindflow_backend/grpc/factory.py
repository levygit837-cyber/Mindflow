"""Transport factory — selects the runtime client implementation.

Controls whether the HTTP gateway talks to the agent runtime via the in-process
LocalAgentClient (mode=local) or a real gRPC network channel (mode=network), with
an optional auto-fallback mode that prefers network but falls back to local.

The active mode is read from settings (GRPC_TRANSPORT_MODE env var) but can be
overridden per-call, which is useful for benchmarking and canary deployments.
"""

from __future__ import annotations

from enum import Enum

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class TransportMode(str, Enum):
    LOCAL = "local"
    NETWORK = "network"
    AUTO = "auto"


def get_runtime_client(mode: str | None = None):
    """Return the runtime client for the requested transport mode.

    Args:
        mode: One of "local", "network", or "auto".  When ``None`` the value is
              read from ``settings.grpc_transport_mode`` (default: "local").

    Returns:
        A client object that implements ``stream_chat(**kwargs)``.
    """
    from mindflow_backend.infra.config import get_settings
    settings = get_settings()
    resolved = mode or getattr(settings, "grpc_transport_mode", TransportMode.LOCAL)
    resolved = TransportMode(resolved)

    if resolved == TransportMode.NETWORK:
        return _get_network_client()
    if resolved == TransportMode.AUTO:
        return _get_network_client_with_local_fallback()
    return _get_local_client()


# ── Internal helpers ──────────────────────────────────────────────────────────

_local_client_singleton = None


def _get_local_client():
    """Return (or create) the cached LocalAgentClient singleton."""
    global _local_client_singleton
    if _local_client_singleton is None:
        from mindflow_backend.grpc.client import LocalAgentClient
        _local_client_singleton = LocalAgentClient()
        _logger.debug("transport_factory_created_local_client")
    return _local_client_singleton


def _get_network_client():
    """Create a fresh EnhancedGrpcAgentClient for real network transport."""
    from mindflow_backend.grpc.client import EnhancedGrpcAgentClient
    _logger.debug("transport_factory_created_network_client")
    return EnhancedGrpcAgentClient()


def _get_network_client_with_local_fallback():
    """Try to return a network client; fall back to local on any error."""
    try:
        return _get_network_client()
    except Exception as exc:
        _logger.warning("transport_factory_network_unavailable_using_local", error=str(exc))
        return _get_local_client()

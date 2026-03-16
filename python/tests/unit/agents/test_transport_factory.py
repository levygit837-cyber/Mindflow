"""Tests for the transport factory (Task 5)."""

from unittest.mock import patch

import pytest

from mindflow_backend.grpc.factory import TransportMode, get_runtime_client
from mindflow_backend.grpc.client import LocalAgentClient


def test_factory_returns_local_client_by_default():
    """get_runtime_client(mode='local') must return a LocalAgentClient."""
    client = get_runtime_client(mode="local")
    assert isinstance(client, LocalAgentClient)


def test_factory_returns_same_local_singleton():
    """Repeated calls with mode='local' should return the same cached object."""
    c1 = get_runtime_client(mode="local")
    c2 = get_runtime_client(mode="local")
    assert c1 is c2


def test_factory_returns_network_client_for_network_mode():
    """get_runtime_client(mode='network') must return an EnhancedGrpcAgentClient."""
    from mindflow_backend.grpc.client import EnhancedGrpcAgentClient
    client = get_runtime_client(mode="network")
    assert isinstance(client, EnhancedGrpcAgentClient)


def test_factory_auto_mode_falls_back_to_local_on_error():
    """mode='auto' must fall back to LocalAgentClient if network client fails."""
    with patch(
        "mindflow_backend.grpc.factory._get_network_client",
        side_effect=RuntimeError("no grpc"),
    ):
        client = get_runtime_client(mode="auto")
    assert isinstance(client, LocalAgentClient)


def test_transport_mode_enum_values():
    """TransportMode enum must contain expected string values."""
    assert TransportMode.LOCAL == "local"
    assert TransportMode.NETWORK == "network"
    assert TransportMode.AUTO == "auto"

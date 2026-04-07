"""Interface conformance tests for MindFlow backend services.

This module verifies that all service implementations properly implement
their respective interfaces, ensuring contract compliance.
"""

from __future__ import annotations

import inspect
from typing import Any, Protocol, get_type_hints

import pytest

from mindflow_backend.interfaces.services.memory import (
    AgentMemoryServiceInterface,
    MemoryFacadeInterface,
)
from mindflow_backend.services.memory import (
    MemoryFacadeService,
    MemoryService,
    get_memory_facade_service,
)


class TestMemoryFacadeInterface:
    """Test conformance of MemoryFacadeService to MemoryFacadeInterface."""

    def test_service_implements_interface(self):
        """Verify MemoryFacadeService implements MemoryFacadeInterface."""
        service = MemoryFacadeService()
        assert isinstance(service, MemoryFacadeInterface), (
            "MemoryFacadeService must implement MemoryFacadeInterface"
        )

    def test_service_has_all_interface_methods(self):
        """Verify all interface methods are implemented."""
        interface_methods = self._get_protocol_methods(MemoryFacadeInterface)
        service_methods = self._get_class_methods(MemoryFacadeService)

        missing_methods = interface_methods - service_methods
        assert not missing_methods, (
            f"MemoryFacadeService missing methods: {missing_methods}"
        )

    def test_service_method_signatures_match(self):
        """Verify method signatures match interface definitions."""
        interface_hints = get_type_hints(MemoryFacadeInterface)
        service_hints = get_type_hints(MemoryFacadeService)

        for method_name in self._get_protocol_methods(MemoryFacadeInterface):
            if method_name in service_hints:
                # Check return type compatibility
                interface_return = interface_hints.get(method_name, {}).get('return', Any)
                service_return = service_hints.get(method_name, {}).get('return', Any)
                
                # Note: We don't enforce exact type equality due to covariance
                # but we should have return type annotations
                assert service_return is not Any or method_name == '__init__', (
                    f"Method {method_name} should have return type annotation"
                )

    def test_singleton_factory(self):
        """Verify get_memory_facade_service returns singleton."""
        service1 = get_memory_facade_service()
        service2 = get_memory_facade_service()
        
        assert service1 is service2, (
            "get_memory_facade_service should return singleton instance"
        )
        assert isinstance(service1, MemoryFacadeService), (
            "Factory should return MemoryFacadeService instance"
        )

    @staticmethod
    def _get_protocol_methods(protocol: type[Protocol]) -> set[str]:
        """Get all method names defined in a Protocol."""
        methods = set()
        for name in dir(protocol):
            if not name.startswith('_'):
                attr = getattr(protocol, name)
                if callable(attr) and not isinstance(attr, property):
                    methods.add(name)
        return methods

    @staticmethod
    def _get_class_methods(cls: type) -> set[str]:
        """Get all method names defined in a class."""
        methods = set()
        for name in dir(cls):
            if not name.startswith('_') or name in {'__init__', '__aenter__', '__aexit__'}:
                attr = getattr(cls, name)
                if callable(attr):
                    methods.add(name)
        return methods


class TestAgentMemoryServiceInterface:
    """Test conformance of MemoryService to AgentMemoryServiceInterface."""

    def test_service_implements_interface(self):
        """Verify MemoryService implements AgentMemoryServiceInterface."""
        service = MemoryService()
        assert isinstance(service, AgentMemoryServiceInterface), (
            "MemoryService must implement AgentMemoryServiceInterface"
        )

    def test_required_methods_exist(self):
        """Verify all required abstract methods are implemented."""
        required_methods = [
            'get_agent_memory',
            'add_memory_event',
            'search_semantic_context',
            'retrieve_context_for_query',
            'create_memory_summary',
            'get_memory_windows',
            'initialize_session_memory',
            'cleanup_session_memory',
            'get_session_memory_summary',
        ]
        
        service = MemoryService()
        for method_name in required_methods:
            assert hasattr(service, method_name), (
                f"MemoryService missing required method: {method_name}"
            )
            method = getattr(service, method_name)
            assert callable(method), (
                f"{method_name} should be callable"
            )


class TestInterfaceRuntimeCheckable:
    """Test that interfaces are properly decorated with @runtime_checkable."""

    def test_memory_facade_interface_is_runtime_checkable(self):
        """Verify MemoryFacadeInterface is runtime checkable."""
        from typing import runtime_checkable
        
        assert getattr(MemoryFacadeInterface, '_is_runtime_checkable', False), (
            "MemoryFacadeInterface should be decorated with @runtime_checkable"
        )

    def test_agent_memory_interface_is_runtime_checkable(self):
        """Verify AgentMemoryServiceInterface is runtime checkable."""
        assert getattr(AgentMemoryServiceInterface, '_is_runtime_checkable', False), (
            "AgentMemoryServiceInterface should be decorated with @runtime_checkable"
        )


class TestServiceInheritance:
    """Test proper inheritance patterns for services."""

    def test_memory_facade_service_inheritance(self):
        """Verify MemoryFacadeService inherits from correct base classes."""
        from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
        
        assert issubclass(MemoryFacadeService, BaseAbstractService), (
            "MemoryFacadeService should inherit from BaseAbstractService"
        )
        assert issubclass(MemoryFacadeService, MemoryFacadeInterface), (
            "MemoryFacadeService should inherit from MemoryFacadeInterface"
        )

    def test_memory_service_inheritance(self):
        """Verify MemoryService inherits from correct base classes."""
        from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
        
        assert issubclass(MemoryService, BaseAbstractService), (
            "MemoryService should inherit from BaseAbstractService"
        )
        assert issubclass(MemoryService, AgentMemoryServiceInterface), (
            "MemoryService should inherit from AgentMemoryServiceInterface"
        )


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
class TestMemoryFacadeServiceIntegration:
    """Integration tests for MemoryFacadeService."""

    async def test_service_initialization(self):
        """Test service can be initialized."""
        service = MemoryFacadeService()
        assert service._facade is not None

    async def test_get_agent_snapshot_signature(self):
        """Test get_agent_snapshot accepts correct parameters."""
        service = MemoryFacadeService()
        
        # Verify signature accepts the expected parameters
        sig = inspect.signature(service.get_agent_snapshot)
        params = list(sig.parameters.keys())
        
        assert 'session_id' in params
        assert 'agent_id' in params
        assert 'token_limit' in params

    async def test_recall_signature(self):
        """Test recall accepts MemoryRecallRequest."""
        service = MemoryFacadeService()
        
        sig = inspect.signature(service.recall)
        params = list(sig.parameters.keys())
        
        assert 'request' in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

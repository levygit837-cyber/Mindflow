"""Enhanced node registry for MindFlow orchestration."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
from mindflow_backend.runtime.node_registry import (
    NodeCategory as RuntimeNodeCategory,
)
from mindflow_backend.runtime.node_registry import (
    classify_node as runtime_classify_node,
)
from mindflow_backend.runtime.node_registry import (
    get_node_label as runtime_get_node_label,
)
from mindflow_backend.runtime.node_registry import (
    is_streamable_node as runtime_is_streamable_node,
)


class NodeCapability(StrEnum):
    """Capabilities that nodes can provide."""
    
    STREAMING = "streaming"
    STATEFUL = "stateful"
    ASYNC = "async"
    RETRYABLE = "retryable"
    CACHABLE = "cachable"
    MONITORABLE = "monitorable"
    PARALLELIZABLE = "parallelizable"
    CONDITIONAL = "conditional"


class NodeMetadata:
    """Metadata for registered nodes."""
    
    def __init__(
        self,
        node_class: type[BaseNode],
        node_type: NodeType,
        category: NodeCategory,
        description: str = "",
        capabilities: list[NodeCapability] = None,
        tags: list[str] = None,
        version: str = "1.0.0",
        author: str = "",
    ) -> None:
        self.node_class = node_class
        self.node_type = node_type
        self.category = category
        self.description = description
        self.capabilities = capabilities or []
        self.tags = tags or []
        self.version = version
        self.author = author
        self.registered_at = self._get_timestamp()
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def has_capability(self, capability: NodeCapability) -> bool:
        """Check if node has a specific capability."""
        return capability in self.capabilities
    
    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "node_class": self.node_class.__name__,
            "node_type": self.node_type.value,
            "category": self.category.value,
            "description": self.description,
            "capabilities": [cap.value for cap in self.capabilities],
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
            "registered_at": self.registered_at,
        }


class NodeRegistry:
    """Enhanced registry for node discovery and instantiation."""
    
    def __init__(self) -> None:
        self._nodes: dict[str, NodeMetadata] = {}
        self._node_instances: dict[str, BaseNode] = {}
        self._type_index: dict[NodeType, list[str]] = {}
        self._category_index: dict[NodeCategory, list[str]] = {}
        self._capability_index: dict[NodeCapability, list[str]] = {}
        self._tag_index: dict[str, list[str]] = {}
    
    def register(
        self,
        node_id: str,
        node_class: type[BaseNode],
        node_type: NodeType,
        category: NodeCategory,
        description: str = "",
        capabilities: list[NodeCapability] = None,
        tags: list[str] = None,
        version: str = "1.0.0",
        author: str = "",
        instance: BaseNode | None = None,
    ) -> None:
        """Register a node class with the registry."""
        if node_id in self._nodes:
            raise ValueError(f"Node {node_id} is already registered")
        
        metadata = NodeMetadata(
            node_class=node_class,
            node_type=node_type,
            category=category,
            description=description,
            capabilities=capabilities,
            tags=tags,
            version=version,
            author=author,
        )
        
        self._nodes[node_id] = metadata
        
        # Update indexes
        self._type_index.setdefault(node_type, []).append(node_id)
        self._category_index.setdefault(category, []).append(node_id)
        
        for capability in metadata.capabilities:
            self._capability_index.setdefault(capability, []).append(node_id)
        
        for tag in metadata.tags:
            self._tag_index.setdefault(tag, []).append(node_id)
        
        # Store instance if provided
        if instance:
            self._node_instances[node_id] = instance
    
    def unregister(self, node_id: str) -> bool:
        """Unregister a node from the registry."""
        if node_id not in self._nodes:
            return False
        
        metadata = self._nodes[node_id]
        
        # Remove from indexes
        self._type_index[metadata.node_type].remove(node_id)
        self._category_index[metadata.category].remove(node_id)
        
        for capability in metadata.capabilities:
            if node_id in self._capability_index[capability]:
                self._capability_index[capability].remove(node_id)
        
        for tag in metadata.tags:
            if node_id in self._tag_index[tag]:
                self._tag_index[tag].remove(node_id)
        
        # Remove from registry
        del self._nodes[node_id]
        if node_id in self._node_instances:
            del self._node_instances[node_id]
        
        return True
    
    def get_metadata(self, node_id: str) -> NodeMetadata | None:
        """Get metadata for a registered node."""
        return self._nodes.get(node_id)
    
    def create_instance(
        self, 
        node_id: str, 
        **kwargs
    ) -> BaseNode | None:
        """Create an instance of a registered node."""
        metadata = self._nodes.get(node_id)
        if not metadata:
            return None
        
        try:
            return metadata.node_class(node_id=node_id, **kwargs)
        except Exception:
            return None
    
    def get_instance(self, node_id: str) -> BaseNode | None:
        """Get a stored instance of a node."""
        return self._node_instances.get(node_id)
    
    def list_nodes(self) -> list[str]:
        """List all registered node IDs."""
        return list(self._nodes.keys())
    
    def find_by_type(self, node_type: NodeType) -> list[str]:
        """Find nodes by type."""
        return list(self._type_index.get(node_type, []))
    
    def find_by_category(self, category: NodeCategory) -> list[str]:
        """Find nodes by category."""
        return list(self._category_index.get(category, []))
    
    def find_by_capability(self, capability: NodeCapability) -> list[str]:
        """Find nodes by capability."""
        return list(self._capability_index.get(capability, []))
    
    def find_by_tag(self, tag: str) -> list[str]:
        """Find nodes by tag."""
        return list(self._tag_index.get(tag, []))
    
    def search(self, query: str) -> list[str]:
        """Search nodes by query in description, tags, and node ID."""
        query = query.lower()
        results = []
        
        for node_id, metadata in self._nodes.items():
            if (query in node_id.lower() or
                query in metadata.description.lower() or
                any(query in tag.lower() for tag in metadata.tags)):
                results.append(node_id)
        
        return results
    
    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_nodes": len(self._nodes),
            "nodes_by_type": {
                node_type.value: len(nodes)
                for node_type, nodes in self._type_index.items()
            },
            "nodes_by_category": {
                category.value: len(nodes)
                for category, nodes in self._category_index.items()
            },
            "nodes_by_capability": {
                capability.value: len(nodes)
                for capability, nodes in self._capability_index.items()
            },
            "total_instances": len(self._node_instances),
        }
    
    def validate_node(self, node_id: str) -> list[str]:
        """Validate a registered node."""
        metadata = self._nodes.get(node_id)
        if not metadata:
            return [f"Node {node_id} not found"]
        
        issues = []
        
        # Check if node class is valid
        if not issubclass(metadata.node_class, BaseNode):
            issues.append("Node class must inherit from BaseNode")
        
        # Try to create an instance
        try:
            instance = metadata.node_class(node_id="test")
            if not hasattr(instance, 'execute'):
                issues.append("Node must have execute method")
            if not hasattr(instance, 'validate_inputs'):
                issues.append("Node must have validate_inputs method")
        except Exception as e:
            issues.append(f"Failed to create instance: {e}")
        
        return issues
    
    def export_registry(self) -> dict[str, Any]:
        """Export registry data for serialization."""
        return {
            "nodes": {
                node_id: metadata.to_dict()
                for node_id, metadata in self._nodes.items()
            },
            "stats": self.get_stats(),
            "exported_at": self._get_timestamp(),
        }
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()


# Global registry instance
_global_registry: NodeRegistry | None = None


def get_node_registry() -> NodeRegistry:
    """Get the global node registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = NodeRegistry()
    return _global_registry


# Backward compatibility functions
def classify_node(node_name: str) -> NodeCategory:
    """Classify node using enhanced registry or fallback to runtime."""
    registry = get_node_registry()
    metadata = registry.get_metadata(node_name)
    
    if metadata:
        return metadata.category
    
    # Fallback to runtime classification
    runtime_category = runtime_classify_node(node_name)
    category_mapping = {
        RuntimeNodeCategory.LLM_INVOKE: NodeCategory.LLM_INVOKE,
        RuntimeNodeCategory.TOOL_EXECUTION: NodeCategory.TOOL_EXECUTION,
        RuntimeNodeCategory.SUBGRAPH: NodeCategory.SUBGRAPH,
        RuntimeNodeCategory.INTERNAL: NodeCategory.INTERNAL,
        RuntimeNodeCategory.UNKNOWN: NodeCategory.UNKNOWN,
    }
    return category_mapping.get(runtime_category, NodeCategory.UNKNOWN)


def get_node_label(node_name: str) -> str:
    """Get node label using enhanced registry or fallback to runtime."""
    registry = get_node_registry()
    metadata = registry.get_metadata(node_name)
    
    if metadata:
        return metadata.description or runtime_get_node_label(node_name)
    
    return runtime_get_node_label(node_name)


def is_streamable_node(node_name: str) -> bool:
    """Check if node is streamable using enhanced registry or fallback to runtime."""
    registry = get_node_registry()
    metadata = registry.get_metadata(node_name)
    
    if metadata:
        return metadata.has_capability(NodeCapability.STREAMING)
    
    return runtime_is_streamable_node(node_name)


# Auto-register common nodes
def _auto_register_common_nodes() -> None:
    """Auto-register common orchestrator nodes."""
    registry = get_node_registry()
    
    # Import nodes to register them
    from mindflow_backend.nodes.orchestrator.execute_node import ExecuteNode
    from mindflow_backend.nodes.orchestrator.respond_node import RespondNode
    from mindflow_backend.nodes.orchestrator.route_node import RouteNode
    
    # Register route node
    registry.register(
        node_id="route",
        node_class=RouteNode,
        node_type=NodeType.ROUTER,
        category=NodeCategory.CONTROL_FLOW,
        description="Analyze user message and select agent personality",
        capabilities=[NodeCapability.STATEFUL, NodeCapability.ASYNC],
        tags=["routing", "agent-selection", "classification"],
        author="MindFlow",
    )
    
    # Register execute node
    registry.register(
        node_id="execute",
        node_class=ExecuteNode,
        node_type=NodeType.EXECUTOR,
        category=NodeCategory.LLM_INVOKE,
        description="Invoke the LLM using the selected agent's personality and tools",
        capabilities=[NodeCapability.STREAMING, NodeCapability.STATEFUL, NodeCapability.ASYNC],
        tags=["llm", "execution", "tools", "agents"],
        author="MindFlow",
    )
    
    # Register respond node
    registry.register(
        node_id="respond",
        node_class=RespondNode,
        node_type=NodeType.FORMATTER,
        category=NodeCategory.DATA_PROCESSING,
        description="Finalize the response and handle post-processing",
        capabilities=[NodeCapability.STATEFUL, NodeCapability.ASYNC],
        tags=["formatting", "post-processing", "response"],
        author="MindFlow",
    )


# Initialize auto-registration
_auto_register_common_nodes()

# Memory graph tools — upsert_node, create_relation, search_graph
# FEATURE: Memory - Graph operations for RAG system

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.contextplus.core.embeddings import fetch_embedding
from mindflow_backend.contextplus.core.memory_graph import (
    NodeType,
    RelationType,
    create_relation,
    get_graph_stats,
    search_graph,
    upsert_node,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.base import (
    ParameterType,
    ToolParameter,
    ToolSchema,
)

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Upsert Memory Node
# ---------------------------------------------------------------------------

UPSERT_MEMORY_NODE_SCHEMA = ToolSchema(
    name="upsert_memory_node",
    description=(
        "Create or update a memory node in the linking graph. Nodes represent concepts, "
        "files, symbols, or notes with auto-generated embeddings. If a node with the same "
        "label and type exists, it updates content and increments access count."
    ),
    category="memory",
    parameters=[
        ToolParameter(
            name="node_type",
            type=ParameterType.STRING,
            description="Node type: concept, file, symbol, note.",
            required=True,
            enum=["concept", "file", "symbol", "note"],
        ),
        ToolParameter(
            name="label",
            type=ParameterType.STRING,
            description="Short identifier for the node. Used for deduplication with type.",
            required=True,
        ),
        ToolParameter(
            name="content",
            type=ParameterType.STRING,
            description="Detailed content for the node. Used for embedding generation.",
            required=True,
        ),
        ToolParameter(
            name="metadata",
            type=ParameterType.OBJECT,
            description="Optional key-value metadata pairs.",
            required=False,
        ),
    ],
)


class UpsertMemoryNodeTool(AsyncToolInterface):
    """Create or update memory nodes with auto-embeddings."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "upsert_memory_node"
        self.description = UPSERT_MEMORY_NODE_SCHEMA.description
        self._schema = UPSERT_MEMORY_NODE_SCHEMA

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        node_type = kwargs.get("node_type")
        label = kwargs.get("label")
        content = kwargs.get("content")

        if not all([node_type, label, content]):
            return self._format_result(success=False, error="node_type, label, and content are required")

        root_dir = self.root_dir or "."
        metadata = kwargs.get("metadata")

        try:
            embedding = await fetch_embedding(f"{label} {content}")
            node = await upsert_node(
                root_dir=root_dir,
                node_type=node_type,
                label=label,
                content=content,
                embedding=embedding,
                metadata=metadata,
            )
            stats = await get_graph_stats(root_dir)

            result = (
                f"✅ Memory node upserted: {node.label}\n"
                f"  ID: {node.id}\n"
                f"  Type: {node.type}\n"
                f"  Access count: {node.access_count}\n"
                f"\nGraph: {stats['nodes']} nodes, {stats['edges']} edges"
            )
            return self._format_result(success=True, result=result)
        except Exception as e:
            _logger.error(f"upsert_memory_node failed: {e}")
            return self._format_result(success=False, error=str(e))


# ---------------------------------------------------------------------------
# Create Relation
# ---------------------------------------------------------------------------

CREATE_RELATION_SCHEMA = ToolSchema(
    name="create_relation",
    description=(
        "Create a typed edge between two memory nodes. Supports relation types: "
        "relates_to, depends_on, implements, references, similar_to, contains."
    ),
    category="memory",
    parameters=[
        ToolParameter(
            name="source_id",
            type=ParameterType.STRING,
            description="ID of the source memory node.",
            required=True,
        ),
        ToolParameter(
            name="target_id",
            type=ParameterType.STRING,
            description="ID of the target memory node.",
            required=True,
        ),
        ToolParameter(
            name="relation",
            type=ParameterType.STRING,
            description="Relationship type between nodes.",
            required=True,
            enum=["relates_to", "depends_on", "implements", "references", "similar_to", "contains"],
        ),
        ToolParameter(
            name="weight",
            type=ParameterType.FLOAT,
            description="Edge weight 0-1. Higher = stronger relationship. Default: 1.0.",
            required=False,
            default=1.0,
        ),
    ],
)


class CreateRelationTool(AsyncToolInterface):
    """Create typed edges between memory nodes."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "create_relation"
        self.description = CREATE_RELATION_SCHEMA.description
        self._schema = CREATE_RELATION_SCHEMA

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        source_id = kwargs.get("source_id")
        target_id = kwargs.get("target_id")
        relation = kwargs.get("relation")

        if not all([source_id, target_id, relation]):
            return self._format_result(success=False, error="source_id, target_id, and relation are required")

        root_dir = self.root_dir or "."
        weight = kwargs.get("weight", 1.0)

        try:
            edge = await create_relation(
                root_dir=root_dir,
                source_id=source_id,
                target_id=target_id,
                relation=relation,
                weight=weight,
            )

            if not edge:
                return self._format_result(
                    success=False,
                    error=f"Failed: one or both node IDs not found (source: {source_id}, target: {target_id})",
                )

            stats = await get_graph_stats(root_dir)
            result = (
                f"✅ Relation created: {source_id} --[{edge.relation}]--> {target_id}\n"
                f"  Edge ID: {edge.id}\n"
                f"  Weight: {edge.weight}\n"
                f"\nGraph: {stats['nodes']} nodes, {stats['edges']} edges"
            )
            return self._format_result(success=True, result=result)
        except Exception as e:
            _logger.error(f"create_relation failed: {e}")
            return self._format_result(success=False, error=str(e))


# ---------------------------------------------------------------------------
# Search Memory Graph
# ---------------------------------------------------------------------------

SEARCH_MEMORY_GRAPH_SCHEMA = ToolSchema(
    name="search_memory_graph",
    description=(
        "Search the memory graph by meaning with graph traversal. Finds direct matches "
        "via embedding similarity, then traverses 1st/2nd-degree neighbors to discover "
        "linked context."
    ),
    category="memory",
    parameters=[
        ToolParameter(
            name="query",
            type=ParameterType.STRING,
            description="Natural language query to search the memory graph.",
            required=True,
        ),
        ToolParameter(
            name="max_depth",
            type=ParameterType.INTEGER,
            description="How many hops to traverse from direct matches. Default: 1.",
            required=False,
            default=1,
        ),
        ToolParameter(
            name="top_k",
            type=ParameterType.INTEGER,
            description="Number of direct matches to return. Default: 5.",
            required=False,
            default=5,
        ),
    ],
)


def _format_traversal_result(result: Any) -> str:
    """Format a traversal result for display."""
    content_preview = result.node.content[:120]
    if len(result.node.content) > 120:
        content_preview += "..."
    path_str = " ".join(result.path_relations) if result.path_relations else ""
    return (
        f"  [{result.node.type}] {result.node.label} (depth: {result.depth}, score: {result.relevance_score:.3f})\n"
        f"    Content: {content_preview}\n"
        f"    Path: {path_str}\n"
        f"    ID: {result.node.id} | Accessed: {result.node.access_count}x"
    )


class SearchMemoryGraphTool(AsyncToolInterface):
    """Search memory graph with embedding similarity and graph traversal."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "search_memory_graph"
        self.description = SEARCH_MEMORY_GRAPH_SCHEMA.description
        self._schema = SEARCH_MEMORY_GRAPH_SCHEMA

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query")
        if not query:
            return self._format_result(success=False, error="query is required")

        root_dir = self.root_dir or "."
        max_depth = kwargs.get("max_depth", 1)
        top_k = kwargs.get("top_k", 5)

        try:
            query_embedding = await fetch_embedding(query)
            search_result = await search_graph(
                root_dir=root_dir,
                query_embedding=query_embedding,
                max_depth=max_depth,
                top_k=top_k,
            )

            if not search_result.direct:
                return self._format_result(
                    success=True,
                    result=f'No memory nodes found for: "{query}"\nGraph has {search_result.total_nodes} nodes, {search_result.total_edges} edges.',
                )

            sections = [
                f'Memory Graph Search: "{query}"',
                f"Graph: {search_result.total_nodes} nodes, {search_result.total_edges} edges\n",
                "Direct Matches:",
            ]
            for hit in search_result.direct:
                sections.append(_format_traversal_result(hit))

            if search_result.neighbors:
                sections.append("\nLinked Neighbors:")
                for neighbor in search_result.neighbors:
                    sections.append(_format_traversal_result(neighbor))

            return self._format_result(success=True, result="\n".join(sections))
        except Exception as e:
            _logger.error(f"search_memory_graph failed: {e}")
            return self._format_result(success=False, error=str(e))
# In-memory property graph with JSON persistence for memory nodes
# FEATURE: Memory graph with traversal, decay scoring, and auto-similarity edges

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

NodeType = Literal["concept", "file", "symbol", "note"]
RelationType = Literal["relates_to", "depends_on", "implements", "references", "similar_to", "contains"]

CACHE_DIR = ".mindflow_contextplus"
GRAPH_FILE = "memory-graph.json"
DECAY_LAMBDA = 0.05
SIMILARITY_THRESHOLD = 0.72
STALE_THRESHOLD = 0.15


@dataclass
class MemoryNode:
    """A single node in the memory graph."""

    id: str
    type: NodeType
    label: str
    content: str
    embedding: list[float]
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 1
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "content": self.content,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MemoryNode:
        return cls(
            id=data["id"],
            type=data["type"],
            label=data["label"],
            content=data["content"],
            embedding=data.get("embedding", []),
            created_at=data.get("created_at", time.time()),
            last_accessed=data.get("last_accessed", time.time()),
            access_count=data.get("access_count", 1),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MemoryEdge:
    """A single edge in the memory graph."""

    id: str
    source: str
    target: str
    relation: RelationType
    weight: float = 1.0
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MemoryEdge:
        return cls(
            id=data["id"],
            source=data["source"],
            target=data["target"],
            relation=data["relation"],
            weight=data.get("weight", 1.0),
            created_at=data.get("created_at", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TraversalResult:
    """Result of a graph traversal operation."""

    node: MemoryNode
    depth: int
    path_relations: list[str]
    relevance_score: float


@dataclass
class GraphSearchResult:
    """Result of a graph search operation."""

    direct: list[TraversalResult]
    neighbors: list[TraversalResult]
    total_nodes: int
    total_edges: int


@dataclass
class GraphStore:
    """In-memory graph store with JSON persistence."""

    nodes: dict[str, MemoryNode] = field(default_factory=dict)
    edges: dict[str, MemoryEdge] = field(default_factory=dict)


_graph_cache: dict[str, GraphStore] = {}


def _generate_id(prefix: str) -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}-{int(time.time() * 1000)}-{os.urandom(3).hex()}"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    arr_a = np.array(a)
    arr_b = np.array(b)
    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))


def _decay_weight(edge: MemoryEdge) -> float:
    """Compute decayed weight for an edge."""
    days_since_creation = (time.time() - edge.created_at) / 86400
    return edge.weight * math.exp(-DECAY_LAMBDA * days_since_creation)


def _get_cache_dir(root_dir: str) -> str:
    """Get the cache directory path."""
    return os.path.join(root_dir, CACHE_DIR)


def _get_graph_path(root_dir: str) -> str:
    """Get the graph file path."""
    return os.path.join(_get_cache_dir(root_dir), GRAPH_FILE)


async def _load_graph(root_dir: str) -> GraphStore:
    """Load graph from disk or cache."""
    if root_dir in _graph_cache:
        return _graph_cache[root_dir]

    graph_path = _get_graph_path(root_dir)
    store = GraphStore()

    try:
        if os.path.exists(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            nodes_raw = raw.get("nodes", {})
            edges_raw = raw.get("edges", {})
            store.nodes = {k: MemoryNode.from_dict(v) for k, v in nodes_raw.items()}
            store.edges = {k: MemoryEdge.from_dict(v) for k, v in edges_raw.items()}
    except Exception:
        pass

    _graph_cache[root_dir] = store
    return store


async def _persist_graph(root_dir: str) -> None:
    """Persist graph to disk."""
    store = _graph_cache.get(root_dir)
    if not store:
        return

    cache_dir = _get_cache_dir(root_dir)
    os.makedirs(cache_dir, exist_ok=True)

    graph_path = _get_graph_path(root_dir)
    data = {
        "nodes": {k: v.to_dict() for k, v in store.nodes.items()},
        "edges": {k: v.to_dict() for k, v in store.edges.items()},
    }

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get_edges_for_node(store: GraphStore, node_id: str) -> list[MemoryEdge]:
    """Get all edges connected to a node."""
    return [e for e in store.edges.values() if e.source == node_id or e.target == node_id]


def _get_neighbor_id(edge: MemoryEdge, from_id: str) -> str:
    """Get the neighbor node ID from an edge."""
    return edge.target if edge.source == from_id else edge.source


async def upsert_node(
    root_dir: str,
    node_type: NodeType,
    label: str,
    content: str,
    embedding: list[float],
    metadata: dict[str, str] | None = None,
) -> MemoryNode:
    """Create or update a memory node."""
    store = await _load_graph(root_dir)

    existing = next((n for n in store.nodes.values() if n.label == label and n.type == node_type), None)

    if existing:
        existing.content = content
        existing.last_accessed = time.time()
        existing.access_count += 1
        if metadata:
            existing.metadata.update(metadata)
        existing.embedding = embedding
        await _persist_graph(root_dir)
        return existing

    node = MemoryNode(
        id=_generate_id("mn"),
        type=node_type,
        label=label,
        content=content,
        embedding=embedding,
        metadata=metadata or {},
    )
    store.nodes[node.id] = node
    await _persist_graph(root_dir)
    return node


async def create_relation(
    root_dir: str,
    source_id: str,
    target_id: str,
    relation: RelationType,
    weight: float = 1.0,
    metadata: dict[str, str] | None = None,
) -> MemoryEdge | None:
    """Create a relation between two memory nodes."""
    store = await _load_graph(root_dir)

    if source_id not in store.nodes or target_id not in store.nodes:
        return None

    existing = next(
        (e for e in store.edges.values() if e.source == source_id and e.target == target_id and e.relation == relation),
        None,
    )

    if existing:
        existing.weight = weight
        existing.metadata.update(metadata or {})
        await _persist_graph(root_dir)
        return existing

    edge = MemoryEdge(
        id=_generate_id("me"),
        source=source_id,
        target=target_id,
        relation=relation,
        weight=weight,
        metadata=metadata or {},
    )
    store.edges[edge.id] = edge
    await _persist_graph(root_dir)
    return edge


async def search_graph(
    root_dir: str,
    query_embedding: list[float],
    max_depth: int = 1,
    top_k: int = 5,
    edge_filter: list[RelationType] | None = None,
) -> GraphSearchResult:
    """Search the memory graph by embedding similarity."""
    store = await _load_graph(root_dir)

    scored: list[tuple[MemoryNode, float]] = []
    for node in store.nodes.values():
        if node.embedding:
            sim = _cosine_similarity(query_embedding, node.embedding)
            if sim > 0:
                scored.append((node, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_nodes = scored[:top_k]

    direct_results = [
        TraversalResult(
            node=node,
            depth=0,
            path_relations=[],
            relevance_score=score,
        )
        for node, score in top_nodes
    ]

    neighbor_results: list[TraversalResult] = []
    visited = {node.id for node, _ in top_nodes}

    for node, base_score in top_nodes:
        queue = [(node.id, 0, [])]
        while queue:
            current_id, depth, path = queue.pop(0)
            if depth >= max_depth:
                continue

            edges = _get_edges_for_node(store, current_id)
            for edge in edges:
                if edge_filter and edge.relation not in edge_filter:
                    continue
                neighbor_id = _get_neighbor_id(edge, current_id)
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)

                neighbor_node = store.nodes.get(neighbor_id)
                if not neighbor_node:
                    continue

                decayed = _decay_weight(edge)
                score = base_score * decayed * (1.0 / (depth + 1))

                neighbor_results.append(
                    TraversalResult(
                        node=neighbor_node,
                        depth=depth + 1,
                        path_relations=[*path, edge.relation],
                        relevance_score=score,
                    )
                )
                queue.append((neighbor_id, depth + 1, [*path, edge.relation]))

    neighbor_results.sort(key=lambda x: x.relevance_score, reverse=True)

    return GraphSearchResult(
        direct=direct_results,
        neighbors=neighbor_results,
        total_nodes=len(store.nodes),
        total_edges=len(store.edges),
    )


async def get_graph_stats(root_dir: str) -> dict[str, int]:
    """Get graph statistics."""
    store = await _load_graph(root_dir)
    return {
        "nodes": len(store.nodes),
        "edges": len(store.edges),
    }


async def prune_stale_links(root_dir: str, threshold: float = STALE_THRESHOLD) -> int:
    """Remove stale edges with decayed weights."""
    store = await _load_graph(root_dir)
    to_remove = [
        edge_id for edge_id, edge in store.edges.items()
        if _decay_weight(edge) < threshold
    ]
    for edge_id in to_remove:
        del store.edges[edge_id]
    await _persist_graph(root_dir)
    return len(to_remove)
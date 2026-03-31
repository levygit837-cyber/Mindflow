"""Memory tools for MindFlow agents.

Provides tools for agents to interact with the memory system:
- store_fact: Save facts, notes, procedures, context to AgenticMemoryStore
- search_facts: Semantic search across stored facts
- retrieve_task_context: Retrieve context from other tasks (cross-task)
- recall_session_memory: Search session memory semantically
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.memory_integration import recall_memory
from mindflow_backend.schemas.tools.base import (
    ParameterType,
    ToolParameter,
    ToolSchema,
)

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

STORE_FACT_SCHEMA = ToolSchema(
    name="store_fact",
    description=(
        "Store a fact, note, procedure, or context in the agent's long-term memory. "
        "Use this to remember important information for future sessions."
    ),
    category="memory",
    parameters=[
        ToolParameter(name="content", type=ParameterType.STRING, description="The content to store", required=True),
        ToolParameter(name="fact_type", type=ParameterType.STRING, description="Type of memory: fact, about, procedure, or context", required=False, default="fact"),
        ToolParameter(name="key", type=ParameterType.STRING, description="A short key/title for this memory item", required=False, default=""),
        ToolParameter(name="namespace", type=ParameterType.STRING, description="Optional namespace to organize memories", required=False, default="general"),
    ],
)

SEARCH_FACTS_SCHEMA = ToolSchema(
    name="search_facts",
    description=(
        "Search the agent's long-term memory for stored facts, notes, and procedures. "
        "Uses semantic search to find relevant memories."
    ),
    category="memory",
    parameters=[
        ToolParameter(name="query", type=ParameterType.STRING, description="Search query to find relevant memories", required=True),
        ToolParameter(name="fact_type", type=ParameterType.STRING, description="Filter by type: fact, about, procedure, context, or all", required=False, default="all"),
        ToolParameter(name="limit", type=ParameterType.INTEGER, description="Maximum number of results", required=False, default=5),
    ],
)

RETRIEVE_TASK_CONTEXT_SCHEMA = ToolSchema(
    name="retrieve_task_context",
    description=(
        "Retrieve context from another task or sub-task. "
        "Use this to access results and context from sibling or parent tasks during execution."
    ),
    category="memory",
    parameters=[
        ToolParameter(name="query", type=ParameterType.STRING, description="Search query to find relevant task context", required=True),
        ToolParameter(name="session_id", type=ParameterType.STRING, description="Session ID to search within", required=False, default=""),
        ToolParameter(name="limit", type=ParameterType.INTEGER, description="Maximum number of results", required=False, default=5),
    ],
)

RECALL_SESSION_MEMORY_SCHEMA = ToolSchema(
    name="recall_session_memory",
    description=(
        "Search session memory for past interactions. "
        "Retrieves semantically similar messages from current or all sessions."
    ),
    category="memory",
    parameters=[
        ToolParameter(name="query", type=ParameterType.STRING, description="Search query", required=True),
        ToolParameter(name="cross_session", type=ParameterType.BOOLEAN, description="Search across all sessions (True) or only current session (False)", required=False, default=False),
        ToolParameter(name="limit", type=ParameterType.INTEGER, description="Maximum number of results", required=False, default=5),
    ],
)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


class StoreFactTool(AsyncToolInterface):
    """Store facts/notes/procedures in long-term memory."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "store_fact"
        self.description = STORE_FACT_SCHEMA.description
        self._schema = STORE_FACT_SCHEMA

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        content = kwargs.get("content", "")
        fact_type = kwargs.get("fact_type", "fact")
        key = kwargs.get("key", "")
        namespace = kwargs.get("namespace", "general")

        if not content:
            return {"success": False, "error": "content is required"}

        try:
            from mindflow_backend.memory.agent_memory.store import AgenticMemoryStore
            store = AgenticMemoryStore()
            await store.initialize()

            result = await store.put(
                namespace_type=fact_type,
                key=key or content[:50],
                content=content,
                metadata={"namespace": namespace, "fact_type": fact_type},
            )

            return {
                "success": True,
                "fact_type": fact_type,
                "key": key or content[:50],
                "stored": True,
                "result": str(result) if result else "stored",
            }
        except Exception as exc:
            _logger.error("store_fact_failed", error=str(exc))
            return {"success": False, "error": str(exc)}

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()


class SearchFactsTool(AsyncToolInterface):
    """Search long-term memory for stored facts."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "search_facts"
        self.description = SEARCH_FACTS_SCHEMA.description
        self._schema = SEARCH_FACTS_SCHEMA

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query", "")
        fact_type = kwargs.get("fact_type", "all")
        limit = int(kwargs.get("limit", 5))

        if not query:
            return {"success": False, "error": "query is required"}

        try:
            from mindflow_backend.memory.agent_memory.store import AgenticMemoryStore
            store = AgenticMemoryStore()
            await store.initialize()

            if fact_type == "all":
                # Search across all types
                all_results = []
                for ns_type in ["fact", "about", "procedure", "context"]:
                    results = await store.search(namespace_type=ns_type, query=query, limit=limit)
                    for r in results:
                        all_results.append({"type": ns_type, **r})
                # Sort by score if available, take top N
                all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
                return {"success": True, "results": all_results[:limit], "count": len(all_results[:limit])}
            else:
                results = await store.search(namespace_type=fact_type, query=query, limit=limit)
                return {"success": True, "results": results, "count": len(results)}

        except Exception as exc:
            _logger.error("search_facts_failed", error=str(exc))
            return {"success": False, "error": str(exc), "results": []}

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()


class RetrieveTaskContextTool(AsyncToolInterface):
    """Retrieve context from other tasks (cross-task)."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "retrieve_task_context"
        self.description = RETRIEVE_TASK_CONTEXT_SCHEMA.description
        self._schema = RETRIEVE_TASK_CONTEXT_SCHEMA

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query", "")
        session_id = kwargs.get("session_id", "")
        limit = int(kwargs.get("limit", 5))

        if not query:
            return {"success": False, "error": "query is required"}

        try:
            from mindflow_backend.memory.task_memory.service import TaskMemoryService
            from mindflow_backend.storage import db_session

            service = TaskMemoryService()
            async with db_session() as db:
                results = await service.search_tasks(
                    db,
                    query=query,
                    session_id=session_id or None,
                    limit=limit,
                )
                return {"success": True, "results": results, "count": len(results)}

        except Exception as exc:
            _logger.error("retrieve_task_context_failed", error=str(exc))
            return {"success": False, "error": str(exc), "results": []}

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()


class RecallSessionMemoryTool(AsyncToolInterface):
    """Search session memory semantically."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "recall_session_memory"
        self.description = RECALL_SESSION_MEMORY_SCHEMA.description
        self._schema = RECALL_SESSION_MEMORY_SCHEMA

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query", "")
        cross_session = bool(kwargs.get("cross_session", False))
        limit = int(kwargs.get("limit") or 5)

        if not query:
            return {"success": False, "error": "query is required"}

        try:
            session_id = getattr(self, "session_id", "") or ""
            result = await recall_memory(
                session_id=session_id,
                query=query,
                agent_id="tool:recall_session_memory",
                limit=limit,
                cross_session=cross_session,
            )

            hits = [
                hit.model_dump() if hasattr(hit, "model_dump") else dict(hit)
                for hit in result.hits
            ]
            message_hits = [
                hit for hit in hits if str(hit.get("source_type")) != "session_block"
            ]
            block_hits = [
                hit for hit in hits if str(hit.get("source_type")) == "session_block"
            ]

            return {
                "success": True,
                "context": result.context,
                "hits": hits,
                "message_hits": message_hits,
                "block_hits": block_hits,
                "references": result.references,
                "count": result.hit_count or len(hits) or len(result.references),
                "best_score": result.best_score,
                "grounding_recommended": result.grounding_recommended,
                "filtered_hits_count": result.filtered_hits_count,
                "scope_used": str(result.scope_used),
                "cross_session": cross_session,
            }

        except Exception as exc:
            _logger.error("recall_session_memory_failed", error=str(exc))
            return {"success": False, "error": str(exc), "results": []}

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()

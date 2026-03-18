"""Canonical orchestrator memory shim."""

from __future__ import annotations

import re
from typing import Any, Tuple

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory import get_memory_service
from mindflow_backend.schemas.memory.contracts import (
    AgentMemorySnapshot as _CanonicalAgentMemorySnapshot,
    MemoryPersistResult as _CanonicalMemoryPersistResult,
    MemoryRecallRequest as _CanonicalMemoryRecallRequest,
    MemoryRecallResponse as _CanonicalMemoryRecallResponse,
    MemoryRecallScope,
    MemorySourceType,
)

_logger = get_logger(__name__)


def _get_db_session_factory():
    from mindflow_backend.infra.database.connection import get_db_session

    return get_db_session


class MemoryPersistResult(_CanonicalMemoryPersistResult):
    """Backward-compatible alias to the canonical persist result."""


class MemoryRecallRequest(_CanonicalMemoryRecallRequest):
    """Orchestrator-flavoured recall request with plan defaults."""

    top_k: int = 4
    min_score: float = 0.35
    top_k_messages: int = 4
    top_k_blocks: int = 2


class MemoryRecallResponse(_CanonicalMemoryRecallResponse):
    """Backward-compatible alias to the canonical recall response."""


class AgentMemorySnapshot(_CanonicalAgentMemorySnapshot):
    """Backward-compatible alias to the canonical agent snapshot."""


async def recall_memory(
    *,
    session_id: str,
    query: str,
    agent_id: str = "orchestrator",
    limit: int = 4,
    cross_session: bool = False,
    min_score: float = 0.35,
    category_filters: list[str] | None = None,
    include_messages: bool = True,
    include_blocks: bool = True,
    top_k_messages: int | None = None,
    top_k_blocks: int | None = None,
    exclude_session_id: str | None = None,
) -> MemoryRecallResponse:
    """Query the canonical memory facade with the orchestrator defaults."""
    service = get_memory_service()
    request = MemoryRecallRequest(
        session_id=session_id,
        query=query,
        agent_id=agent_id,
        top_k=limit,
        cross_session=cross_session,
        min_score=min_score,
        scope=(
            MemoryRecallScope.CROSS_SESSION
            if cross_session
            else MemoryRecallScope.CURRENT_SESSION
        ),
        category_filters=category_filters or [],
        include_messages=include_messages,
        include_blocks=include_blocks,
        top_k_messages=top_k_messages or limit,
        top_k_blocks=top_k_blocks or 2,
        exclude_session_id=exclude_session_id,
    )
    response = await service.recall(request)
    if isinstance(response, MemoryRecallResponse):
        return response
    return MemoryRecallResponse.model_validate(response.model_dump())


class MemoryIntegration:
    """Adaptive orchestrator shim backed by the canonical memory facade."""

    async def _recall_session(
        self,
        *,
        session_id: str,
        query: str,
        top_k: int,
        min_score: float,
        top_k_messages: int,
        top_k_blocks: int,
        category_filters: list[str] | None = None,
        agent_id: str = "orchestrator",
    ) -> list[dict[str, Any]]:
        response = await recall_memory(
            session_id=session_id,
            query=query,
            agent_id=agent_id,
            limit=top_k,
            cross_session=False,
            min_score=min_score,
            category_filters=category_filters,
            include_messages=True,
            include_blocks=True,
            top_k_messages=top_k_messages,
            top_k_blocks=top_k_blocks,
        )
        return self._extract_hits(response)

    async def _recall_cross_session(
        self,
        *,
        query: str,
        top_k: int,
        min_score: float,
        top_k_messages: int,
        top_k_blocks: int,
        exclude_session_id: str | None = None,
        category_filters: list[str] | None = None,
        agent_id: str = "orchestrator",
    ) -> list[dict[str, Any]]:
        response = await recall_memory(
            session_id=exclude_session_id or "",
            query=query,
            agent_id=agent_id,
            limit=top_k,
            cross_session=True,
            min_score=min_score,
            exclude_session_id=exclude_session_id,
            category_filters=category_filters,
            include_messages=True,
            include_blocks=True,
            top_k_messages=top_k_messages,
            top_k_blocks=top_k_blocks,
        )
        return self._extract_hits(response)

    async def recall(self, request: MemoryRecallRequest) -> MemoryRecallResponse:
        """Adaptive recall: current session first, then cross-session fallback."""
        if request.cross_session or request.scope == MemoryRecallScope.CROSS_SESSION:
            cross_hits = await self._recall_cross_session(
                query=request.query,
                top_k=request.top_k,
                min_score=request.min_score,
                top_k_messages=request.top_k_messages,
                top_k_blocks=request.top_k_blocks,
                exclude_session_id=request.exclude_session_id or request.session_id,
                category_filters=request.category_filters,
                agent_id=request.agent_id,
            )
            return self._build_response(
                hits=cross_hits,
                fallback_used=True,
                scope_used=MemoryRecallScope.CROSS_SESSION,
            )

        session_hits = await self._recall_session(
            session_id=request.session_id,
            query=request.query,
            top_k=request.top_k,
            min_score=request.min_score,
            top_k_messages=request.top_k_messages,
            top_k_blocks=request.top_k_blocks,
            category_filters=request.category_filters,
            agent_id=request.agent_id,
        )
        best_score = max((float(hit.get("score", 0.0)) for hit in session_hits), default=0.0)
        session_hit_count = len(session_hits)

        should_fallback = (
            request.scope != MemoryRecallScope.CURRENT_SESSION
            and str(request.policy) != "session_only"
            and request.cross_session_fallback
            and (
                session_hit_count < request.cross_session_min_hits
                or best_score < request.fallback_score_threshold
            )
        )

        if should_fallback:
            cross_hits = await self._recall_cross_session(
                query=request.query,
                top_k=request.top_k,
                min_score=request.min_score,
                top_k_messages=request.top_k_messages,
                top_k_blocks=request.top_k_blocks,
                exclude_session_id=request.session_id,
                category_filters=request.category_filters,
                agent_id=request.agent_id,
            )
            if cross_hits:
                return self._build_response(
                    hits=cross_hits,
                    fallback_used=True,
                    scope_used=MemoryRecallScope.CROSS_SESSION,
                )

        return self._build_response(
            hits=session_hits,
            fallback_used=False,
            scope_used=MemoryRecallScope.CURRENT_SESSION,
        )

    async def record_message(
        self,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
        idempotency_key: str | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> MemoryPersistResult:
        service = get_memory_service()
        async with _get_db_session_factory()() as db:
            result = await service.record_message(
                db,
                session_id=session_id,
                agent_id=agent_id,
                role=role,
                content=content,
                source_message_id=source_message_id,
                idempotency_key=idempotency_key,
                source_status=source_status,
                derived_from_recall=derived_from_recall,
            )
        if isinstance(result, MemoryPersistResult):
            return result
        return MemoryPersistResult.model_validate(result.model_dump())

    async def get_agent_snapshot(
        self,
        session_id: str,
        agent_id: str,
        token_limit: int | None = None,
    ) -> AgentMemorySnapshot:
        result = await get_memory_service().get_agent_snapshot(
            session_id=session_id,
            agent_id=agent_id,
            token_limit=token_limit,
        )
        if isinstance(result, AgentMemorySnapshot):
            return result
        return AgentMemorySnapshot.model_validate(result.model_dump())

    def format_context(self, response: MemoryRecallResponse) -> str:
        """Render a single `Memory Context` block or an empty string."""
        if response.context.strip():
            return response.context
        if not response.hits:
            return ""
        return self._format_hits(self._extract_hits(response), crossed_session=response.crossed_session)

    def infer_categories(self, query: str) -> list[str]:
        lowered = query.lower()
        categories: list[str] = []
        if re.search(r"\b(decis[aã]o|decis(?:ion|ions)|definimos)\b", lowered):
            categories.append("decision")
        if re.search(r"\b(debug|erro|bug|falha|corrig)\b", lowered):
            categories.append("debugging")
        if re.search(r"\b(implement|c[oó]digo|migration|schema|endpoint)\b", lowered):
            categories.append("implementation")
        if re.search(r"\b(teste|pytest|valida)\b", lowered):
            categories.append("testing")
        if re.search(r"\b(pesquisa|research|benchmark|investig)\b", lowered):
            categories.append("research")
        return categories

    def _build_response(
        self,
        *,
        hits: list[dict[str, Any]],
        fallback_used: bool,
        scope_used: MemoryRecallScope,
    ) -> MemoryRecallResponse:
        best_score = max(
            (float(hit.get("final_score", hit.get("score", 0.0))) for hit in hits),
            default=0.0,
        )
        references = [str(hit.get("reference")) for hit in hits if hit.get("reference")]
        context = self._format_hits(
            hits,
            crossed_session=fallback_used or scope_used == MemoryRecallScope.CROSS_SESSION,
        )
        return MemoryRecallResponse(
            context=context,
            references=references,
            hit_count=len(hits),
            hits=hits,
            best_score=best_score,
            grounding_recommended=(
                best_score >= 0.72
                or any(bool(hit.get("answer_bearing")) for hit in hits)
            ),
            scope_used=scope_used,
            fallback_used=fallback_used,
            metadata={
                "result_count": len(hits),
                "best_score": best_score,
                "scope_used": scope_used,
                "fallback_used": fallback_used,
            },
        )

    def _extract_hits(self, response: MemoryRecallResponse) -> list[dict[str, Any]]:
        if response.hits:
            extracted: list[dict[str, Any]] = []
            for hit in response.hits:
                if hasattr(hit, "model_dump"):
                    extracted.append(hit.model_dump())
                else:
                    extracted.append(dict(hit))
            return extracted

        hits: list[dict[str, Any]] = []
        references = list(response.references)
        for line in response.context.splitlines():
            stripped = line.strip()
            if not stripped or stripped.lower().startswith("memory context"):
                continue
            if stripped.startswith("- "):
                stripped = stripped[2:].strip()
            hit: dict[str, Any] = {"content": stripped, "score": response.best_score}
            if references:
                hit["reference"] = references.pop(0)
            hits.append(hit)
        return hits

    def _format_hits(self, hits: list[dict[str, Any]], *, crossed_session: bool) -> str:
        if not hits:
            return ""
        session_label = "cross-session" if crossed_session else "session"
        lines = ["Memory Context:"]
        for hit in hits:
            source_type = str(hit.get("source_type", MemorySourceType.SESSION_MESSAGE.value))
            if source_type == MemorySourceType.SESSION_BLOCK.value:
                category = hit.get("category") or "general"
                title = hit.get("title") or "Session block"
                summary = hit.get("summary_md") or hit.get("content") or hit.get("content_excerpt") or ""
                if summary:
                    lines.append(f"- [{session_label}:block:{category}] {title}: {summary}")
                continue

            content = str(hit.get("content") or hit.get("content_excerpt") or "").strip()
            if content:
                lines.append(f"- [{session_label}] {content}")
        return "\n".join(lines)


_memory_integration: MemoryIntegration | None = None


def get_memory_integration() -> MemoryIntegration:
    global _memory_integration
    if _memory_integration is None:
        _memory_integration = MemoryIntegration()
    return _memory_integration


async def get_context_for_agent(
    session_id: str,
    query: str,
    token_range: Tuple[int, int] | None = None,
    limit: int = 4,
) -> str:
    del token_range
    mi = get_memory_integration()
    response = await mi.recall(
        MemoryRecallRequest(
            session_id=session_id,
            query=query,
            agent_id="orchestrator",
            top_k=limit,
            category_filters=mi.infer_categories(query),
        )
    )
    return mi.format_context(response)


async def store_orchestrator_interaction(
    session_id: str,
    agent_id: str,
    message: str,
    response: str,
    token_start: int,
    token_end: int,
) -> tuple[str | None, str | None]:
    del token_start, token_end
    mi = get_memory_integration()
    user_result = await mi.record_message(
        session_id=session_id,
        agent_id="user",
        role="user",
        content=message,
    )
    assistant_result = await mi.record_message(
        session_id=session_id,
        agent_id=agent_id,
        role="assistant",
        content=response,
    )
    return user_result.embedding_id, assistant_result.embedding_id


async def get_token_range_context(
    session_id: str,
    start_token: int,
    end_token: int,
) -> str:
    del start_token, end_token
    return await get_context_for_agent(session_id=session_id, query="", limit=4)

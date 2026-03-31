"""ContextAwareResolver — executes a sub-task with semantic context enrichment.

Steps:
1. Resolve direct dependency contexts
2. Semantic search for related prior task outputs
3. Wait for missing dependencies (with timeout)
4. Build combined context string
5. Execute task via the assigned agent
6. Store result in the semantic context store
"""

from __future__ import annotations

# TYPE-ONLY import — actual value is loaded lazily inside _ensure_initialized
# to avoid pulling sentence_transformers at module load time.
from typing import TYPE_CHECKING, Any

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.decomposition.engine import TaskResolver
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import SubTaskContract
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode

if TYPE_CHECKING:
    from mindflow_backend.orchestrator.semantic_context_manager import ContextMatch

_logger = get_logger(__name__)


class _ContextResolution:
    """Internal representation of resolved context for a task."""

    def __init__(
        self,
        context_found: bool,
        semantic_matches: list[ContextMatch],
        dependency_contexts: list[ContextMatch],
        wait_required: bool = False,
        missing_dependencies: list[str] | None = None,
    ) -> None:
        self.context_found = context_found
        self.semantic_matches = semantic_matches
        self.dependency_contexts = dependency_contexts
        self.wait_required = wait_required
        self.missing_dependencies = missing_dependencies or []


class ContextAwareResolver(TaskResolver):
    """Resolver that enriches each sub-task with semantic context before execution."""

    def __init__(self) -> None:
        self.context_manager = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        from mindflow_backend.orchestrator.semantic_context_manager import (
            get_semantic_context_manager,  # noqa: PLC0415
        )
        self.context_manager = await get_semantic_context_manager()
        self._initialized = True
        settings = get_settings()
        self.context_similarity_threshold: float = getattr(
            settings, "context_similarity_threshold", 0.7
        )
        self.max_context_wait_time: int = getattr(
            settings, "max_context_wait_time", 30
        )
        self.enable_semantic_search: bool = getattr(
            settings, "enable_semantic_search", True
        )

    # ------------------------------------------------------------------
    # Public API (TaskResolver)
    # ------------------------------------------------------------------

    async def resolve(
        self,
        contract: SubTaskContract,
        prior_results: dict[str, str],
        provider: str,
        model: str,
        memory_context: str = "",
        session_id: str = "default",
        reflection_context: str = "",
    ) -> dict[str, Any]:
        await self._ensure_initialized()

        try:
            _logger.info(
                "resolver_start",
                task_id=str(contract.task_id),
                title=contract.title,
                agent=contract.owner_agent.value,
            )

            dep_resolution = await self._resolve_dependencies(contract, session_id)

            semantic_ctx: list[ContextMatch] = []
            if self.enable_semantic_search:
                semantic_ctx = await self._find_semantic_context(
                    contract, session_id, prior_results
                )

            if dep_resolution.wait_required:
                wait_result = await self._wait_for_dependencies(
                    contract, dep_resolution.missing_dependencies, session_id
                )
                if wait_result.get("status") == "timeout":
                    _logger.warning(
                        "resolver_dependency_timeout",
                        task_id=str(contract.task_id),
                    )

            combined_context = self._build_context(
                memory_context, dep_resolution, semantic_ctx, prior_results, reflection_context
            )

            task_result = await self._execute(contract, combined_context, provider, model)

            await self._store_context(contract, task_result, session_id)

            return {
                "task_id": str(contract.task_id),
                "title": contract.title,
                "result": task_result,
                "context_used": {
                    "dependency_contexts": len(dep_resolution.dependency_contexts),
                    "semantic_matches": len(semantic_ctx),
                    "combined_length": len(combined_context),
                },
                "dependencies_resolved": not dep_resolution.wait_required,
            }

        except Exception as exc:
            _logger.error(
                "resolver_failed",
                task_id=str(contract.task_id),
                error=str(exc),
            )
            raise RuntimeError(f"Context-aware resolution failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _resolve_dependencies(
        self,
        contract: SubTaskContract,
        session_id: str,
    ) -> _ContextResolution:
        if not contract.dependencies:
            return _ContextResolution(
                context_found=False,
                semantic_matches=[],
                dependency_contexts=[],
                wait_required=False,
            )
        try:
            dep_ids = [str(dep) for dep in contract.dependencies]
            dep_contexts = await self.context_manager.get_task_dependencies_context(
                task_id=str(contract.task_id),
                dependency_task_ids=dep_ids,
                session_id=session_id,
            )
            available = {ctx.task_id for ctx in dep_contexts}
            missing = set(dep_ids) - available
            return _ContextResolution(
                context_found=bool(dep_contexts),
                semantic_matches=[],
                dependency_contexts=dep_contexts,
                wait_required=bool(missing),
                missing_dependencies=list(missing),
            )
        except Exception as exc:
            _logger.error("resolver_dep_resolution_failed", error=str(exc))
            return _ContextResolution(False, [], [], False)

    async def _find_semantic_context(
        self,
        contract: SubTaskContract,
        session_id: str,
        prior_results: dict[str, str],
    ) -> list[ContextMatch]:
        try:
            query = f"{contract.title} {contract.scope}"
            matches = await self.context_manager.find_relevant_context(
                task_id=str(contract.task_id),
                query=query,
                session_id=session_id,
                limit=5,
            )
            dep_ids = {str(dep) for dep in contract.dependencies}
            return [
                m
                for m in matches
                if m.task_id != str(contract.task_id) and m.task_id not in dep_ids
            ]
        except Exception as exc:
            _logger.error("resolver_semantic_search_failed", error=str(exc))
            return []

    async def _wait_for_dependencies(
        self,
        contract: SubTaskContract,
        missing: list[str],
        session_id: str,
    ) -> dict[str, Any]:
        try:
            return await self.context_manager.wait_for_context(
                task_id=str(contract.task_id),
                required_context_ids=missing,
                session_id=session_id,
                timeout=self.max_context_wait_time,
            )
        except Exception as exc:
            _logger.error("resolver_wait_failed", error=str(exc))
            return {"status": "error", "error": str(exc)}

    def _build_context(
        self,
        memory_context: str,
        dep_resolution: _ContextResolution,
        semantic_ctx: list[ContextMatch],
        prior_results: dict[str, str],
        reflection_context: str = "",
    ) -> str:
        parts: list[str] = []
        if memory_context.strip():
            parts.append(f"## Memory Context\n{memory_context}")
        if reflection_context.strip():
            parts.append(f"## Orchestrator Reflection Context\n{reflection_context}")
        if prior_results:
            parts.append("\n## Previous Task Results")
            for tid, result in prior_results.items():
                parts.append(f"Task {tid}: {result[:500]}...")
        if dep_resolution.dependency_contexts:
            parts.append("\n## Dependency Context")
            for ctx in dep_resolution.dependency_contexts:
                parts.append(
                    f"From {ctx.agent_type} task {ctx.task_id}:\n{ctx.content}"
                )
        if semantic_ctx:
            parts.append("\n## Relevant Context")
            for m in semantic_ctx:
                parts.append(
                    f"From {m.agent_type} task {m.task_id} "
                    f"(similarity: {m.similarity:.2f}):\n{m.content}"
                )
        return "\n\n".join(parts)

    async def _execute(
        self,
        contract: SubTaskContract,
        context: str,
        provider: str,
        model: str,
    ) -> str:
        agent = get_agent(contract.owner_agent)
        system_prompt = agent.system_prompt
        if context.strip():
            system_prompt += f"\n\n## Available Context\n{context}"
        system_prompt += f"\n\n## Your Task\n{contract.scope}"

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Please complete this task: {contract.title}\n\n{contract.scope}",
            },
        ]

        settings = get_settings()
        sandbox_root = getattr(settings, "working_path", None)
        sandbox = MindFlowSandbox(
            root_dir=sandbox_root,
            read_only=(agent.sandbox == SandboxMode.READ_ONLY),
        )

        tools: list = []
        if agent.sandbox != SandboxMode.NONE:
            registry = create_default_registry(sandbox)
            tools = registry.get_tools_for_agent(agent)

        llm = get_model_for_provider(provider, model)
        if tools:
            llm = llm.bind_tools(tools)

        response = await llm.ainvoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    async def _store_context(
        self,
        contract: SubTaskContract,
        result: str,
        session_id: str,
    ) -> None:
        try:
            content = (
                f"Task: {contract.title}\n\n"
                f"Scope: {contract.scope}\n\n"
                f"Result: {result}"
            )
            await self.context_manager.store_task_context(
                task_id=str(contract.task_id),
                agent_type=contract.owner_agent.value,
                content=content,
                metadata={
                    "session_id": session_id,
                    "task_title": contract.title,
                    "agent_type": contract.owner_agent.value,
                    "priority": contract.priority,
                    "dependencies": [str(d) for d in contract.dependencies],
                    "expected_artifacts": contract.expected_artifacts,
                },
                dependencies=[str(d) for d in contract.dependencies],
            )
            await self.context_manager.update_task_status(
                task_id=str(contract.task_id),
                status="completed",
                session_id=session_id,
                completion_data={"result": result[:500]},
            )
        except Exception as exc:
            _logger.error("resolver_store_context_failed", error=str(exc))

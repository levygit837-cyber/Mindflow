"""EnhancedTasker — semantic-context-aware task decomposer.

Implements ``TaskDecomposer`` with semantic context integration and
multilingual embedding support.  The LLM response is validated against
``TASKER_VALIDATION_RULES`` before sub-tasks are constructed.
"""

from __future__ import annotations

import json
import uuid as _uuid
from typing import Any

from mindflow_backend.agents.prompts.specialized.tasker import (
    TASKER_SYSTEM_PROMPT,
    TASKER_USER_PROMPT_TEMPLATE,
    TASKER_VALIDATION_RULES,
)
from mindflow_backend.decomposition.engine import TaskDecomposer
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

# lazy import inside _ensure_initialized
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    ComponentOwner,
    MainTaskContract,
    SubTaskContract,
    SynthesisStrategy,
)
from mindflow_backend.utils.formatting import extract_json_from_response
from mindflow_backend.utils.validation import validate_task_dependencies

_logger = get_logger(__name__)


class EnhancedTasker(TaskDecomposer):
    """Task decomposer with semantic context awareness."""

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def decompose(
        self,
        message: str,
        session_id: str,
        complexity_score: float,
        provider: str | None = None,
        model: str | None = None,
        memory_context: str = "",
    ) -> tuple[MainTaskContract, list[SubTaskContract]]:
        """Decompose *message* into a MainTaskContract and sub-tasks."""
        await self._ensure_initialized()

        settings = get_settings()
        p = provider or settings.default_provider
        m = model or settings.default_model

        try:
            existing_context = await self._get_existing_context(message, session_id)

            llm = get_model_for_provider(p, m)
            user_prompt = TASKER_USER_PROMPT_TEMPLATE.format(
                user_message=message,
                memory_context=memory_context,
                semantic_context=existing_context,
            )
            messages = [
                {"role": "system", "content": TASKER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            response = await llm.ainvoke(messages)
            raw_content = response.content if hasattr(response, "content") else str(response)
            # VertexAI / some providers return a list of content blocks
            if isinstance(raw_content, list):
                content = " ".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in raw_content
                )
            else:
                content = raw_content

            data = self._validate_and_parse_response(content)

            main_id = _uuid.uuid4()
            goal = data.get("goal", message)
            raw_components_preview = data.get("components", [])
            subtask_titles = [
                c.get("title", f"Task {i + 1}")
                for i, c in enumerate(raw_components_preview[:5])
                if isinstance(c, dict)
            ]
            description = (
                f"User request: {message[:200]}. "
                f"Decomposed into {len(raw_components_preview)} subtask(s): "
                + ", ".join(f'"{t}"' for t in subtask_titles)
                + ("..." if len(raw_components_preview) > 5 else ".")
            )
            main = MainTaskContract(
                main_task_id=main_id,
                goal=goal,
                description=description,
                success_criteria=data.get("success_criteria", []),
                global_constraints=data.get("global_constraints", []),
                target_confidence=0.85,
                synthesis_strategy=SynthesisStrategy(
                    data.get("synthesis_strategy", "sequential_merge")
                ),
            )

            raw_components = data.get("components", [])
            component_ids = [_uuid.uuid4() for _ in raw_components]

            components: list[SubTaskContract] = []
            for idx, raw in enumerate(raw_components):
                deps: list[_uuid.UUID] = []
                for dep_idx in raw.get("dependencies", []):
                    if isinstance(dep_idx, int) and 0 <= dep_idx < len(component_ids):
                        deps.append(component_ids[dep_idx])

                owner = ComponentOwner.CODER
                raw_agent = raw.get("owner_agent", "coder")
                try:
                    owner = ComponentOwner(raw_agent)
                except ValueError:
                    _logger.warning("tasker_invalid_agent_type", agent=raw_agent)

                components.append(
                    SubTaskContract(
                        task_id=component_ids[idx],
                        parent_id=main_id,
                        title=raw.get("title", f"Task {idx + 1}"),
                        scope=raw.get("scope", ""),
                        dependencies=deps,
                        context_boundary=raw.get("context_boundary", ""),
                        allowed_inputs=raw.get("allowed_inputs", []),
                        forbidden_inputs=raw.get("forbidden_inputs", []),
                        expected_artifacts=raw.get("expected_artifacts", []),
                        owner_agent=owner,
                        priority=raw.get("priority", "medium"),
                        complexity_score=float(raw.get("complexity_score", 0.0) or 0.0),
                        complexity_reason=raw.get("complexity_reason", ""),
                    )
                )

            await self._store_decomposition_context(
                session_id=session_id,
                main_task_id=str(main_id),
                message=message,
                components=components,
                complexity_score=complexity_score,
            )
            await self._register_main_task(session_id, main, components)

            errors = validate_task_dependencies(components)
            if errors:
                _logger.warning("task_decomposition_cycle_detected", errors=errors)

            _logger.info(
                "enhanced_tasker_completed",
                session_id=session_id,
                tasks=len(components),
            )
            return main, components

        except Exception as exc:
            _logger.error("enhanced_tasker_failed", error=str(exc))
            return self._fallback_decomposition(message)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_existing_context(self, message: str, session_id: str) -> str:
        try:
            if not self.context_manager:
                return ""
            matches = await self.context_manager.find_relevant_context(
                task_id="decomposition",
                query=message,
                session_id=session_id,
                limit=5,
            )
            if not matches:
                return ""
            lines = [
                f"From {m.agent_type} task {m.task_id}: {m.content[:200]}..."
                for m in matches
            ]
            return "\n".join(lines)
        except Exception as exc:
            _logger.warning("tasker_context_fetch_failed", error=str(exc))
            return ""

    def _validate_and_parse_response(self, content: str) -> dict[str, Any]:
        try:
            json_str = extract_json_from_response(content)
            data = json.loads(json_str)

            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object")

            for field in TASKER_VALIDATION_RULES["required_fields"]:
                if field not in data:
                    data[field] = self._default_field(field)

            components = data.get("components", [])
            if not isinstance(components, list):
                raise ValueError("components must be a list")

            data["components"] = [
                self._validate_component(c) for c in components if isinstance(c, dict)
            ]
            return data

        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

    def _validate_component(self, comp: dict[str, Any]) -> dict[str, Any]:
        for field in TASKER_VALIDATION_RULES["component_fields"]:
            if field not in comp:
                comp[field] = self._default_component_field(field)

        valid_agents = TASKER_VALIDATION_RULES["valid_agents"]
        if comp.get("owner_agent") not in valid_agents:
            comp["owner_agent"] = "coder"

        if comp.get("priority") not in TASKER_VALIDATION_RULES["valid_priorities"]:
            comp["priority"] = "medium"

        try:
            comp["complexity_score"] = min(max(float(comp.get("complexity_score", 0.0) or 0.0), 0.0), 1.0)
        except (TypeError, ValueError):
            comp["complexity_score"] = 0.0

        return comp

    def _default_field(self, field: str) -> Any:
        return {
            "goal": "Process user request",
            "success_criteria": ["Task completed successfully"],
            "global_constraints": [],
            "synthesis_strategy": "sequential_merge",
            "components": [],
        }.get(field, "")

    def _default_component_field(self, field: str) -> Any:
        return {
            "title": "Untitled Task",
            "scope": "Complete the assigned work",
            "owner_agent": "coder",
            "dependencies": [],
            "context_boundary": "Standard task context",
            "expected_artifacts": ["Task completion"],
            "priority": "medium",
            "complexity_score": 0.0,
            "complexity_reason": "",
            "requires_context_sharing": False,
            "semantic_tags": [],
        }.get(field, "")

    def _fallback_decomposition(
        self, message: str
    ) -> tuple[MainTaskContract, list[SubTaskContract]]:
        _logger.info("tasker_using_fallback")
        main_id = _uuid.uuid4()
        comp_id = _uuid.uuid4()
        main = MainTaskContract(
            main_task_id=main_id,
            goal=message,
            description=f"Fallback single-task decomposition for: {message[:200]}",
            success_criteria=["Request processed"],
            global_constraints=[],
            target_confidence=0.5,
            synthesis_strategy=SynthesisStrategy.SEQUENTIAL_MERGE,
        )
        comp = SubTaskContract(
            task_id=comp_id,
            parent_id=main_id,
            title="Process Request",
            scope=message,
            dependencies=[],
            context_boundary="Standard processing",
            expected_artifacts=["Processed result"],
            owner_agent=ComponentOwner.CODER,
            priority="medium",
            complexity_score=0.4,
            complexity_reason="Fallback single comprehensive task",
        )
        return main, [comp]

    async def _register_main_task(
        self,
        session_id: str,
        main: MainTaskContract,
        components: list[SubTaskContract],
    ) -> None:
        """Register the MainTask and its SubTasks in the task registry."""
        try:
            if not self.context_manager:
                return
            await self.context_manager.register_main_task(
                session_id=session_id,
                main_contract=main,
                subtasks=components,
            )
        except Exception as exc:
            _logger.warning("tasker_register_main_task_failed", error=str(exc))

    async def _store_decomposition_context(
        self,
        session_id: str,
        main_task_id: str,
        message: str,
        components: list[SubTaskContract],
        complexity_score: float,
    ) -> None:
        try:
            if not self.context_manager:
                return
            summaries = [
                f"Task: {c.title}, Agent: {c.owner_agent.value}, "
                f"Priority: {c.priority}, Deps: {len(c.dependencies)}"
                for c in components
            ]
            content = (
                f"Original Request: {message}\n\n"
                f"Decomposed into {len(components)} tasks:\n"
                + "\n".join(summaries)
            )
            await self.context_manager.store_task_context(
                task_id=f"decomposition_{main_task_id}",
                agent_type="enhanced_tasker",
                content=content,
                metadata={
                    "session_id": session_id,
                    "main_task_id": main_task_id,
                    "complexity_score": complexity_score,
                    "component_count": len(components),
                },
            )
        except Exception as exc:
            _logger.warning("tasker_store_context_failed", error=str(exc))

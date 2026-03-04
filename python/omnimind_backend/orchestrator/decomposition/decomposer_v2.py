"""DT v2 Decomposer — breaks user messages into v2 contracts.

Implements DecomposerProtocol. Uses LLM to produce a MainComponentContract
and a list of SubComponentContracts. Falls back to a single-component
plan on parse errors.
"""

from __future__ import annotations

import json
import uuid as _uuid

from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    ComponentOwner,
    MainComponentContract,
    SubComponentContract,
    SynthesisStrategy,
)

_logger = get_logger(__name__)


_SYSTEM_PROMPT = """\
You are the OmniMind Decomposer v2. Break a complex request into structured components.

## Output Format
Return ONLY valid JSON with this schema:
{
  "goal": "High-level objective",
  "success_criteria": ["criterion 1", "criterion 2"],
  "global_constraints": ["constraint 1"],
  "synthesis_strategy": "sequential_merge",
  "components": [
    {
      "title": "Short title",
      "scope": "Detailed description of work to do",
      "owner_agent": "coder|analyst|researcher|arch_tech|critic",
      "dependencies": [],
      "context_boundary": "What context this component can access",
      "expected_artifacts": ["artifact 1"],
      "priority": "low|medium|high"
    }
  ]
}

## Rules
- Components must form a DAG (no cycles).
- Dependencies reference component indices (0-based).
- Assign the best agent personality for each component.
- Be specific in scope (mention files, patterns, tools).
- Keep components atomic and independently verifiable.
"""


class DecomposerV2:
    """DecomposerProtocol implementation for v2 contracts."""

    async def decompose(
        self,
        message: str,
        session_id: str,
        complexity_score: float,
        provider: str | None = None,
        model: str | None = None,
        memory_context: str = "",
    ) -> tuple[MainComponentContract, list[SubComponentContract]]:
        """Break a user message into a main contract and sub-components."""
        settings = get_settings()
        p = provider or settings.default_provider
        m = model or settings.default_model

        try:
            llm = get_model_for_provider(p, m)

            prompt = (
                f"{_SYSTEM_PROMPT}\n\n"
                f"Memory Context (if available):\n{memory_context}\n\n"
                f"Request: {message}"
            )

            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Parse JSON from response
            json_str = _extract_json(content)
            data = json.loads(json_str)

            main_id = _uuid.uuid4()
            main = MainComponentContract(
                main_component_id=main_id,
                goal=data.get("goal", message),
                success_criteria=data.get("success_criteria", []),
                global_constraints=data.get("global_constraints", []),
                target_confidence=0.85,
                synthesis_strategy=SynthesisStrategy(
                    data.get("synthesis_strategy", "sequential_merge")
                ),
            )

            raw_components = data.get("components", [])
            # First pass: assign UUIDs so we can resolve dependency indices
            component_ids = [_uuid.uuid4() for _ in raw_components]

            components: list[SubComponentContract] = []
            for idx, raw in enumerate(raw_components):
                # Resolve index-based dependencies to UUIDs
                deps: list[_uuid.UUID] = []
                for dep_idx in raw.get("dependencies", []):
                    if isinstance(dep_idx, int) and 0 <= dep_idx < len(component_ids):
                        deps.append(component_ids[dep_idx])

                owner = ComponentOwner.CODER
                try:
                    owner = ComponentOwner(raw.get("owner_agent", "coder"))
                except ValueError:
                    pass

                components.append(
                    SubComponentContract(
                        component_id=component_ids[idx],
                        parent_id=main_id,
                        title=raw.get("title", f"Component {idx + 1}"),
                        scope=raw.get("scope", raw.get("description", "")),
                        dependencies=deps,
                        context_boundary=raw.get("context_boundary", ""),
                        allowed_inputs=raw.get("allowed_inputs", []),
                        forbidden_inputs=raw.get("forbidden_inputs", []),
                        expected_artifacts=raw.get("expected_artifacts", []),
                        owner_agent=owner,
                        priority=raw.get("priority", "medium"),
                    )
                )

            return main, components

        except Exception as e:
            _logger.error("decomposer_v2_error", error=str(e))
            return _fallback(message)


def _extract_json(content: str) -> str:
    """Strip markdown code fences if present."""
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    return content.strip()


def _fallback(
    message: str,
) -> tuple[MainComponentContract, list[SubComponentContract]]:
    """Single-component fallback when decomposition fails."""
    main_id = _uuid.uuid4()
    comp_id = _uuid.uuid4()
    main = MainComponentContract(
        main_component_id=main_id,
        goal=message,
    )
    comp = SubComponentContract(
        component_id=comp_id,
        parent_id=main_id,
        title="Process request",
        scope=message,
        owner_agent=ComponentOwner.CODER,
    )
    return main, [comp]

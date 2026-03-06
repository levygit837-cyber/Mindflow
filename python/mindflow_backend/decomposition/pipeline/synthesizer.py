"""TaskSynthesizer — combines validated sub-task results into a SynthesisContract.

Uses an LLM to produce a coherent final answer with consistency checks.
Falls back to plain concatenation on LLM errors.
"""

from __future__ import annotations

import json
from uuid import UUID

from mindflow_backend.decomposition.engine import TaskSynthesizerBase
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    ConsistencyCheck,
    MainTaskContract,
    SynthesisContract,
    ValidatedTask,
)

_logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are the MindFlow Synthesizer. Combine validated sub-task results into a \
final, coherent response for the user.

## Output Format
Return ONLY valid JSON:
{
  "final_answer": "The complete, coherent response for the user",
  "consistency_checks": [
    {"check_name": "name", "passed": true, "details": "explanation"}
  ],
  "overall_confidence": 0.85,
  "open_risks": ["risk 1"]
}

## Rules
- Integrate all sub-task results into a flowing, natural response.
- Do NOT expose internal sub-task names or agent identities unless relevant.
- Evaluate whether results satisfy the success criteria.
- Be honest about gaps or risks.
- Maintain a professional, pragmatic engineering tone.
"""


class TaskSynthesizer(TaskSynthesizerBase):
    """LLM-powered synthesizer for the Task DAG pipeline."""

    async def synthesize(
        self,
        session_id: UUID,
        main_contract: MainTaskContract,
        validated_components: list[ValidatedTask],
        provider: str | None = None,
        model: str | None = None,
    ) -> SynthesisContract:
        """Produce a SynthesisContract from all validated sub-task results."""
        settings = get_settings()
        p = provider or settings.default_provider
        m = model or settings.default_model

        component_text = ""
        for vt in validated_components:
            component_text += (
                f"### {vt.title} (score: {vt.score:.2f})\n"
                f"{vt.summary}\n"
                f"Artifacts: {', '.join(vt.artifacts) or 'none'}\n\n"
            )

        prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Goal: {main_contract.goal}\n"
            f"Success Criteria: {', '.join(main_contract.success_criteria) or 'none specified'}\n"
            f"Global Constraints: {', '.join(main_contract.global_constraints) or 'none'}\n\n"
            f"Validated Sub-Tasks:\n{component_text}"
        )

        try:
            llm = get_model_for_provider(p, m)
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            json_str = _extract_json(content)
            data = json.loads(json_str)

            checks = [
                ConsistencyCheck(
                    check_name=c.get("check_name", "unknown"),
                    passed=bool(c.get("passed", False)),
                    details=c.get("details", ""),
                )
                for c in data.get("consistency_checks", [])
            ]

            return SynthesisContract(
                session_id=session_id,
                main_task_id=main_contract.main_task_id,
                validated_tasks=validated_components,
                global_consistency_checks=checks,
                final_answer=data.get("final_answer", ""),
                overall_confidence=float(data.get("overall_confidence", 0.0)),
                open_risks=data.get("open_risks", []),
            )

        except Exception as exc:
            _logger.error("synthesizer_error", error=str(exc))
            return _fallback(session_id, main_contract, validated_components)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json(content: str) -> str:
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    return content.strip()


def _fallback(
    session_id: UUID,
    main_contract: MainTaskContract,
    validated_components: list[ValidatedTask],
) -> SynthesisContract:
    parts = [f"Results for: {main_contract.goal}\n"]
    for vt in validated_components:
        parts.append(f"--- {vt.title} ---\n{vt.summary}")
    return SynthesisContract(
        session_id=session_id,
        main_task_id=main_contract.main_task_id,
        validated_tasks=validated_components,
        final_answer="\n\n".join(parts),
        overall_confidence=0.0,
    )

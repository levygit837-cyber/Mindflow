"""DT v2 Synthesizer — combines validated components into a final answer.

Implements SynthesizerProtocol. Uses LLM to produce a coherent
SynthesisContract with consistency checks and confidence scoring.
Falls back to concatenation on LLM errors.
"""

from __future__ import annotations

import json
from uuid import UUID

from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    ConsistencyCheck,
    MainComponentContract,
    SynthesisContract,
    ValidatedComponent,
)

_logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are the OmniMind Synthesizer v2. Combine validated sub-component results into a final answer.

## Input
You will receive the original goal, success criteria, and validated component results.

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
- Integrate all component results into a flowing, natural response.
- Do NOT mention internal sub-tasks or agents unless relevant.
- Evaluate if results satisfy the success criteria.
- Be honest about gaps or risks.
- Maintain a professional, pragmatic, senior engineering tone.
"""


class SynthesizerV2:
    """SynthesizerProtocol implementation for v2 contracts."""

    async def synthesize(
        self,
        session_id: UUID,
        main_contract: MainComponentContract,
        validated_components: list[ValidatedComponent],
        provider: str | None = None,
        model: str | None = None,
    ) -> SynthesisContract:
        """Combine validated components into a final synthesis."""
        settings = get_settings()
        p = provider or settings.default_provider
        m = model or settings.default_model

        # Build component summaries for the LLM
        component_text = ""
        for vc in validated_components:
            component_text += (
                f"### {vc.title} (score: {vc.score:.2f})\n"
                f"{vc.summary}\n"
                f"Artifacts: {', '.join(vc.artifacts) or 'none'}\n\n"
            )

        prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Goal: {main_contract.goal}\n"
            f"Success Criteria: {', '.join(main_contract.success_criteria) or 'none specified'}\n"
            f"Global Constraints: {', '.join(main_contract.global_constraints) or 'none'}\n\n"
            f"Validated Components:\n{component_text}"
        )

        try:
            llm = get_model_for_provider(p, m)
            response = await llm.ainvoke(prompt)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            json_str = _extract_json(content)
            data = json.loads(json_str)

            checks = [
                ConsistencyCheck(
                    check_name=c.get("check_name", "unknown"),
                    passed=c.get("passed", False),
                    details=c.get("details", ""),
                )
                for c in data.get("consistency_checks", [])
            ]

            return SynthesisContract(
                session_id=session_id,
                main_component_id=main_contract.main_component_id,
                validated_components=validated_components,
                global_consistency_checks=checks,
                final_answer=data.get("final_answer", ""),
                overall_confidence=float(data.get("overall_confidence", 0.0)),
                open_risks=data.get("open_risks", []),
            )

        except Exception as e:
            _logger.error("synthesizer_v2_error", error=str(e))
            return _fallback(session_id, main_contract, validated_components)


def _extract_json(content: str) -> str:
    """Strip markdown code fences if present."""
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    return content.strip()


def _fallback(
    session_id: UUID,
    main_contract: MainComponentContract,
    validated_components: list[ValidatedComponent],
) -> SynthesisContract:
    """Concatenation fallback when LLM synthesis fails."""
    parts = [
        f"Results for: {main_contract.goal}\n",
    ]
    for vc in validated_components:
        parts.append(f"--- {vc.title} ---\n{vc.summary}")

    return SynthesisContract(
        session_id=session_id,
        main_component_id=main_contract.main_component_id,
        validated_components=validated_components,
        final_answer="\n\n".join(parts),
        overall_confidence=0.0,
    )

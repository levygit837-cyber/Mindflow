"""Coding Task Chain - explicit workflow steps with preserved agent identity.

This chain is designed to turn a coding request into a structured workflow:
1) Analyst (optionally with Deep Analysis protocol) gathers code context.
2) Coder performs the implementation.
3) Analyst-as-Critic performs a focused code review.

The chain executes real agent calls (LLM + tools) and returns a final response
that the Orchestrator can stream back to the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.step_runner import run_workflow_step
from mindflow_backend.schemas.orchestration.workflow import WorkflowPlan, WorkflowStep

_logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CodingTaskChainConfig:
    chain_id: str = "coding_task"
    use_deep_analysis: bool = False
    max_context_chars_for_coder: int = 6_000


class CodingTaskChain:
    """Agent-driven coding workflow chain."""

    def __init__(self, config: CodingTaskChainConfig | None = None) -> None:
        self.config = config or CodingTaskChainConfig()
        self.settings = get_settings()

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the chain and return a context dict with `response`."""

        message: str = context.get("message") or ""
        if not message.strip():
            return {"response": "", "error": "CodingTaskChain requires non-empty `message`."}

        session_id: str = str(context.get("session_id") or "")
        provider: str = context.get("provider") or self.settings.default_provider
        model: str = context.get("model") or self.settings.default_model
        folder_path: str | None = context.get("folder_path")

        workflow_plan = WorkflowPlan.model_validate(context.get("workflow_plan") or {})
        steps = list(workflow_plan.steps)
        if not steps:
            return {"response": "", "error": "CodingTaskChain requires workflow_plan.steps."}

        analysis_step, implementation_step, review_step = steps

        analyst_result = await self._run_step(
            step=analysis_step,
            user_message=message,
            provider=provider,
            model=model,
            session_id=session_id,
            context_from_previous="",
            folder_path=folder_path,
        )

        if analyst_result.get("error"):
            return analyst_result

        analyst_summary: str = analyst_result.get("key_findings", "") or analyst_result.get("full_output", "")

        # Step 2: Coder implements using Analyst summary
        coder_context = analyst_summary[: self.config.max_context_chars_for_coder]
        coder_result = await self._run_step(
            step=implementation_step,
            user_message=message,
            provider=provider,
            model=model,
            session_id=session_id,
            context_from_previous=coder_context,
            folder_path=folder_path,
        )

        if coder_result.get("error"):
            return coder_result

        coder_output: str = coder_result.get("full_output", "")

        review_context = (
            "Resumo do Analyst (contexto do codebase):\n"
            f"{analyst_summary}\n\n"
            "Saída do Coder (implementação):\n"
            f"{coder_output}"
        )

        review_result = await self._run_step(
            step=review_step,
            user_message=message,
            provider=provider,
            model=model,
            session_id=session_id,
            context_from_previous=review_context,
            folder_path=folder_path,
        )

        if review_result.get("error"):
            # Still return coder output if review fails
            return {
                "response": coder_output,
                "error": f"Code review failed: {review_result['error']}",
                "chain": {
                    "analyst": analyst_result,
                    "coder": coder_result,
                    "review": review_result,
                },
            }

        review_output: str = review_result.get("full_output", "")

        final = (
            "## Implementação\n\n"
            f"{coder_output}\n\n"
            "## Code Review\n\n"
            f"{review_output}\n"
        )

        return {
            "response": final,
            "error": None,
            "chain": {
                "analyst": analyst_result,
                "coder": coder_result,
                "review": review_result,
            },
        }

    async def _run_step(
        self,
        *,
        step: WorkflowStep,
        user_message: str,
        provider: str,
        model: str,
        session_id: str,
        context_from_previous: str,
        folder_path: str | None = None,
    ) -> dict[str, Any]:
        """Run a canonical workflow step and return DelegationResult-like output."""

        result = await run_workflow_step(
            step=step,
            user_message=user_message,
            provider=provider,
            model=model,
            session_id=session_id,
            folder_path=folder_path,
            prior_context=context_from_previous,
        )
        if result.get("error"):
            _logger.error("coding_task_chain_step_failed", agent_id=step.agent_id, error=result["error"])
            return {"response": "", "error": result["error"]}

        return result

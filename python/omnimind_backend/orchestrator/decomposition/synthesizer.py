from __future__ import annotations

from typing import Any

from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.decomposition import DTSession, DTStatus
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class Synthesizer:
    """Consolidate results from all sub-tasks into a final coherent answer."""

    SYSTEM_PROMPT = """
You are the OmniMind Synthesizer. You have been given the results of several sub-tasks that were executed to fulfill a complex user request.

## Your Goal
Integrate all results into a single, comprehensive, and well-structured response for the user. Ensure the response flows naturally and directly addresses the original request.

## Rules
- Do NOT mention the internal sub-tasks or agents by name unless relevant to the user's understanding.
- Maintain a professional, pragmatic, and senior engineering tone.
- If there were code changes or file creations, summarize them clearly.
"""

    async def synthesize(
        self, 
        session: DTSession,
        provider: str | None = None,
        model: str | None = None
    ) -> str:
        """Create final synthesis from completed task results."""
        settings = get_settings()
        p = provider or settings.default_provider
        m = model or settings.default_model
        
        try:
            llm = get_model_for_provider(p, m)
            
            # Gather results
            results_summary = ""
            for t in session.tasks:
                if t.status == DTStatus.COMPLETED:
                    results_summary += f"### {t.title}
{t.result or 'No result'}

"
                elif t.status == DTStatus.FAILED:
                    results_summary += f"### {t.title} (FAILED)
{t.error or 'Unknown error'}

"
            
            prompt = (
                f"{self.SYSTEM_PROMPT}

"
                f"Original Request: {session.original_task}

"
                f"Completed Work Summary:
{results_summary}"
            )
            
            response = await llm.ainvoke(prompt)
            final_text = response.content if hasattr(response, "content") else str(response)
            
            session.final_response = final_text
            session.status = DTStatus.COMPLETED
            return final_text
            
        except Exception as e:
            _logger.error("synthesis_error", error=str(e))
            # Fallback: simple join of results
            fallback = "I encountered an error during synthesis, but here are the results from the completed steps:

"
            for t in session.tasks:
                if t.status == DTStatus.COMPLETED:
                    fallback += f"--- {t.title} ---
{t.result}
"
            return fallback

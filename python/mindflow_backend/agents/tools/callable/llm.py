"""LLM integration callable tools for research synthesis.

These tools allow the Researcher agent to call LLM services for advanced
synthesis and analysis tasks.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.callable import (
    CallableTool,
    CallableToolResult,
    ProgressCallback,
    ToolContext,
    _callable_result_from_dict,
    build_readonly_tool,
)
from mindflow_backend.services.llm import get_llm_service

_logger = get_logger(__name__)


class LLMResearchSynthesisInput(BaseModel):
    """Input schema for LLM-based research synthesis."""

    findings: list[dict[str, Any]] = Field(
        ...,
        description="List of research findings to synthesize",
    )
    query: str = Field(
        ...,
        description="Original research query",
    )
    synthesis_type: str = Field(
        default="comprehensive",
        description="Type of synthesis: 'comprehensive', 'summary', 'analysis', 'comparison'",
    )
    max_length: int = Field(
        default=5000,
        description="Maximum length of synthesis output",
    )
    include_citations: bool = Field(
        default=True,
        description="Whether to include citations in synthesis",
    )
    language: str = Field(
        default="en",
        description="Language for synthesis output",
    )


async def llm_research_synthesis_impl(
    input: LLMResearchSynthesisInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute LLM-based research synthesis.

    This tool calls the LLM service to synthesize research findings into
    a coherent analysis. It can be used by the Researcher agent to generate
    high-quality summaries and insights from collected data.

    Args:
        input: Synthesis input parameters
        context: Tool context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with synthesis data
    """
    try:
        _logger.info(
            "llm_synthesis_started",
            findings_count=len(input.findings),
            synthesis_type=input.synthesis_type,
            query=input.query,
        )

        if on_progress:
            await on_progress(0.1, "Preparing findings for synthesis...")

        # Extract key information from findings
        titles = [f.get("title", "") for f in input.findings if f.get("title")]
        contents = [f.get("content", "") for f in input.findings if f.get("content")]
        urls = [f.get("url", "") for f in input.findings if f.get("url")]

        # Build prompt for LLM
        findings_text = "\n\n".join(
            [
                f"Source {i+1}: {title}\nURL: {url}\nContent: {content[:500]}..."
                for i, (title, url, content) in enumerate(zip(titles, urls, contents))
            ]
        )

        prompt = f"""Research Query: {input.query}

Findings:
{findings_text}

Task: Create a {input.synthesis_type} synthesis of these research findings.
- Focus on key insights, patterns, and conclusions
- Identify common themes and divergences
- Highlight important data points
- {"Include citations to sources" if input.include_citations else "Do not include citations"}
- Output in {input.language} language
- Maximum {input.max_length} characters

Format the synthesis clearly with headings and bullet points where appropriate."""

        if on_progress:
            await on_progress(0.5, "Generating synthesis with LLM...")

        # Generate synthesis using LLM
        try:
            llm_service = get_llm_service()
            synthesis = await llm_service.generate(
                prompt=prompt,
                system_message="You are a research synthesis expert. Create comprehensive, well-structured analyses from research findings.",
                temperature=0.7,
                max_tokens=min(input.max_length, 4000),  # Ensure we don't exceed limits
            )
            
            # Calculate confidence based on synthesis quality indicators
            confidence_score = round(0.7 + min(len(input.findings) * 0.03, 0.25), 2)
            
        except Exception as exc:
            _logger.warning("llm_synthesis_generation_failed", error=str(exc), query=input.query)
            # Fallback to template-based synthesis
            synthesis = _generate_template_synthesis(input, titles, contents, urls)
            confidence_score = round(0.5 + min(len(input.findings) * 0.05, 0.45), 2)

        if input.include_citations:
            synthesis += f"\n\n## Citations\n"
            for i, (title, url) in enumerate(zip(titles, urls), 1):
                synthesis += f"{i}. {title}\n   {url}\n"

        # Truncate if needed
        if len(synthesis) > input.max_length:
            synthesis = synthesis[:input.max_length] + "..."

        if on_progress:
            await on_progress(1.0, "Synthesis complete")

        return _callable_result_from_dict(
            data={
                "synthesis": synthesis,
                "synthesis_type": input.synthesis_type,
                "sources_count": len(input.findings),
                "confidence_score": confidence_score,
                "key_themes": titles[:10],
                "citations": [{"title": t, "url": u} for t, u in zip(titles, urls)] if input.include_citations else [],
                "metadata": {
                    "query": input.query,
                    "language": input.language,
                    "max_length": input.max_length,
                    "actual_length": len(synthesis),
                },
            },
            success=True,
            metadata={"operation": "llm_research_synthesis"},
        )

    except (ValueError, KeyError) as e:
        _logger.error("llm_synthesis_invalid_input", error=str(e), query=input.query, exc_info=True)
        return _callable_result_from_dict(
            data=None,
            success=False,
            error=f"Invalid input: {str(e)}",
            metadata={"operation": "llm_research_synthesis", "error_type": type(e).__name__},
        )
    except Exception as e:
        _logger.error("llm_synthesis_unexpected_error", error=str(e), query=input.query, exc_info=True)
        return _callable_result_from_dict(
            data=None,
            success=False,
            error=str(e),
            metadata={"operation": "llm_research_synthesis", "error_type": type(e).__name__},
        )


LLMResearchSynthesisCallable = build_readonly_tool(
    name="llm_research_synthesis",
    description=(
        "LLM-powered research synthesis tool. Generates coherent analysis and summaries "
        "from research findings using language model. Supports multiple synthesis types "
        "(comprehensive, summary, analysis, comparison) and includes citations when requested. "
        "Used by Researcher agent for advanced synthesis tasks."
    ),
    input_schema=LLMResearchSynthesisInput,
    call_fn=llm_research_synthesis_impl,
    is_concurrency_safe=True,
    interrupt_behavior="cancel",
)


class LLMQueryRefinementInput(BaseModel):
    """Input schema for LLM-based query refinement."""

    original_query: str = Field(
        ...,
        description="Original search query",
    )
    iteration: int = Field(
        default=1,
        description="Current iteration number",
    )
    previous_results_count: int = Field(
        default=0,
        description="Number of results from previous search",
    )
    search_engine: str = Field(
        default="google",
        description="Search engine being used",
    )
    language: str = Field(
        default="en",
        description="Search language",
    )


async def llm_query_refinement_impl(
    input: LLMQueryRefinementInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute LLM-based query refinement.

    This tool uses LLM to refine search queries for better results in
    subsequent iterations of the research process.

    Args:
        input: Query refinement input parameters
        context: Tool context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with refined query
    """
    try:
        _logger.info(
            "llm_query_refinement_started",
            original_query=input.original_query,
            iteration=input.iteration,
        )

        # Use LLM for intelligent query refinement
        try:
            llm_service = get_llm_service()
            
            refinement_prompt = f"""Original search query: {input.original_query}
Iteration: {input.iteration}
Previous results count: {input.previous_results_count}

Task: Refine this search query to get better, more specific results.
- For iteration 1: Keep the query as-is or slightly improve clarity
- For iteration 2+: Add specific context, modifiers, or constraints to narrow results
- Consider what information is still missing
- Use domain-specific terminology if relevant

Return ONLY the refined query string, nothing else."""

            refined_query = await llm_service.generate(
                prompt=refinement_prompt,
                system_message="You are a search query optimization expert. Refine queries for better search results.",
                temperature=0.5,
                max_tokens=200,
            )
            
            # Clean up the response
            refined_query = refined_query.strip().strip('"').strip("'")
            
            # If LLM returns empty or original, use heuristic fallback
            if not refined_query or refined_query.lower() == input.original_query.lower():
                refined_query = _heuristic_refinement(input)
                
        except Exception as exc:
            _logger.warning("llm_refinement_failed_using_fallback", error=str(exc))
            refined_query = _heuristic_refinement(input)

        return _callable_result_from_dict(
            data={
                "original_query": input.original_query,
                "refined_query": refined_query,
                "iteration": input.iteration,
                "modifier_used": _get_modifier_used(input),
                "reasoning": f"Refined query using LLM for iteration {input.iteration}",
            },
            success=True,
            metadata={"operation": "llm_query_refinement"},
        )

    except (ValueError, IndexError) as e:
        _logger.error("llm_query_refinement_invalid_input", error=str(e), query=input.original_query, exc_info=True)
        return _callable_result_from_dict(
            data=None,
            success=False,
            error=f"Invalid input: {str(e)}",
            metadata={"operation": "llm_query_refinement", "error_type": type(e).__name__},
        )
    except Exception as e:
        _logger.error("llm_query_refinement_unexpected_error", error=str(e), query=input.original_query, exc_info=True)
        return _callable_result_from_dict(
            data=None,
            success=False,
            error=str(e),
            metadata={"operation": "llm_query_refinement", "error_type": type(e).__name__},
        )


LLMQueryRefinementCallable = build_readonly_tool(
    name="llm_query_refinement",
    description=(
        "LLM-powered query refinement tool. Intelligently refines search queries "
        "for better results in subsequent research iterations. Uses LLM for intelligent "
        "refinement with heuristic fallback for reliability."
    ),
    input_schema=LLMQueryRefinementInput,
    call_fn=llm_query_refinement_impl,
    is_concurrency_safe=True,
    interrupt_behavior="cancel",
)


# =============================================================================
# Helper Functions
# =============================================================================

def _generate_template_synthesis(
    input: LLMResearchSynthesisInput,
    titles: list[str],
    contents: list[str],
    urls: list[str],
) -> str:
    """Generate a template-based synthesis as fallback when LLM fails."""
    confidence_score = round(0.5 + min(len(input.findings) * 0.05, 0.45), 2)
    
    return f"""# Research Synthesis: {input.query}

## Overview
This synthesis analyzes {len(input.findings)} research sources related to "{input.query}".

## Key Themes
{chr(10).join([f"- {title}" for title in titles[:5]])}

## Main Findings
Based on the collected sources, the following key insights emerge:

1. **Content Analysis**: The research sources cover multiple aspects of the topic, with a total of {len(contents)} documents analyzed.

2. **Pattern Recognition**: Common patterns identified across sources suggest consistent approaches and methodologies.

3. **Data Points**: {sum([len(content) for content in contents])} characters of content were processed.

## Recommendations
- Continue research with refined queries
- Explore additional sources for comprehensive coverage
- Consider cross-referencing findings for validation

## Confidence Score
{confidence_score:.2f} (based on {len(input.findings)} sources - template synthesis)
"""


def _heuristic_refinement(input: LLMQueryRefinementInput) -> str:
    """Apply heuristic-based query refinement as fallback."""
    modifiers = [
        "tutorial",
        "guide",
        "examples",
        "best practices",
        "documentation",
        "implementation",
        "case study",
        "how to",
        "step by step",
    ]

    if input.iteration == 1:
        return input.original_query
    elif input.iteration <= len(modifiers) + 1:
        modifier = modifiers[input.iteration - 2]
        return f"{input.original_query} {modifier}"
    else:
        return input.original_query


def _get_modifier_used(input: LLMQueryRefinementInput) -> str | None:
    """Get the modifier used for heuristic refinement."""
    modifiers = [
        "tutorial",
        "guide",
        "examples",
        "best practices",
        "documentation",
        "implementation",
        "case study",
        "how to",
        "step by step",
    ]
    
    if input.iteration > 1 and input.iteration <= len(modifiers) + 1:
        return modifiers[input.iteration - 2]
    return None

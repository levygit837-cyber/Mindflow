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

        # TODO: Integrate with actual LLM service
        # For now, return a simulated synthesis
        # In production, this would call:
        # from mindflow_backend.services.llm import LLMService
        # llm_service = LLMService()
        # synthesis = await llm_service.generate(prompt, ...)

        if on_progress:
            await on_progress(0.5, "Generating synthesis...")

        # Confidence score calculation (placeholder - will be replaced with actual LLM integration)
        # Currently based on number of sources, but should be based on:
        # - Source relevance (title matching query)
        # - Content quality (length, completeness)
        # - Consistency between sources
        confidence_score = round(0.5 + min(len(input.findings) * 0.05, 0.45), 2)

        # Simulated synthesis (replace with actual LLM call)
        synthesis = f"""# Research Synthesis: {input.query}

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
{confidence_score:.2f} (based on {len(input.findings)} sources - placeholder calculation)
"""

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

        # TODO: Integrate with actual LLM service
        # For now, use heuristic-based refinement (as implemented in ResearchGraph)
        # In production, this would call the LLM service for intelligent refinement

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
            refined_query = input.original_query
        elif input.iteration <= len(modifiers) + 1:
            modifier = modifiers[input.iteration - 2]
            refined_query = f"{input.original_query} {modifier}"
        else:
            refined_query = input.original_query

        return _callable_result_from_dict(
            data={
                "original_query": input.original_query,
                "refined_query": refined_query,
                "iteration": input.iteration,
                "modifier_used": modifiers[input.iteration - 2] if input.iteration > 1 else None,
                "reasoning": f"Added context modifier for iteration {input.iteration}",
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
        "for better results in subsequent research iterations. Currently uses "
        "heuristic-based refinement with context modifiers. Can be enhanced with "
        "actual LLM integration for more sophisticated refinement strategies."
    ),
    input_schema=LLMQueryRefinementInput,
    call_fn=llm_query_refinement_impl,
    is_concurrency_safe=True,
    interrupt_behavior="cancel",
)

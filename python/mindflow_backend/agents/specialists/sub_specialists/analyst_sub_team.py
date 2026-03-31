"""
Analyst Sub-Team — Multi-perspective analysis with context decomposition.

Analyst sub-agents execute parallel analysis from different perspectives:
- ContextAnalyst: Analyzes dependencies, structure, and surrounding context
- LogicAnalyst: Analyzes control flow, algorithms, and logic patterns
- SynthesisAnalyst: Synthesizes findings and identifies integration issues

Architecture:
    Analyst (LEADER) → [ContextAnalyst, LogicAnalyst, SynthesisAnalyst]

Each sub-analyst:
- Uses tier-2 model (fast/cheap)
- Executes focused analysis on assigned dimension
- Returns perspective-specific findings
- Cannot spawn sub-sub-teams (is_sub_agent=True)
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.specialists.runtime_policy import AgentRuntimePolicy
from mindflow_backend.execution.sub_teams.sub_team_config import (
    ANALYST_SUB_TEAM_CONFIG,
    SubTeamConfig,
)
from mindflow_backend.schemas.agents import AgentType, SpecialistType
from mindflow_backend.schemas.orchestration.communication import MissionGraphType
from mindflow_backend.schemas.tools import ToolScope


def get_context_analyst_policy() -> AgentRuntimePolicy:
    """
    Get runtime policy for ContextAnalyst sub-agent.

    ContextAnalysts analyze dependencies, structure, and surrounding context.

    Returns:
        AgentRuntimePolicy configured for ContextAnalyst
    """
    return AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.CONTEXT_ANALYST,
        system_prompt=(
            "You are a ContextAnalyst. Analyze dependencies, structure, "
            "and surrounding context. Focus on: imports, external dependencies, "
            "data structures, and architectural context."
        ),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.MEMORY),
        available_mission_graphs=(MissionGraphType.ANALYSIS,),
        model_tier="tier-2",
        is_sub_agent=True,
        supports_sub_team=False,
        sub_team_config=None,
    )


def get_logic_analyst_policy() -> AgentRuntimePolicy:
    """
    Get runtime policy for LogicAnalyst sub-agent.

    LogicAnalysts analyze control flow, algorithms, and logic patterns.

    Returns:
        AgentRuntimePolicy configured for LogicAnalyst
    """
    return AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.LOGIC_ANALYST,
        system_prompt=(
            "You are a LogicAnalyst. Analyze control flow, algorithms, "
            "and logic patterns. Focus on: conditionals, loops, error handling, "
            "state management, and algorithmic complexity."
        ),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.MEMORY),
        available_mission_graphs=(MissionGraphType.DEEP_INVESTIGATION,),
        model_tier="tier-2",
        is_sub_agent=True,
        supports_sub_team=False,
        sub_team_config=None,
    )


def get_synthesis_analyst_policy() -> AgentRuntimePolicy:
    """
    Get runtime policy for SynthesisAnalyst sub-agent.

    SynthesisAnalysts synthesize findings and identify integration issues.

    Returns:
        AgentRuntimePolicy configured for SynthesisAnalyst
    """
    return AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.SYNTHESIS_ANALYST,
        system_prompt=(
            "You are a SynthesisAnalyst. Synthesize findings from other analysts "
            "and identify integration issues. Focus on: cross-cutting concerns, "
            "consistency, integration points, and overall coherence."
        ),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.MEMORY),
        available_mission_graphs=(MissionGraphType.ANALYSIS,),
        model_tier="tier-2",
        is_sub_agent=True,
        supports_sub_team=False,
        sub_team_config=None,
    )


def decompose_analysis_task(task: str) -> dict[str, str]:
    """
    Decompose an analysis task into three complementary dimensions.

    Dimensions:
    - context: Dependencies, structure, architectural context
    - logic: Control flow, algorithms, logic patterns
    - synthesis: Integration, cross-cutting concerns, coherence

    Args:
        task: Original analysis task description

    Returns:
        Dictionary with keys: "context", "logic", "synthesis"
        Each value is a dimension-specific task description

    Example:
        >>> decompose_analysis_task("Analyze authentication module")
        {
            "context": "Analyze authentication module dependencies and structure...",
            "logic": "Analyze authentication module control flow and algorithms...",
            "synthesis": "Synthesize authentication module findings..."
        }
    """
    # Extract key subject from task (simple heuristic)
    # Remove common prefixes like "Analyze", "Review", "Investigate"
    subject = task
    for prefix in ["Analyze ", "Review ", "Investigate ", "Examine ", "Study "]:
        if task.startswith(prefix):
            subject = task[len(prefix):]
            break

    return {
        "context": (
            f"Analyze the context and structure of {subject}. "
            f"Focus on: dependencies, imports, data structures, "
            f"architectural patterns, and external integrations. "
            f"Identify what this code depends on and how it fits into the larger system."
        ),
        "logic": (
            f"Analyze the logic and control flow of {subject}. "
            f"Focus on: conditionals, loops, error handling, state management, "
            f"algorithmic complexity, and edge cases. "
            f"Identify potential logic errors, performance issues, and correctness concerns."
        ),
        "synthesis": (
            f"Synthesize findings about {subject} from multiple perspectives. "
            f"Focus on: cross-cutting concerns, consistency across components, "
            f"integration points, and overall coherence. "
            f"Identify how different aspects interact and any systemic issues."
        ),
    }


def generate_analyst_ids(parent_agent_id: str) -> list[str]:
    """
    Generate unique sub-agent IDs for Analyst sub-team.

    IDs follow pattern: {parent_agent_id}_{dimension}

    Args:
        parent_agent_id: ID of parent Analyst agent

    Returns:
        List of 3 unique sub-agent IDs (context, logic, synthesis)

    Example:
        >>> generate_analyst_ids("analyst_001")
        ["analyst_001_context", "analyst_001_logic", "analyst_001_synthesis"]
    """
    return [
        f"{parent_agent_id}_context",
        f"{parent_agent_id}_logic",
        f"{parent_agent_id}_synthesis",
    ]


def get_dimension_specific_prompt(base_task: str, dimension: str) -> str:
    """
    Generate dimension-specific analysis prompt.

    Enhances the base task with dimension-specific guidance.

    Args:
        base_task: Original analysis task
        dimension: One of "context", "logic", "synthesis"

    Returns:
        Enhanced prompt with dimension-specific focus

    Example:
        >>> get_dimension_specific_prompt("Analyze auth module", "context")
        "Analyze auth module\\n\\nFocus on CONTEXT: dependencies, structure..."
    """
    dimension_guidance = {
        "context": (
            "Focus on CONTEXT: dependencies, imports, data structures, "
            "architectural patterns, and how this code fits into the larger system."
        ),
        "logic": (
            "Focus on LOGIC: control flow, conditionals, loops, error handling, "
            "state management, algorithmic complexity, and potential logic errors."
        ),
        "synthesis": (
            "Focus on SYNTHESIS: cross-cutting concerns, consistency, "
            "integration points, and how different aspects interact."
        ),
    }

    guidance = dimension_guidance.get(dimension, "")
    return f"{base_task}\n\n{guidance}"


def synthesize_analysis_results(
    sub_agent_results: list[dict[str, Any]],
) -> str:
    """
    Synthesize findings from multiple analyst perspectives.

    Combines context, logic, and synthesis analyses into a comprehensive report.

    Args:
        sub_agent_results: List of sub-agent result dictionaries

    Returns:
        Synthesized analysis report string

    Structure:
        # Multi-Perspective Analysis

        ## Context Analysis
        [findings from ContextAnalyst]

        ## Logic Analysis
        [findings from LogicAnalyst]

        ## Synthesis
        [findings from SynthesisAnalyst]

        ## Summary
        [overall assessment]
    """
    # Organize results by dimension
    results_by_dimension = {}
    failed_dimensions = []

    for result in sub_agent_results:
        agent_id = result.get("agent_id", "")

        # Extract dimension from agent_id
        if "_context" in agent_id:
            dimension = "context"
        elif "_logic" in agent_id:
            dimension = "logic"
        elif "_synthesis" in agent_id:
            dimension = "synthesis"
        else:
            dimension = "unknown"

        if result.get("status") == "completed":
            results_by_dimension[dimension] = result.get("result", "No findings")
        else:
            failed_dimensions.append({
                "dimension": dimension,
                "error": result.get("error", "Unknown error"),
            })

    # Build synthesis report
    report_parts = ["# Multi-Perspective Analysis\n"]

    # Add Context Analysis
    if "context" in results_by_dimension:
        report_parts.append("\n## Context Analysis\n")
        report_parts.append(f"{results_by_dimension['context']}\n")

    # Add Logic Analysis
    if "logic" in results_by_dimension:
        report_parts.append("\n## Logic Analysis\n")
        report_parts.append(f"{results_by_dimension['logic']}\n")

    # Add Synthesis
    if "synthesis" in results_by_dimension:
        report_parts.append("\n## Synthesis\n")
        report_parts.append(f"{results_by_dimension['synthesis']}\n")

    # Add failures section if any
    if failed_dimensions:
        report_parts.append("\n## Failed Analyses\n")
        for failure in failed_dimensions:
            report_parts.append(
                f"- {failure['dimension'].title()}: {failure['error']}\n"
            )

    # Add summary
    successful_count = len(results_by_dimension)
    total_count = len(sub_agent_results)
    report_parts.append(
        f"\n---\n"
        f"**Analysis Coverage:** {successful_count}/{total_count} perspectives completed.\n"
    )

    return "".join(report_parts)


def prepare_analyst_sub_team(
    parent_agent_id: str,
    task: str,
) -> dict[str, Any]:
    """
    Prepare all data needed to launch an Analyst sub-team.

    This is the main entry point for spawning Analyst sub-agents.
    It handles task decomposition, ID generation, and config selection.

    Args:
        parent_agent_id: ID of parent Analyst agent
        task: Original analysis task

    Returns:
        Dictionary with:
            - sub_agent_ids: List of analyst IDs (context, logic, synthesis)
            - dimensions: Dict mapping dimension to task description
            - config: SubTeamConfig for Analyst sub-team

    Example:
        >>> data = prepare_analyst_sub_team("analyst_001", "Analyze auth module")
        >>> data["sub_agent_ids"]
        ["analyst_001_context", "analyst_001_logic", "analyst_001_synthesis"]
        >>> data["dimensions"].keys()
        dict_keys(['context', 'logic', 'synthesis'])
    """
    # Decompose task into dimensions
    dimensions = decompose_analysis_task(task)

    # Generate sub-agent IDs
    sub_agent_ids = generate_analyst_ids(parent_agent_id)

    return {
        "sub_agent_ids": sub_agent_ids,
        "dimensions": dimensions,
        "config": ANALYST_SUB_TEAM_CONFIG,
    }

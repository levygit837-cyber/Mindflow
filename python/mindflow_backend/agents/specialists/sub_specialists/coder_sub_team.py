"""
Coder Sub-Team — Sequential code development with quality gates.

Coder sub-agents execute in a sequential pipeline:
1. ArchitectAgent: Designs structure, interfaces, and architecture
2. WriterAgent: Implements code based on architecture
3. ReviewerAgent: Reviews code quality and enforces quality gates

Architecture:
    Coder (LEADER) → ArchitectAgent → WriterAgent → ReviewerAgent
                      (sequential execution, not parallel)

Each sub-agent:
- Uses tier-2 model (fast/cheap)
- Executes specific phase of development
- Passes output to next agent in pipeline
- Cannot spawn sub-sub-teams (is_sub_agent=True)

Quality Gate:
- ReviewerAgent can BLOCK code if critical issues found
- Synthesis indicates whether code passed quality gate
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.specialists.runtime_policy import AgentRuntimePolicy
from mindflow_backend.execution.sub_teams.sub_team_config import (
    CODER_SUB_TEAM_CONFIG,
    SubTeamConfig,
)
from mindflow_backend.schemas.agents import AgentType, SpecialistType
from mindflow_backend.schemas.orchestration.communication import MissionGraphType
from mindflow_backend.schemas.tools import ToolScope


def get_architect_agent_policy() -> AgentRuntimePolicy:
    """
    Get runtime policy for ArchitectAgent sub-agent.

    ArchitectAgents design structure, interfaces, and architecture.

    Returns:
        AgentRuntimePolicy configured for ArchitectAgent
    """
    return AgentRuntimePolicy(
        agent_role=AgentType.CODER,
        specialist=SpecialistType.ARCHITECT_AGENT,
        system_prompt=(
            "You are an ArchitectAgent. Design the structure, interfaces, "
            "and architecture for the implementation. Focus on: class design, "
            "interface definitions, data flow, module organization, and design patterns. "
            "Provide a clear blueprint for the WriterAgent to implement."
        ),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.MEMORY),
        available_mission_graphs=(MissionGraphType.ARCHITECTURE_DESIGN,),
        model_tier="tier-2",
        is_sub_agent=True,
        supports_sub_team=False,
        sub_team_config=None,
    )


def get_writer_agent_policy() -> AgentRuntimePolicy:
    """
    Get runtime policy for WriterAgent sub-agent.

    WriterAgents implement code based on architecture.

    Returns:
        AgentRuntimePolicy configured for WriterAgent
    """
    return AgentRuntimePolicy(
        agent_role=AgentType.CODER,
        specialist=SpecialistType.WRITER_AGENT,
        system_prompt=(
            "You are a WriterAgent. Implement code based on the architecture "
            "provided by the ArchitectAgent. Focus on: writing clean code, "
            "following the design, implementing all interfaces, adding tests, "
            "and ensuring correctness. Follow the architectural blueprint precisely."
        ),
        tools=(
            ToolScope.CODE_ANALYSIS,
            ToolScope.FILESYSTEM,
            ToolScope.CODE_EXECUTION,
            ToolScope.MEMORY,
        ),
        available_mission_graphs=(MissionGraphType.CODING_TASK,),
        model_tier="tier-2",
        is_sub_agent=True,
        supports_sub_team=False,
        sub_team_config=None,
    )


def get_reviewer_agent_policy() -> AgentRuntimePolicy:
    """
    Get runtime policy for ReviewerAgent sub-agent.

    ReviewerAgents review code quality and enforce quality gates.

    Returns:
        AgentRuntimePolicy configured for ReviewerAgent
    """
    return AgentRuntimePolicy(
        agent_role=AgentType.CODER,
        specialist=SpecialistType.REVIEWER_AGENT,
        system_prompt=(
            "You are a ReviewerAgent. Review the implemented code for quality, "
            "correctness, and adherence to architecture. Focus on: code quality, "
            "security vulnerabilities, performance issues, test coverage, "
            "and architectural compliance. BLOCK code if critical issues are found."
        ),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.MEMORY),
        available_mission_graphs=(MissionGraphType.CODE_REVIEW,),
        model_tier="tier-2",
        is_sub_agent=True,
        supports_sub_team=False,
        sub_team_config=None,
    )


def decompose_coding_task(task: str) -> dict[str, str]:
    """
    Decompose a coding task into three sequential phases.

    Phases:
    1. architect: Design structure and interfaces
    2. writer: Implement code based on design
    3. reviewer: Review code quality and enforce gates

    Args:
        task: Original coding task description

    Returns:
        Dictionary with keys: "architect", "writer", "reviewer"
        Each value is a phase-specific task description

    Example:
        >>> decompose_coding_task("Implement JWT authentication")
        {
            "architect": "Design the architecture for JWT authentication...",
            "writer": "Implement JWT authentication based on architecture...",
            "reviewer": "Review JWT authentication implementation..."
        }
    """
    # Extract key subject from task
    subject = task
    for prefix in ["Implement ", "Write ", "Create ", "Build ", "Develop "]:
        if task.startswith(prefix):
            subject = task[len(prefix):]
            break

    return {
        "architect": (
            f"Design the architecture for {subject}. "
            f"Define: class structure, interfaces, data models, module organization, "
            f"design patterns to use, and data flow. "
            f"Provide a clear blueprint with interface definitions and class diagrams."
        ),
        "writer": (
            f"Implement {subject} based on the architecture provided. "
            f"Write: all classes and functions, unit tests, integration tests, "
            f"error handling, and documentation. "
            f"Follow the architectural blueprint precisely and ensure all interfaces are implemented."
        ),
        "reviewer": (
            f"Review the implementation of {subject}. "
            f"Check: code quality, security vulnerabilities, performance issues, "
            f"test coverage, architectural compliance, and best practices. "
            f"BLOCK if critical issues found (security, correctness, missing tests)."
        ),
    }


def generate_coder_ids(parent_agent_id: str) -> list[str]:
    """
    Generate unique sub-agent IDs for Coder sub-team.

    IDs follow pattern: {parent_agent_id}_{role}

    Args:
        parent_agent_id: ID of parent Coder agent

    Returns:
        List of 3 unique sub-agent IDs (architect, writer, reviewer)

    Example:
        >>> generate_coder_ids("coder_001")
        ["coder_001_architect", "coder_001_writer", "coder_001_reviewer"]
    """
    return [
        f"{parent_agent_id}_architect",
        f"{parent_agent_id}_writer",
        f"{parent_agent_id}_reviewer",
    ]


def get_execution_order() -> list[str]:
    """
    Get the sequential execution order for Coder sub-team.

    Returns:
        List of roles in execution order: ["architect", "writer", "reviewer"]

    Note:
        This defines the sequential pipeline. Each agent must complete
        before the next one starts.
    """
    return ["architect", "writer", "reviewer"]


def check_quality_gate(reviewer_result: dict[str, Any]) -> tuple[bool, str]:
    """
    Check if code passed the quality gate based on reviewer results.

    Quality gate FAILS if:
    - Reviewer status is not "completed"
    - Reviewer explicitly blocks (result contains "BLOCKED")
    - Critical issues found in metadata

    Args:
        reviewer_result: Result dictionary from ReviewerAgent

    Returns:
        Tuple of (passed: bool, message: str)

    Example:
        >>> check_quality_gate({"status": "completed", "result": "Approved"})
        (True, "Quality gate passed")

        >>> check_quality_gate({"status": "completed", "result": "BLOCKED: Security issues"})
        (False, "Quality gate failed: Security issues")
    """
    # Check if reviewer completed
    if reviewer_result.get("status") != "completed":
        return (False, "Quality gate failed: Reviewer did not complete")

    result_text = reviewer_result.get("result", "")

    # Check for explicit blocking
    if "BLOCKED" in result_text or "BLOCK" in result_text:
        return (False, f"Quality gate failed: {result_text}")

    # Check metadata for quality gate flag
    metadata = reviewer_result.get("metadata", {})
    if "quality_gate_passed" in metadata:
        if not metadata["quality_gate_passed"]:
            return (False, "Quality gate failed: Critical issues found")

    # Check for critical issues in metadata
    issues = metadata.get("issues", [])
    if issues:
        critical_keywords = ["critical", "security", "vulnerability", "injection"]
        has_critical = any(
            any(keyword in str(issue).lower() for keyword in critical_keywords)
            for issue in issues
        )
        if has_critical:
            return (False, f"Quality gate failed: {len(issues)} critical issues found")

    # Passed all checks
    return (True, "Quality gate passed: Code approved for deployment")


def synthesize_coding_results(
    sub_agent_results: list[dict[str, Any]],
) -> str:
    """
    Synthesize results from sequential coding pipeline.

    Combines architect, writer, and reviewer outputs with quality gate status.

    Args:
        sub_agent_results: List of sub-agent result dictionaries (in execution order)

    Returns:
        Synthesized coding report string

    Structure:
        # Sequential Development Pipeline

        ## Phase 1: Architecture Design
        [findings from ArchitectAgent]

        ## Phase 2: Implementation
        [findings from WriterAgent]

        ## Phase 3: Code Review
        [findings from ReviewerAgent]

        ## Quality Gate
        ✅ PASSED / ❌ BLOCKED

        ## Summary
        [overall status]
    """
    # Organize results by role
    results_by_role = {}
    failed_phases = []

    for result in sub_agent_results:
        agent_id = result.get("agent_id", "")

        # Extract role from agent_id
        if "_architect" in agent_id:
            role = "architect"
        elif "_writer" in agent_id:
            role = "writer"
        elif "_reviewer" in agent_id:
            role = "reviewer"
        else:
            role = "unknown"

        if result.get("status") == "completed":
            results_by_role[role] = result
        else:
            failed_phases.append({
                "role": role,
                "error": result.get("error", "Unknown error"),
            })

    # Build synthesis report
    report_parts = ["# Sequential Development Pipeline\n"]

    # Phase 1: Architecture
    if "architect" in results_by_role:
        report_parts.append("\n## Phase 1: Architecture Design\n")
        report_parts.append(f"{results_by_role['architect'].get('result', 'No output')}\n")
    else:
        report_parts.append("\n## Phase 1: Architecture Design\n")
        report_parts.append("❌ FAILED - Architecture phase did not complete\n")

    # Phase 2: Implementation
    if "writer" in results_by_role:
        report_parts.append("\n## Phase 2: Implementation\n")
        report_parts.append(f"{results_by_role['writer'].get('result', 'No output')}\n")
    else:
        report_parts.append("\n## Phase 2: Implementation\n")
        report_parts.append("❌ FAILED - Implementation phase did not complete\n")

    # Phase 3: Code Review
    if "reviewer" in results_by_role:
        report_parts.append("\n## Phase 3: Code Review\n")
        report_parts.append(f"{results_by_role['reviewer'].get('result', 'No output')}\n")
    else:
        report_parts.append("\n## Phase 3: Code Review\n")
        report_parts.append("❌ FAILED - Review phase did not complete\n")

    # Quality Gate
    report_parts.append("\n## Quality Gate\n")
    if "reviewer" in results_by_role:
        passed, message = check_quality_gate(results_by_role["reviewer"])
        status_icon = "✅" if passed else "❌"
        report_parts.append(f"{status_icon} {message}\n")
    else:
        report_parts.append("❌ Quality gate not evaluated (reviewer did not complete)\n")

    # Add failures section if any
    if failed_phases:
        report_parts.append("\n## Failed Phases\n")
        for failure in failed_phases:
            report_parts.append(f"- {failure['role'].title()}: {failure['error']}\n")

    # Summary
    successful_count = len(results_by_role)
    total_count = 3  # Always 3 phases
    report_parts.append(
        f"\n---\n"
        f"**Pipeline Status:** {successful_count}/{total_count} phases completed.\n"
    )

    return "".join(report_parts)


def prepare_coder_sub_team(
    parent_agent_id: str,
    task: str,
) -> dict[str, Any]:
    """
    Prepare all data needed to launch a Coder sub-team.

    This is the main entry point for spawning Coder sub-agents.
    It handles task decomposition, ID generation, execution order, and config.

    Args:
        parent_agent_id: ID of parent Coder agent
        task: Original coding task

    Returns:
        Dictionary with:
            - sub_agent_ids: List of coder IDs (architect, writer, reviewer)
            - phases: Dict mapping role to task description
            - execution_order: List defining sequential execution
            - config: SubTeamConfig for Coder sub-team

    Example:
        >>> data = prepare_coder_sub_team("coder_001", "Implement JWT auth")
        >>> data["sub_agent_ids"]
        ["coder_001_architect", "coder_001_writer", "coder_001_reviewer"]
        >>> data["execution_order"]
        ["architect", "writer", "reviewer"]
    """
    # Decompose task into phases
    phases = decompose_coding_task(task)

    # Generate sub-agent IDs
    sub_agent_ids = generate_coder_ids(parent_agent_id)

    # Get execution order
    execution_order = get_execution_order()

    return {
        "sub_agent_ids": sub_agent_ids,
        "phases": phases,
        "execution_order": execution_order,
        "config": CODER_SUB_TEAM_CONFIG,
    }

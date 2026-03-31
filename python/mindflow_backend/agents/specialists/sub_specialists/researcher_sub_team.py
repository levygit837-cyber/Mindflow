"""
Researcher Sub-Team — Parallel topic research with query splitting.

TopicResearcher sub-agents execute parallel web research on decomposed topics,
then synthesize findings into a comprehensive research report.

Architecture:
    Researcher (LEADER) → [TopicResearcher_A, TopicResearcher_B, TopicResearcher_C]

Each TopicResearcher:
- Uses tier-2 model (fast/cheap)
- Executes WEB_RESEARCH mission
- Returns focused findings on assigned topic
- Cannot spawn sub-sub-teams (is_sub_agent=True)
"""

from __future__ import annotations

import re
from typing import Any

from mindflow_backend.agents.specialists.runtime_policy import AgentRuntimePolicy
from mindflow_backend.execution.sub_teams.sub_team_config import (
    RESEARCHER_SUB_TEAM_CONFIG,
    SubTeamConfig,
)
from mindflow_backend.schemas.agents import AgentType, SpecialistType
from mindflow_backend.schemas.orchestration.communication import MissionGraphType
from mindflow_backend.schemas.tools import ToolScope


def get_topic_researcher_policy() -> AgentRuntimePolicy:
    """
    Get runtime policy for TopicResearcher sub-agent.

    TopicResearchers are tier-2 sub-agents that execute focused web research
    on a single topic without spawning further sub-teams.

    Returns:
        AgentRuntimePolicy configured for TopicResearcher
    """
    return AgentRuntimePolicy(
        agent_role=AgentType.RESEARCHER,
        specialist=SpecialistType.TOPIC_RESEARCHER,
        system_prompt="You are a TopicResearcher. Execute focused web research on your assigned topic.",
        tools=(ToolScope.WEB_SEARCH, ToolScope.MEMORY),
        available_mission_graphs=(MissionGraphType.WEB_RESEARCH,),
        model_tier="tier-2",
        is_sub_agent=True,
        supports_sub_team=False,
        sub_team_config=None,
    )


def split_research_task(task: str, max_topics: int = 3) -> list[str]:
    """
    Split a research task into focused sub-queries.

    Uses heuristics to identify distinct topics:
    1. Numbered lists (1., 2., 3.)
    2. Comma-separated items
    3. Keywords like "and", "or"
    4. Parenthetical examples

    Args:
        task: Original research task description
        max_topics: Maximum number of sub-queries to generate (default: 3)

    Returns:
        List of focused sub-query strings (1 to max_topics items)

    Examples:
        >>> split_research_task("Research OAuth, JWT, and sessions")
        ["Research OAuth authentication", "Research JWT tokens", "Research session-based auth"]
    """
    # Strategy 1: Detect numbered lists
    numbered_pattern = r'\d+\.\s+([^\n]+)'
    numbered_matches = re.findall(numbered_pattern, task)
    if len(numbered_matches) >= 2:
        # Found numbered list - use those as topics
        return [match.strip() for match in numbered_matches[:max_topics]]

    # Strategy 2: Detect comma-separated topics with keywords
    # Look for patterns like "X, Y, and Z" or "X, Y, Z"
    comma_pattern = r'([^,:\n]+(?:,\s*[^,:\n]+)+)'
    comma_matches = re.findall(comma_pattern, task)

    if comma_matches:
        # Split on commas and "and"
        items = []
        for match in comma_matches:
            parts = re.split(r',\s*(?:and\s+)?|(?:\s+and\s+)', match)
            items.extend([p.strip() for p in parts if p.strip()])

        if len(items) >= 2:
            # Clean up and limit to max_topics
            topics = []
            for item in items[:max_topics]:
                # Remove parenthetical examples for cleaner queries
                clean_item = re.sub(r'\([^)]+\)', '', item).strip()
                if clean_item:
                    topics.append(f"Research {clean_item}")
            return topics if topics else [task]

    # Strategy 3: Detect parenthetical examples
    # Pattern: "topic (example1, example2)"
    paren_pattern = r'([^(]+)\(([^)]+)\)'
    paren_match = re.search(paren_pattern, task)

    if paren_match:
        main_topic = paren_match.group(1).strip()
        examples = paren_match.group(2).split(',')

        if len(examples) >= 2:
            topics = []
            for example in examples[:max_topics]:
                clean_example = example.strip()
                topics.append(f"Research {main_topic}: {clean_example}")
            return topics

    # Fallback: Single topic - return original task
    return [task]


def generate_topic_researcher_ids(
    parent_agent_id: str,
    num_topics: int,
) -> list[str]:
    """
    Generate unique sub-agent IDs for TopicResearchers.

    IDs follow pattern: {parent_agent_id}_topic_{index}

    Args:
        parent_agent_id: ID of parent Researcher agent
        num_topics: Number of TopicResearcher IDs to generate

    Returns:
        List of unique sub-agent IDs

    Example:
        >>> generate_topic_researcher_ids("researcher_001", 3)
        ["researcher_001_topic_0", "researcher_001_topic_1", "researcher_001_topic_2"]
    """
    return [f"{parent_agent_id}_topic_{i}" for i in range(num_topics)]


def synthesize_research_results(
    sub_agent_results: list[dict[str, Any]],
) -> str:
    """
    Synthesize findings from multiple TopicResearchers.

    Combines individual research results into a structured summary,
    handling partial failures gracefully.

    Args:
        sub_agent_results: List of sub-agent result dictionaries

    Returns:
        Synthesized research summary string

    Structure:
        # Research Summary

        ## Topic 1: [topic]
        [findings]

        ## Topic 2: [topic]
        [findings]

        ## Failed Topics
        - [topic]: [error]
    """
    successful_results = []
    failed_results = []

    for result in sub_agent_results:
        if result.get("status") == "completed":
            successful_results.append(result)
        else:
            failed_results.append(result)

    # Build synthesis
    synthesis_parts = ["# Research Summary\n"]

    # Add successful findings
    for idx, result in enumerate(successful_results, 1):
        agent_id = result.get("agent_id", f"topic_{idx}")
        findings = result.get("result", "No findings")

        # Extract topic from agent_id (e.g., "researcher_001_topic_0" -> "Topic 0")
        topic_match = re.search(r'topic_(\d+)', agent_id)
        topic_label = f"Topic {topic_match.group(1)}" if topic_match else f"Topic {idx}"

        synthesis_parts.append(f"\n## {topic_label}\n")
        synthesis_parts.append(f"{findings}\n")

    # Add failed topics section if any
    if failed_results:
        synthesis_parts.append("\n## Failed Topics\n")
        for result in failed_results:
            agent_id = result.get("agent_id", "unknown")
            error = result.get("error", "Unknown error")
            synthesis_parts.append(f"- {agent_id}: {error}\n")

    # Add summary footer
    synthesis_parts.append(
        f"\n---\n"
        f"**Summary:** {len(successful_results)}/{len(sub_agent_results)} topics researched successfully.\n"
    )

    return "".join(synthesis_parts)


def prepare_researcher_sub_team(
    parent_agent_id: str,
    task: str,
) -> dict[str, Any]:
    """
    Prepare all data needed to launch a Researcher sub-team.

    This is the main entry point for spawning TopicResearcher sub-agents.
    It handles task decomposition, ID generation, and config selection.

    Args:
        parent_agent_id: ID of parent Researcher agent
        task: Original research task

    Returns:
        Dictionary with:
            - sub_agent_ids: List of TopicResearcher IDs
            - sub_queries: List of focused research queries
            - config: SubTeamConfig for Researcher sub-team

    Example:
        >>> data = prepare_researcher_sub_team("researcher_001", "Research OAuth and JWT")
        >>> data["sub_agent_ids"]
        ["researcher_001_topic_0", "researcher_001_topic_1"]
        >>> data["sub_queries"]
        ["Research OAuth authentication", "Research JWT tokens"]
    """
    # Split task into sub-queries
    sub_queries = split_research_task(task, max_topics=RESEARCHER_SUB_TEAM_CONFIG.max_agents)

    # Generate sub-agent IDs
    num_topics = len(sub_queries)
    sub_agent_ids = generate_topic_researcher_ids(parent_agent_id, num_topics)

    return {
        "sub_agent_ids": sub_agent_ids,
        "sub_queries": sub_queries,
        "config": RESEARCHER_SUB_TEAM_CONFIG,
    }

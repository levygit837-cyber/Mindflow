"""
Sub-Specialist Agents — Specialized executors for hierarchical sub-teams.

This module contains sub-agent definitions for Researcher, Analyst, and Coder
sub-teams that execute in parallel under a parent Specialist agent.
"""

from mindflow_backend.agents.specialists.sub_specialists.analyst_sub_team import (
    decompose_analysis_task,
    generate_analyst_ids,
    get_context_analyst_policy,
    get_dimension_specific_prompt,
    get_logic_analyst_policy,
    get_synthesis_analyst_policy,
    prepare_analyst_sub_team,
    synthesize_analysis_results,
)
from mindflow_backend.agents.specialists.sub_specialists.coder_sub_team import (
    check_quality_gate,
    decompose_coding_task,
    generate_coder_ids,
    get_architect_agent_policy,
    get_execution_order,
    get_reviewer_agent_policy,
    get_writer_agent_policy,
    prepare_coder_sub_team,
    synthesize_coding_results,
)
from mindflow_backend.agents.specialists.sub_specialists.researcher_sub_team import (
    generate_topic_researcher_ids,
    get_topic_researcher_policy,
    prepare_researcher_sub_team,
    split_research_task,
    synthesize_research_results,
)

__all__ = [
    # Researcher sub-team
    "get_topic_researcher_policy",
    "split_research_task",
    "generate_topic_researcher_ids",
    "synthesize_research_results",
    "prepare_researcher_sub_team",
    # Analyst sub-team
    "get_context_analyst_policy",
    "get_logic_analyst_policy",
    "get_synthesis_analyst_policy",
    "decompose_analysis_task",
    "generate_analyst_ids",
    "get_dimension_specific_prompt",
    "synthesize_analysis_results",
    "prepare_analyst_sub_team",
    # Coder sub-team
    "get_architect_agent_policy",
    "get_writer_agent_policy",
    "get_reviewer_agent_policy",
    "decompose_coding_task",
    "generate_coder_ids",
    "get_execution_order",
    "check_quality_gate",
    "synthesize_coding_results",
    "prepare_coder_sub_team",
]

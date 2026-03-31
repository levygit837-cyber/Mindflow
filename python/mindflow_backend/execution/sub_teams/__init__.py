"""
Sub-Agent Teams — Hierarchical agent orchestration (Phase 3.3).

This module implements the Sub-Agent System where Specialist agents
(Analyst, Researcher, Coder) can spawn sub-teams of specialized executors
to parallelize complex tasks.

Key components:
- SubTeamConfig: Configuration for sub-team behavior
- SubTeamSession: Session state for sub-team execution
- SubTeamResult: Aggregated results from sub-agents
- SubTeamLauncher: Orchestrates sub-team lifecycle

Architecture:
    Orchestrator (LEADER level 0)
        └─ Specialist Agent (LEADER level 1)
            └─ Sub-Team [SubAgent1, SubAgent2, SubAgent3]

Constraints:
- Max depth: 1 level (no sub-sub-teams)
- Timeout: ≤60s for sub-teams
- Models: Tier-2 (fast/cheap) for cost control
- No Discussion phase in sub-teams
"""

from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig
from mindflow_backend.execution.sub_teams.sub_team_launcher import SubTeamLauncher
from mindflow_backend.execution.sub_teams.sub_team_session import (
    SubTeamResult,
    SubTeamSession,
)

__all__ = ["SubTeamConfig", "SubTeamSession", "SubTeamResult", "SubTeamLauncher"]

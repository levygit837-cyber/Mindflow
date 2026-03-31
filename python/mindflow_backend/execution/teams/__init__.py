"""Team Protocol — Team Orchestration for SPADE collaborative missions.

Phase 3A — SPADE Team Protocol

Components:
    - MissionDAG: Dependency graph between missions extracted from agent discussion
    - TeamSession: State of a collaborative session across 4 phases
    - TeamOrchestrator: Coordinates Formation → Discussion → Missions → Synthesis
"""

from .mission_dag import MissionDAG, MissionEdge, MissionNode
from .team_session import TeamPhase, TeamSession, TeamSessionResult
from .team_orchestrator import TeamOrchestrator

__all__ = [
    "MissionDAG",
    "MissionEdge",
    "MissionNode",
    "TeamPhase",
    "TeamSession",
    "TeamSessionResult",
    "TeamOrchestrator",
]
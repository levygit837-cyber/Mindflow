"""Orchestrator pipeline interfaces.

Provides contracts for Task Thinking components:
tasker, scheduler, resolver, synthesizer, scorer,
plus core orchestrator, personality management, and delegation contracts.
"""

from omnimind_backend.agents.interfaces.orchestrator.core import OrchestratorCoreContract
from omnimind_backend.agents.interfaces.orchestrator.tasker import TaskerProtocol
from omnimind_backend.agents.interfaces.orchestrator.resolver import ResolverProtocol
from omnimind_backend.agents.interfaces.orchestrator.scheduler import SchedulerProtocol
from omnimind_backend.agents.interfaces.orchestrator.scorer import ScorerProtocol
from omnimind_backend.agents.interfaces.orchestrator.synthesizer import SynthesizerProtocol
from omnimind_backend.agents.interfaces.orchestrator.personality import PersonalityManagerContract
from omnimind_backend.agents.interfaces.orchestrator.delegation_manager import DelegationManagerContract

__all__ = [
    "OrchestratorCoreContract",
    "PersonalityManagerContract",
    "DelegationManagerContract",
    "TaskerProtocol",
    "SchedulerProtocol",
    "ResolverProtocol",
    "SynthesizerProtocol",
    "ScorerProtocol",
]

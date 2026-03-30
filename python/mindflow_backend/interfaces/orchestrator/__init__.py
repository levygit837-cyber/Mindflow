"""Orchestrator pipeline interfaces.

Provides contracts for Task Thinking components:
tasker, scheduler, resolver, synthesizer, scorer,
plus core orchestrator, personality management, and delegation contracts.
"""

from mindflow_backend.interfaces.orchestrator.core import OrchestratorCoreContract
from mindflow_backend.interfaces.orchestrator.tasker import TaskerProtocol
from mindflow_backend.interfaces.orchestrator.resolver import ResolverProtocol
from mindflow_backend.interfaces.orchestrator.scheduler import SchedulerProtocol
from mindflow_backend.interfaces.orchestrator.scorer import ScorerProtocol
from mindflow_backend.interfaces.orchestrator.synthesizer import SynthesizerProtocol
from mindflow_backend.interfaces.orchestrator.personality import PersonalityManagerContract
from mindflow_backend.interfaces.orchestrator.delegation_manager import DelegationManagerContract

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

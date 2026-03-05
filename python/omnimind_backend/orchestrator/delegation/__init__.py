"""Delegation sub-package — agent task execution."""
from omnimind_backend.orchestrator.delegation.engine import DelegationEngine, get_delegation_engine

__all__ = ["DelegationEngine", "get_delegation_engine"]

"""Compatibility re-export for DelegationEngine (adapter only).

Newer code lives under `mindflow_backend.orchestrator.delegation.engine`, but some
modules import `mindflow_backend.orchestrator.delegation_engine`.
"""

from __future__ import annotations

from mindflow_backend.orchestrator.delegation.engine import DelegationEngine, get_delegation_engine

__all__ = ["DelegationEngine", "get_delegation_engine"]

"""Backward-compatibility shim — decomposition logic has moved to
``mindflow_backend.decomposition``.

All imports are forwarded so that existing code that references
``orchestrator.decomposition.*`` continues to work during the migration.
"""

from __future__ import annotations

from mindflow_backend.decomposition.engine import DecompositionEngine
from mindflow_backend.decomposition.pipeline.resolver import ContextAwareResolver
from mindflow_backend.decomposition.pipeline.scheduler import SemanticScheduler as SchedulerV2
from mindflow_backend.decomposition.pipeline.synthesizer import TaskSynthesizer as SynthesizerV2

# Forward the canonical implementations from the new package
from mindflow_backend.decomposition.pipeline.tasker import EnhancedTasker as TaskerV2
from mindflow_backend.decomposition.scoring import TaskScorer

__all__ = [
    "TaskerV2",
    "ContextAwareResolver",
    "SchedulerV2",
    "SynthesizerV2",
    "TaskScorer",
    "DecompositionEngine",
]

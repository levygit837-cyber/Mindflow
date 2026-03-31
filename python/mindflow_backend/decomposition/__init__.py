"""MindFlow Decomposition Package.

Standalone pipeline that breaks complex requests into a Task DAG,
executes each sub-task via the appropriate agent, and synthesises
the results.  Lives outside ``orchestrator/`` so the routing logic
stays decoupled from the execution pipeline.

Hierarchy
---------
decomposition/
  engine.py        ← DecompositionEngine (coordinates all stages)
  pipeline/        ← concrete pipeline stages
    tasker.py      ← EnhancedTasker  (decompose → MainTaskContract + [SubTaskContract])
    resolver.py    ← ContextAwareResolver  (resolve one sub-task, store context)
    scheduler.py   ← SemanticScheduler  (topological sort by dependency UUIDs)
    synthesizer.py ← TaskSynthesizer  (combine validated results → SynthesisContract)
  context/         ← semantic context sharing between sub-tasks
    __init__.py    ← re-exports SemanticContextManager
  scoring/         ← validation scoring
    __init__.py    ← compute_task_score, TaskScorer
  utils/           ← shared helpers
    __init__.py
"""

from __future__ import annotations

from mindflow_backend.decomposition.engine import DecompositionEngine
from mindflow_backend.decomposition.pipeline.resolver import ContextAwareResolver
from mindflow_backend.decomposition.pipeline.scheduler import SemanticScheduler
from mindflow_backend.decomposition.pipeline.synthesizer import TaskSynthesizer
from mindflow_backend.decomposition.pipeline.tasker import EnhancedTasker
from mindflow_backend.decomposition.scoring import TaskScorer, compute_task_score

__all__ = [
    "DecompositionEngine",
    "EnhancedTasker",
    "ContextAwareResolver",
    "SemanticScheduler",
    "TaskSynthesizer",
    "TaskScorer",
    "compute_task_score",
]

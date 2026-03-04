"""Composite system prompts.

Pre-built combinations of core and specialized prompts for common use cases.
These provide backward compatibility and examples of prompt composition.
"""

from __future__ import annotations

# Composite prompts
from omnimind_backend.agents.prompts.composite.full_analyst import FULL_ANALYST_PROMPT
from omnimind_backend.agents.prompts.composite.full_coder import FULL_CODER_PROMPT
from omnimind_backend.agents.prompts.composite.full_orchestrator import FULL_ORCHESTRATOR_PROMPT

__all__ = [
    "FULL_ANALYST_PROMPT",
    "FULL_CODER_PROMPT",
    "FULL_ORCHESTRATOR_PROMPT",
]

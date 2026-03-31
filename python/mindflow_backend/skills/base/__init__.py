"""Base components for Skills system."""

from .executor import SkillExecutor
from .skill import BaseSkill

__all__ = [
    "BaseSkill",
    "SkillExecutor",
]

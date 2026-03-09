"""Base components for Skills system."""

from .skill import BaseSkill
from .executor import SkillExecutor

__all__ = [
    "BaseSkill",
    "SkillExecutor",
]

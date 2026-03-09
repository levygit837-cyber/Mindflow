"""Personality management interfaces.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.personality
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import PersonalitySpecialistSelector, PersonalityRuleEngine
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.agents.personality import (
    PersonalitySpecialistSelector,
    PersonalityRuleEngine,
)

# Maintain backward compatibility
__all__ = [
    "PersonalitySpecialistSelector",
    "PersonalityRuleEngine",
]

"""Specialist management interfaces.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.specialist
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import SpecialistSelector, RuleEngine
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.agents.specialist import SpecialistSelector, RuleEngine, SpecialistCache as Cache

# Maintain backward compatibility
__all__ = ["SpecialistSelector", "RuleEngine", "Cache"]

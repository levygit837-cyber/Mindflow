"""Specialist tool schemas organized by agent expertise.

Provides schemas specific to each agent type:
- research/: Web search, browser automation, source validation schemas
- analyst/: Code analysis, quality metrics, security scanning schemas  
- coder/: Filesystem operations, shell commands, architecture schemas
- common/: Shared tool schemas across agent types
"""

from __future__ import annotations

# Import specialist schemas when needed
# from .research import *
# from .analyst import *
# from .coder import *
# from .common import *

__all__ = [
    "research",
    "analyst", 
    "coder",
    "common",
]

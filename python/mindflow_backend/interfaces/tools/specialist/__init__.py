"""Specialist tool interfaces organized by agent expertise.

Provides interfaces specific to each agent type:
- research/: Web search, browser automation, source validation interfaces
- analyst/: Code analysis, quality metrics, security scanning interfaces  
- coder/: Filesystem operations, shell commands, architecture interfaces
- common/: Shared tool interfaces across agent types
"""

from __future__ import annotations

# Import specialist interfaces when needed
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

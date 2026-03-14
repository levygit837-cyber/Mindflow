"""Specialist tools organized by agent expertise.

Each subdirectory contains tools specific to an agent type:
- research/: Web search, browser automation, source validation
- analyst/: Code analysis, quality metrics, security scanning
- coder/: Filesystem operations, shell commands, architecture tools
- common/: Shared tools across agent types (AI, data, integration, web)
"""

from __future__ import annotations

# Lazy imports to prevent circular dependencies
# Import specific tools when needed

__all__ = [
    "research",
    "analyst", 
    "coder",
    "common",
]

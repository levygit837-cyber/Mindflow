"""Output Styles system for MindFlow agents.

This module provides the output styles system that allows customizing
how agents respond to users, controlling tone, verbosity, and behavior.

Inspired by Claude Code's Output Styles system.
"""

from __future__ import annotations

from mindflow_backend.agents.prompts.styles.manager import OutputStyleManager

__all__ = ["OutputStyleManager"]
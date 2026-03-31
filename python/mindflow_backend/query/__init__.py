"""QueryEngine & Context Management for MindFlow.

Mirrors Claude Code's QueryEngine architecture:
- QueryEngine: orchestrates query lifecycle with budget management
- ContextBuilder: builds context from multiple providers
- Context providers: git, file, memory, MCP
- TokenBudget: manages context window budget

Design principles:
- Providers are pluggable and independent
- Budget is enforced at every level
- Context is built incrementally and can be compressed
"""

from mindflow_backend.query.engine import QueryEngine
from mindflow_backend.query.context_builder import ContextBuilder
from mindflow_backend.query.budget import TokenBudget

__all__ = ["QueryEngine", "ContextBuilder", "TokenBudget"]
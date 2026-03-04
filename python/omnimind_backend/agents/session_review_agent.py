"""Shim de compatibilidade para o import path de session_review_service.py.

A implementação canônica está em agents/review/agent.py.
Este módulo re-exporta get_session_review_agent para backward compatibility.
"""

from __future__ import annotations

from omnimind_backend.agents.review.agent import (
    SessionReviewAgentImplementation,
    get_session_review_agent,
)

__all__ = ["SessionReviewAgentImplementation", "get_session_review_agent"]

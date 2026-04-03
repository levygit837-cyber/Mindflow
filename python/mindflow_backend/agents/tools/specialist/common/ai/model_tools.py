"""Compatibility wrapper for canonical AI tool implementations."""

from mindflow_backend.agents.tools.ai.model_tools import EmbeddingTool, LocalModelTool

__all__ = ["LocalModelTool", "EmbeddingTool"]

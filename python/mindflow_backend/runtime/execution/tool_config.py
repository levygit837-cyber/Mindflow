"""Tool execution configuration with feature flags.

This module provides the configuration class for tool execution,
including feature flags and execution parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mindflow_backend.runtime.feature_flags import FeatureFlags


@dataclass
class ToolExecutionConfig:
    """Configuration for tool execution.

    Attributes:
        enable_streaming_execution: Whether to use streaming tool execution
        enable_concurrent_execution: Whether to enable concurrent tool execution
        max_concurrent: Maximum number of concurrent tool executions
        max_turn_result_chars: Maximum characters for tool results per turn
        max_result_size_chars_per_tool: Per-tool result size limit
        result_store_dir: Directory for persisting oversized tool results
    """

    enable_streaming_execution: bool = field(
        default_factory=lambda: FeatureFlags.streaming_tool_execution_enabled()
    )
    enable_concurrent_execution: bool = field(
        default_factory=lambda: FeatureFlags.concurrent_tool_execution_enabled()
    )
    max_concurrent: int = 5
    max_turn_result_chars: int = 250_000
    max_result_size_chars_per_tool: int | None = None
    result_store_dir: str | None = None

    @classmethod
    def from_environment(cls) -> "ToolExecutionConfig":
        """Create config from environment variables and feature flags.

        Returns:
            ToolExecutionConfig with values from environment
        """
        return cls()

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Dictionary representation of the config
        """
        return {
            "enable_streaming_execution": self.enable_streaming_execution,
            "enable_concurrent_execution": self.enable_concurrent_execution,
            "max_concurrent": self.max_concurrent,
            "max_turn_result_chars": self.max_turn_result_chars,
            "max_result_size_chars_per_tool": self.max_result_size_chars_per_tool,
            "result_store_dir": self.result_store_dir,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolExecutionConfig":
        """Create config from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            ToolExecutionConfig instance
        """
        return cls(
            enable_streaming_execution=data.get(
                "enable_streaming_execution",
                FeatureFlags.streaming_tool_execution_enabled(),
            ),
            enable_concurrent_execution=data.get(
                "enable_concurrent_execution",
                FeatureFlags.concurrent_tool_execution_enabled(),
            ),
            max_concurrent=data.get("max_concurrent", 5),
            max_turn_result_chars=data.get("max_turn_result_chars", 250_000),
            max_result_size_chars_per_tool=data.get("max_result_size_chars_per_tool"),
            result_store_dir=data.get("result_store_dir"),
        )

"""Feature flags for gradual rollout of new features.

This module provides feature flag management for the MindFlow backend,
allowing gradual rollout and A/B testing of new features.
"""

from __future__ import annotations

import os
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class FeatureFlags:
    """Feature flag manager.

    Reads flags from environment variables and provides a clean API
    for checking feature availability.
    """

    # Unified Execution Engine
    ENABLE_UNIFIED_ENGINE = "ENABLE_UNIFIED_ENGINE"

    # Team Protocol
    ENABLE_TEAM_SESSIONS = "ENABLE_TEAM_SESSIONS"

    # Communication Bus
    ENABLE_COMMUNICATION_BUS = "ENABLE_COMMUNICATION_BUS"

    # Deep Work
    ENABLE_DEEP_WORK = "ENABLE_DEEP_WORK"

    @staticmethod
    def is_enabled(flag_name: str, default: bool = False) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag_name: Name of the feature flag
            default: Default value if flag is not set

        Returns:
            True if enabled, False otherwise
        """
        value = os.environ.get(flag_name)

        if value is None:
            return default

        # Parse boolean values
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        if value.lower() in ("false", "0", "no", "off"):
            return False

        # Parse percentage rollout (e.g., "50" means 50% of requests)
        try:
            percentage = int(value)
            if 0 <= percentage <= 100:
                # Use session_id hash for consistent rollout
                # For now, just return True if percentage >= 50
                return percentage >= 50
        except ValueError:
            pass

        _logger.warning(
            "invalid_feature_flag_value",
            flag=flag_name,
            value=value,
        )
        return default

    @staticmethod
    def get_rollout_percentage(flag_name: str) -> int:
        """Get rollout percentage for a feature flag.

        Args:
            flag_name: Name of the feature flag

        Returns:
            Percentage (0-100) or 0 if not set
        """
        value = os.environ.get(flag_name)

        if value is None:
            return 0

        if value.lower() in ("true", "1", "yes", "on"):
            return 100

        if value.lower() in ("false", "0", "no", "off"):
            return 0

        try:
            percentage = int(value)
            return max(0, min(100, percentage))
        except ValueError:
            return 0

    @classmethod
    def unified_engine_enabled(cls) -> bool:
        """Check if unified execution engine is enabled."""
        return cls.is_enabled(cls.ENABLE_UNIFIED_ENGINE, default=False)

    @classmethod
    def team_sessions_enabled(cls) -> bool:
        """Check if team sessions are enabled."""
        return cls.is_enabled(cls.ENABLE_TEAM_SESSIONS, default=False)

    @classmethod
    def communication_bus_enabled(cls) -> bool:
        """Check if communication bus is enabled."""
        return cls.is_enabled(cls.ENABLE_COMMUNICATION_BUS, default=False)

    @classmethod
    def deep_work_enabled(cls) -> bool:
        """Check if deep work is enabled."""
        return cls.is_enabled(cls.ENABLE_DEEP_WORK, default=True)

    @classmethod
    def get_all_flags(cls) -> dict[str, Any]:
        """Get all feature flags and their current values.

        Returns:
            Dictionary of flag names and values
        """
        return {
            "unified_engine": cls.unified_engine_enabled(),
            "team_sessions": cls.team_sessions_enabled(),
            "communication_bus": cls.communication_bus_enabled(),
            "deep_work": cls.deep_work_enabled(),
            "rollout_percentages": {
                "unified_engine": cls.get_rollout_percentage(cls.ENABLE_UNIFIED_ENGINE),
                "team_sessions": cls.get_rollout_percentage(cls.ENABLE_TEAM_SESSIONS),
            },
        }

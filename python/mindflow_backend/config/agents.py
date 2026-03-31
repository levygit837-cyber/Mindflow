"""Agent configuration settings.

Centralized configuration for agent behavior,
thresholds, and system parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

from mindflow_backend.agents._base import SandboxMode, ThinkingLevel


@dataclass
class AgentConfig:
    """Configuration for agent system behavior."""
    
    # Default settings
    default_thinking_level: ThinkingLevel = ThinkingLevel.MEDIUM
    default_sandbox: SandboxMode = SandboxMode.NONE
    default_timeout_seconds: int = 300
    
    # Cache settings
    cache_size: int = 1000
    cache_ttl_seconds: int = 3600
    
    # Context retrieval
    max_context_results: int = 10
    context_similarity_threshold: float = 0.3
    max_context_window: int = 100000
    
    # Personality selection
    personality_cache_size: int = 500
    personality_confidence_threshold: float = 0.7
    max_personality_switches_per_session: int = 5
    
    # Session review
    review_window_size_tokens: int = 5000
    review_quality_threshold: float = 0.8
    max_review_time_minutes: int = 10
    
    # Performance
    max_concurrent_agents: int = 10
    agent_response_timeout: int = 120
    
    # Logging
    log_level: str = "INFO"
    enable_performance_logging: bool = True
    
    # Feature flags
    enable_context_caching: bool = True
    enable_personality_switching: bool = True
    enable_session_review: bool = True
    enable_semantic_search: bool = True


# Global configuration instance
_config: AgentConfig | None = None


def get_agent_config() -> AgentConfig:
    """Get the global agent configuration."""
    global _config
    if _config is None:
        _config = AgentConfig()
    return _config


def set_agent_config(config: AgentConfig) -> None:
    """Set the global agent configuration."""
    global _config
    _config = config


def update_agent_config(**kwargs) -> None:
    """Update specific configuration values."""
    config = get_agent_config()
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            raise ValueError(f"Unknown configuration key: {key}")

"""Output Style schemas for MindFlow.

This module defines the configuration and types for output styles,
inspired by Claude Code's Output Styles system.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class OutputStyleSource(str, Enum):
    """Source of an output style configuration."""
    
    BUILT_IN = "built-in"
    PLUGIN = "plugin"
    USER_SETTINGS = "userSettings"
    PROJECT_SETTINGS = "projectSettings"
    POLICY_SETTINGS = "policySettings"


class OutputStyleConfig(BaseModel):
    """Configuration for an output style.
    
    Output styles define how the agent responds to users,
    controlling tone, verbosity, and behavior.
    """
    
    name: str = Field(
        ...,
        description="Unique identifier for the style",
        min_length=1,
        max_length=64,
    )
    
    description: str = Field(
        ...,
        description="Human-readable description of the style",
        min_length=1,
        max_length=256,
    )
    
    prompt: str = Field(
        ...,
        description="The style instructions to inject into the system prompt",
        min_length=1,
    )
    
    source: OutputStyleSource = Field(
        ...,
        description="Where this style comes from",
    )
    
    keep_coding_instructions: bool = Field(
        default=True,
        description="Whether to preserve coding instructions when this style is active",
    )
    
    force_for_plugin: bool = Field(
        default=False,
        description="If True, this style is automatically applied when its plugin is enabled",
    )
    
    file_path: Optional[Path] = Field(
        default=None,
        description="Path to the .md file that defines this style (for custom styles)",
    )

    class Config:
        """Pydantic configuration."""
        
        json_schema_extra = {
            "example": {
                "name": "explanatory",
                "description": "Explains decisions in detail with step-by-step reasoning",
                "prompt": "When providing solutions, explain your reasoning step-by-step.",
                "source": "built-in",
                "keep_coding_instructions": True,
                "force_for_plugin": False,
            }
        }


class OutputStyles(str, Enum):
    """Built-in output style names."""
    
    DEFAULT = "default"
    EXPLANATORY = "explanatory"
    LEARNING = "learning"
    CONCISE = "concise"


# Default style constants
DEFAULT_OUTPUT_STYLE_NAME = OutputStyles.DEFAULT.value
DEFAULT_OUTPUT_STYLE_LABEL = "Default"
DEFAULT_OUTPUT_STYLE_DESCRIPTION = (
    "MindFlow completes tasks efficiently and provides concise responses"
)
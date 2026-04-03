"""Markdown skill configuration schemas."""

from typing import Any
from pydantic import Field, validator
from mindflow_backend.schemas.skills.base import SkillConfiguration


class MarkdownSkillConfig(SkillConfiguration):
    """Configuration for skills loaded from Markdown files."""
    
    display_name: str | None = Field(None, description="Display name for the skill")
    description: str = Field(..., description="Skill description")
    when_to_use: str | None = Field(None, description="When to use this skill")
    arguments: list[str] = Field(default_factory=list, description="Skill arguments")
    allowed_tools: list[str] = Field(default_factory=list, description="Allowed tools for this skill")
    paths: list[str] = Field(default_factory=list, description="Activation paths (glob patterns)")
    user_invocable: bool = Field(default=True, description="Whether user can explicitly invoke this skill")
    version: str = Field(default="1.0.0", description="Skill version")
    model: str | None = Field(None, description="Specific model to use for this skill")
    disable_model_invocation: bool = Field(default=False, description="Whether to disable model invocation")
    context: str | None = Field(None, description="Execution context (e.g., 'fork')")
    agent: str | None = Field(None, description="Specific agent to use")
    effort: str | int | None = Field(None, description="Effort level or value")

    @validator('display_name', pre=True, always=True)
    def set_display_name(cls, v, values):
        if v is None and 'name' in values:
            return values['name']
        return v

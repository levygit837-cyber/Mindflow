"""Base schemas for Skills system."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator


class SkillType(str, Enum):
    """Base skill types."""
    ANALYSIS = "analysis"
    CODING = "coding"
    RESEARCH = "research"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    CUSTOM = "custom"


class SkillCategory(str, Enum):
    """Skill categories for organization."""
    CORE = "core"
    SPECIALIZED = "specialized"
    DOMAIN_SPECIFIC = "domain_specific"
    UTILITY = "utility"


class SkillStatus(str, Enum):
    """Skill status in the system."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    DEVELOPMENT = "development"
    TESTING = "testing"


class SkillPriority(str, Enum):
    """Skill execution priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SkillMetadata(BaseModel):
    """Metadata for a skill."""
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    version: str = Field(default="1.0.0", description="Skill version")
    author: str | None = Field(None, description="Skill author")
    tags: list[str] = Field(default_factory=list, description="Skill tags")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SkillConfiguration(BaseModel):
    """Base configuration for skills."""
    enabled: bool = Field(default=True, description="Whether skill is enabled")
    priority: SkillPriority = Field(default=SkillPriority.MEDIUM, description="Execution priority")
    timeout_seconds: int = Field(default=300, description="Execution timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    custom_settings: dict[str, Any] = Field(default_factory=dict, description="Custom settings")
    
    @validator('timeout_seconds')
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v


class SkillInput(BaseModel):
    """Input data for skill execution."""
    data: dict[str, Any] = Field(..., description="Input data")
    context: dict[str, Any] | None = Field(None, description="Execution context")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Skill parameters")
    metadata: dict[str, Any] | None = Field(None, description="Input metadata")


class SkillOutput(BaseModel):
    """Output data from skill execution."""
    success: bool = Field(..., description="Whether execution was successful")
    data: dict[str, Any] | None = Field(None, description="Output data")
    error: str | None = Field(None, description="Error message if failed")
    metadata: dict[str, Any] | None = Field(None, description="Output metadata")
    execution_time_ms: int | None = Field(None, description="Execution time in milliseconds")


class SkillResult(BaseModel):
    """Complete result of skill execution."""
    skill_name: str = Field(..., description="Name of executed skill")
    input: SkillInput = Field(..., description="Input provided to skill")
    output: SkillOutput = Field(..., description="Output from skill")
    execution_id: str = Field(..., description="Unique execution identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SkillBase(BaseModel):
    """Base model for all skills."""
    skill_type: SkillType = Field(..., description="Type of skill")
    category: SkillCategory = Field(..., description="Skill category")
    status: SkillStatus = Field(default=SkillStatus.ACTIVE, description="Skill status")
    metadata: SkillMetadata = Field(..., description="Skill metadata")
    configuration: SkillConfiguration = Field(default_factory=SkillConfiguration, description="Skill configuration")
    
    class Config:
        use_enum_values = True

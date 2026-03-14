"""Registry schemas for Skills system."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from .base import SkillType, SkillCategory, SkillStatus, SkillMetadata


class SkillRegistration(BaseModel):
    """Skill registration request."""
    skill_name: str = Field(..., description="Name of the skill to register")
    skill_type: SkillType = Field(..., description="Type of skill")
    category: SkillCategory = Field(..., description="Skill category")
    metadata: SkillMetadata = Field(..., description="Skill metadata")
    implementation_path: str = Field(..., description="Path to skill implementation")
    configuration_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for configuration")
    dependencies: List[str] = Field(default_factory=list, description="Skill dependencies")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill_name": "CodeAnalyzer",
                "skill_type": "analysis",
                "category": "core",
                "metadata": {
                    "name": "Code Analyzer",
                    "description": "Analyzes code structure and dependencies",
                    "version": "1.0.0",
                    "author": "MindFlow Team",
                    "tags": ["analysis", "static", "code"]
                },
                "implementation_path": "mindflow_backend.skills.core.analysis.CodeAnalyzer",
                "configuration_schema": {
                    "type": "object",
                    "properties": {
                        "analysis_depth": {"type": "string", "enum": ["shallow", "standard", "deep"]},
                        "include_dependencies": {"type": "boolean"}
                    }
                },
                "dependencies": []
            }
        }


class SkillDiscovery(BaseModel):
    """Skill discovery request/response."""
    query: Optional[str] = Field(None, description="Search query for skill discovery")
    skill_types: Optional[List[SkillType]] = Field(None, description="Filter by skill types")
    categories: Optional[List[SkillCategory]] = Field(None, description="Filter by categories")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    status: Optional[SkillStatus] = Field(default=SkillStatus.ACTIVE, description="Filter by status")
    limit: Optional[int] = Field(default=50, description="Maximum results to return")
    offset: Optional[int] = Field(default=0, description="Results offset for pagination")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "code analysis",
                "skill_types": ["analysis"],
                "categories": ["core"],
                "tags": ["static", "code"],
                "status": "active",
                "limit": 20,
                "offset": 0
            }
        }


class SkillRegistryEntry(BaseModel):
    """Entry in the skill registry."""
    id: str = Field(..., description="Unique skill identifier")
    registration: SkillRegistration = Field(..., description="Skill registration data")
    registered_at: datetime = Field(default_factory=datetime.now, description="Registration timestamp")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    usage_count: int = Field(default=0, description="Number of times skill was used")
    success_rate: float = Field(default=1.0, description="Success rate (0.0 to 1.0)")
    average_execution_time_ms: float = Field(default=0.0, description="Average execution time in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "id": "skill_code_analyzer_001",
                "registration": {
                    "skill_name": "CodeAnalyzer",
                    "skill_type": "analysis",
                    "category": "core"
                },
                "registered_at": "2024-01-01T00:00:00Z",
                "last_updated": "2024-01-15T12:30:00Z",
                "usage_count": 150,
                "success_rate": 0.95,
                "average_execution_time_ms": 2500.0
            }
        }


class SkillQuery(BaseModel):
    """Query for skill selection."""
    requirements: Dict[str, Any] = Field(..., description="Skill requirements")
    context: Optional[Dict[str, Any]] = Field(None, description="Execution context")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Execution constraints")
    
    class Config:
        json_schema_extra = {
            "example": {
                "requirements": {
                    "skill_type": "analysis",
                    "capabilities": ["static_analysis", "dependency_mapping"],
                    "language": "python"
                },
                "context": {
                    "project_type": "web_application",
                    "team_size": "medium"
                },
                "preferences": {
                    "priority": "high",
                    "include_recommendations": True
                },
                "constraints": {
                    "max_execution_time": 300,
                    "memory_limit": "1GB"
                }
            }
        }


class SkillFilter(BaseModel):
    """Filter for skill searches."""
    skill_types: Optional[List[SkillType]] = Field(None, description="Filter by skill types")
    categories: Optional[List[SkillCategory]] = Field(None, description="Filter by categories")
    status: Optional[List[SkillStatus]] = Field(None, description="Filter by status")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    authors: Optional[List[str]] = Field(None, description="Filter by authors")
    date_range: Optional[Dict[str, datetime]] = Field(None, description="Filter by date range")
    performance_threshold: Optional[float] = Field(None, description="Minimum success rate")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "skill_types": ["analysis", "coding"],
                "categories": ["core"],
                "status": ["active"],
                "tags": ["python", "web"],
                "performance_threshold": 0.8
            }
        }


class SkillRecommendation(BaseModel):
    """Skill recommendation result."""
    skill: SkillRegistryEntry = Field(..., description="Recommended skill")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    reasoning: str = Field(..., description="Reasoning for recommendation")
    alternatives: List[SkillRegistryEntry] = Field(default_factory=list, description="Alternative skills")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill": {
                    "id": "skill_code_analyzer_001",
                    "registration": {"skill_name": "CodeAnalyzer"}
                },
                "confidence": 0.92,
                "reasoning": "Best match for Python code analysis with high success rate",
                "alternatives": []
            }
        }

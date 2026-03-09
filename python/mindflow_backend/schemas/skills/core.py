"""Core skill schemas."""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from .base import SkillConfiguration


class CoreSkillType(str, Enum):
    """Core skill types enumeration."""
    ANALYSIS = "analysis"
    CODING = "coding"
    RESEARCH = "research"


class AnalysisSkillConfig(SkillConfiguration):
    """Configuration for analysis skills."""
    analysis_depth: str = Field(default="standard", description="Analysis depth: shallow, standard, deep")
    include_dependencies: bool = Field(default=True, description="Include dependency analysis")
    generate_summary: bool = Field(default=True, description="Generate analysis summary")
    export_format: str = Field(default="json", description="Export format: json, yaml, markdown")
    
    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "priority": "medium",
                "timeout_seconds": 300,
                "max_retries": 3,
                "analysis_depth": "standard",
                "include_dependencies": True,
                "generate_summary": True,
                "export_format": "json"
            }
        }


class CodingSkillConfig(SkillConfiguration):
    """Configuration for coding skills."""
    language: str = Field(default="python", description="Target programming language")
    code_style: str = Field(default="pep8", description="Code style guide")
    include_tests: bool = Field(default=True, description="Generate unit tests")
    include_docs: bool = Field(default=True, description="Generate documentation")
    validate_syntax: bool = Field(default=True, description="Validate syntax before output")
    auto_format: bool = Field(default=True, description="Auto-format generated code")
    
    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "priority": "high",
                "timeout_seconds": 600,
                "max_retries": 2,
                "language": "python",
                "code_style": "pep8",
                "include_tests": True,
                "include_docs": True,
                "validate_syntax": True,
                "auto_format": True
            }
        }


class ResearchSkillConfig(SkillConfiguration):
    """Configuration for research skills."""
    search_sources: List[str] = Field(
        default_factory=lambda: ["local", "web", "documentation"],
        description="Search sources to use"
    )
    max_results: int = Field(default=20, description="Maximum results to return")
    include_sources: bool = Field(default=True, description="Include source references")
    credibility_threshold: float = Field(default=0.7, description="Minimum credibility score")
    synthesis_mode: str = Field(default="comprehensive", description="Synthesis mode: quick, balanced, comprehensive")
    
    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "priority": "medium",
                "timeout_seconds": 400,
                "max_retries": 3,
                "search_sources": ["local", "web", "documentation"],
                "max_results": 20,
                "include_sources": True,
                "credibility_threshold": 0.7,
                "synthesis_mode": "comprehensive"
            }
        }


class CoreSkillDefinition(BaseModel):
    """Definition for core skills."""
    skill_type: CoreSkillType = Field(..., description="Core skill type")
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    capabilities: List[str] = Field(..., description="Skill capabilities")
    supported_languages: List[str] = Field(default_factory=list, description="Supported languages")
    required_tools: List[str] = Field(default_factory=list, description="Required tools")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Default configuration")
    
    class Config:
        schema_extra = {
            "example": {
                "skill_type": "analysis",
                "name": "Code Analysis",
                "description": "Analyzes code structure and dependencies",
                "capabilities": ["static_analysis", "dependency_mapping", "complexity_analysis"],
                "supported_languages": ["python", "javascript", "typescript"],
                "required_tools": ["ast_parser", "graph_analyzer"],
                "configuration": {
                    "analysis_depth": "standard",
                    "include_dependencies": True
                }
            }
        }

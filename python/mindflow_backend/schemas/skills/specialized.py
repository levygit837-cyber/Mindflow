"""Specialized skill schemas."""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from .base import SkillConfiguration


class SpecializedSkillType(str, Enum):
    """Specialized skill types enumeration."""
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"


class SecuritySkillConfig(SkillConfiguration):
    """Configuration for security skills."""
    scan_types: List[str] = Field(
        default_factory=lambda: ["vulnerability", "dependency_check", "code_analysis"],
        description="Types of security scans to perform"
    )
    severity_threshold: str = Field(default="medium", description="Minimum severity level: low, medium, high, critical")
    compliance_standards: List[str] = Field(default_factory=list, description="Compliance standards to check")
    include_sast: bool = Field(default=True, description="Include static application security testing")
    include_dast: bool = Field(default=False, description="Include dynamic application security testing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "priority": "high",
                "timeout_seconds": 900,
                "max_retries": 2,
                "scan_types": ["vulnerability", "dependency_check", "code_analysis"],
                "severity_threshold": "medium",
                "compliance_standards": ["OWASP_TOP_10", "SOC2"],
                "include_sast": True,
                "include_dast": False
            }
        }


class ArchitectureSkillConfig(SkillConfiguration):
    """Configuration for architecture skills."""
    analysis_scope: str = Field(default="full_system", description="Analysis scope: component, module, full_system")
    design_patterns: List[str] = Field(default_factory=list, description="Design patterns to evaluate")
    generate_diagrams: bool = Field(default=True, description="Generate architecture diagrams")
    include_scalability: bool = Field(default=True, description="Include scalability analysis")
    include_performance: bool = Field(default=True, description="Include performance considerations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "priority": "medium",
                "timeout_seconds": 600,
                "max_retries": 3,
                "analysis_scope": "full_system",
                "design_patterns": ["MVC", "Microservices", "Event-Driven"],
                "generate_diagrams": True,
                "include_scalability": True,
                "include_performance": True
            }
        }


class TestingSkillConfig(SkillConfiguration):
    """Configuration for testing skills."""
    test_types: List[str] = Field(
        default_factory=lambda: ["unit", "integration"],
        description="Types of tests to generate"
    )
    coverage_threshold: float = Field(default=80.0, description="Minimum code coverage percentage")
    framework: str = Field(default="pytest", description="Testing framework to use")
    include_performance_tests: bool = Field(default=False, description="Include performance tests")
    include_security_tests: bool = Field(default=False, description="Include security tests")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "priority": "medium",
                "timeout_seconds": 400,
                "max_retries": 2,
                "test_types": ["unit", "integration"],
                "coverage_threshold": 80.0,
                "framework": "pytest",
                "include_performance_tests": False,
                "include_security_tests": False
            }
        }


class DocumentationSkillConfig(SkillConfiguration):
    """Configuration for documentation skills."""
    doc_types: List[str] = Field(
        default_factory=lambda: ["api", "readme", "inline"],
        description="Types of documentation to generate"
    )
    output_format: str = Field(default="markdown", description="Output format: markdown, html, pdf")
    include_examples: bool = Field(default=True, description="Include usage examples")
    include_diagrams: bool = Field(default=True, description="Include diagrams and charts")
    target_audience: str = Field(default="developers", description="Target audience: developers, users, business")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "priority": "low",
                "timeout_seconds": 300,
                "max_retries": 3,
                "doc_types": ["api", "readme", "inline"],
                "output_format": "markdown",
                "include_examples": True,
                "include_diagrams": True,
                "target_audience": "developers"
            }
        }


class SpecializedSkillDefinition(BaseModel):
    """Definition for specialized skills."""
    skill_type: SpecializedSkillType = Field(..., description="Specialized skill type")
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    domain: str = Field(..., description="Domain specialization")
    capabilities: List[str] = Field(..., description="Skill capabilities")
    expertise_level: str = Field(default="intermediate", description="Expertise level: beginner, intermediate, advanced, expert")
    dependencies: List[str] = Field(default_factory=list, description="Other skills this depends on")
    integrations: List[str] = Field(default_factory=list, description="External tool integrations")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Default configuration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill_type": "security",
                "name": "Security Vulnerability Scanner",
                "description": "Scans code for security vulnerabilities and compliance issues",
                "domain": "cybersecurity",
                "capabilities": ["vulnerability_scanning", "compliance_checking", "risk_assessment"],
                "expertise_level": "advanced",
                "dependencies": ["analysis"],
                "integrations": ["snyk", "owasp_zap"],
                "configuration": {
                    "severity_threshold": "medium",
                    "compliance_standards": ["OWASP_TOP_10"]
                }
            }
        }

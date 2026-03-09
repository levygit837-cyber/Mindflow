"""Execution schemas for Skills system."""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from .base import SkillInput, SkillOutput


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionContext(BaseModel):
    """Context for skill execution."""
    execution_id: str = Field(..., description="Unique execution identifier")
    skill_name: str = Field(..., description="Name of skill to execute")
    agent_id: Optional[str] = Field(None, description="Agent requesting execution")
    session_id: Optional[str] = Field(None, description="Session identifier")
    input_data: SkillInput = Field(..., description="Input data for execution")
    environment: Dict[str, Any] = Field(default_factory=dict, description="Execution environment variables")
    permissions: List[str] = Field(default_factory=list, description="Required permissions")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Execution constraints")
    
    class Config:
        schema_extra = {
            "example": {
                "execution_id": "exec_123456_001",
                "skill_name": "CodeAnalyzer",
                "agent_id": "agent_analyst_001",
                "session_id": "session_789",
                "input_data": {
                    "data": {"code": "def example(): pass"},
                    "parameters": {"analysis_depth": "standard"}
                },
                "environment": {"PYTHONPATH": "/app/src"},
                "permissions": ["read_files", "write_reports"],
                "constraints": {"max_memory": "1GB", "timeout": 300}
            }
        }


class ExecutionMetrics(BaseModel):
    """Metrics for skill execution."""
    start_time: datetime = Field(..., description="Execution start time")
    end_time: Optional[datetime] = Field(None, description="Execution end time")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    disk_io_mb: Optional[float] = Field(None, description="Disk I/O in MB")
    network_io_mb: Optional[float] = Field(None, description="Network I/O in MB")
    
    @validator('duration_ms')
    def calculate_duration(cls, v, values):
        if v is None and 'start_time' in values and 'end_time' in values and values['end_time']:
            start = values['start_time']
            end = values['end_time']
            v = int((end - start).total_seconds() * 1000)
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "start_time": "2024-01-01T10:00:00Z",
                "end_time": "2024-01-01T10:00:05Z",
                "duration_ms": 5000,
                "cpu_usage_percent": 25.5,
                "memory_usage_mb": 512.0,
                "disk_io_mb": 10.2,
                "network_io_mb": 0.0
            }
        }


class PerformanceMetrics(BaseModel):
    """Performance metrics aggregated over time."""
    skill_name: str = Field(..., description="Skill name")
    total_executions: int = Field(default=0, description="Total number of executions")
    successful_executions: int = Field(default=0, description="Number of successful executions")
    failed_executions: int = Field(default=0, description="Number of failed executions")
    success_rate: float = Field(default=0.0, description="Success rate (0.0 to 1.0)")
    average_duration_ms: float = Field(default=0.0, description="Average duration in milliseconds")
    min_duration_ms: Optional[float] = Field(None, description="Minimum duration")
    max_duration_ms: Optional[float] = Field(None, description="Maximum duration")
    p50_duration_ms: Optional[float] = Field(None, description="50th percentile duration")
    p95_duration_ms: Optional[float] = Field(None, description="95th percentile duration")
    p99_duration_ms: Optional[float] = Field(None, description="99th percentile duration")
    
    @validator('success_rate')
    def calculate_success_rate(cls, v, values):
        if 'total_executions' in values and values['total_executions'] > 0:
            successful = values.get('successful_executions', 0)
            total = values['total_executions']
            v = successful / total
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "skill_name": "CodeAnalyzer",
                "total_executions": 1000,
                "successful_executions": 950,
                "failed_executions": 50,
                "success_rate": 0.95,
                "average_duration_ms": 2500.0,
                "min_duration_ms": 500.0,
                "max_duration_ms": 8000.0,
                "p50_duration_ms": 2200.0,
                "p95_duration_ms": 5000.0,
                "p99_duration_ms": 6500.0
            }
        }


class ExecutionResult(BaseModel):
    """Result of skill execution."""
    execution_id: str = Field(..., description="Execution identifier")
    status: ExecutionStatus = Field(..., description="Execution status")
    output: Optional[SkillOutput] = Field(None, description="Execution output")
    error: Optional[str] = Field(None, description="Error message if failed")
    metrics: ExecutionMetrics = Field(..., description="Execution metrics")
    logs: List[str] = Field(default_factory=list, description="Execution logs")
    artifacts: Dict[str, Any] = Field(default_factory=dict, description="Generated artifacts")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "execution_id": "exec_123456_001",
                "status": "completed",
                "output": {
                    "success": True,
                    "data": {"analysis_result": "..."},
                    "execution_time_ms": 5000
                },
                "metrics": {
                    "start_time": "2024-01-01T10:00:00Z",
                    "end_time": "2024-01-01T10:00:05Z",
                    "duration_ms": 5000
                },
                "logs": ["Starting analysis...", "Analysis completed"],
                "artifacts": {"report_file": "analysis_report.json"}
            }
        }


class SkillExecution(BaseModel):
    """Complete skill execution record."""
    context: ExecutionContext = Field(..., description="Execution context")
    result: ExecutionResult = Field(..., description="Execution result")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionRequest(BaseModel):
    """Request to execute a skill."""
    skill_name: str = Field(..., description="Name of skill to execute")
    input_data: Dict[str, Any] = Field(..., description="Input data")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")
    context: Optional[Dict[str, Any]] = Field(None, description="Execution context")
    priority: str = Field(default="medium", description="Execution priority")
    timeout_seconds: Optional[int] = Field(None, description="Override default timeout")
    async_execution: bool = Field(default=False, description="Execute asynchronously")
    
    class Config:
        schema_extra = {
            "example": {
                "skill_name": "CodeAnalyzer",
                "input_data": {"code": "def example(): pass"},
                "parameters": {"analysis_depth": "standard"},
                "context": {"project": "my_app"},
                "priority": "high",
                "timeout_seconds": 600,
                "async_execution": True
            }
        }


class BatchExecutionRequest(BaseModel):
    """Request to execute multiple skills."""
    executions: List[ExecutionRequest] = Field(..., description="List of execution requests")
    execution_mode: str = Field(default="parallel", description="Execution mode: parallel, sequential")
    fail_fast: bool = Field(default=False, description="Stop on first failure")
    max_concurrent: int = Field(default=5, description="Maximum concurrent executions")
    
    class Config:
        schema_extra = {
            "example": {
                "executions": [
                    {
                        "skill_name": "CodeAnalyzer",
                        "input_data": {"code": "def example(): pass"}
                    },
                    {
                        "skill_name": "DocumentationGenerator",
                        "input_data": {"code": "def example(): pass"}
                    }
                ],
                "execution_mode": "parallel",
                "fail_fast": False,
                "max_concurrent": 3
            }
        }

"""Chain step definitions and execution results."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.orchestration.orchestrator import AgentType, ToolScope


class StepType(StrEnum):
    """Types of steps in a chain."""
    
    AGENT_EXECUTION = "agent_execution"
    TOOL_CALL = "tool_call"
    DATA_PROCESSING = "data_processing"
    CONDITION_CHECK = "condition_check"
    LOOP_CONTROL = "loop_control"
    PARALLEL_EXECUTION = "parallel_execution"
    CUSTOM = "custom"


class StepStatus(StrEnum):
    """Status of a step execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ChainStep(BaseModel):
    """Enhanced chain step with more detailed configuration."""
    
    step_id: str
    step_type: StepType
    agent: AgentType | None = None
    task: str = ""
    tools: list[ToolScope] = Field(default_factory=list)
    
    # Execution configuration
    timeout: float | None = Field(default=30.0, gt=0.0)
    retry_attempts: int = Field(default=3, ge=0)
    enable_streaming: bool = False
    
    # Dependencies and conditions
    depends_on: list[str] = Field(default_factory=list)
    condition: str | None = None  # Conditional execution logic
    parallel_group: str | None = None  # For parallel execution
    
    # Input/Output mapping
    input_mapping: dict[str, str] = Field(default_factory=dict)
    output_mapping: dict[str, str] = Field(default_factory=dict)
    required_inputs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    
    # Metadata
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    custom_parameters: dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class StepResult(BaseModel):
    """Result of a step execution."""
    
    step_id: str
    status: StepStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    execution_time: float = 0.0
    tokens_used: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # Execution details
    started_at: float | None = None
    completed_at: float | None = None
    retry_count: int = 0
    
    class Config:
        use_enum_values = True


class StepContext(BaseModel):
    """Context for step execution."""
    
    chain_id: str
    execution_id: str
    step_id: str
    global_state: dict[str, Any] = Field(default_factory=dict)
    step_state: dict[str, Any] = Field(default_factory=dict)
    
    # Execution metadata
    execution_order: int = 0
    parent_step: str | None = None
    parallel_group: str | None = None
    
    class Config:
        use_enum_values = True


class StepMetrics(BaseModel):
    """Metrics collected for a step."""
    
    step_id: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    total_tokens_used: int = 0
    last_execution_time: float | None = None
    
    class Config:
        use_enum_values = True
    
    def update_metrics(self, result: StepResult) -> None:
        """Update metrics with new execution result."""
        self.execution_count += 1
        
        if result.status == StepStatus.COMPLETED:
            self.success_count += 1
        elif result.status == StepStatus.FAILED:
            self.failure_count += 1
        
        self.total_execution_time += result.execution_time
        self.average_execution_time = self.total_execution_time / self.execution_count
        self.total_tokens_used += result.tokens_used
        self.last_execution_time = result.completed_at


class StepDependency(BaseModel):
    """Dependency relationship between steps."""
    
    step_id: str
    depends_on: str
    dependency_type: str = "completion"  # completion, success, failure
    condition: str | None = None
    
    class Config:
        use_enum_values = True


class StepTemplate(BaseModel):
    """Template for creating common step types."""
    
    template_id: str
    step_type: StepType
    name: str
    description: str
    default_parameters: dict[str, Any] = Field(default_factory=dict)
    required_parameters: list[str] = Field(default_factory=list)
    
    # Template structure
    step_template: dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
    
    def create_step(self, step_id: str, **kwargs) -> ChainStep:
        """Create a step from this template."""
        # Merge default parameters with provided parameters
        parameters = dict(self.default_parameters)
        parameters.update(kwargs)
        
        # Validate required parameters
        missing_params = set(self.required_parameters) - set(parameters.keys())
        if missing_params:
            raise ValueError(f"Missing required parameters: {missing_params}")
        
        # Create step from template
        step_data = dict(self.step_template)
        step_data.update(parameters)
        step_data["step_id"] = step_id
        
        return ChainStep(**step_data)


# Common step templates
COMMON_STEP_TEMPLATES = {
    "agent_execution": StepTemplate(
        template_id="agent_execution",
        step_type=StepType.AGENT_EXECUTION,
        name="Agent Execution",
        description="Execute a task using a specific agent",
        default_parameters={
            "timeout": 30.0,
            "retry_attempts": 3,
            "enable_streaming": False,
        },
        required_parameters=["agent", "task"],
        step_template={
            "step_type": StepType.AGENT_EXECUTION,
            "tools": [],
            "depends_on": [],
            "required_inputs": ["message"],
            "expected_outputs": ["response"],
        },
    ),
    
    "tool_call": StepTemplate(
        template_id="tool_call",
        step_type=StepType.TOOL_CALL,
        name="Tool Call",
        description="Execute a specific tool",
        default_parameters={
            "timeout": 15.0,
            "retry_attempts": 2,
        },
        required_parameters=["tool_name", "tool_parameters"],
        step_template={
            "step_type": StepType.TOOL_CALL,
            "depends_on": [],
            "required_inputs": ["tool_name", "tool_parameters"],
            "expected_outputs": ["tool_result"],
        },
    ),
    
    "condition_check": StepTemplate(
        template_id="condition_check",
        step_type=StepType.CONDITION_CHECK,
        name="Condition Check",
        description="Check a condition and branch execution",
        default_parameters={},
        required_parameters=["condition"],
        step_template={
            "step_type": StepType.CONDITION_CHECK,
            "depends_on": [],
            "required_inputs": ["condition"],
            "expected_outputs": ["condition_result"],
        },
    ),
}

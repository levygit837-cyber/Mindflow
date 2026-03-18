"""Conditional Workflow Chain - Demonstrates advanced chain patterns.

This chain shows how to build complex workflows with:
- Conditional branching based on analysis results
- Parallel execution of independent tasks
- Dynamic step selection based on context
- Error recovery and fallback paths
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.chains.base.chain import BaseChain, ChainConfig, ChainType, ChainStatus
from mindflow_backend.chains.base.step import ChainStep, StepResult, StepStatus, StepType
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    Priority,
    SandboxMode,
)

_logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ConditionalWorkflowConfig:
    chain_id: str = "conditional_workflow"
    enable_parallel_paths: bool = True
    fallback_on_failure: bool = True
    max_parallel_tasks: int = 3
    confidence_threshold: float = 0.7


class ConditionalWorkflowChain(BaseChain):
    """Advanced chain with conditional branching and parallel execution."""

    def __init__(self, config: ConditionalWorkflowConfig | None = None) -> None:
        self.config = config or ConditionalWorkflowConfig()
        chain_config = ChainConfig(
            chain_type=ChainType.CONDITIONAL,
            enable_parallel_execution=self.config.enable_parallel_paths,
            continue_on_step_failure=True,  # Allow fallback paths
            enable_metrics=True,
            enable_step_logging=True,
        )
        super().__init__(self.config.chain_id, chain_config, "Conditional workflow with dynamic branching")
        self.settings = get_settings()
        self._setup_workflow_steps()

    @property
    def chain_type(self) -> ChainType:
        return ChainType.CONDITIONAL

    def _setup_workflow_steps(self) -> None:
        """Setup the workflow steps with dependencies and conditions."""
        
        # Step 1: Initial Analysis (always runs)
        self.add_step(ChainStep(
            step_id="initial_analysis",
            step_type=StepType.AGENT_EXECUTION,
            agent=AgentType.ANALYST,
            task="Analyze request and determine workflow path",
            required_inputs=["message"],
            expected_outputs=["analysis_result", "complexity_score", "recommended_path"],
            timeout=30.0,
        ))

        # Step 2: Condition Check - determines which path to take
        self.add_step(ChainStep(
            step_id="path_selection",
            step_type=StepType.CONDITION_CHECK,
            task="Select execution path based on analysis",
            depends_on=["initial_analysis"],
            required_inputs=["analysis_result", "complexity_score"],
            expected_outputs=["selected_path", "parallel_tasks"],
            condition="complexity_score > 0.7",
            timeout=15.0,
        ))

        # Step 3a: Simple Path (low complexity)
        self.add_step(ChainStep(
            step_id="simple_execution",
            step_type=StepType.AGENT_EXECUTION,
            agent=AgentType.GENERALIST,
            task="Execute simple workflow",
            depends_on=["path_selection"],
            condition="selected_path == 'simple'",
            required_inputs=["message", "analysis_result"],
            expected_outputs=["simple_result"],
            timeout=45.0,
        ))

        # Step 3b: Complex Path - Parallel Tasks
        self.add_step(ChainStep(
            step_id="parallel_research",
            step_type=StepType.PARALLEL_EXECUTION,
            task="Execute parallel research tasks",
            depends_on=["path_selection"],
            condition="selected_path == 'complex'",
            parallel_group="research_group",
            required_inputs=["message", "analysis_result"],
            expected_outputs=["research_findings"],
            timeout=60.0,
        ))

        self.add_step(ChainStep(
            step_id="parallel_analysis",
            step_type=StepType.PARALLEL_EXECUTION,
            task="Execute parallel analysis tasks",
            depends_on=["path_selection"],
            condition="selected_path == 'complex'",
            parallel_group="research_group",
            required_inputs=["message", "analysis_result"],
            expected_outputs=["analysis_findings"],
            timeout=60.0,
        ))

        # Step 4: Synthesis (for complex path)
        self.add_step(ChainStep(
            step_id="synthesis",
            step_type=StepType.AGENT_EXECUTION,
            agent=AgentType.ANALYST,
            task="Synthesize parallel results",
            depends_on=["parallel_research", "parallel_analysis"],
            condition="selected_path == 'complex'",
            required_inputs=["research_findings", "analysis_findings"],
            expected_outputs=["synthesized_result"],
            timeout=30.0,
        ))

        # Step 5: Quality Check (always runs if possible)
        self.add_step(ChainStep(
            step_id="quality_check",
            step_type=StepType.AGENT_EXECUTION,
            agent=AgentType.ANALYST,
            task="Quality validation of results",
            depends_on=["simple_execution", "synthesis"],
            required_inputs=["final_result"],
            expected_outputs=["quality_score", "validation_report"],
            timeout=20.0,
        ))

        # Step 6: Fallback (if quality check fails)
        self.add_step(ChainStep(
            step_id="fallback_execution",
            step_type=StepType.AGENT_EXECUTION,
            agent=AgentType.GENERALIST,
            task="Fallback execution path",
            depends_on=["quality_check"],
            condition="quality_score < 0.6",
            required_inputs=["message", "original_result"],
            expected_outputs=["fallback_result"],
            timeout=30.0,
        ))

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the conditional workflow."""
        import time
        
        start_time = time.time()
        self.status = ChainStatus.RUNNING
        
        await self.initialize()
        
        _logger.info("conditional_workflow_started", chain_id=self.chain_id)
        
        try:
            # Execute steps with conditional logic
            execution_context = dict(context)
            execution_path = []
            
            for step in self.steps:
                # Check if step should execute based on conditions
                if not self._should_execute_step(step, execution_context):
                    _logger.info("conditional_workflow_step_skipped", step_id=step.step_id)
                    continue
                
                _logger.info("conditional_workflow_step_executing", step_id=step.step_id)
                
                try:
                    if step.step_type == StepType.CONDITION_CHECK:
                        result = await self._execute_condition_check(step, execution_context)
                    elif step.step_type == StepType.PARALLEL_EXECUTION:
                        result = await self._execute_parallel_step(step, execution_context)
                    else:
                        result = await self._execute_agent_step(step, execution_context)
                    
                    execution_context.update(result.output)
                    execution_context[f"{step.step_id}_completed"] = True
                    execution_path.append(step.step_id)
                    
                    self.step_metrics[step.step_id].update_metrics(result)
                    
                except Exception as e:
                    _logger.error("conditional_workflow_step_failed", step_id=step.step_id, error=str(e))
                    
                    if not self.config.fallback_on_failure:
                        raise
                    
                    # Continue with fallback logic
                    execution_context[f"{step.step_id}_error"] = str(e)
                    continue
            
            # Compile final result
            final_result = self._compile_final_result(execution_context, execution_path)
            
            self.status = ChainStatus.COMPLETED
            execution_time = time.time() - start_time
            
            _logger.info("conditional_workflow_completed", 
                        chain_id=self.chain_id, 
                        execution_time=execution_time,
                        steps_executed=len(execution_path))
            
            return {
                "response": final_result,
                "error": None,
                "execution_path": execution_path,
                "execution_time": execution_time,
                "context": execution_context,
            }
            
        except Exception as e:
            self.status = ChainStatus.FAILED
            _logger.error("conditional_workflow_failed", chain_id=self.chain_id, error=str(e))
            
            return {
                "response": "",
                "error": f"Workflow failed: {str(e)}",
                "execution_path": execution_path,
            }

    def _should_execute_step(self, step: ChainStep, context: Dict[str, Any]) -> bool:
        """Check if a step should execute based on conditions and dependencies."""
        
        # Check dependencies
        for dependency in step.depends_on:
            if context.get(f"{dependency}_completed") is not True:
                return False
        
        # Check condition
        if step.condition:
            try:
                return self._evaluate_condition(step.condition, context)
            except Exception as e:
                _logger.warning("condition_evaluation_failed", step_id=step.step_id, error=str(e))
                return False
        
        return True

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string against the context."""
        
        # Simple condition evaluation - can be enhanced with proper expression parser
        try:
            # Replace common variables
            eval_context = {
                "complexity_score": context.get("complexity_score", 0.0),
                "selected_path": context.get("selected_path", ""),
                "quality_score": context.get("quality_score", 1.0),
            }
            
            # Simple string replacement for basic conditions
            for key, value in eval_context.items():
                if isinstance(value, str):
                    condition = condition.replace(key, f"'{value}'")
                else:
                    condition = condition.replace(key, str(value))
            
            return eval(condition)
            
        except Exception:
            # If evaluation fails, default to executing the step
            return True

    async def _execute_condition_check(self, step: ChainStep, context: Dict[str, Any]) -> StepResult:
        """Execute a condition check step."""
        import time
        
        start_time = time.time()
        
        try:
            # Extract relevant data from context
            analysis_result = context.get("analysis_result", "")
            complexity_score = context.get("complexity_score", 0.5)
            
            # Determine execution path
            if complexity_score > 0.7:
                selected_path = "complex"
                parallel_tasks = ["research", "analysis", "synthesis"]
            else:
                selected_path = "simple"
                parallel_tasks = []
            
            output = {
                "selected_path": selected_path,
                "parallel_tasks": parallel_tasks,
                "complexity_score": complexity_score,
            }
            
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                output=output,
                execution_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time(),
            )
            
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time(),
            )

    async def _execute_parallel_step(self, step: ChainStep, context: Dict[str, Any]) -> StepResult:
        """Execute a parallel step (simplified implementation)."""
        import time
        import asyncio
        
        start_time = time.time()
        
        try:
            # For demonstration, simulate parallel execution
            # In real implementation, this would spawn multiple agent tasks
            
            if "research" in step.step_id:
                output = {"research_findings": "Research results from parallel execution"}
            elif "analysis" in step.step_id:
                output = {"analysis_findings": "Analysis results from parallel execution"}
            else:
                output = {"parallel_result": "Generic parallel result"}
            
            # Simulate parallel work
            await asyncio.sleep(0.1)
            
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                output=output,
                execution_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time(),
            )
            
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time(),
            )

    async def _execute_agent_step(self, step: ChainStep, context: Dict[str, Any]) -> StepResult:
        """Execute an agent step."""
        import time
        
        start_time = time.time()
        
        try:
            agent = get_agent(step.agent)
            
            # Build prompt based on step and context
            system_prompt = agent.system_prompt
            
            user_message = context.get("message", "")
            task_context = self._build_task_context(step, context)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Task: {step.task}\n\nContext: {task_context}\n\nUser: {user_message}"}
            ]
            
            # Setup tools (simplified)
            sandbox_root = getattr(self.settings, "working_path", None)
            sandbox = MindFlowSandbox(
                root_dir=sandbox_root,
                read_only=(agent.sandbox == SandboxMode.READ_ONLY),
            )
            
            tool_registry = create_default_registry(sandbox)
            tools = [] if agent.sandbox == SandboxMode.NONE else tool_registry.get_tools_for_agent(agent)
            
            # Execute
            llm = get_model_for_provider(self.settings.default_provider, self.settings.default_model)
            if tools:
                llm = llm.bind_tools(tools)
            
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
            
            output = {f"{step.step_id}_result": response_text}
            
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                output=output,
                execution_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time(),
            )
            
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
                started_at=start_time,
                completed_at=time.time(),
            )

    def _build_task_context(self, step: ChainStep, context: Dict[str, Any]) -> str:
        """Build context for the step execution."""
        
        context_parts = []
        
        # Add relevant context from previous steps
        for dependency in step.depends_on:
            dep_result = context.get(f"{dependency}_result")
            if dep_result:
                context_parts.append(f"From {dependency}: {dep_result}")
        
        # Add analysis results if available
        if "analysis_result" in context:
            context_parts.append(f"Analysis: {context['analysis_result']}")
        
        return "\n".join(context_parts)

    def _compile_final_result(self, context: Dict[str, Any], execution_path: List[str]) -> str:
        """Compile the final result from the execution context."""
        
        result_parts = ["# Conditional Workflow Result\n"]
        result_parts.append(f"## Execution Path: {' → '.join(execution_path)}\n")
        
        # Add results from executed steps
        for step_id in execution_path:
            step_result = context.get(f"{step_id}_result")
            if step_result:
                result_parts.append(f"## {step_id.replace('_', ' ').title()}\n{step_result}\n")
        
        return "\n".join(result_parts)

    def validate(self) -> List[str]:
        """Validate the conditional workflow structure."""
        issues = self.validate_structure()
        
        # Additional validation for conditional chains
        if not any(step.step_type == StepType.CONDITION_CHECK for step in self.steps):
            issues.append("Conditional workflow requires at least one CONDITION_CHECK step")
        
        # Check for circular dependencies in conditional paths
        # (Additional validation logic can be added here)
        
        return issues


# Factory function
def create_conditional_workflow_chain(config: ConditionalWorkflowConfig | None = None) -> ConditionalWorkflowChain:
    """Create a ConditionalWorkflowChain instance."""
    return ConditionalWorkflowChain(config)

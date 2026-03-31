"""Sequential Chain Builder - Builds sequential execution chains.

This builder creates chains where steps execute one after another,
with the output of each step becoming input for the next step.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mindflow_backend.chains.base.chain import BaseChain, ChainStatus, ChainType
from mindflow_backend.chains.base.step import ChainStep, StepStatus, StepType
from mindflow_backend.chains.base.types import ChainConfig, ExecutionContext


class SequentialChainBuilder:
    """Builder for creating sequential execution chains.
    
    A sequential chain executes steps in order, where each step
    receives the output of the previous step as input.
    """
    
    def __init__(self, chain_id: str = "sequential_chain") -> None:
        self.chain_id = chain_id
        self.steps: list[ChainStep] = []
        self.config = ChainConfig(chain_type=ChainType.SEQUENTIAL)
        self.error_handlers: dict[str, Callable] = {}
        self.step_timeout: float = 30.0
        self.continue_on_error: bool = False
    
    def add_step(
        self,
        step_id: str,
        step_function: Callable,
        step_type: StepType = StepType.PROCESSING,
        description: str = "",
        timeout: float | None = None,
        retry_count: int = 3
    ) -> SequentialChainBuilder:
        """Add a step to the sequential chain.
        
        Args:
            step_id: Unique identifier for the step
            step_function: Function to execute for this step
            step_type: Type of step (processing, validation, transformation, etc.)
            description: Human-readable description of the step
            timeout: Custom timeout for this step (overrides chain default)
            retry_count: Number of retries for this step
            
        Returns:
            Self for method chaining
        """
        step = ChainStep(
            step_id=step_id,
            step_type=step_type,
            step_function=step_function,
            description=description,
            timeout=timeout or self.step_timeout,
            retry_count=retry_count
        )
        
        self.steps.append(step)
        return self
    
    def add_validation_step(
        self,
        step_id: str,
        validation_function: Callable[[Any], bool],
        error_message: str = "Validation failed",
        description: str = ""
    ) -> SequentialChainBuilder:
        """Add a validation step to the chain.
        
        Args:
            step_id: Unique identifier for the validation step
            validation_function: Function that returns True if valid
            error_message: Message to use if validation fails
            description: Human-readable description
            
        Returns:
            Self for method chaining
        """
        def validation_wrapper(context: ExecutionContext) -> dict[str, Any]:
            data = context.get("input", {})
            is_valid = validation_function(data)
            
            if not is_valid:
                raise ValueError(error_message)
            
            return {"output": data, "valid": True}
        
        return self.add_step(
            step_id=step_id,
            step_function=validation_wrapper,
            step_type=StepType.VALIDATION,
            description=description or f"Validate {step_id}"
        )
    
    def add_transformation_step(
        self,
        step_id: str,
        transform_function: Callable[[Any], Any],
        description: str = ""
    ) -> SequentialChainBuilder:
        """Add a transformation step to the chain.
        
        Args:
            step_id: Unique identifier for the transformation step
            transform_function: Function to transform the data
            description: Human-readable description
            
        Returns:
            Self for method chaining
        """
        def transform_wrapper(context: ExecutionContext) -> dict[str, Any]:
            data = context.get("input", {})
            transformed_data = transform_function(data)
            
            return {"output": transformed_data, "transformed": True}
        
        return self.add_step(
            step_id=step_id,
            step_function=transform_wrapper,
            step_type=StepType.TRANSFORMATION,
            description=description or f"Transform {step_id}"
        )
    
    def add_conditional_step(
        self,
        step_id: str,
        condition_function: Callable[[Any], bool],
        true_step: Callable,
        false_step: Callable | None = None,
        description: str = ""
    ) -> SequentialChainBuilder:
        """Add a conditional step to the chain.
        
        Args:
            step_id: Unique identifier for the conditional step
            condition_function: Function that returns True/False
            true_step: Function to execute if condition is True
            false_step: Function to execute if condition is False
            description: Human-readable description
            
        Returns:
            Self for method chaining
        """
        def conditional_wrapper(context: ExecutionContext) -> dict[str, Any]:
            data = context.get("input", {})
            condition_result = condition_function(data)
            
            if condition_result:
                result = true_step(context)
            elif false_step:
                result = false_step(context)
            else:
                result = {"output": data, "skipped": True}
            
            return {
                "output": result.get("output", data),
                "condition_met": condition_result,
                "executed_branch": "true" if condition_result else "false"
            }
        
        return self.add_step(
            step_id=step_id,
            step_function=conditional_wrapper,
            step_type=StepType.CONDITIONAL,
            description=description or f"Conditional {step_id}"
        )
    
    def with_timeout(self, timeout: float) -> SequentialChainBuilder:
        """Set default timeout for all steps.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Self for method chaining
        """
        self.step_timeout = timeout
        return self
    
    def with_error_handling(
        self,
        continue_on_error: bool = True,
        error_handlers: dict[str, Callable] | None = None
    ) -> SequentialChainBuilder:
        """Configure error handling for the chain.
        
        Args:
            continue_on_error: Whether to continue execution after errors
            error_handlers: Mapping of step_id to error handler functions
            
        Returns:
            Self for method chaining
        """
        self.continue_on_error = continue_on_error
        if error_handlers:
            self.error_handlers.update(error_handlers)
        return self
    
    def with_config(self, **config_kwargs) -> SequentialChainBuilder:
        """Set additional configuration options.
        
        Args:
            **config_kwargs: Configuration options for ChainConfig
            
        Returns:
            Self for method chaining
        """
        for key, value in config_kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        return self
    
    def build(self) -> BaseChain:
        """Build the sequential chain.
        
        Returns:
            Configured SequentialChain instance
            
        Raises:
            ValueError: If no steps have been added
        """
        if not self.steps:
            raise ValueError("Cannot build chain: no steps have been added")
        
        return SequentialChain(
            chain_id=self.chain_id,
            steps=self.steps,
            config=self.config,
            error_handlers=self.error_handlers,
            continue_on_error=self.continue_on_error
        )


class SequentialChain(BaseChain):
    """Sequential execution chain implementation."""
    
    def __init__(
        self,
        chain_id: str,
        steps: list[ChainStep],
        config: ChainConfig,
        error_handlers: dict[str, Callable] | None = None,
        continue_on_error: bool = False
    ) -> None:
        super().__init__(chain_id, config)
        self.steps = steps
        self.error_handlers = error_handlers or {}
        self.continue_on_error = continue_on_error
    
    async def execute(self, initial_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the sequential chain.
        
        Args:
            initial_context: Initial context for chain execution
            
        Returns:
            Final execution context with all step results
        """
        context = ExecutionContext(
            chain_id=self.chain_id,
            input=initial_context or {},
            step_results={},
            metadata={}
        )
        
        self.status = ChainStatus.RUNNING
        
        try:
            for step in self.steps:
                # Execute step
                step_result = await self._execute_step(step, context)
                
                # Store step result
                context.step_results[step.step_id] = step_result
                
                # Update context for next step
                if "output" in step_result:
                    context.input = step_result["output"]
                
                # Check if we should continue
                if not self.continue_on_error and step_result.get("error"):
                    self.status = ChainStatus.FAILED
                    break
            
            self.status = ChainStatus.COMPLETED
            
        except Exception as e:
            self.status = ChainStatus.FAILED
            context.metadata["chain_error"] = str(e)
        
        return context.to_dict()
    
    async def _execute_step(self, step: ChainStep, context: ExecutionContext) -> dict[str, Any]:
        """Execute a single step with error handling and retries."""
        import asyncio
        import time
        
        last_error = None
        
        for attempt in range(step.retry_count + 1):
            try:
                start_time = time.time()
                
                # Execute step with timeout
                result = await asyncio.wait_for(
                    step.step_function(context),
                    timeout=step.timeout
                )
                
                execution_time = time.time() - start_time
                
                # Ensure result has required fields
                if not isinstance(result, dict):
                    result = {"output": result}
                
                result.update({
                    "step_id": step.step_id,
                    "attempt": attempt + 1,
                    "execution_time": execution_time,
                    "status": StepStatus.COMPLETED,
                    "error": None
                })
                
                return result
                
            except TimeoutError:
                last_error = f"Step {step.step_id} timed out after {step.timeout}s"
                
            except Exception as e:
                last_error = str(e)
                
                # Check if there's a custom error handler
                if step.step_id in self.error_handlers:
                    try:
                        handler_result = self.error_handlers[step.step_id](e, context)
                        if isinstance(handler_result, dict):
                            return handler_result
                    except Exception as handler_error:
                        last_error = f"Error handler failed: {str(handler_error)}"
        
        # All retries failed
        return {
            "step_id": step.step_id,
            "attempt": step.retry_count + 1,
            "execution_time": 0,
            "status": StepStatus.FAILED,
            "error": last_error,
            "output": None
        }
    
    def validate(self) -> list[str]:
        """Validate the sequential chain configuration."""
        issues = []
        
        if not self.steps:
            issues.append("Sequential chain must have at least one step")
        
        # Check for duplicate step IDs
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            duplicates = [id for id in step_ids if step_ids.count(id) > 1]
            issues.append(f"Duplicate step IDs: {duplicates}")
        
        # Validate each step
        for step in self.steps:
            if not step.step_function:
                issues.append(f"Step {step.step_id} has no function")
            if step.timeout <= 0:
                issues.append(f"Step {step.step_id} has invalid timeout")
        
        return issues
    
    def get_step_summary(self) -> dict[str, Any]:
        """Get a summary of all steps in the chain."""
        return {
            "chain_id": self.chain_id,
            "total_steps": len(self.steps),
            "steps": [
                {
                    "step_id": step.step_id,
                    "type": step.step_type.value,
                    "description": step.description,
                    "timeout": step.timeout,
                    "retry_count": step.retry_count
                }
                for step in self.steps
            ]
        }

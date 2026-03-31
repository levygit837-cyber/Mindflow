"""Conditional Chain Builder - Builds conditional execution chains.

This builder creates chains where execution flow can branch based on conditions,
allowing for complex decision trees and adaptive execution paths.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mindflow_backend.chains.base.chain import BaseChain, ChainStatus, ChainType
from mindflow_backend.chains.base.step import ChainStep, StepStatus, StepType
from mindflow_backend.chains.base.types import ChainConfig, ExecutionContext


class ConditionalBranch:
    """Represents a conditional branch in a chain."""
    
    def __init__(
        self,
        branch_id: str,
        condition: Callable[[dict[str, Any]], bool],
        steps: list[ChainStep],
        description: str = ""
    ) -> None:
        self.branch_id = branch_id
        self.condition = condition
        self.steps = steps
        self.description = description
        self.executed = False
        self.result = None


class ConditionalChainBuilder:
    """Builder for creating conditional execution chains.
    
    A conditional chain evaluates conditions and executes different
    branches based on the results, allowing for complex
    decision trees and adaptive execution paths.
    """
    
    def __init__(self, chain_id: str = "conditional_chain") -> None:
        self.chain_id = chain_id
        self.branches: list[ConditionalBranch] = []
        self.default_branch: ConditionalBranch | None = None
        self.config = ChainConfig(chain_type=ChainType.CONDITIONAL)
        self.error_handlers: dict[str, Callable] = {}
        self.step_timeout: float = 30.0
        self.continue_on_error: bool = False
        self.max_execution_depth: int = 10
    
    def add_branch(
        self,
        branch_id: str,
        condition: Callable[[dict[str, Any]], bool],
        description: str = ""
    ) -> ConditionalBranchBuilder:
        """Add a conditional branch to the chain.
        
        Args:
            branch_id: Unique identifier for the branch
            condition: Function that evaluates to True/False
            description: Human-readable description of the condition
            
        Returns:
            BranchBuilder for adding steps to this branch
        """
        branch = ConditionalBranch(
            branch_id=branch_id,
            condition=condition,
            steps=[],
            description=description
        )
        
        self.branches.append(branch)
        return ConditionalBranchBuilder(self, branch)
    
    def add_default_branch(self, description: str = "Default branch") -> ConditionalBranchBuilder:
        """Add a default branch that executes if no other conditions match.
        
        Args:
            description: Human-readable description
            
        Returns:
            BranchBuilder for adding steps to the default branch
        """
        branch = ConditionalBranch(
            branch_id="default",
            condition=lambda ctx: True,  # Always true if reached
            steps=[],
            description=description
        )
        
        self.default_branch = branch
        return ConditionalBranchBuilder(self, branch)
    
    def with_timeout(self, timeout: float) -> ConditionalChainBuilder:
        """Set default timeout for all steps.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Self for method chaining
        """
        self.step_timeout = timeout
        return self
    
    def with_max_depth(self, max_depth: int) -> ConditionalChainBuilder:
        """Set maximum execution depth to prevent infinite loops.
        
        Args:
            max_depth: Maximum number of branch executions
            
        Returns:
            Self for method chaining
        """
        self.max_execution_depth = max_depth
        return self
    
    def with_error_handling(
        self,
        continue_on_error: bool = True,
        error_handlers: dict[str, Callable] | None = None
    ) -> ConditionalChainBuilder:
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
    
    def with_config(self, **config_kwargs) -> ConditionalChainBuilder:
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
        """Build the conditional chain.
        
        Returns:
            Configured ConditionalChain instance
            
        Raises:
            ValueError: If no branches have been added
        """
        if not self.branches:
            raise ValueError("Cannot build chain: no branches have been added")
        
        return ConditionalChain(
            chain_id=self.chain_id,
            branches=self.branches,
            default_branch=self.default_branch,
            config=self.config,
            error_handlers=self.error_handlers,
            continue_on_error=self.continue_on_error,
            max_execution_depth=self.max_execution_depth
        )


class ConditionalBranchBuilder:
    """Builder for adding steps to a conditional branch."""
    
    def __init__(self, chain_builder: ConditionalChainBuilder, branch: ConditionalBranch) -> None:
        self.chain_builder = chain_builder
        self.branch = branch
    
    def add_step(
        self,
        step_id: str,
        step_function: Callable,
        step_type: StepType = StepType.PROCESSING,
        description: str = "",
        timeout: float | None = None,
        retry_count: int = 3
    ) -> ConditionalBranchBuilder:
        """Add a step to this branch.
        
        Args:
            step_id: Unique identifier for the step
            step_function: Function to execute for this step
            step_type: Type of step
            description: Human-readable description
            timeout: Custom timeout for this step
            retry_count: Number of retries for this step
            
        Returns:
            Self for method chaining
        """
        step = ChainStep(
            step_id=step_id,
            step_type=step_type,
            step_function=step_function,
            description=description,
            timeout=timeout or self.chain_builder.step_timeout,
            retry_count=retry_count
        )
        
        self.branch.steps.append(step)
        return self
    
    def end_branch(self) -> ConditionalChainBuilder:
        """End building this branch and return to chain builder.
        
        Returns:
            The parent ConditionalChainBuilder
        """
        return self.chain_builder


class ConditionalChain(BaseChain):
    """Conditional execution chain implementation."""
    
    def __init__(
        self,
        chain_id: str,
        branches: list[ConditionalBranch],
        default_branch: ConditionalBranch | None,
        config: ChainConfig,
        error_handlers: dict[str, Callable] | None = None,
        continue_on_error: bool = False,
        max_execution_depth: int = 10
    ) -> None:
        super().__init__(chain_id, config)
        self.branches = branches
        self.default_branch = default_branch
        self.error_handlers = error_handlers or {}
        self.continue_on_error = continue_on_error
        self.max_execution_depth = max_execution_depth
        self.execution_path: list[str] = []
    
    async def execute(self, initial_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the conditional chain.
        
        Args:
            initial_context: Initial context for chain execution
            
        Returns:
            Final execution context with all step results
        """
        context = ExecutionContext(
            chain_id=self.chain_id,
            input=initial_context or {},
            step_results={},
            metadata={"execution_path": [], "branches_evaluated": []}
        )
        
        self.status = ChainStatus.RUNNING
        execution_depth = 0
        
        try:
            while execution_depth < self.max_execution_depth:
                # Find matching branch
                matched_branch = None
                
                for branch in self.branches:
                    if not branch.executed:
                        try:
                            condition_result = branch.condition(context.to_dict())
                            
                            context.metadata["branches_evaluated"].append({
                                "branch_id": branch.branch_id,
                                "condition_result": condition_result,
                                "description": branch.description
                            })
                            
                            if condition_result:
                                matched_branch = branch
                                break
                        except Exception as e:
                            context.metadata["branches_evaluated"].append({
                                "branch_id": branch.branch_id,
                                "condition_result": False,
                                "error": str(e)
                            })
                
                # Use default branch if no match found
                if not matched_branch and self.default_branch:
                    matched_branch = self.default_branch
                
                # No branch matched and no default - end execution
                if not matched_branch:
                    context.metadata["execution_ended"] = "No matching branch found"
                    break
                
                # Execute the matched branch
                await self._execute_branch(matched_branch, context)
                
                # Update execution path
                self.execution_path.append(matched_branch.branch_id)
                context.metadata["execution_path"] = list(self.execution_path)
                
                execution_depth += 1
                
                # Check if any branch set a "continue" flag
                if context.metadata.get("stop_execution", False):
                    break
            
            self.status = ChainStatus.COMPLETED
            
        except Exception as e:
            self.status = ChainStatus.FAILED
            context.metadata["chain_error"] = str(e)
        
        return context.to_dict()
    
    async def _execute_branch(self, branch: ConditionalBranch, context: ExecutionContext) -> None:
        """Execute all steps in a branch."""
        import asyncio
        import time
        
        branch.context = context.to_dict()
        
        for step in branch.steps:
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
                    "branch_id": branch.branch_id,
                    "execution_time": execution_time,
                    "status": StepStatus.COMPLETED,
                    "error": None
                })
                
                # Store step result
                context.step_results[f"{branch.branch_id}.{step.step_id}"] = result
                
                # Update context for next step
                if "output" in result:
                    context.input = result["output"]
                
            except TimeoutError:
                error_msg = f"Step {step.step_id} in branch {branch.branch_id} timed out"
                self._handle_step_error(step, branch, context, error_msg)
                
                if not self.continue_on_error:
                    break
            
            except Exception as e:
                error_msg = f"Step {step.step_id} in branch {branch.branch_id} failed: {str(e)}"
                self._handle_step_error(step, branch, context, error_msg)
                
                if not self.continue_on_error:
                    break
        
        branch.executed = True
    
    def _handle_step_error(
        self, 
        step: ChainStep, 
        branch: ConditionalBranch, 
        context: ExecutionContext, 
        error: str
    ) -> None:
        """Handle step execution errors."""
        step_key = f"{branch.branch_id}.{step.step_id}"
        
        # Check for custom error handler
        if step_key in self.error_handlers:
            try:
                handler_result = self.error_handlers[step_key](error, context)
                if isinstance(handler_result, dict):
                    context.step_results[step_key] = handler_result
                    return
            except Exception as handler_error:
                error = f"Error handler failed: {str(handler_error)}"
        
        # Store error result
        context.step_results[step_key] = {
            "step_id": step.step_id,
            "branch_id": branch.branch_id,
            "execution_time": 0,
            "status": StepStatus.FAILED,
            "error": error,
            "output": None
        }
    
    def validate(self) -> list[str]:
        """Validate the conditional chain configuration."""
        issues = []
        
        if not self.branches:
            issues.append("Conditional chain must have at least one branch")
        
        # Check for duplicate branch IDs
        branch_ids = [branch.branch_id for branch in self.branches]
        if len(branch_ids) != len(set(branch_ids)):
            duplicates = [id for id in branch_ids if branch_ids.count(id) > 1]
            issues.append(f"Duplicate branch IDs: {duplicates}")
        
        # Validate each branch
        for branch in self.branches:
            if not branch.condition:
                issues.append(f"Branch {branch.branch_id} has no condition")
            if not branch.steps:
                issues.append(f"Branch {branch.branch_id} has no steps")
        
        # Check default branch
        if self.default_branch and not self.default_branch.steps:
            issues.append("Default branch has no steps")
        
        # Validate execution depth
        if self.max_execution_depth <= 0:
            issues.append("Max execution depth must be greater than 0")
        
        return issues
    
    def get_execution_summary(self) -> dict[str, Any]:
        """Get a summary of the execution path and results."""
        return {
            "chain_id": self.chain_id,
            "execution_path": self.execution_path,
            "total_branches": len(self.branches),
            "has_default_branch": self.default_branch is not None,
            "max_execution_depth": self.max_execution_depth,
            "branches": [
                {
                    "branch_id": branch.branch_id,
                    "description": branch.description,
                    "executed": branch.executed,
                    "step_count": len(branch.steps)
                }
                for branch in self.branches
            ]
        }

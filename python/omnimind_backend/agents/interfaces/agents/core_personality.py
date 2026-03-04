"""Core personality contract.

Defines the fundamental contract that all agent personality implementations
must satisfy, providing a consistent interface for task execution,
validation, capabilities, and error handling.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any

from omnimind_backend.schemas.orchestration.delegation import (
    DelegationTask,
    DelegationResult,
)


@runtime_checkable
class CorePersonalityContract(Protocol):
    """Core contract for all agent personality implementations.
    
    Every agent personality (coder, analyst, researcher, reviewer, etc.)
    must implement this contract to ensure consistent behavior,
    error handling, and integration with the orchestrator.
    """

    async def execute_task(self, task: DelegationTask) -> DelegationResult:
        """Execute a delegated task according to personality specialization.
        
        Args:
            task: Formatted delegation task from orchestrator.
            
        Returns:
            Structured result with key findings and metadata.
        """
        ...

    async def validate_input(self, input_data: Any) -> bool:
        """Validate input data before processing.
        
        Args:
            input_data: Raw input to be processed.
            
        Returns:
            True if input is valid for this personality type.
        """
        ...

    async def get_capabilities(self) -> dict[str, Any]:
        """Get personality capabilities and configuration.
        
        Returns:
            Dictionary describing what this personality can do,
            including supported tools, file types, and operations.
        """
        ...

    async def handle_error(self, error: Exception) -> dict[str, Any]:
        """Handle errors in a personality-specific way.
        
        Args:
            error: Exception that occurred during execution.
            
        Returns:
            Error handling result with recovery suggestions.
        """
        ...

    async def initialize_session(self, session_id: str, agent_id: str) -> None:
        """Initialize personality-specific session state.
        
        Args:
            session_id: Unique session identifier.
            agent_id: Unique agent identifier.
        """
        ...

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up personality-specific session state.
        
        Args:
            session_id: Session identifier to clean up.
        """
        ...

    async def estimate_complexity(self, task: DelegationTask) -> float:
        """Estimate task complexity for this personality.
        
        Args:
            task: Delegation task to analyze.
            
        Returns:
            Complexity estimate between 0.0 (simple) and 1.0 (complex).
        """
        ...

    async def suggest_iterations(self, task: DelegationTask) -> int:
        """Suggest optimal iteration count for this task.
        
        Args:
            task: Delegation task to analyze.
            
        Returns:
            Recommended number of iterations (1-10).
        """
        ...

    async def extract_key_findings(self, full_output: str) -> str:
        """Extract compressed key findings from full output.
        
        Args:
            full_output: Complete agent response.
            
        Returns:
            Compressed summary for orchestrator context integration.
        """
        ...

    async def validate_output(self, output: str, task: DelegationTask) -> bool:
        """Validate that output meets task requirements.
        
        Args:
            output: Generated output to validate.
            task: Original delegation task for requirements.
            
        Returns:
            True if output satisfies task requirements.
        """
        ...

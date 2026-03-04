"""Enhanced coder agent interface.

Extends the basic Coder interface with comprehensive code generation,
modification, review, and feature implementation capabilities
integrated with the core personality contract.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any

from omnimind_backend.agents.interfaces.agents.core_personality import (
    CorePersonalityContract,
)
from omnimind_backend.schemas.orchestration.delegation import DelegationTask, DelegationResult


@runtime_checkable
class EnhancedCoder(CorePersonalityContract, Protocol):
    """Enhanced contract for coder agent implementations.
    
    Extends core personality capabilities with specialized
    code operations including generation, modification, review,
    and feature implementation.
    """

    async def generate_code(
        self,
        requirements: str,
        context: dict,
        language: str = "python",
        framework: str | None = None,
    ) -> dict[str, Any]:
        """Generate code based on requirements.
        
        Args:
            requirements: Code requirements specification.
            context: Development context and constraints.
            language: Target programming language.
            framework: Target framework if applicable.
            
        Returns:
            Generated code with metadata and explanations.
        """
        ...

    async def modify_code(
        self,
        code: str,
        modifications: list[dict],
        preserve_comments: bool = True,
    ) -> dict[str, Any]:
        """Apply modifications to existing code.
        
        Args:
            code: Original code to modify.
            modifications: List of modification specifications.
            preserve_comments: Whether to preserve existing comments.
            
        Returns:
            Modified code with change summary.
        """
        ...

    async def review_code(
        self,
        code: str,
        review_type: str = "comprehensive",
        focus_areas: list[str] | None = None,
    ) -> dict[str, Any]:
        """Review code for quality and best practices.
        
        Args:
            code: Code to review.
            review_type: Type of review (security, performance, style, etc.).
            focus_areas: Specific areas to focus on.
            
        Returns:
            Review results with issues and recommendations.
        """
        ...

    async def implement_feature(
        self,
        feature_spec: dict,
        existing_codebase: dict,
        integration_mode: str = "additive",
    ) -> dict[str, Any]:
        """Implement a complete feature based on specification.
        
        Args:
            feature_spec: Feature specification with requirements.
            existing_codebase: Context of existing code.
            integration_mode: How to integrate with existing code.
            
        Returns:
            Implementation results with integration details.
        """
        ...

    async def refactor_code(
        self,
        code: str,
        refactoring_type: str,
        target_structure: dict | None = None,
    ) -> dict[str, Any]:
        """Refactor code according to patterns or target structure.
        
        Args:
            code: Code to refactor.
            refactoring_type: Type of refactoring (extract, rename, etc.).
            target_structure: Target code structure if applicable.
            
        Returns:
            Refactored code with migration guide.
        """
        ...

    async def optimize_code(
        self,
        code: str,
        optimization_type: str = "performance",
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Optimize code for specific criteria.
        
        Args:
            code: Code to optimize.
            optimization_type: Type of optimization (performance, memory, etc.).
            constraints: Optimization constraints and requirements.
            
        Returns:
            Optimized code with performance metrics.
        """
        ...

    async def generate_tests(
        self,
        code: str,
        test_type: str = "unit",
        coverage_target: float = 0.8,
    ) -> dict[str, Any]:
        """Generate comprehensive tests for code.
        
        Args:
            code: Code to generate tests for.
            test_type: Type of tests (unit, integration, e2e).
            coverage_target: Target code coverage percentage.
            
        Returns:
            Generated tests with coverage analysis.
        """
        ...

    async def analyze_dependencies(
        self,
        code: str,
        analysis_type: str = "comprehensive",
    ) -> dict[str, Any]:
        """Analyze code dependencies and relationships.
        
        Args:
            code: Code to analyze.
            analysis_type: Type of analysis (imports, coupling, etc.).
            
        Returns:
            Dependency analysis with recommendations.
        """
        ...

    async def suggest_improvements(
        self,
        code: str,
        improvement_areas: list[str] | None = None,
    ) -> dict[str, Any]:
        """Suggest code improvements and modernizations.
        
        Args:
            code: Code to analyze for improvements.
            improvement_areas: Specific areas to focus on.
            
        Returns:
            Improvement suggestions with implementation guidance.
        """
        ...

    async def validate_syntax(
        self,
        code: str,
        language: str = "python",
    ) -> dict[str, Any]:
        """Validate code syntax and structure.
        
        Args:
            code: Code to validate.
            language: Programming language.
            
        Returns:
            Validation results with error details.
        """
        ...

    async def estimate_complexity(
        self,
        task: DelegationTask,
    ) -> float:
        """Estimate coding task complexity.
        
        Args:
            task: Delegation task to analyze.
            
        Returns:
            Complexity estimate between 0.0 and 1.0.
        """
        ...

    async def extract_key_findings(
        self,
        full_output: str,
    ) -> str:
        """Extract compressed key findings from code output.
        
        Args:
            full_output: Complete code generation/review output.
            
        Returns:
            Compressed summary for orchestrator integration.
        """
        ...

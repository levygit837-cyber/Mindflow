"""Enhanced reviewer agent interface.

Extends the basic Reviewer interface with comprehensive code review,
quality assessment, security evaluation, and recommendation generation
capabilities integrated with the core personality contract.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any

from mindflow_backend.interfaces.agents.core_personality import (
    CorePersonalityContract,
)
from mindflow_backend.schemas.orchestration.delegation import DelegationTask, DelegationResult
from mindflow_backend.schemas.session.review import ReviewExecutionContext


@runtime_checkable
class EnhancedReviewer(CorePersonalityContract, Protocol):
    """Enhanced contract for reviewer agent implementations.
    
    Extends core personality capabilities with specialized
    review operations including code review, quality assessment,
    security evaluation, and recommendation generation.
    """

    async def review_session_window(
        self,
        task: Any,  # ReviewTask
        context: ReviewExecutionContext,
        review_type: str = "comprehensive",
    ) -> dict[str, Any]:
        """Review a session window for insights and actions.
        
        Args:
            task: Review task specification.
            context: Execution context for the review.
            review_type: Type of review (security, performance, etc.).
            
        Returns:
            Review results with insights and action items.
        """
        ...

    async def assess_quality(
        self,
        content: str,
        quality_dimensions: list[str] | None = None,
        standards: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Assess quality of provided content.
        
        Args:
            content: Content to assess quality for.
            quality_dimensions: Specific quality dimensions to assess.
            standards: Quality standards and thresholds.
            
        Returns:
            Quality assessment with scores and recommendations.
        """
        ...

    async def security_review(
        self,
        code: str,
        security_level: str = "comprehensive",
        threat_model: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform security review of code.
        
        Args:
            code: Code to review for security issues.
            security_level: Depth of security review.
            threat_model: Specific threat model to consider.
            
        Returns:
            Security review with vulnerabilities and mitigations.
        """
        ...

    async def generate_recommendations(
        self,
        analysis: dict,
        recommendation_type: str = "actionable",
        priority_filter: str = "all",
    ) -> list[str]:
        """Generate actionable recommendations from analysis.
        
        Args:
            analysis: Analysis results to base recommendations on.
            recommendation_type: Type of recommendations.
            priority_filter: Filter by priority level.
            
        Returns:
            List of actionable recommendations.
        """
        ...

    async def review_code_changes(
        self,
        changes: dict[str, Any],
        review_scope: str = "full",
    ) -> dict[str, Any]:
        """Review code changes for quality and compliance.
        
        Args:
            changes: Code changes to review.
            review_scope: Scope of the review.
            
        Returns:
            Code change review with approval status.
        """
        ...

    async def assess_maintainability(
        self,
        code: str,
        maintainability_metrics: list[str] | None = None,
    ) -> dict[str, Any]:
        """Assess code maintainability characteristics.
        
        Args:
            code: Code to assess maintainability for.
            maintainability_metrics: Specific metrics to assess.
            
        Returns:
            Maintainability assessment with improvement areas.
        """
        ...

    async def review_documentation(
        self,
        documentation: str,
        documentation_type: str = "api",
    ) -> dict[str, Any]:
        """Review documentation quality and completeness.
        
        Args:
            documentation: Documentation to review.
            documentation_type: Type of documentation.
            
        Returns:
            Documentation review with improvement suggestions.
        """
        ...

    async def evaluate_test_coverage(
        self,
        code: str,
        tests: str,
        coverage_threshold: float = 0.8,
    ) -> dict[str, Any]:
        """Evaluate test coverage and quality.
        
        Args:
            code: Code to evaluate coverage for.
            tests: Test code to analyze.
            coverage_threshold: Minimum coverage threshold.
            
        Returns:
            Test coverage evaluation with gaps identified.
        """
        ...

    async def review_performance_impact(
        self,
        code_or_changes: str,
        baseline_metrics: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Review performance impact of code or changes.
        
        Args:
            code_or_changes: Code or changes to review.
            baseline_metrics: Baseline performance metrics.
            
        Returns:
            Performance impact review with predictions.
        """
        ...

    async def assess_compliance(
        self,
        code_or_system: str,
        compliance_standards: list[str],
    ) -> dict[str, Any]:
        """Assess compliance with standards and regulations.
        
        Args:
            code_or_system: Code or system to assess.
            compliance_standards: Standards to check compliance against.
            
        Returns:
            Compliance assessment with violations and remediation.
        """
        ...

    async def review_architecture_decisions(
        self,
        architecture: dict[str, Any],
        decision_criteria: list[str],
    ) -> dict[str, Any]:
        """Review architectural decisions and trade-offs.
        
        Args:
            architecture: Architecture to review.
            decision_criteria: Criteria for evaluating decisions.
            
        Returns:
            Architecture review with decision validation.
        """
        ...

    async def generate_review_summary(
        self,
        review_results: list[dict[str, Any]],
        summary_type: str = "executive",
    ) -> dict[str, Any]:
        """Generate comprehensive review summary.
        
        Args:
            review_results: Multiple review results to summarize.
            summary_type: Type of summary (executive, technical, etc.).
            
        Returns:
            Review summary with key findings and recommendations.
        """
        ...

    async def validate_review_completeness(
        self,
        review_result: dict[str, Any],
        review_scope: dict[str, Any],
    ) -> bool:
        """Validate that review covers all required areas.
        
        Args:
            review_result: Review result to validate.
            review_scope: Required review scope.
            
        Returns:
            True if review is complete and comprehensive.
        """
        ...

    async def extract_key_findings(
        self,
        full_output: str,
    ) -> str:
        """Extract compressed key findings from review output.
        
        Args:
            full_output: Complete review results.
            
        Returns:
            Compressed summary for orchestrator integration.
        """
        ...

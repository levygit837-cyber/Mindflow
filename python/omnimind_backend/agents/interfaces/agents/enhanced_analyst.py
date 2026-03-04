"""Enhanced analyst agent interface.

Extends the basic Analyst interface with comprehensive system analysis,
architecture evaluation, and insight generation capabilities
integrated with the core personality contract.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any

from omnimind_backend.agents.interfaces.agents.core_personality import (
    CorePersonalityContract,
)
from omnimind_backend.schemas.orchestration.delegation import DelegationTask, DelegationResult


@runtime_checkable
class EnhancedAnalyst(CorePersonalityContract, Protocol):
    """Enhanced contract for analyst agent implementations.
    
    Extends core personality capabilities with specialized
    analysis operations including code analysis, system evaluation,
    architecture review, and insight generation.
    """

    async def analyze_code(
        self,
        code: str,
        context: dict,
        analysis_type: str = "comprehensive",
        focus_areas: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze code structure and quality.
        
        Args:
            code: Code to analyze.
            context: Analysis context and requirements.
            analysis_type: Type of analysis (security, performance, etc.).
            focus_areas: Specific areas to focus on.
            
        Returns:
            Comprehensive analysis results with recommendations.
        """
        ...

    async def evaluate_system(
        self,
        system_description: str,
        evaluation_criteria: list[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate system architecture and design.
        
        Args:
            system_description: Description of system to evaluate.
            evaluation_criteria: Specific criteria to evaluate.
            
        Returns:
            System evaluation with strengths and weaknesses.
        """
        ...

    async def generate_insights(
        self,
        data: Any,
        insight_type: str = "comprehensive",
        context: dict | None = None,
    ) -> list[str]:
        """Generate analytical insights from data.
        
        Args:
            data: Data to analyze for insights.
            insight_type: Type of insights (patterns, anomalies, etc.).
            context: Additional context for insight generation.
            
        Returns:
            List of actionable insights with explanations.
        """
        ...

    async def analyze_architecture(
        self,
        architecture_spec: dict,
        analysis_scope: str = "full",
    ) -> dict[str, Any]:
        """Analyze software architecture patterns and decisions.
        
        Args:
            architecture_spec: Architecture specification.
            analysis_scope: Scope of analysis (components, patterns, etc.).
            
        Returns:
            Architecture analysis with recommendations.
        """
        ...

    async def assess_code_quality(
        self,
        codebase: dict,
        quality_metrics: list[str] | None = None,
    ) -> dict[str, Any]:
        """Assess overall codebase quality.
        
        Args:
            codebase: Codebase structure and files.
            quality_metrics: Specific quality metrics to assess.
            
        Returns:
            Quality assessment with improvement areas.
        """
        ...

    async def analyze_dependencies(
        self,
        code_structure: dict,
        dependency_type: str = "all",
    ) -> dict[str, Any]:
        """Analyze code dependencies and coupling.
        
        Args:
            code_structure: Code structure and relationships.
            dependency_type: Type of dependencies (imports, data, etc.).
            
        Returns:
            Dependency analysis with coupling metrics.
        """
        ...

    async def evaluate_performance(
        self,
        system_or_code: str,
        performance_type: str = "general",
    ) -> dict[str, Any]:
        """Evaluate performance characteristics.
        
        Args:
            system_or_code: System or code to evaluate.
            performance_type: Type of performance (speed, memory, etc.).
            
        Returns:
            Performance evaluation with bottlenecks identified.
        """
        ...

    async def analyze_security(
        self,
        code_or_system: str,
        security_level: str = "comprehensive",
    ) -> dict[str, Any]:
        """Analyze security vulnerabilities and risks.
        
        Args:
            code_or_system: Code or system to analyze.
            security_level: Depth of security analysis.
            
        Returns:
            Security analysis with vulnerability report.
        """
        ...

    async def compare_solutions(
        self,
        solutions: list[dict],
        comparison_criteria: list[str],
    ) -> dict[str, Any]:
        """Compare multiple solutions or approaches.
        
        Args:
            solutions: List of solutions to compare.
            comparison_criteria: Criteria for comparison.
            
        Returns:
            Comparison analysis with recommendations.
        """
        ...

    async def detect_patterns(
        self,
        data: Any,
        pattern_type: str = "all",
    ) -> dict[str, Any]:
        """Detect patterns in code or data.
        
        Args:
            data: Data to analyze for patterns.
            pattern_type: Type of patterns (design, anti-patterns, etc.).
            
        Returns:
            Pattern detection results with explanations.
        """
        ...

    async def generate_metrics_report(
        self,
        analysis_target: dict,
        metric_categories: list[str],
    ) -> dict[str, Any]:
        """Generate comprehensive metrics report.
        
        Args:
            analysis_target: Target to analyze.
            metric_categories: Categories of metrics to include.
            
        Returns:
            Detailed metrics report with visualizations.
        """
        ...

    async def recommend_improvements(
        self,
        analysis_results: dict,
        priority_areas: list[str] | None = None,
    ) -> dict[str, Any]:
        """Recommend improvements based on analysis.
        
        Args:
            analysis_results: Results from previous analysis.
            priority_areas: Areas to prioritize for improvements.
            
        Returns:
            Improvement recommendations with implementation guidance.
        """
        ...

    async def validate_analysis(
        self,
        analysis_result: dict,
        original_target: str,
    ) -> bool:
        """Validate analysis completeness and accuracy.
        
        Args:
            analysis_result: Analysis to validate.
            original_target: Original analysis target.
            
        Returns:
            True if analysis is valid and complete.
        """
        ...

    async def extract_key_findings(
        self,
        full_output: str,
    ) -> str:
        """Extract compressed key findings from analysis output.
        
        Args:
            full_output: Complete analysis results.
            
        Returns:
            Compressed summary for orchestrator integration.
        """
        ...

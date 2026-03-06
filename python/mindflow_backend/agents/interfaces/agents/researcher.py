"""Enhanced research agent interface.

Extends research capabilities with comprehensive query planning,
web search, result synthesis, and integration with core personality contract.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any

from mindflow_backend.agents.interfaces.agents.core_personality import (
    CorePersonalityContract,
)
from mindflow_backend.schemas.orchestration.delegation import DelegationTask, DelegationResult
from mindflow_backend.schemas.agents.research import (
    BrowserAction,
    BrowserActionRequest,
    BrowserActionResponse,
    QueryPlan,
    ResearchConfig,
    ResearchFinding,
    ResearchRequest,
    ResearchResponse,
    SourceClassification,
)


@runtime_checkable
class EnhancedResearcher(CorePersonalityContract, Protocol):
    """Enhanced contract for researcher agent implementations.
    
    Extends core personality capabilities with specialized
    research operations including query planning, web search,
    result synthesis, and source validation.
    """
    
    async def initialize(self, session_id: str, agent_id: str) -> None:
        """Initialize researcher agent for a session."""
        ...

    async def execute_research(self, request: ResearchRequest) -> ResearchResponse:
        """Execute comprehensive research request."""
        ...

    async def plan_queries(self, research_query: str) -> QueryPlan:
        """Plan optimal queries for research."""
        ...

    async def synthesize_results(self, results: list) -> str:
        """Synthesize multiple research results into coherent response."""
        ...

    async def classify_sources(
        self,
        sources: list[str],
        classification_criteria: dict[str, Any] | None = None,
    ) -> list[SourceClassification]:
        """Classify research sources by trust level and relevance.
        
        Args:
            sources: List of source URLs to classify.
            classification_criteria: Custom classification criteria.
            
        Returns:
            List of source classifications with trust levels.
        """
        ...

    async def execute_browser_actions(
        self,
        actions: list[BrowserActionRequest],
    ) -> list[BrowserActionResponse]:
        """Execute browser automation actions for research.
        
        Args:
            actions: List of browser actions to execute.
            
        Returns:
            Results of browser actions with metadata.
        """
        ...

    async def validate_findings(
        self,
        findings: list[ResearchFinding],
        validation_criteria: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate research findings for accuracy and relevance.
        
        Args:
            findings: Research findings to validate.
            validation_criteria: Validation criteria and thresholds.
            
        Returns:
            Validation results with confidence scores.
        """
        ...

    async def identify_conflicts(
        self,
        findings: list[ResearchFinding],
    ) -> list[dict[str, Any]]:
        """Identify conflicts and contradictions in research findings.
        
        Args:
            findings: Research findings to analyze for conflicts.
            
        Returns:
            List of identified conflicts with resolution suggestions.
        """
        ...

    async def assess_research_quality(
        self,
        research_result: ResearchResponse,
        quality_metrics: list[str] | None = None,
    ) -> dict[str, Any]:
        """Assess overall quality of research results.
        
        Args:
            research_result: Complete research result to assess.
            quality_metrics: Specific quality metrics to evaluate.
            
        Returns:
            Quality assessment with improvement recommendations.
        """
        ...

    async def optimize_search_strategy(
        self,
        initial_results: list[ResearchFinding],
        target_quality: float = 0.8,
    ) -> QueryPlan:
        """Optimize search strategy based on initial results.
        
        Args:
            initial_results: Initial research results.
            target_quality: Target quality threshold.
            
        Returns:
            Optimized query plan for improved results.
        """
        ...

    async def extract_key_insights(
        self,
        research_findings: list[ResearchFinding],
        insight_type: str = "comprehensive",
    ) -> list[str]:
        """Extract key insights from research findings.
        
        Args:
            research_findings: Research findings to analyze.
            insight_type: Type of insights to extract.
            
        Returns:
            List of key insights with explanations.
        """
        ...

    async def generate_research_summary(
        self,
        research_result: ResearchResponse,
        summary_type: str = "executive",
    ) -> dict[str, Any]:
        """Generate comprehensive research summary.
        
        Args:
            research_result: Complete research results.
            summary_type: Type of summary to generate.
            
        Returns:
            Research summary with key findings and recommendations.
        """
        ...

    async def estimate_research_complexity(
        self,
        task: DelegationTask,
    ) -> float:
        """Estimate research task complexity.
        
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
        """Extract compressed key findings from research output.
        
        Args:
            full_output: Complete research results.
            
        Returns:
            Compressed summary for orchestrator integration.
        """
        ...

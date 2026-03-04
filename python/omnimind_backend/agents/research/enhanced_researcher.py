"""Enhanced researcher agent with multi-query execution.

Integrates PinchTab browser automation, query planning, and result
synthesis to provide comprehensive research capabilities.
"""

from __future__ import annotations

import asyncio
from typing import Any

from omnimind_backend.agents.research.enhanced_query_planner import get_enhanced_query_planner
from omnimind_backend.agents.research.result_synthesizer import get_result_synthesizer
from omnimind_backend.agents.research.source_trust_engine import get_source_trust_engine
from omnimind_backend.agents.tools.browser_search import get_browser_search_tool
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.schemas.agents.research import (
    QueryPlan,
    ResearchConfig,
    ResearchRequest,
    ResearchResponse,
)

_logger = get_logger(__name__)


class EnhancedResearcherAgent:
    """Enhanced researcher agent with multi-query browser automation."""
    
    def __init__(self) -> None:
        """Initialize enhanced researcher agent."""
        self.query_planner = get_enhanced_query_planner()
        self.browser_tool = None
        self.source_trust_engine = get_source_trust_engine()
        self.result_synthesizer = get_result_synthesizer()
        self.session_id = None
        self.agent_id = None
        
    async def initialize(self, session_id: str, agent_id: str) -> None:
        """Initialize the agent for a research session.
        
        Args:
            session_id: Research session identifier
            agent_id: Agent identifier
        """
        self.session_id = session_id
        self.agent_id = agent_id
        
        # Initialize browser search tool
        self.browser_tool = await get_browser_search_tool()
        await self.browser_tool.initialize(session_id, agent_id)
        
        _logger.info(
            "enhanced_researcher_initialized",
            session_id=session_id,
            agent_id=agent_id,
        )
        
    async def execute_research(
        self,
        query: str,
        config: ResearchConfig | None = None,
        force_browser_search: bool = False,
    ) -> ResearchResponse:
        """Execute comprehensive research using browser automation.
        
        Args:
            query: Research query/question
            config: Optional research configuration
            force_browser_search: Force browser search even for simple queries
            
        Returns:
            Research response with findings and synthesis
        """
        if not self.browser_tool:
            return ResearchResponse(
                success=False,
                error_message="Research agent not initialized"
            )
            
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Analyze query intent using enhanced planner
            intent = self.query_planner.analyze_intent(query)
            
            # Determine if browser search is needed
            use_browser_search = force_browser_search or self._should_use_browser_search(intent)
            
            if not use_browser_search:
                # For simple queries, could fallback to regular web search
                return ResearchResponse(
                    success=False,
                    error_message="Query too simple for browser search. Use regular web search instead."
                )
                
            # Create enhanced query plan
            query_plan = self.query_planner.plan_queries(intent, query)
            
            # Apply configuration overrides
            if config:
                query_plan.max_results_per_browser = config.max_concurrent_browsers
                # Could add more config overrides here
                
            # Execute research with browser automation
            result = await self.browser_tool.execute_research(
                query_plan,
                max_concurrent_browsers=config.max_concurrent_browsers if config else 5
            )
            
            # Enhanced source trust evaluation
            enhanced_findings = []
            for finding in result.findings:
                # Re-evaluate source trust with advanced engine
                enhanced_classification = self.source_trust_engine.evaluate_source(
                    url=finding.source_url,
                    content=finding.content_summary,
                    title="",  # Could be extracted if needed
                    existing_sources=[f.source_url for f in result.findings if f != finding]
                )
                
                # Update finding with enhanced classification
                enhanced_finding = finding.model_copy()
                enhanced_finding.source_classification = enhanced_classification
                enhanced_findings.append(enhanced_finding)
            
            # Advanced result synthesis
            synthesis_results = self.result_synthesizer.synthesize_results(
                enhanced_findings, query
            )
            
            total_duration = int(asyncio.get_event_loop().time() - start_time)
            
            execution_summary = {
                "query_analysis": {
                    "question_type": intent.question_type.value,
                    "complexity_level": intent.complexity_level,
                    "browser_count": intent.browser_count,
                    "estimated_duration": intent.estimated_duration_seconds,
                },
                "execution": {
                    "actual_duration_seconds": total_duration,
                    "browsers_used": result.browsers_used,
                    "findings_count": len(enhanced_findings),
                    "success_rate": sum(1 for f in enhanced_findings if f.confidence_score >= 0.7) / len(enhanced_findings) if enhanced_findings else 0,
                },
                "sources": {
                    "source_types": list(set(f.source_classification.source_type.value for f in enhanced_findings)),
                    "trust_levels": list(set(f.source_classification.trust_level.value for f in enhanced_findings)),
                    "average_confidence": sum(f.confidence_score for f in enhanced_findings) / len(enhanced_findings) if enhanced_findings else 0,
                },
                "synthesis": {
                    "conflicts_detected": len(synthesis_results["conflicts"]),
                    "gaps_identified": len(synthesis_results["gaps"]),
                    "consensus_level": synthesis_results.get("consensus_analysis", {}).get("consensus_level", "unknown"),
                }
            }
            
            # Update result with enhanced findings and synthesis
            result.findings = enhanced_findings
            result.synthesis_summary = synthesis_results["summary"]
            result.conflicts_identified = synthesis_results["conflicts"]
            result.gaps_identified = synthesis_results["gaps"]
            result.recommendations = synthesis_results["recommendations"]
            
            _logger.info(
                "enhanced_research_execution_completed",
                session_id=self.session_id,
                agent_id=self.agent_id,
                query=query,
                duration_seconds=total_duration,
                findings_count=len(enhanced_findings),
                confidence_level=result.confidence_level,
                conflicts_count=len(synthesis_results["conflicts"]),
            )
            
            return ResearchResponse(
                success=True,
                result=result,
                execution_summary=execution_summary,
            )
            
        except Exception as exc:
            duration = int(asyncio.get_event_loop().time() - start_time)
            
            _logger.error(
                "research_execution_failed",
                session_id=self.session_id,
                agent_id=self.agent_id,
                query=query,
                error=str(exc),
                duration_seconds=duration,
            )
            
            return ResearchResponse(
                success=False,
                error_message=str(exc),
                execution_summary={"duration_seconds": duration}
            )
            
    async def execute_simple_search(self, query: str) -> ResearchResponse:
        """Execute a simple search with minimal browser usage.
        
        Args:
            query: Simple research query
            
        Returns:
            Research response with basic findings
        """
        # Create a minimal query plan for simple searches
        from omnimind_backend.schemas.agents.research import QueryIntent, QuestionType
        
        intent = QueryIntent(
            question_type=QuestionType.GENERAL,
            complexity_level="simple",
            browser_count=1,
            estimated_duration_seconds=30,
        )
        
        query_plan = self.query_engine.plan_queries(intent, query)
        
        try:
            result = await self.browser_tool.execute_research(query_plan, max_concurrent_browsers=1)
            
            return ResearchResponse(
                success=True,
                result=result,
                execution_summary={
                    "search_type": "simple",
                    "browsers_used": 1,
                    "findings_count": len(result.findings),
                }
            )
            
        except Exception as exc:
            _logger.error(
                "simple_search_failed",
                session_id=self.session_id,
                agent_id=self.agent_id,
                query=query,
                error=str(exc),
            )
            
            return ResearchResponse(
                success=False,
                error_message=str(exc)
            )
            
    def _should_use_browser_search(self, intent: Any) -> bool:
        """Determine if browser search should be used based on intent.
        
        Args:
            intent: Query intent analysis
            
        Returns:
            True if browser search is recommended
        """
        # Use browser search for complex queries or specific question types
        complex_questions = [
            "comparison",
            "current_state", 
            "debug",
            "informational_data",
        ]
        
        if intent.question_type.value in complex_questions:
            return True
            
        # Use browser search for complex and deep research
        if intent.complexity_level in ["complex", "deep"]:
            return True
            
        # Use browser search if multiple browsers are needed
        if intent.browser_count > 1:
            return True
            
        # Default to simple queries can use regular web search
        return False
        
    async def get_research_capabilities(self) -> dict[str, Any]:
        """Get information about research capabilities.
        
        Returns:
            Dictionary with capability information
        """
        return {
            "supported_question_types": [
                "definition", "tutorial", "comparison", "current_state",
                "debug", "informational_data", "documentation", "general"
            ],
            "complexity_levels": ["simple", "moderate", "complex", "deep"],
            "max_concurrent_browsers": 10,
            "search_engines": ["google.com", "duckduckgo.com", "brave.com", "stackoverflow.com", "github.com"],
            "source_types": [
                "official", "academic", "reputable_community", 
                "tech_publication", "unknown_blog", "social"
            ],
            "features": [
                "multi_query_execution",
                "source_classification",
                "confidence_scoring",
                "action_trail_logging",
                "parallel_browser_execution",
                "result_synthesis",
            ]
        }
        
    async def cleanup(self) -> None:
        """Clean up resources and close browser instances."""
        if self.browser_tool:
            # Browser tool cleanup is handled by PinchTabService context managers
            pass
            
        _logger.info(
            "enhanced_researcher_cleanup_completed",
            session_id=self.session_id,
            agent_id=self.agent_id,
        )


# Global agent instance
_enhanced_researcher: EnhancedResearcherAgent | None = None


async def get_enhanced_researcher_agent() -> EnhancedResearcherAgent:
    """Get or create the global enhanced researcher agent instance."""
    global _enhanced_researcher
    if _enhanced_researcher is None:
        _enhanced_researcher = EnhancedResearcherAgent()
    return _enhanced_researcher

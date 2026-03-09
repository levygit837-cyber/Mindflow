"""Enhanced research agent interface.

Extends research capabilities with comprehensive query planning,
web search, result synthesis, and integration with core personality contract.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any

from mindflow_backend.interfaces.agents.core_personality import (
    CorePersonalityContract,
)
from mindflow_backend.schemas.orchestration.delegation import DelegationTask, DelegationResult
from mindflow_backend.schemas.agents.research import (
    BrowserAction,
    BrowserActionRequest,
    BrowserActionResponse,
    QueryPlan,
    ResearchConfig,
    ResearchResult,
)


@runtime_checkable
class EnhancedResearcher(CorePersonalityContract, Protocol):
    """Contract for enhanced research agents with comprehensive capabilities.
    
    Extends core personality with specialized research methods including
    query planning, web search, result synthesis, and delegation management.
    """
    
    async def plan_query(
        self, 
        query: str, 
        context: dict[str, Any] | None = None
    ) -> QueryPlan:
        """Plan research query with optimal strategy.
        
        Args:
            query: Research query to plan
            context: Additional context for planning
            
        Returns:
            Structured query plan with search strategy
        """
        ...
    
    async def execute_web_search(
        self, 
        plan: QueryPlan
    ) -> ResearchResult:
        """Execute web search according to plan.
        
        Args:
            plan: Structured query plan with sources and strategy
            
        Returns:
            ResearchResult: Search results with metadata and synthesis
        """
        ...
    
    async def synthesize_results(
        self, 
        results: list[ResearchResult], 
        original_query: str
    ) -> ResearchResult:
        """Synthesize multiple search results into coherent response.
        
        Args:
            results: List of search results to synthesize
            original_query: Original research query
            
        Returns:
            Synthesized research result
        """
        ...
    
    async def delegate_research(
        self, 
        task: DelegationTask
    ) -> DelegationResult:
        """Delegate research task to specialized agent.
        
        Args:
            task: Research delegation task
            
        Returns:
            Delegation execution result
        """
        ...
    
    async def manage_research_session(
        self, 
        config: ResearchConfig
    ) -> ResearchSession:
        """Manage persistent research session.
        
        Args:
            config: Research session configuration
            
        Returns:
            Active research session
        """
        ...

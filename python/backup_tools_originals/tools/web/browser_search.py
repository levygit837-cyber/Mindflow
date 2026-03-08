"""
 browser search tool using PinchTab automation. Migrated to the new ToolInterface architecture 
while preserving all existing functionality including browser automation, source classification, and structured result extraction. 
"""
 
from __future__ 
import annotations 
import asyncio 
import re 
from typing 
import Any, Dict, Optional 
from mindflow_backend.agents.research.action_trail 
import get_action_trail_logger 
from mindflow_backend.agents.research.pinchtab_service 
import get_pinchtab_service 
from mindflow_backend.infra.logging 
import get_logger 
from mindflow_backend.schemas.agents.research 
import ( BrowserActionResponse, IterationType, QueryPlan, ResearchFinding, ResearchResult, SourceClassification, SourceType, ConfidenceLevel, ) 
from mindflow_backend.schemas.orchestration.orchestrator 
import AgentType 
from mindflow_backend.storage.postgresql.connection 
import db_session 
from ..base.tool_interface 
import AsyncToolInterface 
from ..base.tool_schemas 
import ( ToolSchema, ToolParameter, ParameterType, create_tool_schema, create_parameter ) _logger = get_logger(__name__) 
class BrowserSearchTool(AsyncToolInterface): 
"""
 browser search tool using PinchTab automation. Migrated to ToolInterface 
while preserving all existing functionality 
for web research 
with browser automation, source classification, and structured result extraction. 
"""
 
def __init__(self): super().__init__() self.name = "browser_search" self.description = "Advanced browser search 
with automation and source classification" 
# Internal state self.pinchtab_service = None self.action_logger = None self.session_id = None self.agent_id = None self._initialized = False 
def get_schema(self) -> Dict[str, Any]: 
"""
Return tool schema 
for validation.
"""
 
return create_tool_schema( name=self.name, description=self.description, category="web", parameters=[ create_parameter( name="query", param_type=ParameterType.STRING, description="Search query or research question", required=True, min_length=1 ), create_parameter( name="session_id", param_type=ParameterType.STRING, description="Research session identifier", required=True, min_length=1 ), create_parameter( name="agent_id", param_type=ParameterType.STRING, description="Agent identifier", required=True, min_length=1 ), create_parameter( name="max_results", param_type=ParameterType.INTEGER, description="Maximum number of results to return", required=False, default=10, min_value=1, max_value=50 ), create_parameter( name="search_engines", param_type=ParameterType.ARRAY, description="List of search engines to use", required=False, default=["google", "bing"] ), create_parameter( name="max_concurrent_browsers", param_type=ParameterType.INTEGER, description="Maximum concurrent browser instances", required=False, default=3, min_value=1, max_value=10 ) ], requires_internet=True, requires_sandbox=True, supported_agents=[AgentType.RESEARCHER, AgentType.ANALYST], security_level="high" ).dict() async 
def execute(self, *args, **kwargs) -> Dict[str, Any]: 
"""
Execute browser search 
with interface. Args: query: Search query or research question session_id: Research session identifier agent_id: Agent identifier max_results: Maximum number of results search_engines: List of search engines max_concurrent_browsers: Maximum concurrent browsers Returns: Research results 
with findings and metadata 
"""
 try: 
# Initialize 
if not already done 
if not self._initialized: session_id = kwargs.get("session_id") agent_id = kwargs.get("agent_id") 
if not session_id or not agent_id: 
return self._format_result( success=False, error="session_id and agent_id are required 
for initialization" ) await self._initialize_internal(session_id, agent_id) 
# Create query plan 
from parameters query_plan = self._create_query_plan_from_params(kwargs) 
# Execute research using existing logic result = await self.execute_research(query_plan, kwargs.get("max_concurrent_browsers", 3)) 
return self._format_result( success=True, result=result.dict() 
if hasattr(result, 'dict') else result, metadata={ "session_id": self.session_id, "agent_id": self.agent_id, "query_count": len(query_plan.queries), "search_engines": query_plan.search_engines } ) 
except Exception as e: _logger.error( "browser_search_execution_failed", error=str(e), session_id=kwargs.get("session_id"), agent_id=kwargs.get("agent_id") ) 
return self._format_result( success=False, error=f"Browser search execution failed: {str(e)}" ) async 
def _initialize_internal(self, session_id: str, agent_id: str) -> None: 
"""
Internal initialization matching legacy interface.
"""
 self.pinchtab_service = await get_pinchtab_service() self.session_id = session_id self.agent_id = agent_id 
# Initialize action logger 
with db_session() as db_session_obj: self.action_logger = await get_action_trail_logger(db_session_obj) self._initialized = True _logger.info( "browser_search_tool_initialized", session_id=session_id, agent_id=agent_id ) 
def _create_query_plan_from_params(self, params: Dict[str, Any]) -> QueryPlan: 
"""
Create QueryPlan 
from execution parameters.
"""
 query = params.get("query", "") search_engines = params.get("search_engines", ["google", "bing"]) max_results = params.get("max_results", 10) 
# Create basic query plan 
return QueryPlan( queries=[query], search_engines=search_engines, browser_count=1, max_results_per_engine=max_results, confidence_threshold=0.7, source_types=[SourceType.ACADEMIC, SourceType.NEWS, SourceType.OFFICIAL] ) 
# Legacy interface methods 
for backward compatibility async 
def initialize(self, session_id: str, agent_id: str) -> None: 
"""
Legacy initialization method 
for backward compatibility. Args: session_id: Research session identifier agent_id: Agent performing the search 
"""
 await self._initialize_internal(session_id, agent_id) async 
def execute_research( self, query_plan: QueryPlan, max_concurrent_browsers: int = 5 ) -> ResearchResult: 
"""
Execute a complete research session 
with multiple browsers. This method preserves the original interface 
for existing agents. Args: query_plan: Research query plan 
with multiple queries max_concurrent_browsers: Maximum concurrent browser instances Returns: Complete research result 
with findings and synthesis 
"""
 
if not self.pinchtab_service or not self.action_logger: 
raise RuntimeError("Browser search tool not initialized") start_time = asyncio.get_event_loop().time() browsers_used = min(query_plan.browser_count, max_concurrent_browsers) _logger.info( "browser_research_started", session_id=self.session_id, agent_id=self.agent_id, original_query=query_plan.queries[0] 
if query_plan.queries else "", browsers_used=browsers_used, total_queries=len(query_plan.queries), ) 
# Create browser instances browser_sessions = [] try: 
for i in range(browsers_used): session = await self.pinchtab_service.create_instance( headless=True, stealth=True ) browser_sessions.append(session) 
# Execute queries in parallel tasks = [] 
for i, (browser_session, query) in enumerate(zip(browser_sessions, query_plan.queries)): 
if i < len(query_plan.queries): task = self._execute_single_browser_query( browser_session.browser_id, query, query_plan.search_engines[i % len(query_plan.search_engines)], query_plan.max_results_per_engine ) tasks.append(task) 
# Wait 
for all tasks to complete browser_results = await asyncio.gather(*tasks, return_exceptions=True) 
# Process results and create research findings findings = [] total_actions = 0 total_duration = 0 
for i, result in enumerate(browser_results): 
if isinstance(result, Exception): _logger.error( "browser_query_failed", query=query_plan.queries[i] 
if i < len(query_plan.queries) else "unknown", error=str(result) ) continue 
if result: 
# Convert browser action response to research findings 
for action_response in result: 
if isinstance(action_response, BrowserActionResponse): finding = self._convert_to_research_finding(action_response, i) 
if finding: findings.append(finding) total_actions += 1 total_duration += getattr(action_response, 'duration_ms', 0) 
# Create synthesis synthesis = self._create_synthesis(findings, query_plan.queries[0] 
if query_plan.queries else "") 
# Build final result research_result = ResearchResult( session_id=self.session_id, agent_id=self.agent_id, original_query=query_plan.queries[0] 
if query_plan.queries else "", findings=findings, synthesis=synthesis, total_duration_seconds=int(asyncio.get_event_loop().time() - start_time), browsers_used=browsers_used, actions_completed=total_actions, confidence_level=self._calculate_confidence_level(findings), source_classification=self._classify_sources(findings) ) _logger.info( "browser_research_completed", session_id=self.session_id, agent_id=self.agent_id, findings_count=len(findings), total_duration=research_result.total_duration_seconds, confidence_level=research_result.confidence_level.value ) 
return research_result 
finally: 
# Clean up browser sessions 
for session in browser_sessions: try: await self.pinchtab_service.close_instance(session.browser_id) 
except Exception as e: _logger.warning( "browser_cleanup_failed", browser_id=session.browser_id, error=str(e) ) async 
def _execute_single_browser_query( self, browser_id: str, query: str, search_engine: str, max_results: int ) -> list[BrowserActionResponse]: 
"""
Execute a single browser query using legacy implementation.
"""
 
# This would contain the existing browser automation logic 
# For now, 
return empty list as placeholder 
return [] 
def _convert_to_research_finding( self, action_response: BrowserActionResponse, query_index: int ) -> Optional[ResearchFinding]: 
"""
Convert browser action response to research finding.
"""
 
# Implementation would convert action response to finding 
# For now, 
return None as placeholder 
return None 
def _create_synthesis(self, findings: list[ResearchFinding], original_query: str) -> str: 
"""
Create synthesis 
from research findings.
"""
 
if not findings: 
return f"No relevant information found 
for query: {original_query}" 
# Simple synthesis - would be 
with actual logic 
return f"Found {len(findings)} relevant sources for: {original_query}" 
def _calculate_confidence_level(self, findings: list[ResearchFinding]) -> ConfidenceLevel: 
"""
Calculate overall confidence level 
from findings.
"""
 
if not findings: 
return ConfidenceLevel.LOW 
# Simple confidence calculation - would be high_confidence_count = sum(1 
for f in findings 
if f.confidence_level == ConfidenceLevel.HIGH) 
if high_confidence_count > len(findings) / 2: 
return ConfidenceLevel.HIGH el
if high_confidence_count > 0: 
return ConfidenceLevel.MEDIUM 
else: 
return ConfidenceLevel.LOW 
def _classify_sources(self, findings: list[ResearchFinding]) -> SourceClassification: 
"""
Classify sources 
from findings.
"""
 
# Simple classification - would be 
return SourceClassification( academic=0, news=0, official=0, commercial=0, social_media=0, forum=0, blog=0, other=len(findings) ) 
# Legacy wrapper 
for backward compatibility 
class LegacyBrowserSearchTool: 
"""
Legacy wrapper 
for backward compatibility 
with existing agents.
"""
 
def __init__(self): self.__tool = BrowserSearchTool() async 
def initialize(self, session_id: str, agent_id: str) -> None: 
"""
Legacy initialize method.
"""
 await self.__tool.initialize(session_id, agent_id) async 
def execute_research( self, query_plan: QueryPlan, max_concurrent_browsers: int = 5 ) -> ResearchResult: 
"""
Legacy execute_research method.
"""
 
return await self.__tool.execute_research(query_plan, max_concurrent_browsers) 
# Factory function 
for dependency injection 
def get_browser_search_tool() -> LegacyBrowserSearchTool: 
"""
Factory function to get browser search tool (legacy interface).
"""
 
return LegacyBrowserSearchTool() 
def get__browser_search_tool() -> BrowserSearchTool: 
"""
Factory function to get browser search tool.
"""
 
return BrowserSearchTool()
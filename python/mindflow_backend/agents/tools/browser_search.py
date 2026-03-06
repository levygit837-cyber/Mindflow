"""Browser search tool using PinchTab automation.

Provides async interface for web research with browser automation,
source classification, and structured result extraction.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from mindflow_backend.agents.research.action_trail import get_action_trail_logger
from mindflow_backend.agents.research.pinchtab_service import get_pinchtab_service
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.agents.research import (
    BrowserActionResponse,
    IterationType,
    QueryPlan,
    ResearchFinding,
    ResearchResult,
    SourceClassification,
    SourceType,
    ConfidenceLevel,
)
from mindflow_backend.storage.postgresql.connection import db_session

_logger = get_logger(__name__)


class BrowserSearchTool:
    """Async browser search tool using PinchTab automation."""
    
    def __init__(self) -> None:
        """Initialize browser search tool."""
        self.pinchtab_service = None
        self.action_logger = None
        
    async def initialize(self, session_id: str, agent_id: str) -> None:
        """Initialize the tool with session context.
        
        Args:
            session_id: Research session identifier
            agent_id: Agent performing the search
        """
        self.pinchtab_service = await get_pinchtab_service()
        self.session_id = session_id
        self.agent_id = agent_id
        
        # Initialize action logger
        with db_session() as db_session_obj:
            self.action_logger = await get_action_trail_logger(db_session_obj)
        
    async def execute_research(
        self, 
        query_plan: QueryPlan,
        max_concurrent_browsers: int = 5
    ) -> ResearchResult:
        """Execute a complete research session with multiple browsers.
        
        Args:
            query_plan: Research query plan with multiple queries
            max_concurrent_browsers: Maximum concurrent browser instances
            
        Returns:
            Complete research result with findings and synthesis
        """
        if not self.pinchtab_service or not self.action_logger:
            raise RuntimeError("Browser search tool not initialized")
            
        start_time = asyncio.get_event_loop().time()
        browsers_used = min(query_plan.browser_count, max_concurrent_browsers)
        
        _logger.info(
            "browser_research_started",
            session_id=self.session_id,
            agent_id=self.agent_id,
            original_query=query_plan.queries[0] if query_plan.queries else "",
            browsers_used=browsers_used,
            total_queries=len(query_plan.queries),
        )
        
        # Create browser instances
        browser_sessions = []
        try:
            for i in range(browsers_used):
                session = await self.pinchtab_service.create_instance(
                    headless=True, 
                    stealth=True
                )
                browser_sessions.append(session)
                
            # Execute queries in parallel
            tasks = []
            for i, (browser_session, query) in enumerate(zip(browser_sessions, query_plan.queries)):
                if i < len(query_plan.queries):
                    task = self._execute_single_browser_query(
                        browser_session.browser_id,
                        query,
                        query_plan.search_engines[i % len(query_plan.search_engines)],
                        query_plan.max_results_per_browser,
                    )
                    tasks.append(task)
                    
            # Wait for all browsers to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect findings from successful results
            all_findings = []
            action_trail = []
            
            for result in results:
                if isinstance(result, Exception):
                    _logger.error(
                        "browser_query_failed",
                        session_id=self.session_id,
                        error=str(result),
                    )
                    continue
                    
                if result:
                    all_findings.extend(result["findings"])
                    action_trail.extend(result["action_trail"])
                    
            # Synthesize results
            synthesis = self._synthesize_findings(all_findings, query_plan.queries[0])
            
            total_duration = int(asyncio.get_event_loop().time() - start_time)
            
            research_result = ResearchResult(
                session_id=self.session_id,
                original_query=query_plan.queries[0],
                question_type=query_plan.intent.question_type,
                browsers_used=browsers_used,
                findings=all_findings,
                synthesis_summary=synthesis["summary"],
                confidence_level=synthesis["confidence_level"],
                conflicts_identified=synthesis["conflicts"],
                gaps_identified=synthesis["gaps"],
                recommendations=synthesis["recommendations"],
                total_duration_seconds=total_duration,
                action_trail=action_trail,
            )
            
            _logger.info(
                "browser_research_completed",
                session_id=self.session_id,
                browsers_used=browsers_used,
                findings_count=len(all_findings),
                total_duration_seconds=total_duration,
                confidence_level=synthesis["confidence_level"],
            )
            
            return research_result
            
        finally:
            # Cleanup all browser instances
            if browser_sessions:
                await self._cleanup_browsers(browser_sessions)
                
    async def _execute_single_browser_query(
        self,
        browser_id: str,
        query: str,
        search_engine: str,
        max_results: int,
    ) -> dict[str, Any]:
        """Execute a single query on a browser instance.
        
        Args:
            browser_id: Browser session identifier
            query: Search query string
            search_engine: Search engine to use
            max_results: Maximum results to extract
            
        Returns:
            Dictionary with findings and action trail
        """
        findings = []
        action_trail = []
        
        try:
            # Navigate to search engine
            search_url = self._get_search_engine_url(search_engine)
            await self._log_and_execute_action(
                browser_id,
                IterationType.NAVIGATE,
                lambda: self.pinchtab_service.navigate(browser_id, search_url)
            )
            
            # Find and fill search box
            await self._perform_search(browser_id, query)
            
            # Extract search results
            results_response = await self._log_and_execute_action(
                browser_id,
                IterationType.EXTRACT,
                lambda: self.pinchtab_service.extract_text(browser_id)
            )
            
            if results_response.success:
                # Parse search results and visit top pages
                search_results = self._parse_search_results(results_response.result_data.get("text", ""))
                
                for i, result in enumerate(search_results[:max_results]):
                    try:
                        # Navigate to result page
                        await self._log_and_execute_action(
                            browser_id,
                            IterationType.NAVIGATE,
                            lambda: self.pinchtab_service.navigate(browser_id, result["url"])
                        )
                        
                        # Extract content
                        content_response = await self._log_and_execute_action(
                            browser_id,
                            IterationType.EXTRACT,
                            lambda: self.pinchtab_service.extract_text(browser_id)
                        )
                        
                        if content_response.success:
                            # Create finding
                            classification = self._classify_source(result["url"])
                            finding = ResearchFinding(
                                source_url=result["url"],
                                source_classification=classification,
                                content_summary=self._extract_summary(
                                    content_response.result_data.get("text", "")
                                ),
                                key_points=self._extract_key_points(
                                    content_response.result_data.get("text", "")
                                ),
                                confidence_score=self._calculate_confidence(classification),
                                relevance_score=self._calculate_relevance(query, result),
                            )
                            findings.append(finding)
                            
                    except Exception as exc:
                        _logger.warning(
                            "result_extraction_failed",
                            browser_id=browser_id,
                            url=result.get("url", ""),
                            error=str(exc),
                        )
                        continue
                        
        except Exception as exc:
            _logger.error(
                "browser_query_execution_failed",
                browser_id=browser_id,
                query=query,
                error=str(exc),
            )
            
        return {
            "findings": findings,
            "action_trail": action_trail,
        }
        
    async def _perform_search(self, browser_id: str, query: str) -> None:
        """Perform search query on current page.
        
        Args:
            browser_id: Browser session identifier
            query: Search query string
        """
        # Get snapshot to find search input
        snapshot_response = await self._log_and_execute_action(
            browser_id,
            IterationType.SNAPSHOT,
            lambda: self.pinchtab_service.get_snapshot(browser_id, filter_interactive=True)
        )
        
        if not snapshot_response.success:
            raise RuntimeError("Failed to get page snapshot")
            
        # Find search input
        search_input = self._find_search_input(snapshot_response.result_data)
        if not search_input:
            raise RuntimeError("Search input not found on page")
            
        # Fill search query
        await self._log_and_execute_action(
            browser_id,
            IterationType.FILL,
            lambda: self.pinchtab_service.fill_input(browser_id, search_input, query)
        )
        
        # Press Enter to search
        await self._log_and_execute_action(
            browser_id,
            IterationType.PRESS,
            lambda: self.pinchtab_service.press_key(browser_id, search_input, "Enter")
        )
        
        # Wait a moment for results to load
        await asyncio.sleep(2)
        
    async def _log_and_execute_action(
        self,
        browser_id: str,
        iteration_type: IterationType,
        action_func,
    ) -> BrowserActionResponse:
        """Execute action with automatic logging.
        
        Args:
            browser_id: Browser session identifier
            iteration_type: Type of action
            action_func: Async function to execute
            
        Returns:
            Browser action response
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await action_func()
            
            # Log the action
            await self.action_logger.log_action(
                session_id=self.session_id,
                agent_id=self.agent_id,
                browser_id=browser_id,
                iteration_type=iteration_type,
                action_data=getattr(action_func, "__name__", "unknown"),
                success=response.success,
                error_message=response.error_message,
                duration_ms=response.duration_ms,
            )
            
            return response
            
        except Exception as exc:
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Log failed action
            await self.action_logger.log_action(
                session_id=self.session_id,
                agent_id=self.agent_id,
                browser_id=browser_id,
                iteration_type=iteration_type,
                action_data=getattr(action_func, "__name__", "unknown"),
                success=False,
                error_message=str(exc),
                duration_ms=duration_ms,
            )
            
            raise
            
    def _get_search_engine_url(self, search_engine: str) -> str:
        """Get search engine homepage URL.
        
        Args:
            search_engine: Search engine name
            
        Returns:
            Search engine URL
        """
        urls = {
            "google.com": "https://www.google.com",
            "duckduckgo.com": "https://duckduckgo.com",
            "brave.com": "https://search.brave.com",
            "stackoverflow.com": "https://stackoverflow.com",
            "github.com": "https://github.com",
        }
        return urls.get(search_engine, "https://www.google.com")
        
    def _parse_search_results(self, text: str) -> list[dict[str, str]]:
        """Parse search results from page text.
        
        Args:
            text: Page text content
            
        Returns:
            List of search results with URL and title
        """
        # Simple regex-based URL extraction
        url_pattern = r'https?://[^\s<>"\'\)]+'
        urls = re.findall(url_pattern, text)
        
        results = []
        for url in urls[:10]:  # Limit to first 10 URLs
            # Extract title from surrounding text (simplified)
            title_start = text.find(url)
            if title_start != -1:
                # Look for title context before URL
                context_start = max(0, title_start - 100)
                context = text[context_start:title_start]
                title = context.strip().split('\n')[-1].strip()
                if not title or len(title) > 100:
                    title = url.split('/')[2]  # Use domain as fallback
            else:
                title = url.split('/')[2]
                
            results.append({
                "url": url,
                "title": title,
            })
            
        return results
        
    def _find_search_input(self, snapshot_data: dict[str, Any]) -> str | None:
        """Find search input element from snapshot.
        
        Args:
            snapshot_data: Page snapshot data
            
        Returns:
            Element reference for search input
        """
        elements = snapshot_data.get("elements", [])
        
        for element in elements:
            if element.get("type") == "input" and (
                "search" in element.get("attributes", {}).get("type", "").lower() or
                "search" in element.get("attributes", {}).get("name", "").lower() or
                "search" in element.get("attributes", {}).get("id", "").lower() or
                "search" in element.get("attributes", {}).get("class", "").lower()
            ):
                return element.get("ref")
                
        # Fallback to first text input
        for element in elements:
            if element.get("type") == "input" and element.get("attributes", {}).get("type") in ["text", "search"]:
                return element.get("ref")
                
        return None
        
    def _classify_source(self, url: str) -> SourceClassification:
        """Classify source by URL pattern.
        
        Args:
            url: Source URL
            
        Returns:
            Source classification
        """
        domain = url.split('/')[2].lower() if '/' in url else ""
        
        # Official sources
        if any(official in domain for official in ["docs.", "api.", "developer.", ".gov", ".edu"]):
            return SourceClassification(
                url=url,
                source_type=SourceType.OFFICIAL,
                trust_level=ConfidenceLevel.HIGH,
                domain_authority=0.9,
            )
            
        # Academic sources
        if any(academic in domain for academic in ["arxiv", "scholar", "research.", ".edu"]):
            return SourceClassification(
                url=url,
                source_type=SourceType.ACADEMIC,
                trust_level=ConfidenceLevel.HIGH,
                domain_authority=0.85,
            )
            
        # Reputable community
        if any(comm in domain for comm in ["stackoverflow", "github", "reddit"]):
            return SourceClassification(
                url=url,
                source_type=SourceType.REPUTABLE_COMMUNITY,
                trust_level=ConfidenceLevel.MEDIUM,
                domain_authority=0.8,
            )
            
        # Tech publications
        if any(tech in domain for tech in ["medium.com", "dev.to", "css-tricks", "hackernoon"]):
            return SourceClassification(
                url=url,
                source_type=SourceType.TECH_PUBLICATION,
                trust_level=ConfidenceLevel.MEDIUM,
                domain_authority=0.7,
            )
            
        # Unknown/blog
        return SourceClassification(
            url=url,
            source_type=SourceType.UNKNOWN_BLOG,
            trust_level=ConfidenceLevel.LOW,
            domain_authority=0.5,
        )
        
    def _extract_summary(self, text: str, max_length: int = 500) -> str:
        """Extract summary from page text.
        
        Args:
            text: Page text content
            max_length: Maximum summary length
            
        Returns:
            Text summary
        """
        # Remove extra whitespace and take first paragraph
        cleaned = re.sub(r'\s+', ' ', text.strip())
        sentences = cleaned.split('. ')
        
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) < max_length:
                summary += sentence + ". "
            else:
                break
                
        return summary.strip() or cleaned[:max_length]
        
    def _extract_key_points(self, text: str) -> list[str]:
        """Extract key points from page text.
        
        Args:
            text: Page text content
            
        Returns:
            List of key points
        """
        # Simple extraction: look for bullet points, numbered lists, or highlighted text
        points = []
        
        # Look for bullet points
        bullet_pattern = r'[•\-\*]\s+([^\n]+)'
        bullets = re.findall(bullet_pattern, text)
        points.extend(bullets[:5])  # Limit to 5 points
        
        # Look for numbered lists
        number_pattern = r'^\d+\.\s+([^\n]+)'
        numbers = re.findall(number_pattern, text, re.MULTILINE)
        points.extend(numbers[:3])  # Limit to 3 numbered points
        
        # If no structured points found, extract important sentences
        if not points:
            sentences = text.split('. ')
            # Look for sentences with important keywords
            important_keywords = ["important", "key", "critical", "essential", "main", "primary"]
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in important_keywords):
                    points.append(sentence.strip())
                    if len(points) >= 3:
                        break
                        
        return [point.strip() for point in points if point.strip()][:5]
        
    def _calculate_confidence(self, classification: SourceClassification) -> float:
        """Calculate confidence score based on source classification.
        
        Args:
            classification: Source classification
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        base_scores = {
            SourceType.OFFICIAL: 0.9,
            SourceType.ACADEMIC: 0.85,
            SourceType.REPUTABLE_COMMUNITY: 0.75,
            SourceType.TECH_PUBLICATION: 0.65,
            SourceType.UNKNOWN_BLOG: 0.4,
            SourceType.SOCIAL: 0.2,
        }
        
        base_score = base_scores.get(classification.source_type, 0.5)
        
        # Adjust based on domain authority
        adjusted_score = base_score * (0.7 + 0.3 * classification.domain_authority)
        
        return min(1.0, max(0.0, adjusted_score))
        
    def _calculate_relevance(self, query: str, result: dict[str, str]) -> float:
        """Calculate relevance score for search result.
        
        Args:
            query: Original search query
            result: Search result with URL and title
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        query_terms = set(query.lower().split())
        title_terms = set(result.get("title", "").lower().split())
        url_terms = set(result.get("url", "").lower().split("/"))
        
        # Calculate term overlap
        title_overlap = len(query_terms.intersection(title_terms)) / max(len(query_terms), 1)
        url_overlap = len(query_terms.intersection(url_terms)) / max(len(query_terms), 1)
        
        # Weight title more heavily than URL
        relevance = 0.7 * title_overlap + 0.3 * url_overlap
        
        return min(1.0, max(0.0, relevance))
        
    def _synthesize_findings(self, findings: list[ResearchFinding], original_query: str) -> dict[str, Any]:
        """Synthesize findings into summary and insights.
        
        Args:
            findings: List of research findings
            original_query: Original search query
            
        Returns:
            Synthesis dictionary with summary, confidence, conflicts, gaps, recommendations
        """
        if not findings:
            return {
                "summary": f"No relevant information found for query: {original_query}",
                "confidence_level": "unknown",
                "conflicts": [],
                "gaps": ["No sources found"],
                "recommendations": ["Try different search terms or search engines"],
            }
            
        # Group findings by source type
        by_source_type = {}
        for finding in findings:
            source_type = finding.source_classification.source_type
            if source_type not in by_source_type:
                by_source_type[source_type] = []
            by_source_type[source_type].append(finding)
            
        # Calculate overall confidence
        confidence_scores = [f.confidence_score for f in findings]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        if avg_confidence >= 0.8:
            confidence_level = "high"
        elif avg_confidence >= 0.6:
            confidence_level = "medium"
        else:
            confidence_level = "low"
            
        # Identify conflicts (simplified)
        conflicts = []
        if len(findings) > 1:
            # Check for contradictory information (basic implementation)
            high_confidence = [f for f in findings if f.confidence_score >= 0.7]
            if len(high_confidence) > 1:
                conflicts.append({
                    "type": "multiple_high_confidence_sources",
                    "description": "Multiple high-confidence sources found",
                    "sources": [f.source_url for f in high_confidence],
                })
                
        # Identify gaps
        gaps = []
        if not by_source_type.get(SourceType.OFFICIAL):
            gaps.append("No official documentation sources found")
        if not by_source_type.get(SourceType.ACADEMIC):
            gaps.append("No academic sources found")
            
        # Generate recommendations
        recommendations = []
        if confidence_level == "low":
            recommendations.append("Verify information with additional sources")
        if len(findings) < 3:
            recommendations.append("Expand search to include more sources")
        if gaps:
            recommendations.append("Look for official documentation to fill gaps")
            
        # Create summary
        summary_parts = []
        if by_source_type.get(SourceType.OFFICIAL):
            summary_parts.append(f"Found {len(by_source_type[SourceType.OFFICIAL])} official sources")
        if by_source_type.get(SourceType.ACADEMIC):
            summary_parts.append(f"Found {len(by_source_type[SourceType.ACADEMIC])} academic sources")
        if by_source_type.get(SourceType.REPUTABLE_COMMUNITY):
            summary_parts.append(f"Found {len(by_source_type[SourceType.REPUTABLE_COMMUNITY])} community sources")
            
        summary = f"Research for '{original_query}' found {len(findings)} sources. " + ". ".join(summary_parts)
        
        return {
            "summary": summary,
            "confidence_level": confidence_level,
            "conflicts": conflicts,
            "gaps": gaps,
            "recommendations": recommendations,
        }
        
    async def _cleanup_browsers(self, browser_sessions: list) -> None:
        """Clean up browser instances.
        
        Args:
            browser_sessions: List of browser sessions to cleanup
        """
        cleanup_tasks = []
        for session in browser_sessions:
            cleanup_tasks.append(self.pinchtab_service.close_instance(session.browser_id))
            
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)


# Global tool instance
_browser_search_tool: BrowserSearchTool | None = None


async def get_browser_search_tool() -> BrowserSearchTool:
    """Get or create the global browser search tool instance."""
    global _browser_search_tool
    if _browser_search_tool is None:
        _browser_search_tool = BrowserSearchTool()
    return _browser_search_tool

"""
Browser search tool using PinchTab automation. Provides async interface 
for web research with browser automation, source classification, and structured result extraction. 
"""

from __future__ import annotations
import asyncio
import re
from typing import Any

from mindflow_backend.agents.tools.specialist.research.monitoring.action_trail import get_action_trail_logger
from mindflow_backend.agents.tools.specialist.research.monitoring.pinchtab_service import get_pinchtab_service
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
from mindflow_backend.storage import db_session

_logger = get_logger(__name__)


class BrowserSearchTool:
    """
    Async browser search tool using PinchTab automation.
    """

    def __init__(self) -> None:
        """
        Initialize browser search tool.
        """
        self.pinchtab_service = None
        self.action_logger = None

    async def initialize(self, session_id: str, agent_id: str) -> None:
        """
        Initialize the tool with session context.
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
        self, query_plan: QueryPlan, max_concurrent_browsers: int = 5
    ) -> ResearchResult:
        """
        Execute a complete research session with multiple browsers.
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
            browsers_count=browsers_used,
            queries_count=len(query_plan.queries)
        )

        try:
            # Create browser tasks
            tasks = []
            for i, query in enumerate(query_plan.queries[:browsers_used]):
                task = self._execute_single_browser_search(query, i)
                tasks.append(task)

            # Execute all browser searches concurrently
            browser_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            all_findings = []
            successful_searches = 0
            
            for result in browser_results:
                if isinstance(result, Exception):
                    _logger.error(
                        "browser_search_failed",
                        session_id=self.session_id,
                        agent_id=self.agent_id,
                        error=str(result)
                    )
                    continue
                
                if result and result.success:
                    all_findings.extend(result.findings or [])
                    successful_searches += 1

            # Synthesize results
            synthesis = await self._synthesize_findings(all_findings, query_plan)
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            
            research_result = ResearchResult(
                session_id=self.session_id,
                agent_id=self.agent_id,
                original_query=query_plan.queries[0] if query_plan.queries else "",
                findings=all_findings,
                synthesis=synthesis,
                browsers_used=browsers_used,
                successful_searches=successful_searches,
                total_time=elapsed_time,
                completed_at=asyncio.get_event_loop().time()
            )

            _logger.info(
                "browser_research_completed",
                session_id=self.session_id,
                agent_id=self.agent_id,
                findings_count=len(all_findings),
                successful_searches=successful_searches,
                elapsed_time=elapsed_time
            )

            return research_result

        except Exception as e:
            _logger.error(
                "browser_research_error",
                session_id=self.session_id,
                agent_id=self.agent_id,
                error=str(e)
            )
            raise

    async def _execute_single_browser_search(self, query: str, browser_index: int) -> ResearchResult:
        """
        Execute search in a single browser instance.
        Args:
            query: Search query
            browser_index: Index of this browser instance
        Returns:
            Research result from this browser
        """
        try:
            await self.action_logger.log_action(
                session_id=self.session_id,
                agent_id=self.agent_id,
                action_type="browser_search_started",
                details={
                    "query": query,
                    "browser_index": browser_index
                }
            )

            # Execute browser search using PinchTab
            search_result = await self.pinchtab_service.search(
                query=query,
                session_id=self.session_id,
                browser_index=browser_index
            )

            # Process search results
            findings = []
            if search_result and search_result.results:
                for result in search_result.results:
                    finding = ResearchFinding(
                        title=result.title or "",
                        url=result.url or "",
                        content=result.content or "",
                        source_classification=self._classify_source(result.url),
                        confidence_score=self._calculate_confidence(result),
                        metadata={
                            "browser_index": browser_index,
                            "search_rank": result.rank if hasattr(result, 'rank') else 0,
                            "domain": self._extract_domain(result.url) if result.url else ""
                        }
                    )
                    findings.append(finding)

            await self.action_logger.log_action(
                session_id=self.session_id,
                agent_id=self.agent_id,
                action_type="browser_search_completed",
                details={
                    "query": query,
                    "browser_index": browser_index,
                    "findings_count": len(findings)
                }
            )

            return ResearchResult(
                session_id=self.session_id,
                agent_id=self.agent_id,
                original_query=query,
                findings=findings,
                synthesis="",
                browsers_used=1,
                successful_searches=1 if findings else 0,
                total_time=0,
                completed_at=asyncio.get_event_loop().time()
            )

        except Exception as e:
            await self.action_logger.log_action(
                session_id=self.session_id,
                agent_id=self.agent_id,
                action_type="browser_search_error",
                details={
                    "query": query,
                    "browser_index": browser_index,
                    "error": str(e)
                }
            )
            _logger.error(
                "single_browser_search_error",
                session_id=self.session_id,
                agent_id=self.agent_id,
                query=query,
                browser_index=browser_index,
                error=str(e)
            )
            return None

    def _classify_source(self, url: str) -> SourceClassification:
        """
        Classify the source type and credibility.
        Args:
            url: Source URL
        Returns:
            Source classification
        """
        if not url:
            return SourceClassification(
                source_type=SourceType.UNKNOWN,
                confidence=ConfidenceLevel.LOW,
                reason="No URL provided"
            )

        domain = self._extract_domain(url)
        
        # Academic sources
        academic_patterns = [
            r'\.edu$', r'\.ac\.', r'scholar\.google\.com',
            r'arxiv\.org', r'pubmed\.ncbi\.nlm\.nih\.gov',
            r'ieee\.org', r'springer\.com', r'sciencedirect\.com'
        ]
        
        # Government sources
        gov_patterns = [
            r'\.gov$', r'\.mil$', r'who\.int',
            r'un\.org', r'worldbank\.org'
        ]
        
        # News sources
        news_patterns = [
            r'cnn\.com', r'bbc\.com', r'reuters\.com',
            r'nytimes\.com', r'washingtonpost\.com', r'wsj\.com'
        ]
        
        # Social media
        social_patterns = [
            r'twitter\.com', r'facebook\.com', r'linkedin\.com',
            r'reddit\.com', r'instagram\.com'
        ]

        for pattern in academic_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return SourceClassification(
                    source_type=SourceType.ACADEMIC,
                    confidence=ConfidenceLevel.HIGH,
                    reason=f"Matches academic pattern: {pattern}"
                )

        for pattern in gov_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return SourceClassification(
                    source_type=SourceType.GOVERNMENT,
                    confidence=ConfidenceLevel.HIGH,
                    reason=f"Matches government pattern: {pattern}"
                )

        for pattern in news_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return SourceClassification(
                    source_type=SourceType.NEWS,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason=f"Matches news pattern: {pattern}"
                )

        for pattern in social_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return SourceClassification(
                    source_type=SourceType.SOCIAL_MEDIA,
                    confidence=ConfidenceLevel.LOW,
                    reason=f"Matches social media pattern: {pattern}"
                )

        # Default to general web
        return SourceClassification(
            source_type=SourceType.GENERAL_WEB,
            confidence=ConfidenceLevel.MEDIUM,
            reason="General web source"
        )

    def _calculate_confidence(self, result) -> ConfidenceLevel:
        """
        Calculate confidence score for a search result.
        Args:
            result: Search result object
        Returns:
            Confidence level
        """
        score = 0
        
        # Check content length
        if hasattr(result, 'content') and result.content:
            content_length = len(result.content)
            if content_length > 1000:
                score += 3
            elif content_length > 500:
                score += 2
            elif content_length > 100:
                score += 1

        # Check title quality
        if hasattr(result, 'title') and result.title:
            title_length = len(result.title)
            if 10 <= title_length <= 100:
                score += 2
            elif title_length > 5:
                score += 1

        # Check URL quality
        if hasattr(result, 'url') and result.url:
            url = result.url.lower()
            if not any(pattern in url for pattern in ['ads', 'spam', 'fake']):
                score += 1

        # Convert score to confidence level
        if score >= 6:
            return ConfidenceLevel.HIGH
        elif score >= 4:
            return ConfidenceLevel.MEDIUM
        elif score >= 2:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.
        Args:
            url: Full URL
        Returns:
            Domain name
        """
        if not url:
            return ""
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    async def _synthesize_findings(self, findings: list, query_plan: QueryPlan) -> str:
        """
        Synthesize findings into a coherent summary.
        Args:
            findings: List of research findings
            query_plan: Original query plan
        Returns:
            Synthesized summary
        """
        if not findings:
            return "No relevant information found for the search query."

        # Group findings by source type
        academic_findings = [f for f in findings if f.source_classification.source_type == SourceType.ACADEMIC]
        gov_findings = [f for f in findings if f.source_classification.source_type == SourceType.GOVERNMENT]
        news_findings = [f for f in findings if f.source_classification.source_type == SourceType.NEWS]
        general_findings = [f for f in findings if f.source_classification.source_type == SourceType.GENERAL_WEB]

        synthesis_parts = []
        
        if academic_findings:
            synthesis_parts.append(f"Academic sources ({len(academic_findings)} findings):")
            for finding in academic_findings[:3]:  # Top 3 academic findings
                synthesis_parts.append(f"- {finding.title}: {finding.content[:200]}...")

        if gov_findings:
            synthesis_parts.append(f"Government sources ({len(gov_findings)} findings):")
            for finding in gov_findings[:3]:  # Top 3 gov findings
                synthesis_parts.append(f"- {finding.title}: {finding.content[:200]}...")

        if news_findings:
            synthesis_parts.append(f"News sources ({len(news_findings)} findings):")
            for finding in news_findings[:3]:  # Top 3 news findings
                synthesis_parts.append(f"- {finding.title}: {finding.content[:200]}...")

        if general_findings:
            synthesis_parts.append(f"Other web sources ({len(general_findings)} findings):")
            for finding in general_findings[:3]:  # Top 3 general findings
                synthesis_parts.append(f"- {finding.title}: {finding.content[:200]}...")

        return "\n\n".join(synthesis_parts)

    async def cleanup(self) -> None:
        """
        Clean up browser resources.
        """
        if self.pinchtab_service:
            try:
                await self.pinchtab_service.cleanup_session(self.session_id)
                _logger.info(
                    "browser_cleanup_completed",
                    session_id=self.session_id,
                    agent_id=self.agent_id
                )
            except Exception as e:
                _logger.error(
                    "browser_cleanup_error",
                    session_id=self.session_id,
                    agent_id=self.agent_id,
                    error=str(e)
                )


# Convenience function for creating browser search tool
def get_browser_search_tool() -> BrowserSearchTool:
    """
    Get a configured browser search tool instance.
    Returns:
        BrowserSearchTool instance
    """
    return BrowserSearchTool()

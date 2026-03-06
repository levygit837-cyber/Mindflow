"""Research task definitions and utilities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.infrastructure.queue_manager import get_queue_manager

_logger = get_logger(__name__)


@dataclass
class ResearchTask:
    """Base class for research tasks."""
    
    task_type: str
    session_id: str
    research_domain: str
    priority: str = "medium"
    task_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Generate task ID if not provided."""
        if "task_id" not in self.metadata:
            self.metadata["task_id"] = str(uuid.uuid4())
    
    @property
    def task_id(self) -> str:
        """Get task ID."""
        return self.metadata["task_id"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for queue publishing."""
        return {
            "task_type": self.task_type,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "research_domain": self.research_domain,
            "priority": self.priority,
            "task_data": self.task_data,
            "metadata": self.metadata,
        }


class ResearchTaskDefinitions:
    """Definitions and utilities for research tasks."""
    
    # Browser Automation Tasks
    @staticmethod
    def create_web_search_task(
        session_id: str,
        search_query: str,
        search_engine: str = "google",
        max_results: int = 10,
        search_depth: str = "standard",
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a web search task."""
        return ResearchTask(
            task_type="web_search",
            session_id=session_id,
            research_domain="browser",
            priority=priority,
            task_data={
                "search_query": search_query,
                "search_engine": search_engine,
                "max_results": max_results,
                "search_depth": search_depth,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 120,
            },
        )
    
    @staticmethod
    def create_page_scraping_task(
        session_id: str,
        target_url: str,
        extraction_rules: Dict[str, Any] = None,
        wait_for_selector: Optional[str] = None,
        include_screenshots: bool = False,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a page scraping task."""
        return ResearchTask(
            task_type="page_scraping",
            session_id=session_id,
            research_domain="browser",
            priority=priority,
            task_data={
                "target_url": target_url,
                "extraction_rules": extraction_rules or {},
                "wait_for_selector": wait_for_selector,
                "include_screenshots": include_screenshots,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 90,
            },
        )
    
    @staticmethod
    def create_screenshot_capture_task(
        session_id: str,
        target_url: str,
        capture_options: Dict[str, Any] = None,
        viewport_size: Dict[str, int] = None,
        full_page: bool = False,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a screenshot capture task."""
        return ResearchTask(
            task_type="screenshot_capture",
            session_id=session_id,
            research_domain="browser",
            priority=priority,
            task_data={
                "target_url": target_url,
                "capture_options": capture_options or {},
                "viewport_size": viewport_size or {"width": 1920, "height": 1080},
                "full_page": full_page,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 60,
            },
        )
    
    @staticmethod
    def create_form_interaction_task(
        session_id: str,
        target_url: str,
        form_data: Dict[str, Any],
        submit_action: str = "click",
        wait_for_result: bool = True,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a form interaction task."""
        return ResearchTask(
            task_type="form_interaction",
            session_id=session_id,
            research_domain="browser",
            priority=priority,
            task_data={
                "target_url": target_url,
                "form_data": form_data,
                "submit_action": submit_action,
                "wait_for_result": wait_for_result,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 90,
            },
        )
    
    @staticmethod
    def create_link_extraction_task(
        session_id: str,
        target_url: str,
        link_filters: Dict[str, Any] = None,
        max_links: int = 50,
        follow_redirects: bool = False,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a link extraction task."""
        return ResearchTask(
            task_type="link_extraction",
            session_id=session_id,
            research_domain="browser",
            priority=priority,
            task_data={
                "target_url": target_url,
                "link_filters": link_filters or {},
                "max_links": max_links,
                "follow_redirects": follow_redirects,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 45,
            },
        )
    
    @staticmethod
    def create_content_validation_task(
        session_id: str,
        target_url: str,
        validation_rules: Dict[str, Any] = None,
        content_expectations: Dict[str, Any] = None,
        accessibility_check: bool = False,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a content validation task."""
        return ResearchTask(
            task_type="content_validation",
            session_id=session_id,
            research_domain="browser",
            priority=priority,
            task_data={
                "target_url": target_url,
                "validation_rules": validation_rules or {},
                "content_expectations": content_expectations or {},
                "accessibility_check": accessibility_check,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 75,
            },
        )
    
    # Content Processing Tasks
    @staticmethod
    def create_content_synthesis_task(
        session_id: str,
        content_sources: List[Dict[str, Any]],
        synthesis_type: str = "comprehensive",
        target_audience: str = "technical",
        synthesis_length: str = "medium",
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a content synthesis task."""
        return ResearchTask(
            task_type="content_synthesis",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "content_sources": content_sources,
                "synthesis_type": synthesis_type,
                "target_audience": target_audience,
                "synthesis_length": synthesis_length,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 120,
            },
        )
    
    @staticmethod
    def create_text_processing_task(
        session_id: str,
        text_content: str,
        processing_operations: List[str] = None,
        language: str = "auto",
        output_format: str = "structured",
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a text processing task."""
        return ResearchTask(
            task_type="text_processing",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "text_content": text_content,
                "processing_operations": processing_operations or ["all"],
                "language": language,
                "output_format": output_format,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 60,
            },
        )
    
    @staticmethod
    def create_content_categorization_task(
        session_id: str,
        content_items: List[Dict[str, Any]],
        categorization_scheme: str = "hierarchical",
        confidence_threshold: float = 0.7,
        auto_tagging: bool = True,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a content categorization task."""
        return ResearchTask(
            task_type="content_categorization",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "content_items": content_items,
                "categorization_scheme": categorization_scheme,
                "confidence_threshold": confidence_threshold,
                "auto_tagging": auto_tagging,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 90,
            },
        )
    
    @staticmethod
    def create_summarization_task(
        session_id: str,
        source_content: str,
        summary_type: str = "extractive",
        summary_length: str = "medium",
        focus_areas: List[str] = None,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a summarization task."""
        return ResearchTask(
            task_type="summarization",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "source_content": source_content,
                "summary_type": summary_type,
                "summary_length": summary_length,
                "focus_areas": focus_areas or [],
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 75,
            },
        )
    
    @staticmethod
    def create_content_enrichment_task(
        session_id: str,
        content_items: List[Dict[str, Any]],
        enrichment_types: List[str] = None,
        metadata_schema: str = "standard",
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a content enrichment task."""
        return ResearchTask(
            task_type="content_enrichment",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "content_items": content_items,
                "enrichment_types": enrichment_types or ["all"],
                "metadata_schema": metadata_schema,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 105,
            },
        )
    
    @staticmethod
    def create_quality_assessment_task(
        session_id: str,
        content_items: List[Dict[str, Any]],
        assessment_criteria: List[str] = None,
        quality_threshold: float = 0.7,
        relevance_context: Dict[str, Any] = None,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a quality assessment task."""
        return ResearchTask(
            task_type="quality_assessment",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "content_items": content_items,
                "assessment_criteria": assessment_criteria or ["all"],
                "quality_threshold": quality_threshold,
                "relevance_context": relevance_context or {},
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 60,
            },
        )
    
    # Advanced Research Tasks
    @staticmethod
    def create_fact_checking_task(
        session_id: str,
        claims: List[str],
        verification_sources: List[str] = None,
        confidence_threshold: float = 0.7,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a fact-checking task."""
        return ResearchTask(
            task_type="fact_checking",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "claims": claims,
                "verification_sources": verification_sources or ["multiple"],
                "confidence_threshold": confidence_threshold,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 150,
            },
        )
    
    @staticmethod
    def create_literature_review_task(
        session_id: str,
        topic: str,
        databases: List[str] = None,
        year_range: str = "2019-2024",
        max_papers: int = 20,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a literature review task."""
        return ResearchTask(
            task_type="literature_review",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "topic": topic,
                "databases": databases or ["arxiv", "pubmed"],
                "year_range": year_range,
                "max_papers": max_papers,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 300,
            },
        )
    
    @staticmethod
    def create_trend_analysis_task(
        session_id: str,
        analysis_target: str,
        time_period: str = "7d",
        confidence_threshold: float = 0.8,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a trend analysis task."""
        return ResearchTask(
            task_type="trend_analysis",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "analysis_target": analysis_target,
                "time_period": time_period,
                "confidence_threshold": confidence_threshold,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 180,
            },
        )
    
    @staticmethod
    def create_source_validation_task(
        session_id: str,
        sources: List[str],
        validation_criteria: List[str] = None,
        strict_mode: bool = False,
        priority: str = "medium",
    ) -> ResearchTask:
        """Create a source validation task."""
        return ResearchTask(
            task_type="source_validation",
            session_id=session_id,
            research_domain="content",
            priority=priority,
            task_data={
                "sources": sources,
                "validation_criteria": validation_criteria or ["reliability", "currency"],
                "strict_mode": strict_mode,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 90,
            },
        )


class ResearchTaskPublisher:
    """Utility class for publishing research tasks to queues."""
    
    def __init__(self) -> None:
        """Initialize the task publisher."""
        self.queue_manager = get_queue_manager()
    
    async def publish_task(self, task: ResearchTask) -> bool:
        """Publish a research task to the appropriate queue.
        
        Args:
            task: Research task to publish
            
        Returns:
            True if task was published successfully
        """
        # Determine queue name based on research domain and priority
        queue_name = self._get_queue_name(task.research_domain, task.priority)
        
        # Convert task to dictionary
        task_dict = task.to_dict()
        
        # Set message priority based on task priority
        priority = self._get_message_priority(task.priority)
        
        # Publish to queue
        success = await self.queue_manager.publish_message(
            queue_name=queue_name,
            message_data=task_dict,
            priority=priority,
        )
        
        if success:
            _logger.info(f"Published {task.task_type} task {task.task_id} to {queue_name}")
        else:
            _logger.error(f"Failed to publish task {task.task_id} to {queue_name}")
        
        return success
    
    def _get_queue_name(self, research_domain: str, priority: str) -> str:
        """Get queue name for research domain and priority."""
        # Map research domains and priorities to queue names
        queue_mappings = {
            ("browser", "critical"): "browser_high",
            ("browser", "high"): "browser_high",
            ("browser", "medium"): "browser_high",
            ("browser", "low"): "browser_high",
            
            ("content", "critical"): "content_medium",
            ("content", "high"): "content_medium",
            ("content", "medium"): "content_medium",
            ("content", "low"): "content_medium",
        }
        
        return queue_mappings.get((research_domain, priority), f"{research_domain}_medium")
    
    def _get_message_priority(self, task_priority: str) -> int:
        """Convert task priority to message priority."""
        priority_mapping = {
            "critical": 9,
            "high": 7,
            "medium": 5,
            "low": 3,
        }
        
        return priority_mapping.get(task_priority, 5)
    
    async def publish_multiple_tasks(self, tasks: List[ResearchTask]) -> Dict[str, bool]:
        """Publish multiple tasks to queues.
        
        Args:
            tasks: List of tasks to publish
            
        Returns:
            Dictionary mapping task IDs to success status
        """
        results = {}
        
        for task in tasks:
            results[task.task_id] = await self.publish_task(task)
        
        return results
    
    async def publish_research_pipeline(
        self,
        session_id: str,
        research_query: str,
        pipeline_config: Dict[str, Any] = None,
    ) -> Dict[str, bool]:
        """Publish a complete research pipeline.
        
        Args:
            session_id: Session ID
            research_query: Main research query
            pipeline_config: Pipeline configuration
            
        Returns:
            Dictionary mapping task IDs to success status
        """
        config = pipeline_config or {}
        
        # Create pipeline tasks
        tasks = []
        
        # 1. Web search task
        search_task = ResearchTaskDefinitions.create_web_search_task(
            session_id=session_id,
            search_query=research_query,
            max_results=config.get("max_results", 10),
            search_depth=config.get("search_depth", "standard"),
            priority="high",
        )
        tasks.append(search_task)
        
        # 2. Content synthesis task (will be processed after search)
        synthesis_task = ResearchTaskDefinitions.create_content_synthesis_task(
            session_id=session_id,
            content_sources=[],  # Will be populated by search results
            synthesis_type=config.get("synthesis_type", "comprehensive"),
            target_audience=config.get("target_audience", "technical"),
            priority="medium",
        )
        tasks.append(synthesis_task)
        
        # 3. Quality assessment task
        assessment_task = ResearchTaskDefinitions.create_quality_assessment_task(
            session_id=session_id,
            content_items=[],  # Will be populated by synthesis results
            assessment_criteria=config.get("assessment_criteria", ["all"]),
            quality_threshold=config.get("quality_threshold", 0.7),
            priority="medium",
        )
        tasks.append(assessment_task)
        
        # Publish all tasks
        return await self.publish_multiple_tasks(tasks)


# Global task publisher instance
_task_publisher: Optional[ResearchTaskPublisher] = None


def get_research_task_publisher() -> ResearchTaskPublisher:
    """Get the global research task publisher instance."""
    global _task_publisher
    if _task_publisher is None:
        _task_publisher = ResearchTaskPublisher()
    return _task_publisher

"""Stub nodes for research graphs (Fase 2A)."""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory

_logger = get_logger(__name__)


class ResearchInitializeNode(BaseNode):
    """Initialize research context: sources, search scope."""

    def __init__(self, node_id: str = "initialize") -> None:
        super().__init__(
            node_id=node_id,
            name="Research Initialize",
            description="Configure sources and search scope.",
            category=NodeCategory.INITIALIZATION,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("research_initialize_node", node_id=self.node_id)
        return {
            "findings": [],
            "sources": [],
            "current_phase": "initialized",
        }


class SearchNode(BaseNode):
    """Search across multiple sources using LightPanda browser."""

    def __init__(self, node_id: str = "search") -> None:
        super().__init__(
            node_id=node_id,
            name="Search",
            description="Search across web using LightPanda browser automation.",
            category=NodeCategory.DATA_COLLECTION,
        )
        self.config.required_inputs = {"query"}
        self.config.outputs = {"search_results", "iteration", "current_phase"}

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute web search using BrowserSearchCallable."""
        from mindflow_backend.agents.tools.callable import BrowserSearchCallable
        from mindflow_backend.schemas.tools.context import ToolContext

        query = state.get("query", "")
        search_engine = state.get("search_engine", "google")
        num_results = state.get("num_results", 10)
        language = state.get("language", "en")
        iteration = state.get("iteration", 0) + 1

        _logger.info(
            "search_node_execute",
            node_id=self.node_id,
            query=query,
            iteration=iteration,
            search_engine=search_engine,
        )

        try:
            # Create tool context
            context = ToolContext(
                root_dir=state.get("root_dir"),
                sandbox_mode=state.get("sandbox_mode"),
            )

            # Execute search through BrowserSearchCallable
            input_data = BrowserSearchCallable.InputSchema(
                query=query,
                search_engine=search_engine,
                num_results=num_results,
                language=language,
            )

            result = await BrowserSearchCallable.call_fn(input_data, context)

            if result.success:
                _logger.info(
                    "search_node_success",
                    node_id=self.node_id,
                    results_count=len(result.data.get("results", [])),
                )
                return {
                    "search_results": result.data.get("results", []),
                    "iteration": iteration,
                    "current_phase": "searching",
                }
            else:
                _logger.error(
                    "search_node_failed",
                    node_id=self.node_id,
                    error=result.error,
                )
                return {
                    "search_results": [],
                    "iteration": iteration,
                    "current_phase": "searching",
                    "error": result.error,
                }

        except Exception as e:
            _logger.error(
                "search_node_exception",
                node_id=self.node_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "search_results": [],
                "iteration": iteration,
                "current_phase": "searching",
                "error": str(e),
            }


class CollectNode(BaseNode):
    """Collect and scrape search results using DeepPageScraperCallable."""

    def __init__(self, node_id: str = "collect") -> None:
        super().__init__(
            node_id=node_id,
            name="Collect",
            description="Collect and scrape search results with scroll and link mapping.",
            category=NodeCategory.DATA_COLLECTION,
        )
        self.config.required_inputs = {"search_results"}
        self.config.outputs = {"findings", "scraping_metrics", "current_phase"}

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute deep page scraping using DeepPageScraperCallable."""
        from mindflow_backend.agents.tools.callable import DeepPageScraperCallable
        from mindflow_backend.schemas.tools.context import ToolContext
        import asyncio
        from datetime import datetime

        search_results = state.get("search_results", [])
        scraping_config = state.get("scraping_config", {})

        scroll_depth = scraping_config.get("scroll_depth", 10)
        extract_links = scraping_config.get("extract_links", True)
        max_content_length = scraping_config.get("max_content_length", 50000)

        _logger.info(
            "collect_node_execute",
            node_id=self.node_id,
            urls_count=len(search_results),
            scroll_depth=scroll_depth,
            extract_links=extract_links,
        )

        findings = []
        successful_scrapes = 0
        failed_scrapes = 0
        total_content_chars = 0
        total_links_extracted = 0
        total_scroll_iterations = 0

        try:
            # Create tool context
            context = ToolContext(
                root_dir=state.get("root_dir"),
                sandbox_mode=state.get("sandbox_mode"),
            )

            # Scrape each URL in parallel (limit concurrency)
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent scrapes

            async def scrape_url(result: dict) -> dict | None:
                async with semaphore:
                    try:
                        url = result.get("url", "")
                        if not url:
                            return None

                        input_data = DeepPageScraperCallable.InputSchema(
                            url=url,
                            scroll_depth=scroll_depth,
                            extract_links=extract_links,
                            max_content_length=max_content_length,
                        )

                        scrape_result = await DeepPageScraperCallable.call_fn(
                            input_data, context
                        )

                        if scrape_result.success:
                            data = scrape_result.data
                            return {
                                "url": url,
                                "title": data.get("title", result.get("title", "")),
                                "content": data.get("content", ""),
                                "snippet": result.get("snippet", ""),
                                "word_count": data.get("word_count", 0),
                                "reading_time_minutes": data.get("reading_time_minutes", 0),
                                "extracted_at": datetime.utcnow().isoformat(),
                                "scroll_iterations": data.get("scroll_iterations", 0),
                                "content_depth": data.get("content_depth", "medium"),
                                "links": data.get("links", {}),
                                "metadata": data.get("metadata", {}),
                            }
                        else:
                            _logger.warning(
                                "collect_scrape_failed",
                                url=url,
                                error=scrape_result.error,
                            )
                            return None

                    except Exception as e:
                        _logger.error(
                            "collect_scrape_exception",
                            url=result.get("url", ""),
                            error=str(e),
                        )
                        return None

            # Execute scrapes in parallel
            tasks = [scrape_url(result) for result in search_results]
            scrape_results = await asyncio.gather(*tasks)

            # Process results
            for result in scrape_results:
                if result:
                    findings.append(result)
                    successful_scrapes += 1
                    total_content_chars += len(result.get("content", ""))
                    total_links_extracted += result.get("links", {}).get("total", 0)
                    total_scroll_iterations += result.get("scroll_iterations", 0)
                else:
                    failed_scrapes += 1

            _logger.info(
                "collect_node_success",
                node_id=self.node_id,
                successful_scrapes=successful_scrapes,
                failed_scrapes=failed_scrapes,
                total_content_chars=total_content_chars,
            )

            return {
                "findings": findings,
                "scraping_metrics": {
                    "total_urls_processed": len(search_results),
                    "successful_scrapes": successful_scrapes,
                    "failed_scrapes": failed_scrapes,
                    "total_content_chars": total_content_chars,
                    "total_links_extracted": total_links_extracted,
                    "average_scroll_iterations": (
                        total_scroll_iterations / successful_scrapes
                        if successful_scrapes > 0
                        else 0
                    ),
                },
                "current_phase": "collected",
            }

        except Exception as e:
            _logger.error(
                "collect_node_exception",
                node_id=self.node_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "findings": findings,
                "scraping_metrics": {
                    "total_urls_processed": len(search_results),
                    "successful_scrapes": successful_scrapes,
                    "failed_scrapes": failed_scrapes + len(search_results),
                    "total_content_chars": total_content_chars,
                },
                "current_phase": "collected",
                "error": str(e),
            }


class DeduplicateNode(BaseNode):
    """Remove redundant sources using real deduplication algorithm."""

    def __init__(self, node_id: str = "deduplicate") -> None:
        super().__init__(
            node_id=node_id,
            name="Deduplicate",
            description="Remove redundant and duplicate sources using URL hash and content similarity.",
            category=NodeCategory.SYNTHESIS,
        )
        self.config.required_inputs = {"findings"}
        self.config.outputs = {"findings", "duplicates_removed", "unique_count", "current_phase"}

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute deduplication using URL hash and content similarity."""
        import hashlib
        from difflib import SequenceMatcher

        findings = state.get("findings", [])
        
        _logger.info(
            "deduplicate_node_execute",
            node_id=self.node_id,
            findings_count=len(findings),
        )

        try:
            # Step 1: URL deduplication (exact matches)
            url_hashes = {}
            duplicates_by_url = 0
            
            for finding in findings:
                url = finding.get("url", "")
                if url:
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    if url_hash not in url_hashes:
                        url_hashes[url_hash] = finding
                    else:
                        duplicates_by_url += 1
            
            findings_after_url = list(url_hashes.values())
            
            # Step 2: Content similarity deduplication
            unique_findings = []
            duplicates_by_content = 0
            similarity_threshold = 0.85  # 85% similarity threshold
            
            def compute_content_similarity(content1: str, content2: str) -> float:
                """Compute similarity between two content strings using SequenceMatcher."""
                if not content1 or not content2:
                    return 0.0
                return SequenceMatcher(None, content1, content2).ratio()
            
            for finding in findings_after_url:
                content = finding.get("content", "")
                is_duplicate = False
                
                for existing in unique_findings:
                    existing_content = existing.get("content", "")
                    similarity = compute_content_similarity(content, existing_content)
                    
                    if similarity > similarity_threshold:
                        duplicates_by_content += 1
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_findings.append(finding)
            
            total_duplicates = duplicates_by_url + duplicates_by_content
            
            _logger.info(
                "deduplicate_node_success",
                node_id=self.node_id,
                original_count=len(findings),
                unique_count=len(unique_findings),
                duplicates_removed=total_duplicates,
                duplicates_by_url=duplicates_by_url,
                duplicates_by_content=duplicates_by_content,
            )
            
            return {
                "findings": unique_findings,
                "duplicates_removed": total_duplicates,
                "unique_count": len(unique_findings),
                "deduplication_details": {
                    "original_count": len(findings),
                    "duplicates_by_url": duplicates_by_url,
                    "duplicates_by_content": duplicates_by_content,
                    "similarity_threshold": similarity_threshold,
                },
                "current_phase": "deduplicated",
            }
            
        except Exception as e:
            _logger.error(
                "deduplicate_node_exception",
                node_id=self.node_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "findings": findings,
                "duplicates_removed": 0,
                "unique_count": len(findings),
                "current_phase": "deduplicated",
                "error": str(e),
            }


class ResearchSynthesizeNode(BaseNode):
    """Merge findings into coherent research."""

    def __init__(self, node_id: str = "synthesize") -> None:
        super().__init__(
            node_id=node_id,
            name="Research Synthesize",
            description="Merge findings into coherent research synthesis.",
            category=NodeCategory.SYNTHESIS,
        )
        self.config.required_inputs = {"findings"}
        self.config.outputs = {"synthesis", "current_phase"}

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Synthesize findings into coherent research."""
        findings = state.get("findings", [])
        
        _logger.info(
            "synthesize_node_execute",
            node_id=self.node_id,
            findings_count=len(findings),
        )

        try:
            # Extract key themes from titles and content
            titles = [f.get("title", "") for f in findings]
            contents = [f.get("content", "") for f in findings]
            
            # Simple synthesis (can be enhanced with LLM later)
            key_themes = list(set([title.split()[0] for title in titles if title]))
            main_findings = [f"{f.get('title', '')}: {f.get('content', '')[:200]}..." for f in findings[:5]]
            
            # Calculate confidence score based on findings count
            confidence_score = min(0.5 + (len(findings) * 0.05), 0.95)
            
            synthesis = {
                "key_themes": key_themes[:10],  # Limit to top 10 themes
                "main_findings": main_findings,
                "confidence_score": round(confidence_score, 2),
                "sources_count": len(findings),
            }
            
            _logger.info(
                "synthesize_node_success",
                node_id=self.node_id,
                themes_count=len(synthesis["key_themes"]),
                confidence_score=synthesis["confidence_score"],
            )
            
            return {
                "synthesis": synthesis,
                "current_phase": "synthesized",
            }
            
        except Exception as e:
            _logger.error(
                "synthesize_node_exception",
                node_id=self.node_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "synthesis": {
                    "key_themes": [],
                    "main_findings": [],
                    "confidence_score": 0.0,
                    "sources_count": len(findings),
                },
                "current_phase": "synthesized",
                "error": str(e),
            }


class CiteNode(BaseNode):
    """Format with references and citations."""

    def __init__(self, node_id: str = "cite") -> None:
        super().__init__(
            node_id=node_id,
            name="Cite",
            description="Format findings with proper citations and references.",
            category=NodeCategory.SYNTHESIS,
        )
        self.config.required_inputs = {"findings", "synthesis"}
        self.config.outputs = {"citations", "formatted_text", "current_phase"}

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Format findings with citations."""
        findings = state.get("findings", [])
        synthesis = state.get("synthesis", {})
        
        _logger.info(
            "cite_node_execute",
            node_id=self.node_id,
            findings_count=len(findings),
        )

        try:
            # Create citations list
            citations = []
            for i, finding in enumerate(findings):
                citation = {
                    "text": f"[{i+1}] {finding.get('title', 'Untitled')}",
                    "source": {
                        "url": finding.get("url", ""),
                        "title": finding.get("title", ""),
                        "extracted_at": finding.get("extracted_at", ""),
                    },
                }
                citations.append(citation)
            
            # Create formatted text
            formatted_lines = [
                "# Research Report",
                "",
                f"Sources: {len(findings)}",
                f"Key Themes: {', '.join(synthesis.get('key_themes', []))}",
                "",
                "## Citations",
            ]
            
            for citation in citations:
                formatted_lines.append(f"- {citation['text']}")
                formatted_lines.append(f"  Source: {citation['source']['url']}")
            
            formatted_text = "\n".join(formatted_lines)
            
            _logger.info(
                "cite_node_success",
                node_id=self.node_id,
                citations_count=len(citations),
            )
            
            return {
                "citations": citations,
                "formatted_text": formatted_text,
                "current_phase": "cited",
            }
            
        except Exception as e:
            _logger.error(
                "cite_node_exception",
                node_id=self.node_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "citations": [],
                "formatted_text": "",
                "current_phase": "cited",
                "error": str(e),
            }


class ResearchReportNode(BaseNode):
    """Generate research report."""

    def __init__(self, node_id: str = "report") -> None:
        super().__init__(
            node_id=node_id,
            name="Research Report",
            description="Generate final research report with metrics.",
            category=NodeCategory.REPORTING,
        )
        self.config.required_inputs = {"findings", "synthesis", "citations"}
        self.config.outputs = {"result", "metrics", "current_phase"}

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate final research report."""
        import time
        from datetime import datetime

        findings = state.get("findings", [])
        synthesis = state.get("synthesis", {})
        citations = state.get("citations", [])
        iteration = state.get("iteration", 0)
        scraping_metrics = state.get("scraping_metrics", {})
        deduplication_details = state.get("deduplication_details", {})

        _logger.info(
            "report_node_execute",
            node_id=self.node_id,
            findings_count=len(findings),
        )

        try:
            # Calculate duration if start time was stored
            duration_seconds = 0
            if "start_time" in state:
                duration_seconds = time.time() - state["start_time"]

            # Build result
            result = {
                "iterations": iteration,
                "findings_count": len(findings),
                "sources_count": len(set([f.get("url", "") for f in findings])),
                "synthesis": synthesis,
                "citations_count": len(citations),
                "deduplication_summary": {
                    "original_count": deduplication_details.get("original_count", 0),
                    "duplicates_removed": deduplication_details.get("duplicates_by_url", 0) + deduplication_details.get("duplicates_by_content", 0),
                    "unique_count": deduplication_details.get("unique_count", len(findings)),
                },
                "generated_at": datetime.utcnow().isoformat(),
            }

            # Build metrics
            metrics = {
                "duration_seconds": round(duration_seconds, 2),
                "nodes_executed": 7,  # Fixed for ResearchGraph
                "scraping_metrics": scraping_metrics,
                "deduplication_metrics": deduplication_details,
                "average_word_count": (
                    sum([f.get("word_count", 0) for f in findings]) / len(findings)
                    if findings
                    else 0
                ),
                "total_content_chars": scraping_metrics.get("total_content_chars", 0),
            }

            _logger.info(
                "report_node_success",
                node_id=self.node_id,
                duration_seconds=duration_seconds,
                findings_count=len(findings),
            )

            return {
                "result": result,
                "metrics": metrics,
                "current_phase": "completed",
            }

        except Exception as e:
            _logger.error(
                "report_node_exception",
                node_id=self.node_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "result": {
                    "iterations": iteration,
                    "findings_count": len(findings),
                    "error": str(e),
                },
                "metrics": {},
                "current_phase": "completed",
                "error": str(e),
            }
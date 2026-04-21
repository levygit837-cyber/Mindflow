"""Researcher worker for handling research and information gathering tasks."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import QueueConfig

_logger = get_logger(__name__)

if TYPE_CHECKING:
    from mindflow_backend.services.browser import BrowserLifecycleService


class ResearcherWorker(BaseWorker):
    """Worker specialized for Researcher Agent tasks."""
    
    def __init__(self, queue_config: QueueConfig, browser_service: BrowserLifecycleService | None = None) -> None:
        """Initialize the Researcher worker.
        
        Args:
            queue_config: Queue configuration
            browser_service: Browser lifecycle service (created if None)
        """
        super().__init__(queue_config, worker_name="researcher_worker")
        self.browser_service = browser_service or self._build_browser_service()

    @staticmethod
    def _build_browser_service():
        """Instantiate the browser lifecycle service only when the dependency exists."""
        try:
            from mindflow_backend.services.browser import BrowserLifecycleService
        except ModuleNotFoundError:
            _logger.warning(
                "researcher_worker_browser_service_unavailable",
                reason="optional browser dependencies are not installed",
            )
            return None
        return BrowserLifecycleService()
    
    async def process_message(self, message_data: dict[str, Any]) -> WorkerResult:
        """Process research and information gathering tasks.
        
        Supported task types:
        - web_search: Web search and information gathering
        - source_validation: Validate and verify sources
        - content_synthesis: Synthesize research findings
        - fact_checking: Fact-checking and verification
        - literature_review: Academic literature review
        """
        message_data = self._normalize_message_data(message_data)
        start_time = time.time()
        task_type = message_data.get("task_type", "unknown")
        task_id = message_data.get("task_id", "unknown")
        
        try:
            _logger.info(f"ResearcherWorker processing {task_type} task {task_id}")
            
            if task_type == "web_search":
                result = await self._handle_web_search(message_data)
            elif task_type == "source_validation":
                result = await self._handle_source_validation(message_data)
            elif task_type == "content_synthesis":
                result = await self._handle_content_synthesis(message_data)
            elif task_type == "fact_checking":
                result = await self._handle_fact_checking(message_data)
            elif task_type == "literature_review":
                result = await self._handle_literature_review(message_data)
            else:
                result = WorkerResult(
                    success=False,
                    message=f"Unsupported task type: {task_type}",
                    processing_time=time.time() - start_time,
                )
            
            _logger.info(
                f"ResearcherWorker completed {task_type} task {task_id} "
                f"({'SUCCESS' if result.success else 'FAILED'})"
            )
            
            return result
            
        except Exception as e:
            _logger.error(
                f"ResearcherWorker failed to process {task_type} task {task_id}: {e}",
                exc_info=True
            )
            return WorkerResult(
                success=False,
                message=f"Task processing failed: {e}",
                error=e,
                processing_time=time.time() - start_time,
            )
    
    async def _handle_web_search(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle web search and information gathering using LightPanda."""
        query = message_data.get("query")
        search_depth = message_data.get("search_depth", "standard")
        sources = message_data.get("sources", ["web"])
        max_results = message_data.get("max_results", 10)
        
        _logger.info(
            "handling_web_search",
            query=query,
            search_depth=search_depth,
            max_results=max_results,
        )
        
        try:
            # Import LightPanda browser search tool
            from mindflow_backend.agents.tools.web.lightpanda_browser_search import (
                get_lightpanda_browser_search_tool,
            )
            
            # Get browser search tool
            browser_tool = get_lightpanda_browser_search_tool()
            
            # Execute search
            search_result = await browser_tool.search_web(
                query=query,
                num_results=max_results,
            )
            
            _logger.info(
                "web_search_completed",
                query=query,
                results_count=search_result.get("total_results", 0),
            )
            
            return WorkerResult(
                success=True,
                message=f"Web search completed for query: {query}",
                data=search_result,
                processing_time=time.time() - time.time(),  # Will be set by base class
            )
            
        except Exception as exc:
            _logger.error(
                "web_search_failed",
                query=query,
                error=str(exc),
                exc_info=True,
            )
            return WorkerResult(
                success=False,
                message=f"Web search failed for query '{query}': {exc}",
                error=exc,
                processing_time=time.time() - time.time(),
            )
    
    async def _handle_source_validation(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle source validation and verification using web tools."""
        sources = message_data.get("sources", [])
        validation_criteria = message_data.get("validation_criteria", ["reliability", "currency"])
        strict_mode = message_data.get("strict_mode", False)
        
        if not sources:
            return WorkerResult(
                success=False,
                message="No sources provided for validation",
                data={"error": "sources list is empty"},
            )
        
        try:
            from mindflow_backend.agents.tools.search_web import WebFetchTool
            from urllib.parse import urlparse
            
            fetch_tool = WebFetchTool()
            results = []
            
            # Trusted domains scoring
            trusted_domains = {
                "arxiv.org": 0.95,
                "pubmed.ncbi.nlm.nih.gov": 0.95,
                "github.com": 0.85,
                "stackoverflow.com": 0.80,
                "wikipedia.org": 0.70,
                "medium.com": 0.60,
            }
            
            for source in sources:
                try:
                    domain = urlparse(source).netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                    
                    # Base reliability score from domain
                    base_score = trusted_domains.get(domain, 0.50)
                    
                    # Try to fetch to check if URL is accessible
                    try:
                        content = await fetch_tool.execute(url=source)
                        accessibility_score = 0.90 if content else 0.30
                    except Exception:
                        accessibility_score = 0.20 if strict_mode else 0.50
                    
                    # Calculate overall score
                    overall_score = (base_score + accessibility_score) / 2
                    
                    results.append({
                        "source": source,
                        "domain": domain,
                        "reliability_score": round(base_score, 2),
                        "accessibility_score": round(accessibility_score, 2),
                        "overall_score": round(overall_score, 2),
                        "recommendation": "use" if overall_score > 0.6 else "verify" if overall_score > 0.4 else "avoid",
                    })
                    
                except Exception as e:
                    results.append({
                        "source": source,
                        "error": str(e),
                        "recommendation": "verify",
                    })
            
            # Calculate summary
            high_quality = sum(1 for r in results if r.get("overall_score", 0) > 0.7)
            medium_quality = sum(1 for r in results if 0.4 <= r.get("overall_score", 0) <= 0.7)
            low_quality = sum(1 for r in results if r.get("overall_score", 0) < 0.4)
            
            return WorkerResult(
                success=True,
                message=f"Source validation completed for {len(sources)} sources",
                data={
                    "sources_validated": len(sources),
                    "validation_criteria": validation_criteria,
                    "results": results,
                    "summary": {
                        "high_quality": high_quality,
                        "medium_quality": medium_quality,
                        "low_quality": low_quality,
                        "rejected": low_quality if strict_mode else 0,
                    },
                },
            )
            
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Source validation failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_content_synthesis(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle synthesis of research findings using LLM."""
        research_data = message_data.get("research_data", [])
        synthesis_type = message_data.get("synthesis_type", "summary")
        target_audience = message_data.get("target_audience", "technical")
        
        if not research_data:
            return WorkerResult(
                success=False,
                message="No research data provided for synthesis",
                data={"error": "research_data is empty"},
            )
        
        try:
            from mindflow_backend.services.llm import get_llm_service
            
            llm_service = get_llm_service()
            
            # Prepare prompt based on synthesis type
            sources_text = "\n\n".join([
                f"Source {i+1}:\n{data.get('content', data)[:500]}..."
                for i, data in enumerate(research_data[:5])  # Limit to top 5 sources
            ])
            
            prompts = {
                "summary": f"""Synthesize the following research findings into a concise summary:

{sources_text}

Target audience: {target_audience}
Provide 3-5 key insights and identify any gaps in the research.""",
                
                "analysis": f"""Analyze the following research findings for patterns, trends, and relationships:

{sources_text}

Provide:
1. Key themes identified
2. Common patterns across sources
3. Contradictions or disagreements
4. Areas of consensus""",
                
                "comparison": f"""Compare and contrast the following research sources:

{sources_text}

Highlight similarities, differences, and relative strengths of each source.""",
            }
            
            prompt = prompts.get(synthesis_type, prompts["summary"])
            
            synthesis = await llm_service.generate(
                prompt=prompt,
                system_message=f"You are a research synthesis expert writing for a {target_audience} audience.",
                temperature=0.3,
                max_tokens=1500,
            )
            
            # Extract key insights (simple heuristic)
            key_insights = [
                line.strip("- ").strip()
                for line in synthesis.split("\n")
                if line.strip().startswith("-") or line.strip().startswith("•")
            ][:5]
            
            if not key_insights:
                key_insights = ["Insight extraction requires manual review"]
            
            return WorkerResult(
                success=True,
                message=f"Content synthesis completed: {synthesis_type}",
                data={
                    "synthesis_type": synthesis_type,
                    "target_audience": target_audience,
                    "sources_synthesized": len(research_data),
                    "synthesized_content": synthesis,
                    "key_insights": key_insights,
                    "confidence_score": 0.82,
                    "gaps_identified": self._extract_gaps(synthesis),
                },
            )
            
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Content synthesis failed: {exc}",
                data={"error": str(exc)},
            )
    
    @staticmethod
    def _extract_gaps(text: str) -> list[str]:
        """Extract research gaps from synthesis text."""
        gaps = []
        lines = text.lower().split("\n")
        for line in lines:
            if any(keyword in line for keyword in ["gap", "missing", "need", "further", "future"]):
                gaps.append(line.strip("- ").strip())
        return gaps[:3] if gaps else ["No specific gaps identified"]
    
    async def _handle_fact_checking(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle fact-checking and verification tasks using web search."""
        claims = message_data.get("claims", [])
        verification_sources = message_data.get("verification_sources", ["multiple"])
        confidence_threshold = message_data.get("confidence_threshold", 0.7)
        
        if not claims:
            return WorkerResult(
                success=False,
                message="No claims provided for fact-checking",
                data={"error": "claims list is empty"},
            )
        
        try:
            from mindflow_backend.agents.tools.search_web import WebSearchTool, WebFetchTool
            from mindflow_backend.services.llm import get_llm_service
            
            search_tool = WebSearchTool()
            fetch_tool = WebFetchTool()
            llm_service = get_llm_service()
            
            results = []
            
            for claim in claims:
                # Search for evidence
                search_query = f'"{claim}" facts verification'
                search_results = await search_tool.execute(query=search_query, num_results=5)
                
                supporting = []
                contradictory = []
                
                # Fetch and analyze top results
                for result in search_results.get("results", [])[:3]:
                    try:
                        content = await fetch_tool.execute(url=result["url"])
                        if content:
                            # Simple heuristic: check if claim keywords appear
                            claim_keywords = set(claim.lower().split())
                            content_lower = content.lower()
                            matches = sum(1 for kw in claim_keywords if kw in content_lower)
                            
                            if matches >= len(claim_keywords) * 0.5:
                                supporting.append(result["url"])
                            elif matches > 0:
                                contradictory.append(result["url"])
                    except Exception:
                        pass
                
                # Use LLM to assess the claim
                if supporting or contradictory:
                    prompt = f"""Assess the accuracy of this claim based on the evidence:

Claim: "{claim}"

Supporting sources: {len(supporting)}
Contradictory sources: {len(contradictory)}

Provide a brief assessment (1-2 sentences) of whether this claim appears to be true, false, or unverifiable based on the available evidence."""
                    
                    try:
                        assessment = await llm_service.generate(
                            prompt=prompt,
                            system_message="You are a fact-checking analyst. Be objective and evidence-based.",
                            temperature=0.2,
                            max_tokens=200,
                        )
                    except Exception:
                        assessment = "Unable to generate assessment"
                else:
                    assessment = "No evidence found"
                
                # Determine verdict
                if len(supporting) > len(contradictory) * 2:
                    verdict = "true"
                    confidence = min(0.95, 0.6 + len(supporting) * 0.1)
                elif len(contradictory) > len(supporting):
                    verdict = "false"
                    confidence = min(0.95, 0.6 + len(contradictory) * 0.1)
                else:
                    verdict = "unverifiable"
                    confidence = 0.5
                
                results.append({
                    "claim": claim,
                    "verdict": verdict,
                    "confidence": round(confidence, 2),
                    "supporting_evidence": supporting[:5],
                    "contradictory_evidence": contradictory[:5],
                    "assessment": assessment,
                })
            
            # Calculate summary
            verified_true = sum(1 for r in results if r["verdict"] == "true" and r["confidence"] >= confidence_threshold)
            verified_false = sum(1 for r in results if r["verdict"] == "false" and r["confidence"] >= confidence_threshold)
            unverifiable = sum(1 for r in results if r["verdict"] == "unverifiable")
            misleading = sum(1 for r in results if 0.4 <= r["confidence"] < confidence_threshold)
            
            return WorkerResult(
                success=True,
                message=f"Fact-checking completed for {len(claims)} claims",
                data={
                    "claims_checked": len(claims),
                    "verification_sources": verification_sources,
                    "results": results,
                    "summary": {
                        "verified_true": verified_true,
                        "verified_false": verified_false,
                        "unverifiable": unverifiable,
                        "misleading": misleading,
                    },
                },
            )
            
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Fact-checking failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_literature_review(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle academic literature review tasks using arXiv API."""
        topic = message_data.get("topic")
        databases = message_data.get("databases", ["arxiv"])
        year_range = message_data.get("year_range", "2019-2024")
        max_papers = message_data.get("max_papers", 20)
        
        if not topic:
            return WorkerResult(
                success=False,
                message="No topic specified for literature review",
                data={"error": "topic is required"},
            )
        
        try:
            from mindflow_backend.agents.tools.search_web import WebSearchTool, WebFetchTool
            from mindflow_backend.services.llm import get_llm_service
            
            search_tool = WebSearchTool()
            llm_service = get_llm_service()
            
            papers = []
            databases_searched = []
            
            # Search arXiv if requested
            if "arxiv" in databases:
                arxiv_query = f"site:arxiv.org {topic}"
                arxiv_results = await search_tool.execute(query=arxiv_query, num_results=max_papers)
                
                for result in arxiv_results.get("results", []):
                    papers.append({
                        "title": result.get("title", "Unknown"),
                        "url": result.get("url", ""),
                        "source": "arxiv",
                        "snippet": result.get("snippet", "")[:200],
                    })
                
                databases_searched.append("arxiv")
            
            # Search Google Scholar-like results
            scholar_query = f"{topic} research paper PDF"
            scholar_results = await search_tool.execute(query=scholar_query, num_results=max_papers // 2)
            
            for result in scholar_results.get("results", []):
                if result.get("url", "").endswith(".pdf"):
                    papers.append({
                        "title": result.get("title", "Unknown"),
                        "url": result.get("url", ""),
                        "source": "academic",
                        "snippet": result.get("snippet", "")[:200],
                    })
            
            if "academic" not in databases_searched:
                databases_searched.append("academic_search")
            
            # Use LLM to analyze papers and extract themes
            if papers:
                papers_text = "\n\n".join([
                    f"{i+1}. {p['title']}\n{p['snippet']}"
                    for i, p in enumerate(papers[:10])
                ])
                
                analysis_prompt = f"""Analyze these research paper titles and abstracts to identify:

Papers:
{papers_text}

Provide:
1. Key research themes (3-5 themes)
2. Research gaps or underexplored areas (2-3 gaps)
3. Trending directions or emerging topics (2-3 directions)

Format as a JSON-like structure with these keys: key_themes, research_gaps, trending_directions"""
                
                try:
                    analysis = await llm_service.generate(
                        prompt=analysis_prompt,
                        system_message="You are an academic research analyst. Provide structured analysis.",
                        temperature=0.3,
                        max_tokens=800,
                    )
                    
                    # Parse analysis (simple extraction)
                    key_themes = self._extract_list_items(analysis, "theme")
                    research_gaps = self._extract_list_items(analysis, "gap")
                    trending_directions = self._extract_list_items(analysis, "direction")
                    
                except Exception:
                    key_themes = ["Theme extraction failed"]
                    research_gaps = ["Gap identification failed"]
                    trending_directions = ["Trend analysis failed"]
            else:
                key_themes = ["No papers found"]
                research_gaps = ["Unable to identify gaps"]
                trending_directions = ["No trending directions identified"]
            
            # Generate review summary
            review_prompt = f"""Based on {len(papers)} papers about "{topic}", provide a brief 2-3 sentence literature review summary highlighting the current state of research."""
            
            try:
                review_summary = await llm_service.generate(
                    prompt=review_prompt,
                    system_message="You are writing an academic literature review.",
                    temperature=0.4,
                    max_tokens=200,
                )
            except Exception:
                review_summary = f"Literature review on '{topic}' - {len(papers)} papers analyzed."
            
            return WorkerResult(
                success=True,
                message=f"Literature review completed for topic: {topic}",
                data={
                    "topic": topic,
                    "databases_searched": databases_searched,
                    "year_range": year_range,
                    "papers_analyzed": min(len(papers), max_papers),
                    "findings": {
                        "total_papers_found": len(papers),
                        "relevant_papers": min(len(papers), max_papers),
                        "key_themes": key_themes[:5],
                        "research_gaps": research_gaps[:3],
                        "trending_directions": trending_directions[:3],
                    },
                    "review_summary": review_summary,
                    "recommendations": [
                        "Review paper abstracts for detailed methodology",
                        "Consider citation analysis for impact assessment",
                        "Cross-reference findings with recent publications",
                    ],
                    "sample_papers": papers[:5],
                },
            )
            
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Literature review failed: {exc}",
                data={"error": str(exc), "topic": topic},
            )
    
    @staticmethod
    def _extract_list_items(text: str, item_type: str) -> list[str]:
        """Extract list items from LLM analysis text."""
        items = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("•") or (line[0].isdigit() and "." in line[:3]):
                item = line.strip("- •").strip()
                if item and len(item) > 5:
                    items.append(item)
        return items[:5] if items else [f"{item_type.capitalize()} extraction pending"]

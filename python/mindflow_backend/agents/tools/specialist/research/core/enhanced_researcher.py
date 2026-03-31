"""Enhanced Researcher agent backed by the PinchTab browser fleet."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from itertools import cycle
from time import perf_counter
from typing import Any
from urllib.parse import quote_plus

from mindflow_backend.agents.tools.specialist.research.analysis.result_synthesizer import (
    get_result_synthesizer,
)
from mindflow_backend.agents.tools.specialist.research.analysis.source_trust_engine import (
    get_source_trust_engine,
)
from mindflow_backend.agents.tools.specialist.research.core.query_engine import (
    ResearchQueryEngine,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.agents.research import (
    BrowserAction,
    BrowserActionRequest,
    BrowserActionResponse,
    ConfidenceLevel,
    IterationType,
    QueryPlan,
    QuestionType,
    ResearchBrowserSelection,
    ResearchConfig,
    ResearchFinding,
    ResearchRequest,
    ResearchResponse,
    ResearchResult,
    SourceClassification,
    SourceType,
)
from mindflow_backend.schemas.orchestration.delegation import DelegationTask
from mindflow_backend.schemas.tools.pinchtab_schemas import (
    BrowserCommandAction,
    BrowserCommandRequest,
    BrowserCommandResponse,
    CreateBrowserRequest,
    CreateBrowserResponse,
    ListBrowsersRequest,
    ListBrowsersResponse,
    ReconcileFleetResponse,
)
from mindflow_backend.services.core import get_pinchtab_fleet_service

_logger = get_logger(__name__)


class EnhancedResearcherAgent:
    """Research agent that plans queries and dispatches them to owned browsers."""

    def __init__(self) -> None:
        self.query_engine = ResearchQueryEngine()
        self.fleet_service = get_pinchtab_fleet_service()
        self.source_trust_engine = get_source_trust_engine()
        self.result_synthesizer = get_result_synthesizer()
        self.session_id: str | None = None
        self.agent_id: str | None = None

    async def initialize(self, session_id: str, agent_id: str) -> None:
        """Bind the agent to a session."""
        self.session_id = session_id
        self.agent_id = agent_id
        _logger.info("enhanced_researcher_initialized", session_id=session_id, agent_id=agent_id)

    async def execute_research(
        self,
        request: ResearchRequest | str,
        config: ResearchConfig | None = None,
        force_browser_search: bool = False,
    ) -> ResearchResponse:
        """Execute research by routing individual queries to managed browsers."""
        request = self._coerce_request(request, config=config, force_browser_search=force_browser_search)
        await self._ensure_initialized(request.session_id, request.agent_id)

        started_at = perf_counter()
        intent = self.query_engine.analyze_intent(request.query)
        plan = self.query_engine.plan_queries(intent, request.query)

        try:
            selection = await self.select_browsers_for_research(request)
            if not selection.selected_browser_ids:
                return ResearchResponse(
                    success=False,
                    error_message="No browsers available for this research request",
                    execution_summary={"session_id": request.session_id},
                )

            raw_results = await self._execute_plan_on_browsers(
                request=request,
                plan=plan,
                browser_ids=selection.selected_browser_ids,
            )
            successful_results = [item for item in raw_results if item["success"]]
            finding_sources = [item["source_url"] for item in successful_results]

            findings: list[ResearchFinding] = []
            action_trail: list[BrowserAction] = []
            for item in raw_results:
                action_trail.extend(item["actions"])
                if not item["success"]:
                    continue

                classification = self.source_trust_engine.evaluate_source(
                    url=item["source_url"],
                    content=item["content"],
                    existing_sources=[url for url in finding_sources if url != item["source_url"]],
                )
                findings.append(
                    self._build_finding(
                        source_url=item["source_url"],
                        content=item["content"],
                        classification=classification,
                    )
                )

            synthesis = self.result_synthesizer.synthesize_results(findings, request.query)
            duration_seconds = int(perf_counter() - started_at)
            confidence_level = self._normalize_confidence(synthesis.get("confidence_level", "unknown"))
            result = ResearchResult(
                session_id=request.session_id,
                original_query=request.query,
                question_type=intent.question_type,
                browsers_used=len(selection.selected_browser_ids),
                findings=findings,
                synthesis_summary=synthesis["summary"],
                confidence_level=confidence_level,
                conflicts_identified=synthesis["conflicts"],
                gaps_identified=synthesis["gaps"],
                recommendations=synthesis["recommendations"],
                total_duration_seconds=duration_seconds,
                action_trail=action_trail,
            )
            return ResearchResponse(
                success=True,
                result=result,
                execution_summary={
                    "query_plan": plan.model_dump(mode="json"),
                    "selected_browser_ids": selection.selected_browser_ids,
                    "auto_created_browser_ids": selection.auto_created_browser_ids,
                    "successful_browsers": len(successful_results),
                    "failed_browsers": len(raw_results) - len(successful_results),
                },
            )
        except Exception as exc:
            _logger.error(
                "enhanced_research_execution_failed",
                session_id=request.session_id,
                agent_id=request.agent_id,
                error=str(exc),
            )
            return ResearchResponse(
                success=False,
                error_message=str(exc),
                execution_summary={"session_id": request.session_id, "agent_id": request.agent_id},
            )

    async def create_browser(self, request: CreateBrowserRequest) -> CreateBrowserResponse:
        return await self.fleet_service.create_browser(request)

    async def list_browsers(self, request: ListBrowsersRequest) -> ListBrowsersResponse:
        return await self.fleet_service.list_browsers(request)

    async def get_browser_interface(self, browser_id: str):
        if not self.session_id:
            raise RuntimeError("Researcher is not initialized")
        return await self.fleet_service.get_browser_interface(self.session_id, browser_id)

    async def dispatch_browser_query(
        self,
        browser_id: str,
        request: BrowserCommandRequest,
    ) -> BrowserCommandResponse:
        if request.browser_id != browser_id:
            request = request.model_copy(update={"browser_id": browser_id})
        return await self.fleet_service.dispatch_command(request)

    async def reconcile_browser_fleet(self, session_id: str) -> ReconcileFleetResponse:
        return await self.fleet_service.reconcile_session(session_id)

    async def plan_queries(self, research_query: str) -> QueryPlan:
        intent = self.query_engine.analyze_intent(research_query)
        return self.query_engine.plan_queries(intent, research_query)

    async def get_research_capabilities(self) -> dict[str, Any]:
        """Expose legacy capability metadata for compatibility callers."""
        config = ResearchConfig()
        return {
            "supported_question_types": [question_type.value for question_type in QuestionType],
            "complexity_levels": ["simple", "moderate", "complex", "deep"],
            "max_concurrent_browsers": config.max_concurrent_browsers,
            "search_engines": config.preferred_search_engines,
            "source_types": [source_type.value for source_type in SourceType],
            "features": [
                "pinchtab_fleet_management",
                "per_browser_query_dispatch",
                "session_scoped_browser_ownership",
                "warm_paused_economy_mode",
                "source_trust_classification",
                "result_synthesis",
            ],
        }

    async def select_browsers_for_research(
        self,
        request: ResearchRequest,
    ) -> ResearchBrowserSelection:
        """Select existing browsers or auto-create enough to satisfy the plan."""
        config = request.config or ResearchConfig()
        intent = self.query_engine.analyze_intent(request.query)
        target_count = min(
            intent.browser_count,
            config.max_concurrent_browsers,
            config.max_browsers_per_session,
        )
        auto_created: list[str] = []

        if request.target_browser_ids:
            return ResearchBrowserSelection(
                session_id=request.session_id,
                selected_browser_ids=request.target_browser_ids[:target_count],
            )

        listed = await self.list_browsers(
            ListBrowsersRequest(
                session_id=request.session_id,
                agent_id=request.agent_id,
                include_closed=False,
            )
        )
        selected_ids = [browser.browser_id for browser in listed.browsers[:target_count]]
        missing = target_count - len(selected_ids)

        if missing > 0 and config.allow_browser_auto_create:
            for _ in range(missing):
                created = await self.create_browser(
                    CreateBrowserRequest(
                        session_id=request.session_id,
                        agent_id=request.agent_id,
                        economy_mode=config.default_economy_mode,
                        profile={
                            "headless": config.headless_mode,
                            "stealth": config.enable_stealth_mode,
                        },
                    )
                )
                if created.success and created.browser is not None:
                    selected_ids.append(created.browser.browser_id)
                    auto_created.append(created.browser.browser_id)

        return ResearchBrowserSelection(
            session_id=request.session_id,
            selected_browser_ids=selected_ids,
            auto_created_browser_ids=auto_created,
        )

    async def synthesize_results(self, results: list[ResearchFinding]) -> str:
        return self.result_synthesizer.synthesize_results(results, "")["summary"]

    async def classify_sources(
        self,
        sources: list[str],
        classification_criteria: dict[str, Any] | None = None,
    ) -> list[SourceClassification]:
        del classification_criteria
        return [
            self.source_trust_engine.evaluate_source(url=source, content="")
            for source in sources
        ]

    async def execute_browser_actions(
        self,
        actions: list[BrowserActionRequest],
    ) -> list[BrowserActionResponse]:
        if not self.session_id:
            raise RuntimeError("Researcher is not initialized")

        responses: list[BrowserActionResponse] = []
        for action in actions:
            command_action, payload = self._translate_browser_action(action)
            command = BrowserCommandRequest(
                session_id=self.session_id,
                browser_id=action.browser_id,
                action=command_action,
                payload=payload,
                timeout_seconds=action.timeout_seconds,
            )
            result = await self.dispatch_browser_query(action.browser_id, command)
            responses.append(
                BrowserActionResponse(
                    success=result.success,
                    browser_id=action.browser_id,
                    iteration_type=action.iteration_type,
                    result_data=result.data,
                    error_message=result.error_message,
                )
            )
        return responses

    async def validate_findings(
        self,
        findings: list[ResearchFinding],
        validation_criteria: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del validation_criteria
        average_confidence = (
            sum(item.confidence_score for item in findings) / len(findings)
            if findings
            else 0.0
        )
        return {
            "average_confidence": average_confidence,
            "high_confidence_findings": len([item for item in findings if item.confidence_score >= 0.8]),
            "is_valid": average_confidence >= 0.5,
        }

    async def identify_conflicts(
        self,
        findings: list[ResearchFinding],
    ) -> list[dict[str, Any]]:
        return self.result_synthesizer.synthesize_results(findings, "")["conflicts"]

    async def assess_research_quality(
        self,
        research_result: ResearchResponse,
        quality_metrics: list[str] | None = None,
    ) -> dict[str, Any]:
        quality_metrics = quality_metrics or ["confidence", "coverage", "conflicts"]
        result = research_result.result
        if result is None:
            return {"quality_metrics": quality_metrics, "score": 0.0}
        findings_count = len(result.findings)
        score = min(1.0, ((findings_count / 3.0) + (1.0 if not result.conflicts_identified else 0.5)) / 2.0)
        return {"quality_metrics": quality_metrics, "score": score}

    async def optimize_search_strategy(
        self,
        initial_results: list[ResearchFinding],
        target_quality: float = 0.8,
    ) -> QueryPlan:
        if not initial_results:
            return await self.plan_queries("general follow-up research")
        original_query = initial_results[0].content_summary[:120] or "follow-up research"
        plan = await self.plan_queries(original_query)
        if target_quality > 0.9 and len(plan.queries) < 3:
            plan.queries.append(f"{original_query} official documentation")
        return plan

    async def extract_key_insights(
        self,
        research_findings: list[ResearchFinding],
        insight_type: str = "comprehensive",
    ) -> list[str]:
        del insight_type
        insights: list[str] = []
        for finding in research_findings:
            insights.extend(finding.key_points[:2])
        return insights[:10]

    async def generate_research_summary(
        self,
        research_result: ResearchResponse,
        summary_type: str = "executive",
    ) -> dict[str, Any]:
        del summary_type
        if research_result.result is None:
            return {"summary": "", "findings": 0}
        return {
            "summary": research_result.result.synthesis_summary,
            "findings": len(research_result.result.findings),
            "recommendations": research_result.result.recommendations,
        }

    async def estimate_research_complexity(self, task: DelegationTask) -> float:
        query = task.objective or task.expected_output or "research task"
        intent = self.query_engine.analyze_intent(query)
        mapping = {"simple": 0.25, "moderate": 0.5, "complex": 0.75, "deep": 1.0}
        return mapping[intent.complexity_level]

    async def extract_key_findings(self, full_output: str) -> str:
        return "\n".join(full_output.splitlines()[:5]).strip()

    async def cleanup(self) -> None:
        """No-op cleanup hook kept for compatibility."""
        _logger.info("enhanced_researcher_cleanup_completed", session_id=self.session_id, agent_id=self.agent_id)

    async def _execute_plan_on_browsers(
        self,
        request: ResearchRequest,
        plan: QueryPlan,
        browser_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Run the generated plan across selected browsers."""
        queries = plan.queries or [request.query]
        engines = list(plan.search_engines or ["google.com"])
        assignments = []
        for browser_id, query, search_engine in zip(browser_ids, queries, cycle(engines)):
            assignments.append(self._run_browser_query(request, browser_id, query, search_engine))
        return await asyncio.gather(*assignments)

    async def _run_browser_query(
        self,
        request: ResearchRequest,
        browser_id: str,
        query: str,
        search_engine: str,
    ) -> dict[str, Any]:
        """Run a single query on a specific browser and collect raw output."""
        source_url = self._build_search_url(search_engine, query)
        actions: list[BrowserAction] = []

        navigate = BrowserCommandRequest(
            session_id=request.session_id,
            browser_id=browser_id,
            action=BrowserCommandAction.NAVIGATE,
            payload={"url": source_url},
            timeout_seconds=(request.config or ResearchConfig()).default_timeout_seconds,
        )
        navigate_response = await self.dispatch_browser_query(browser_id, navigate)
        actions.append(
            self._record_action(
                browser_id,
                IterationType.NAVIGATE,
                {"url": source_url},
                navigate_response,
            )
        )
        if not navigate_response.success:
            return {
                "success": False,
                "browser_id": browser_id,
                "source_url": source_url,
                "content": "",
                "actions": actions,
            }

        extract = BrowserCommandRequest(
            session_id=request.session_id,
            browser_id=browser_id,
            action=BrowserCommandAction.EXTRACT_TEXT,
            payload={},
            timeout_seconds=(request.config or ResearchConfig()).default_timeout_seconds,
        )
        extract_response = await self.dispatch_browser_query(browser_id, extract)
        actions.append(
            self._record_action(
                browser_id,
                IterationType.EXTRACT,
                {},
                extract_response,
            )
        )
        content = self._extract_content(extract_response.data)
        return {
            "success": extract_response.success,
            "browser_id": browser_id,
            "source_url": source_url,
            "content": content,
            "actions": actions,
        }

    def _build_finding(
        self,
        source_url: str,
        content: str,
        classification: SourceClassification,
    ) -> ResearchFinding:
        """Convert raw browser output into a typed research finding."""
        summary = content[:500].strip() or "No content extracted"
        key_points = [line.strip("- ").strip() for line in content.splitlines() if line.strip()][:3]
        confidence_score = min(1.0, max(0.2, classification.domain_authority))
        return ResearchFinding(
            source_url=source_url,
            source_classification=classification,
            content_summary=summary,
            key_points=key_points,
            confidence_score=confidence_score,
            relevance_score=min(1.0, 0.4 + (0.2 * len(key_points))),
            extraction_method="pinchtab_browser",
        )

    def _record_action(
        self,
        browser_id: str,
        iteration_type: IterationType,
        action_data: dict[str, Any],
        response: BrowserCommandResponse,
    ) -> BrowserAction:
        """Convert a browser command result into the research action trail schema."""
        return BrowserAction(
            browser_id=browser_id,
            iteration_type=iteration_type,
            timestamp=datetime.now(UTC).isoformat(),
            action_data=action_data,
            success=response.success,
            error_message=response.error_message,
        )

    def _extract_content(self, payload: dict[str, Any]) -> str:
        """Extract text content from heterogeneous PinchTab payloads."""
        for key in ("text", "content", "body", "markdown"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return str(payload)

    def _normalize_confidence(self, value: str | ConfidenceLevel) -> ConfidenceLevel:
        if isinstance(value, ConfidenceLevel):
            return value
        try:
            return ConfidenceLevel(value)
        except ValueError:
            return ConfidenceLevel.UNKNOWN

    def _translate_browser_action(
        self,
        action: BrowserActionRequest,
    ) -> tuple[BrowserCommandAction, dict[str, Any]]:
        """Translate legacy browser-action requests into PinchTab commands."""
        payload = dict(action.action_data)
        if action.iteration_type == IterationType.NAVIGATE:
            return BrowserCommandAction.NAVIGATE, {"url": payload.get("url")}
        if action.iteration_type == IterationType.SNAPSHOT:
            return BrowserCommandAction.GET_SNAPSHOT, {
                "filter_interactive": payload.get("filter_interactive", True)
            }
        if action.iteration_type == IterationType.EXTRACT:
            return BrowserCommandAction.EXTRACT_TEXT, {}
        if action.iteration_type == IterationType.CLICK:
            return BrowserCommandAction.CLICK_ELEMENT, {"element_ref": payload.get("ref")}
        if action.iteration_type == IterationType.FILL:
            return BrowserCommandAction.FILL_INPUT, {
                "element_ref": payload.get("ref"),
                "value": payload.get("value"),
            }
        if action.iteration_type == IterationType.PRESS:
            return BrowserCommandAction.PRESS_KEY, {
                "element_ref": payload.get("ref"),
                "key": payload.get("key"),
            }
        return BrowserCommandAction.GET_STATE, {}

    async def _ensure_initialized(self, session_id: str, agent_id: str) -> None:
        if self.session_id != session_id or self.agent_id != agent_id:
            await self.initialize(session_id, agent_id)

    def _coerce_request(
        self,
        request: ResearchRequest | str,
        config: ResearchConfig | None = None,
        force_browser_search: bool = False,
    ) -> ResearchRequest:
        if isinstance(request, ResearchRequest):
            return request
        if not self.session_id or not self.agent_id:
            raise RuntimeError("Researcher is not initialized")
        return ResearchRequest(
            query=request,
            session_id=self.session_id,
            agent_id=self.agent_id,
            config=config,
            force_browser_search=force_browser_search,
        )

    def _build_search_url(self, search_engine: str, query: str) -> str:
        host = search_engine.removeprefix("https://").removeprefix("http://").rstrip("/")
        return f"https://{host}/search?q={quote_plus(query)}"

    def _should_use_browser_search(self, intent: Any) -> bool:
        """Legacy heuristic kept for older integration tests and callers."""
        complexity = getattr(intent, "complexity_level", "moderate")
        browser_count = getattr(intent, "browser_count", 1)
        question_type = getattr(getattr(intent, "question_type", None), "value", "general")
        return complexity in {"moderate", "complex", "deep"} or browser_count > 1 or question_type in {
            "comparison",
            "current_state",
            "debug",
            "informational_data",
        }


_enhanced_researcher: EnhancedResearcherAgent | None = None


async def get_enhanced_researcher_agent() -> EnhancedResearcherAgent:
    global _enhanced_researcher
    if _enhanced_researcher is None:
        _enhanced_researcher = EnhancedResearcherAgent()
    return _enhanced_researcher


__all__ = ["EnhancedResearcherAgent", "get_enhanced_researcher_agent"]

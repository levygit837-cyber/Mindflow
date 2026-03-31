from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.specialist.research.core.enhanced_researcher import (
    EnhancedResearcherAgent,
)
from mindflow_backend.schemas.agents.research import (
    ConfidenceLevel,
    ResearchRequest,
    SourceClassification,
    SourceType,
)
from mindflow_backend.schemas.tools.pinchtab_schemas import (
    BrowserCommandAction,
    BrowserCommandResponse,
    BrowserEconomyMode,
    BrowserInstanceState,
    BrowserRuntimeState,
    CreateBrowserResponse,
    ListBrowsersResponse,
)


class _FakeFleetService:
    def __init__(self) -> None:
        self.created_browser_ids: list[str] = []

    async def list_browsers(self, request) -> ListBrowsersResponse:
        del request
        return ListBrowsersResponse(success=True, browsers=[])

    async def create_browser(self, request) -> CreateBrowserResponse:
        browser_id = f"browser-{len(self.created_browser_ids) + 1}"
        browser = BrowserInstanceState(
            browser_id=browser_id,
            session_id=request.session_id,
            agent_id=request.agent_id,
            economy_mode=BrowserEconomyMode.WARM_PAUSED,
            runtime_state=BrowserRuntimeState.WARM_PAUSED,
            runtime_endpoint="http://127.0.0.1:9867",
            tab_id="tab-1",
        )
        self.created_browser_ids.append(browser.browser_id)
        return CreateBrowserResponse(success=True, browser=browser)

    async def dispatch_command(self, request) -> BrowserCommandResponse:
        if request.action == BrowserCommandAction.NAVIGATE:
            return BrowserCommandResponse(
                success=True,
                browser_id=request.browser_id,
                action=request.action,
                runtime_state=BrowserRuntimeState.ACTIVE,
                data={"url": request.payload["url"]},
            )
        return BrowserCommandResponse(
            success=True,
            browser_id=request.browser_id,
            action=request.action,
            runtime_state=BrowserRuntimeState.ACTIVE,
            data={"text": "Python async updates\nTask groups\nImproved diagnostics"},
        )

    async def get_browser_interface(self, session_id: str, browser_id: str):
        del session_id, browser_id
        raise NotImplementedError

    async def reconcile_session(self, session_id: str):
        del session_id
        raise NotImplementedError


@pytest.mark.asyncio
async def test_enhanced_researcher_auto_creates_browser_and_builds_findings() -> None:
    agent = EnhancedResearcherAgent()
    agent.fleet_service = _FakeFleetService()
    agent.source_trust_engine = type(
        "_FakeSourceTrustEngine",
        (),
        {
            "evaluate_source": staticmethod(
                lambda url, content, existing_sources=None: SourceClassification(
                    url=url,
                    source_type=SourceType.OFFICIAL,
                    trust_level=ConfidenceLevel.HIGH,
                    domain_authority=0.9,
                    content_type="search-results",
                    last_updated=None,
                )
            )
        },
    )()
    agent.result_synthesizer = type(
        "_FakeSynthesizer",
        (),
        {
            "synthesize_results": staticmethod(
                lambda findings, query: {
                    "summary": f"Summary for {query}",
                    "conflicts": [],
                    "gaps": [],
                    "recommendations": ["Continue validating with official sources"],
                    "confidence_level": "high",
                }
            )
        },
    )()
    await agent.initialize("session-1", "researcher")

    response = await agent.execute_research(
        ResearchRequest(
            query="latest Python async improvements",
            session_id="session-1",
            agent_id="researcher",
        )
    )

    assert response.success is True
    assert response.result is not None
    assert response.result.browsers_used == 2
    assert len(response.result.findings) == 2
    assert response.execution_summary["auto_created_browser_ids"] == ["browser-1", "browser-2"]

"""Session-scoped fleet service for dockerized PinchTab browsers."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.interfaces.tools.pinchtab import PinchTabBrowserHandleInterface
from mindflow_backend.schemas.tools.pinchtab_schemas import (
    BrowserCommandAction,
    BrowserCommandRequest,
    BrowserCommandResponse,
    BrowserEconomyMode,
    BrowserInstanceState,
    BrowserOwnershipScope,
    BrowserRuntimeState,
    CreateBrowserRequest,
    CreateBrowserResponse,
    ListBrowsersRequest,
    ListBrowsersResponse,
    PinchTabBrowserProfile,
    ReconcileFleetResponse,
)
from mindflow_backend.services.core.pinchtab_browser_service import PinchTabBrowserService
from mindflow_backend.services.core.pinchtab_container_service import PinchTabContainerService
from mindflow_backend.storage.postgresql.models import BrowserInstance, ResearchSession, utcnow

_logger = get_logger(__name__)

if TYPE_CHECKING:
    from mindflow_backend.workers.research.interfaces.browser import BrowserTaskPublisher
    from mindflow_backend.workers.research.interfaces.content import ContentTaskPublisher
    from mindflow_backend.workers.research.schemas.browser_tasks import BrowserTaskPayload


class PinchTabBrowserHandle(PinchTabBrowserHandleInterface):
    """Bound helper for controlling a single browser via the fleet service."""

    def __init__(self, fleet_service: PinchTabFleetService, session_id: str, browser_id: str) -> None:
        self._fleet_service = fleet_service
        self._session_id = session_id
        self._browser_id = browser_id

    @property
    def browser_id(self) -> str:
        return self._browser_id

    async def navigate(self, url: str, timeout_seconds: int | None = None) -> BrowserCommandResponse:
        return await self._dispatch(
            BrowserCommandAction.NAVIGATE,
            {"url": url},
            timeout_seconds=timeout_seconds,
        )

    async def get_snapshot(
        self,
        filter_interactive: bool = True,
        timeout_seconds: int | None = None,
    ) -> BrowserCommandResponse:
        return await self._dispatch(
            BrowserCommandAction.GET_SNAPSHOT,
            {"filter_interactive": filter_interactive},
            timeout_seconds=timeout_seconds,
        )

    async def extract_text(self, timeout_seconds: int | None = None) -> BrowserCommandResponse:
        return await self._dispatch(BrowserCommandAction.EXTRACT_TEXT, timeout_seconds=timeout_seconds)

    async def click_element(self, element_ref: str, timeout_seconds: int | None = None) -> BrowserCommandResponse:
        return await self._dispatch(
            BrowserCommandAction.CLICK_ELEMENT,
            {"element_ref": element_ref},
            timeout_seconds=timeout_seconds,
        )

    async def fill_input(
        self,
        element_ref: str,
        value: str,
        timeout_seconds: int | None = None,
    ) -> BrowserCommandResponse:
        return await self._dispatch(
            BrowserCommandAction.FILL_INPUT,
            {"element_ref": element_ref, "value": value},
            timeout_seconds=timeout_seconds,
        )

    async def press_key(
        self,
        element_ref: str,
        key: str,
        timeout_seconds: int | None = None,
    ) -> BrowserCommandResponse:
        return await self._dispatch(
            BrowserCommandAction.PRESS_KEY,
            {"element_ref": element_ref, "key": key},
            timeout_seconds=timeout_seconds,
        )

    async def get_state(self) -> BrowserInstanceState:
        return await self._fleet_service.get_browser(self._session_id, self._browser_id)

    async def _dispatch(
        self,
        action: BrowserCommandAction,
        payload: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> BrowserCommandResponse:
        request = BrowserCommandRequest(
            session_id=self._session_id,
            browser_id=self._browser_id,
            action=action,
            payload=payload or {},
            timeout_seconds=timeout_seconds,
        )
        return await self._fleet_service.dispatch_command(request)


class PinchTabFleetService:
    """Manage browser ownership, persistence, and per-browser command routing."""

    def __init__(
        self,
        container_orchestrator: PinchTabContainerService | None = None,
        browser_service: PinchTabBrowserService | None = None,
        session_factory: Callable[[], Any] | None = None,
        browser_task_publisher: BrowserTaskPublisher | None = None,
        content_task_publisher: ContentTaskPublisher | None = None,
    ) -> None:
        self.settings = get_settings()
        self.container_orchestrator = container_orchestrator or PinchTabContainerService()
        self.browser_service = browser_service or PinchTabBrowserService()
        self._session_factory = session_factory
        self._browser_task_publisher = browser_task_publisher
        self._content_task_publisher = content_task_publisher
        self.idle_timeout_seconds = self.settings.pinchtab_idle_timeout_seconds
        self.max_browsers_per_session = self.settings.pinchtab_max_browsers_per_session
        self._idle_tasks: dict[str, asyncio.Task[None]] = {}

    async def queue_web_search(
        self,
        *,
        session_id: str,
        query: str,
        search_engine: str = "google",
        max_results: int = 10,
        search_depth: str = "standard",
    ) -> bool:
        """Queue browser-backed web search without blocking the interactive runtime."""
        if self._browser_task_publisher is None:
            from mindflow_backend.workers.research.publishers.browser_publisher import (
                RabbitMQBrowserTaskPublisher,
            )

            self._browser_task_publisher = RabbitMQBrowserTaskPublisher()

        return await self._browser_task_publisher.publish_web_search(
            session_id=session_id,
            query=query,
            search_engine=search_engine,
            max_results=max_results,
            search_depth=search_depth,
        )

    async def queue_content_synthesis(
        self,
        *,
        session_id: str,
        content_sources: list[dict[str, Any]],
        synthesis_type: str = "comprehensive",
        target_audience: str = "technical",
        synthesis_length: str = "medium",
    ) -> bool:
        """Queue content synthesis separately from browser acquisition."""
        if self._content_task_publisher is None:
            from mindflow_backend.workers.research.publishers.content_publisher import (
                RabbitMQContentTaskPublisher,
            )

            self._content_task_publisher = RabbitMQContentTaskPublisher()

        return await self._content_task_publisher.publish_content_synthesis(
            session_id=session_id,
            content_sources=content_sources,
            synthesis_type=synthesis_type,
            target_audience=target_audience,
            synthesis_length=synthesis_length,
        )

    async def execute_browser_task(self, payload: BrowserTaskPayload) -> dict[str, Any]:
        """Execute a queued browser task using the managed fleet lifecycle."""
        if payload.task_type == "web_search":
            return await self._execute_web_search_task(payload)
        if payload.task_type == "page_scraping":
            return await self._execute_page_scraping_task(payload)
        raise ValueError(f"Unsupported browser task type: {payload.task_type}")

    async def create_browser(self, request: CreateBrowserRequest) -> CreateBrowserResponse:
        """Create a managed browser and persist its ownership."""
        try:
            async with self._open_session() as db:
                owner_session = await self._ensure_owner_session(
                    db,
                    session_id=request.session_id,
                    agent_id=request.agent_id,
                    research_session_id=request.research_session_id,
                )
                existing_browsers = await self._list_browser_records(
                    db,
                    session_id=request.session_id,
                    agent_id=request.agent_id,
                    include_closed=False,
                )
                if len(existing_browsers) >= self.max_browsers_per_session:
                    raise ValueError(
                        f"Session {request.session_id} reached the limit of "
                        f"{self.max_browsers_per_session} browsers"
                    )

                browser_id = request.browser_id or self._generate_browser_id(
                    request.session_id,
                    len(existing_browsers) + 1,
                )
                runtime = await self.container_orchestrator.create_container(
                    browser_id=browser_id,
                    session_id=request.session_id,
                    agent_id=request.agent_id,
                    payload=request.model_dump(mode="json"),
                )
                is_healthy = False
                if runtime.get("runtime_endpoint"):
                    is_healthy = await self.browser_service.health_check(runtime["runtime_endpoint"])

                browser = BrowserInstance(
                    browser_id=browser_id,
                    instance_id=browser_id,
                    tab_id=runtime.get("tab_id") or browser_id,
                    research_session_id=owner_session.id,
                    current_url=None,
                    status="active" if is_healthy else "pending",
                    container_id=runtime.get("container_id"),
                    container_name=runtime.get("container_name"),
                    runtime_endpoint=runtime.get("runtime_endpoint"),
                    economy_mode=request.economy_mode.value,
                    runtime_state=BrowserRuntimeState.HEALTHY.value if is_healthy else BrowserRuntimeState.PROVISIONING.value,
                    last_activity=utcnow(),
                    resumed_at=utcnow(),
                    last_heartbeat_at=utcnow() if is_healthy else None,
                )
                db.add(browser)
                await db.flush()

                if request.economy_mode == BrowserEconomyMode.WARM_PAUSED and browser.container_id:
                    await self.container_orchestrator.pause_container(browser.container_id)
                    browser.runtime_state = BrowserRuntimeState.WARM_PAUSED.value
                    browser.paused_at = utcnow()

                await db.commit()
                await db.refresh(browser)
                return CreateBrowserResponse(
                    success=True,
                    browser=self._to_state(browser, request.session_id, request.agent_id, request.profile),
                )
        except Exception as exc:
            _logger.error("pinchtab_browser_create_failed", session_id=request.session_id, error=str(exc))
            return CreateBrowserResponse(success=False, error_message=str(exc))

    async def list_browsers(self, request: ListBrowsersRequest) -> ListBrowsersResponse:
        """List browsers owned by a session."""
        try:
            async with self._open_session() as db:
                rows = await self._list_browser_records(
                    db,
                    session_id=request.session_id,
                    agent_id=request.agent_id or "researcher",
                    include_closed=request.include_closed,
                )
                return ListBrowsersResponse(
                    success=True,
                    browsers=[
                        self._to_state(browser, request.session_id, request.agent_id or "researcher")
                        for browser in rows
                    ],
                )
        except Exception as exc:
            _logger.error("pinchtab_list_browsers_failed", session_id=request.session_id, error=str(exc))
            return ListBrowsersResponse(success=False, error_message=str(exc))

    async def get_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Return a single browser state owned by the given session."""
        async with self._open_session() as db:
            browser, owner = await self._get_owned_browser(db, session_id, browser_id)
            return self._to_state(browser, owner.session_id, owner.agent_id)

    async def pause_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Pause a managed browser runtime."""
        async with self._open_session() as db:
            browser, owner = await self._get_owned_browser(db, session_id, browser_id)
            if browser.container_id:
                await self.container_orchestrator.pause_container(browser.container_id)
            browser.runtime_state = (
                BrowserRuntimeState.WARM_PAUSED.value
                if browser.economy_mode == BrowserEconomyMode.WARM_PAUSED.value
                else BrowserRuntimeState.PAUSED.value
            )
            browser.paused_at = utcnow()
            browser.last_activity = utcnow()
            await db.commit()
            self._cancel_idle_task(session_id, browser_id)
            return self._to_state(browser, owner.session_id, owner.agent_id)

    async def resume_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Resume a managed browser runtime."""
        async with self._open_session() as db:
            browser, owner = await self._get_owned_browser(db, session_id, browser_id)
            if browser.container_id:
                await self.container_orchestrator.resume_container(browser.container_id)
            browser.runtime_state = BrowserRuntimeState.ACTIVE.value
            browser.resumed_at = utcnow()
            browser.last_activity = utcnow()
            await db.commit()
            return self._to_state(browser, owner.session_id, owner.agent_id)

    async def close_browser(self, session_id: str, browser_id: str) -> BrowserInstanceState:
        """Stop a managed browser runtime and mark it closed."""
        async with self._open_session() as db:
            browser, owner = await self._get_owned_browser(db, session_id, browser_id)
            if browser.container_id:
                await self.container_orchestrator.stop_container(browser.container_id)
            browser.runtime_state = BrowserRuntimeState.CLOSED.value
            browser.status = "closed"
            browser.closed_at = utcnow()
            browser.last_activity = utcnow()
            await db.commit()
            self._cancel_idle_task(session_id, browser_id)
            return self._to_state(browser, owner.session_id, owner.agent_id)

    async def dispatch_command(self, request: BrowserCommandRequest) -> BrowserCommandResponse:
        """Execute a command against a single owned browser."""
        async with self._open_session() as db:
            browser, owner = await self._get_owned_browser(db, request.session_id, request.browser_id)

            try:
                if request.auto_resume and browser.runtime_state in {
                    BrowserRuntimeState.WARM_PAUSED.value,
                    BrowserRuntimeState.PAUSED.value,
                }:
                    if browser.container_id:
                        await self.container_orchestrator.resume_container(browser.container_id)
                    browser.runtime_state = BrowserRuntimeState.ACTIVE.value
                    browser.resumed_at = utcnow()

                data = await self._execute_browser_action(browser, request)
                browser.actions_completed = (browser.actions_completed or 0) + 1
                browser.last_activity = utcnow()
                browser.last_heartbeat_at = utcnow()
                if request.action == BrowserCommandAction.NAVIGATE:
                    browser.current_url = request.payload.get("url")
                await db.commit()
                self._schedule_idle_pause(request.session_id, request.browser_id)
                return BrowserCommandResponse(
                    success=True,
                    browser_id=request.browser_id,
                    action=request.action,
                    runtime_state=BrowserRuntimeState(browser.runtime_state),
                    data=data,
                )
            except Exception as exc:
                browser.error_count = (browser.error_count or 0) + 1
                browser.runtime_state = BrowserRuntimeState.ERROR.value
                browser.last_activity = utcnow()
                await db.commit()
                _logger.error(
                    "pinchtab_browser_command_failed",
                    session_id=request.session_id,
                    browser_id=request.browser_id,
                    action=request.action.value,
                    error=str(exc),
                )
                return BrowserCommandResponse(
                    success=False,
                    browser_id=request.browser_id,
                    action=request.action,
                    runtime_state=BrowserRuntimeState.ERROR,
                    error_message=str(exc),
                )

    async def reconcile_session(self, session_id: str) -> ReconcileFleetResponse:
        """Reconcile persisted browser rows against actual docker runtime state."""
        recovered: list[str] = []
        orphaned: list[str] = []
        closed: list[str] = []
        reconciled: list[BrowserInstanceState] = []

        async with self._open_session() as db:
            records = await self._list_browser_records(db, session_id, "researcher", include_closed=True)
            for browser in records:
                previous_state = browser.runtime_state
                info = None
                if browser.container_id:
                    info = await self.container_orchestrator.inspect_container(browser.container_id)

                if info is None:
                    if browser.closed_at is not None:
                        browser.runtime_state = BrowserRuntimeState.CLOSED.value
                        closed.append(browser.browser_id)
                    else:
                        browser.runtime_state = BrowserRuntimeState.ORPHANED.value
                        orphaned.append(browser.browser_id)
                else:
                    browser.runtime_endpoint = info.get("runtime_endpoint")
                    browser.container_name = info.get("container_name")
                    browser.last_heartbeat_at = utcnow()
                    if info.get("paused"):
                        browser.runtime_state = (
                            BrowserRuntimeState.WARM_PAUSED.value
                            if browser.economy_mode == BrowserEconomyMode.WARM_PAUSED.value
                            else BrowserRuntimeState.PAUSED.value
                        )
                    else:
                        browser.runtime_state = BrowserRuntimeState.HEALTHY.value
                    if previous_state in {
                        BrowserRuntimeState.ORPHANED.value,
                        BrowserRuntimeState.ERROR.value,
                    }:
                        recovered.append(browser.browser_id)

                owner = await self._get_owner_session(db, browser.research_session_id)
                reconciled.append(self._to_state(browser, owner.session_id, owner.agent_id))

            await db.commit()

        return ReconcileFleetResponse(
            success=True,
            session_id=session_id,
            browsers=reconciled,
            recovered_browser_ids=recovered,
            orphaned_browser_ids=orphaned,
            closed_browser_ids=closed,
        )

    async def get_browser_interface(self, session_id: str, browser_id: str) -> PinchTabBrowserHandle:
        """Return a bound browser handle."""
        await self.get_browser(session_id, browser_id)
        return PinchTabBrowserHandle(self, session_id, browser_id)

    async def _execute_web_search_task(self, payload: BrowserTaskPayload) -> dict[str, Any]:
        """Create a temporary browser, run the search navigation, and extract text."""
        browser_id = await self._provision_browser_for_task(payload)
        target_url = self._build_search_url(payload.search_engine, payload.query)

        try:
            navigation = await self.dispatch_command(
                BrowserCommandRequest(
                    session_id=payload.session_id,
                    browser_id=browser_id,
                    action=BrowserCommandAction.NAVIGATE,
                    payload={"url": target_url},
                    timeout_seconds=payload.timeout_seconds,
                )
            )
            if not navigation.success:
                raise RuntimeError(navigation.error_message or f"Failed to navigate browser {browser_id}")

            extraction = await self.dispatch_command(
                BrowserCommandRequest(
                    session_id=payload.session_id,
                    browser_id=browser_id,
                    action=BrowserCommandAction.EXTRACT_TEXT,
                    timeout_seconds=payload.timeout_seconds,
                )
            )
            if not extraction.success:
                raise RuntimeError(extraction.error_message or f"Failed to extract text from browser {browser_id}")

            return {
                "session_id": payload.session_id,
                "browser_id": browser_id,
                "query": payload.query,
                "target_url": target_url,
                "search_engine": payload.search_engine,
                "max_results": payload.max_results,
                "search_depth": payload.search_depth,
                "extracted_text": extraction.data.get("text", ""),
            }
        finally:
            if payload.close_browser_after:
                await self._close_browser_safely(payload.session_id, browser_id)

    async def _execute_page_scraping_task(self, payload: BrowserTaskPayload) -> dict[str, Any]:
        """Create a temporary browser, navigate to a page, and extract text."""
        browser_id = await self._provision_browser_for_task(payload)

        try:
            navigation = await self.dispatch_command(
                BrowserCommandRequest(
                    session_id=payload.session_id,
                    browser_id=browser_id,
                    action=BrowserCommandAction.NAVIGATE,
                    payload={"url": payload.target_url},
                    timeout_seconds=payload.timeout_seconds,
                )
            )
            if not navigation.success:
                raise RuntimeError(navigation.error_message or f"Failed to navigate browser {browser_id}")

            extraction = await self.dispatch_command(
                BrowserCommandRequest(
                    session_id=payload.session_id,
                    browser_id=browser_id,
                    action=BrowserCommandAction.EXTRACT_TEXT,
                    timeout_seconds=payload.timeout_seconds,
                )
            )
            if not extraction.success:
                raise RuntimeError(extraction.error_message or f"Failed to extract text from browser {browser_id}")

            return {
                "session_id": payload.session_id,
                "browser_id": browser_id,
                "target_url": payload.target_url,
                "extraction_rules": payload.extraction_rules,
                "include_screenshots": payload.include_screenshots,
                "extracted_text": extraction.data.get("text", ""),
            }
        finally:
            if payload.close_browser_after:
                await self._close_browser_safely(payload.session_id, browser_id)

    async def _provision_browser_for_task(self, payload: BrowserTaskPayload) -> str:
        """Provision a browser dedicated to a queued browser task."""
        response = await self.create_browser(
            CreateBrowserRequest(
                session_id=payload.session_id,
                agent_id=payload.agent_id,
                economy_mode=BrowserEconomyMode.EPHEMERAL,
            )
        )
        if not response.success or response.browser is None:
            raise RuntimeError(response.error_message or "Failed to provision browser for queued task")
        return response.browser.browser_id

    async def _close_browser_safely(self, session_id: str, browser_id: str) -> None:
        """Close a browser without hiding the primary task error."""
        try:
            await self.close_browser(session_id, browser_id)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            _logger.warning(
                "pinchtab_browser_cleanup_failed",
                session_id=session_id,
                browser_id=browser_id,
                error=str(exc),
            )

    def _build_search_url(self, search_engine: str, query: str) -> str:
        """Build a deterministic search URL for queued web-search work."""
        encoded_query = quote_plus(query)
        if search_engine.lower() == "bing":
            return f"https://www.bing.com/search?q={encoded_query}"
        if search_engine.lower() == "duckduckgo":
            return f"https://duckduckgo.com/?q={encoded_query}"
        return f"https://www.google.com/search?q={encoded_query}"

    async def _execute_browser_action(
        self,
        browser: BrowserInstance,
        request: BrowserCommandRequest,
    ) -> dict[str, Any]:
        """Map a browser command request to the runtime HTTP client."""
        runtime_endpoint = browser.runtime_endpoint
        if not runtime_endpoint:
            raise RuntimeError(f"Browser {browser.browser_id} does not have a runtime endpoint")
        tab_id = browser.tab_id or browser.browser_id
        timeout = request.timeout_seconds

        if request.action == BrowserCommandAction.NAVIGATE:
            return await self.browser_service.navigate(
                runtime_endpoint,
                tab_id,
                request.payload["url"],
                timeout_seconds=timeout,
            )
        if request.action == BrowserCommandAction.GET_SNAPSHOT:
            return await self.browser_service.get_snapshot(
                runtime_endpoint,
                tab_id,
                filter_interactive=request.payload.get("filter_interactive", True),
                timeout_seconds=timeout,
            )
        if request.action == BrowserCommandAction.EXTRACT_TEXT:
            return await self.browser_service.extract_text(runtime_endpoint, tab_id, timeout_seconds=timeout)
        if request.action == BrowserCommandAction.CLICK_ELEMENT:
            return await self.browser_service.click_element(
                runtime_endpoint,
                tab_id,
                request.payload["element_ref"],
                timeout_seconds=timeout,
            )
        if request.action == BrowserCommandAction.FILL_INPUT:
            return await self.browser_service.fill_input(
                runtime_endpoint,
                tab_id,
                request.payload["element_ref"],
                request.payload["value"],
                timeout_seconds=timeout,
            )
        if request.action == BrowserCommandAction.PRESS_KEY:
            return await self.browser_service.press_key(
                runtime_endpoint,
                tab_id,
                request.payload["element_ref"],
                request.payload["key"],
                timeout_seconds=timeout,
            )
        if request.action == BrowserCommandAction.GET_STATE:
            return await self.browser_service.get_state(runtime_endpoint, tab_id)

        raise ValueError(f"Unsupported browser action: {request.action}")

    async def _ensure_owner_session(
        self,
        db: AsyncSession,
        session_id: str,
        agent_id: str,
        research_session_id: str | None = None,
    ) -> ResearchSession:
        """Ensure there is a research session row to anchor browser ownership."""
        if research_session_id:
            try:
                parsed_id = UUID(research_session_id)
                result = await db.execute(
                    select(ResearchSession).where(ResearchSession.id == parsed_id)
                )
                row = result.scalar_one_or_none()
                if row is not None:
                    return row
            except ValueError:
                pass

        result = await db.execute(
            select(ResearchSession)
            .where(
                ResearchSession.session_id == session_id,
                ResearchSession.agent_id == agent_id,
            )
            .order_by(ResearchSession.created_at.desc())
        )
        row = result.scalars().first()
        if row is not None:
            return row

        row = ResearchSession(
            session_id=session_id,
            agent_id=agent_id,
            original_query="pinchtab_fleet_session",
            question_type="general",
            complexity_level="simple",
            browser_count=0,
            status="in_progress",
            confidence_level="unknown",
            session_metadata={"source": "pinchtab_fleet"},
        )
        db.add(row)
        await db.flush()
        return row

    async def _get_owner_session(self, db: AsyncSession, research_session_id: Any) -> ResearchSession:
        """Resolve the owning ResearchSession for a browser record."""
        result = await db.execute(
            select(ResearchSession).where(ResearchSession.id == research_session_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise LookupError(f"Research session {research_session_id} not found")
        return row

    async def _get_owned_browser(
        self,
        db: AsyncSession,
        session_id: str,
        browser_id: str,
    ) -> tuple[BrowserInstance, ResearchSession]:
        """Fetch an owned browser and validate session ownership."""
        result = await db.execute(
            select(BrowserInstance, ResearchSession)
            .join(ResearchSession, BrowserInstance.research_session_id == ResearchSession.id)
            .where(BrowserInstance.browser_id == browser_id)
        )
        row = result.first()
        if row is None:
            raise LookupError(f"Browser {browser_id} was not found")
        browser, owner = row
        if owner.session_id != session_id:
            raise PermissionError(
                f"Browser {browser_id} does not belong to session {session_id}"
            )
        return browser, owner

    async def _list_browser_records(
        self,
        db: AsyncSession,
        session_id: str,
        agent_id: str,
        include_closed: bool,
    ) -> list[BrowserInstance]:
        """List browser ORM rows for a session."""
        stmt = (
            select(BrowserInstance)
            .join(ResearchSession, BrowserInstance.research_session_id == ResearchSession.id)
            .where(
                ResearchSession.session_id == session_id,
                ResearchSession.agent_id == agent_id,
            )
            .order_by(BrowserInstance.created_at.asc())
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        if include_closed:
            return rows
        return [
            row
            for row in rows
            if row.runtime_state != BrowserRuntimeState.CLOSED.value and row.closed_at is None
        ]

    def _generate_browser_id(self, session_id: str, sequence: int) -> str:
        """Generate a stable browser identifier for a session."""
        compact_session = session_id.replace(" ", "-")[:24]
        return f"{compact_session}-browser-{sequence}"

    def _to_state(
        self,
        browser: BrowserInstance,
        session_id: str,
        agent_id: str,
        profile: PinchTabBrowserProfile | None = None,
    ) -> BrowserInstanceState:
        """Convert ORM row to public browser state schema."""
        return BrowserInstanceState(
            browser_id=browser.browser_id,
            session_id=session_id,
            agent_id=agent_id,
            ownership_scope=BrowserOwnershipScope.RESEARCH_SESSION,
            research_session_id=str(browser.research_session_id) if browser.research_session_id else None,
            profile=profile or PinchTabBrowserProfile(),
            economy_mode=BrowserEconomyMode(browser.economy_mode),
            runtime_state=BrowserRuntimeState(browser.runtime_state),
            current_url=browser.current_url,
            container_id=browser.container_id,
            container_name=browser.container_name,
            runtime_endpoint=browser.runtime_endpoint,
            tab_id=browser.tab_id,
            actions_completed=browser.actions_completed or 0,
            error_count=browser.error_count or 0,
            last_activity_at=self._iso(browser.last_activity),
            last_heartbeat_at=self._iso(browser.last_heartbeat_at),
            paused_at=self._iso(browser.paused_at),
            resumed_at=self._iso(browser.resumed_at),
            created_at=self._iso(browser.created_at),
            closed_at=self._iso(browser.closed_at),
        )

    def _iso(self, value: datetime | None) -> str | None:
        """Serialize datetimes consistently."""
        return value.isoformat() if value is not None else None

    def _idle_task_key(self, session_id: str, browser_id: str) -> str:
        return f"{session_id}:{browser_id}"

    def _cancel_idle_task(self, session_id: str, browser_id: str) -> None:
        """Cancel a pending idle pause task if one exists."""
        key = self._idle_task_key(session_id, browser_id)
        task = self._idle_tasks.pop(key, None)
        if task is not None:
            task.cancel()

    def _schedule_idle_pause(self, session_id: str, browser_id: str) -> None:
        """Pause warm-paused browsers again after the idle timeout elapses."""
        if self.idle_timeout_seconds <= 0:
            return

        async def _pause_when_idle() -> None:
            try:
                await asyncio.sleep(self.idle_timeout_seconds)
                async with self._open_session() as db:
                    browser, _owner = await self._get_owned_browser(db, session_id, browser_id)
                    if browser.economy_mode != BrowserEconomyMode.WARM_PAUSED.value:
                        return
                    if browser.runtime_state not in {
                        BrowserRuntimeState.ACTIVE.value,
                        BrowserRuntimeState.HEALTHY.value,
                    }:
                        return
                await self.pause_browser(session_id, browser_id)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                _logger.warning(
                    "pinchtab_idle_pause_failed",
                    session_id=session_id,
                    browser_id=browser_id,
                    error=str(exc),
                )

        self._cancel_idle_task(session_id, browser_id)
        key = self._idle_task_key(session_id, browser_id)
        self._idle_tasks[key] = asyncio.create_task(_pause_when_idle())

    def _open_session(self):
        """Resolve the async DB session factory lazily for test-friendly imports."""
        if self._session_factory is None:
            from mindflow_backend.infra.database.connection import get_db_session

            self._session_factory = get_db_session
        return self._session_factory()


__all__ = ["PinchTabBrowserHandle", "PinchTabFleetService"]

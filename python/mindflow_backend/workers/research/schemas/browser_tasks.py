"""Schemas for the research-domain browser queue pipeline."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope


def build_browser_task_hash(*, session_id: str, task_type: str, value: str) -> str:
    normalized = f"{session_id}:{task_type}:{value.strip()}".encode()
    return hashlib.sha256(normalized).hexdigest()


class WebSearchPayload(BaseModel):
    """Payload published for queued browser-based web search."""

    model_config = ConfigDict(extra="forbid")

    task_type: Literal["web_search"] = "web_search"
    session_id: str
    query: str
    search_engine: str = "google"
    max_results: int = 10
    search_depth: str = "standard"
    agent_id: str = "researcher"
    origin: str = "pinchtab_fleet_service"
    timeout_seconds: int | None = None
    close_browser_after: bool = True


class PageScrapingPayload(BaseModel):
    """Payload published for queued browser-based page scraping."""

    model_config = ConfigDict(extra="forbid")

    task_type: Literal["page_scraping"] = "page_scraping"
    session_id: str
    target_url: str
    extraction_rules: dict[str, Any] = Field(default_factory=dict)
    wait_for_selector: str | None = None
    include_screenshots: bool = False
    agent_id: str = "researcher"
    origin: str = "pinchtab_fleet_service"
    timeout_seconds: int | None = None
    close_browser_after: bool = True


BrowserTaskPayload = WebSearchPayload | PageScrapingPayload


def build_web_search_idempotency_key(*, session_id: str, query: str) -> str:
    return f"browser:web_search:{build_browser_task_hash(session_id=session_id, task_type='web_search', value=query)}"


def build_web_search_envelope(
    *,
    session_id: str,
    query: str,
    search_engine: str = "google",
    max_results: int = 10,
    search_depth: str = "standard",
    agent_id: str = "researcher",
    origin: str = "pinchtab_fleet_service",
    timeout_seconds: int | None = None,
    close_browser_after: bool = True,
) -> QueueMessageEnvelope:
    idempotency_key = build_web_search_idempotency_key(session_id=session_id, query=query)
    payload = WebSearchPayload(
        session_id=session_id,
        query=query,
        search_engine=search_engine,
        max_results=max_results,
        search_depth=search_depth,
        agent_id=agent_id,
        origin=origin,
        timeout_seconds=timeout_seconds,
        close_browser_after=close_browser_after,
    )
    return QueueMessageEnvelope(
        schema_version="1.0",
        task_id=idempotency_key,
        task_type=payload.task_type,
        session_id=session_id,
        correlation_id=idempotency_key,
        idempotency_key=idempotency_key,
        created_at=datetime.now(UTC),
        payload=payload.model_dump(mode="json"),
    )


def build_page_scraping_idempotency_key(*, session_id: str, target_url: str) -> str:
    return f"browser:page_scraping:{build_browser_task_hash(session_id=session_id, task_type='page_scraping', value=target_url)}"


def build_page_scraping_envelope(
    *,
    session_id: str,
    target_url: str,
    extraction_rules: dict[str, Any] | None = None,
    wait_for_selector: str | None = None,
    include_screenshots: bool = False,
    agent_id: str = "researcher",
    origin: str = "pinchtab_fleet_service",
    timeout_seconds: int | None = None,
    close_browser_after: bool = True,
) -> QueueMessageEnvelope:
    idempotency_key = build_page_scraping_idempotency_key(
        session_id=session_id,
        target_url=target_url,
    )
    payload = PageScrapingPayload(
        session_id=session_id,
        target_url=target_url,
        extraction_rules=extraction_rules or {},
        wait_for_selector=wait_for_selector,
        include_screenshots=include_screenshots,
        agent_id=agent_id,
        origin=origin,
        timeout_seconds=timeout_seconds,
        close_browser_after=close_browser_after,
    )
    return QueueMessageEnvelope(
        schema_version="1.0",
        task_id=idempotency_key,
        task_type=payload.task_type,
        session_id=session_id,
        correlation_id=idempotency_key,
        idempotency_key=idempotency_key,
        created_at=datetime.now(UTC),
        payload=payload.model_dump(mode="json"),
    )

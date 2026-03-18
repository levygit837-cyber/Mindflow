"""PinchTab fleet schemas and tool contracts.

Defines the public payloads used by the Researcher browser fleet,
including lifecycle requests, per-browser commands, and tool schemas.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema


class BrowserEconomyMode(StrEnum):
    """Runtime economy strategies for managed PinchTab browsers."""

    WARM_PAUSED = "warm_paused"
    ALWAYS_ON = "always_on"
    EPHEMERAL = "ephemeral"


class BrowserRuntimeState(StrEnum):
    """Operational state of a managed PinchTab browser."""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    HEALTHY = "healthy"
    ACTIVE = "active"
    WARM_PAUSED = "warm_paused"
    PAUSED = "paused"
    CLOSED = "closed"
    ORPHANED = "orphaned"
    ERROR = "error"


class BrowserCommandAction(StrEnum):
    """Commands supported by an individual browser handle."""

    NAVIGATE = "navigate"
    GET_SNAPSHOT = "get_snapshot"
    EXTRACT_TEXT = "extract_text"
    CLICK_ELEMENT = "click_element"
    FILL_INPUT = "fill_input"
    PRESS_KEY = "press_key"
    GET_STATE = "get_state"


class BrowserOwnershipScope(StrEnum):
    """Ownership boundary for browser isolation."""

    RESEARCH_SESSION = "research_session"


class PinchTabBrowserProfile(BaseModel):
    """Desired runtime profile for a managed browser."""

    browser_engine: str = "chromium"
    headless: bool = True
    stealth: bool = True
    viewport_width: int = Field(default=1440, ge=320)
    viewport_height: int = Field(default=900, ge=320)
    locale: str = "en-US"
    user_agent: str | None = None
    launch_args: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BrowserInstanceState(BaseModel):
    """Canonical representation of a managed browser instance."""

    browser_id: str
    session_id: str
    agent_id: str = "researcher"
    ownership_scope: BrowserOwnershipScope = BrowserOwnershipScope.RESEARCH_SESSION
    research_session_id: str | None = None
    profile: PinchTabBrowserProfile = Field(default_factory=PinchTabBrowserProfile)
    economy_mode: BrowserEconomyMode = BrowserEconomyMode.WARM_PAUSED
    runtime_state: BrowserRuntimeState = BrowserRuntimeState.PENDING
    current_url: str | None = None
    container_id: str | None = None
    container_name: str | None = None
    runtime_endpoint: str | None = None
    tab_id: str | None = None
    actions_completed: int = 0
    error_count: int = 0
    last_activity_at: str | None = None
    last_heartbeat_at: str | None = None
    paused_at: str | None = None
    resumed_at: str | None = None
    created_at: str | None = None
    closed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateBrowserRequest(BaseModel):
    """Request to provision a managed browser for a research session."""

    session_id: str = Field(min_length=1)
    agent_id: str = Field(default="researcher", min_length=1)
    research_session_id: str | None = None
    browser_id: str | None = None
    profile: PinchTabBrowserProfile = Field(default_factory=PinchTabBrowserProfile)
    ownership_scope: BrowserOwnershipScope = BrowserOwnershipScope.RESEARCH_SESSION
    economy_mode: BrowserEconomyMode = BrowserEconomyMode.WARM_PAUSED
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateBrowserResponse(BaseModel):
    """Result of browser creation."""

    success: bool
    browser: BrowserInstanceState | None = None
    error_message: str | None = None


class ListBrowsersRequest(BaseModel):
    """Query the browser fleet visible to a research session."""

    session_id: str = Field(min_length=1)
    agent_id: str | None = None
    include_closed: bool = False


class ListBrowsersResponse(BaseModel):
    """Response containing browsers owned by a research session."""

    success: bool
    browsers: list[BrowserInstanceState] = Field(default_factory=list)
    error_message: str | None = None


class BrowserCommandRequest(BaseModel):
    """Request to execute a command against a specific browser."""

    session_id: str = Field(min_length=1)
    browser_id: str = Field(min_length=1)
    action: BrowserCommandAction
    payload: dict[str, Any] = Field(default_factory=dict)
    auto_resume: bool = True
    timeout_seconds: int | None = Field(default=None, ge=1)


class BrowserCommandResponse(BaseModel):
    """Result of a single browser command."""

    success: bool
    browser_id: str
    action: BrowserCommandAction
    runtime_state: BrowserRuntimeState | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class ReconcileFleetResponse(BaseModel):
    """Result of reconciling persisted browsers with runtime state."""

    success: bool
    session_id: str
    browsers: list[BrowserInstanceState] = Field(default_factory=list)
    recovered_browser_ids: list[str] = Field(default_factory=list)
    orphaned_browser_ids: list[str] = Field(default_factory=list)
    closed_browser_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None


PINCHTAB_FLEET_SCHEMA = ToolSchema(
    name="pinchtab_fleet",
    description="Manage the Researcher PinchTab browser fleet for a session",
    category="web",
    parameters=[
        ToolParameter(
            name="action",
            type="string",
            description="Fleet action: create_browser, list_browsers, get_browser, pause_browser, resume_browser, close_browser, reconcile_session",
            required=True,
        ),
        ToolParameter(
            name="session_id",
            type="string",
            description="Research session owner for the browser fleet",
            required=False,
        ),
        ToolParameter(
            name="browser_id",
            type="string",
            description="Target browser identifier when required by the action",
            required=False,
        ),
        ToolParameter(
            name="payload",
            type="object",
            description="Action-specific payload",
            required=False,
            default={},
        ),
    ],
    returns={
        "type": "object",
        "description": "Fleet management result",
        "properties": {
            "success": {"type": "boolean"},
            "browser": {"type": "object"},
            "browsers": {"type": "array"},
            "error_message": {"type": "string"},
        },
    },
)


PINCHTAB_BROWSER_SCHEMA = ToolSchema(
    name="pinchtab_browser",
    description="Execute browser commands on an owned PinchTab browser",
    category="web",
    parameters=[
        ToolParameter(
            name="browser_id",
            type="string",
            description="Target managed browser identifier",
            required=True,
        ),
        ToolParameter(
            name="action",
            type="string",
            description="Browser action: navigate, get_snapshot, extract_text, click_element, fill_input, press_key, get_state",
            required=True,
        ),
        ToolParameter(
            name="session_id",
            type="string",
            description="Owning research session identifier",
            required=False,
        ),
        ToolParameter(
            name="payload",
            type="object",
            description="Action payload such as url, ref, value, or key",
            required=False,
            default={},
        ),
    ],
    returns={
        "type": "object",
        "description": "Browser command result",
        "properties": {
            "success": {"type": "boolean"},
            "browser_id": {"type": "string"},
            "action": {"type": "string"},
            "runtime_state": {"type": "string"},
            "data": {"type": "object"},
            "error_message": {"type": "string"},
        },
    },
)


PINCHTAB_SCHEMAS = {
    "pinchtab_fleet": PINCHTAB_FLEET_SCHEMA,
    "pinchtab_browser": PINCHTAB_BROWSER_SCHEMA,
}


__all__ = [
    "BrowserCommandAction",
    "BrowserCommandRequest",
    "BrowserCommandResponse",
    "BrowserEconomyMode",
    "BrowserInstanceState",
    "BrowserOwnershipScope",
    "BrowserRuntimeState",
    "CreateBrowserRequest",
    "CreateBrowserResponse",
    "ListBrowsersRequest",
    "ListBrowsersResponse",
    "PINCHTAB_BROWSER_SCHEMA",
    "PINCHTAB_FLEET_SCHEMA",
    "PINCHTAB_SCHEMAS",
    "PinchTabBrowserProfile",
    "ReconcileFleetResponse",
]

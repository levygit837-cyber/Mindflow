"""Session persistence manager for LightPanda browsers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from playwright.async_api import Page, BrowserContext

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.browser.snapshot_models import Snapshot, SnapshotData
from mindflow_backend.services.browser.snapshot_storage import SnapshotStorage

_logger = get_logger(__name__)


@dataclass
class BrowserSession:
    """Represents a persistent browser session."""

    session_id: str
    browser_id: str
    created_at: datetime
    last_used: datetime
    cookies: list[dict[str, Any]]
    localStorage: dict[str, str]
    sessionStorage: dict[str, str]
    page_state: dict[str, Any]

    def is_expired(self, ttl_hours: int = 24) -> bool:
        """Check if session has expired."""
        return (datetime.utcnow() - self.last_used).total_seconds() > (
            ttl_hours * 3600
        )


class SessionManager:
    """Manages browser session persistence."""

    def __init__(
        self, snapshot_storage: SnapshotStorage | None = None, session_ttl_hours: int = 24
    ):
        """Initialize the session manager.

        Args:
            snapshot_storage: Snapshot storage backend (created if None)
            session_ttl_hours: Session time-to-live in hours
        """
        self.snapshot_storage = snapshot_storage or SnapshotStorage()
        self.session_ttl_hours = session_ttl_hours
        self._logger = get_logger(__name__)

    async def capture_session(
        self,
        page: Page,
        context: BrowserContext,
        browser_id: str,
        session_id: str | None = None,
    ) -> BrowserSession:
        """Capture complete session state.

        Args:
            page: Playwright page
            context: Playwright browser context
            browser_id: Browser instance ID
            session_id: Session ID (generated if None)

        Returns:
            BrowserSession: Captured session
        """
        if session_id is None:
            session_id = f"session-{browser_id}-{int(datetime.utcnow().timestamp())}"

        # Capture cookies via CDP
        cookies = await context.cookies()

        # Capture localStorage
        localStorage = await page.evaluate(
            """() => {
            const data = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                data[key] = localStorage.getItem(key);
            }
            return data;
        }"""
        )

        # Capture sessionStorage
        sessionStorage = await page.evaluate(
            """() => {
            const data = {};
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                data[key] = sessionStorage.getItem(key);
            }
            return data;
        }"""
        )

        # Capture page state (URL, scroll position, etc)
        page_state = {
            "url": page.url,
            "title": await page.title(),
            "scroll_position": await page.evaluate(
                """() => ({
                x: window.scrollX,
                y: window.scrollY
            })"""
            ),
        }

        session = BrowserSession(
            session_id=session_id,
            browser_id=browser_id,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow(),
            cookies=cookies,
            localStorage=localStorage,
            sessionStorage=sessionStorage,
            page_state=page_state,
        )

        # Persist via SnapshotStorage
        snapshot = Snapshot(
            snapshot_id=session_id,
            browser_id=browser_id,
            created_at=session.created_at,
            url=session.page_state.get("url"),
            cookies=session.cookies,
            localStorage=session.localStorage,
            sessionStorage=session.sessionStorage,
            page_state=session.page_state,
        )

        snapshot_data = snapshot.validate()
        await self.snapshot_storage.save_snapshot(
            snapshot_id=session_id,
            browser_id=browser_id,
            snapshot_data=snapshot_data.dict(),
        )

        self._logger.info(
            "session_captured",
            session_id=session_id,
            browser_id=browser_id,
            cookies_count=len(cookies),
            localStorage_size=len(localStorage),
        )

        return session

    async def restore_session(
        self, page: Page, context: BrowserContext, session_id: str
    ) -> BrowserSession:
        """Restore persisted session.

        Args:
            page: Playwright page
            context: Playwright browser context
            session_id: Session ID to restore

        Returns:
            BrowserSession: Restored session

        Raises:
            ValueError: If session not found
        """
        # Load from SnapshotStorage
        snapshot_data = await self.snapshot_storage.load_snapshot(session_id)

        if not snapshot_data:
            raise ValueError(f"Session {session_id} not found")

        # Apply cookies
        await context.add_cookies(snapshot_data.get("cookies", []))

        # Restore localStorage
        if snapshot_data.get("localStorage"):
            await page.evaluate(
                """(data) => {
                for (const [key, value] of Object.entries(data)) {
                    localStorage.setItem(key, value);
                }
            }""",
                snapshot_data["localStorage"],
            )

        # Restore sessionStorage
        if snapshot_data.get("sessionStorage"):
            await page.evaluate(
                """(data) => {
                for (const [key, value] of Object.entries(data)) {
                    sessionStorage.setItem(key, value);
                }
            }""",
                snapshot_data["sessionStorage"],
            )

        # Navigate to saved URL if exists
        if snapshot_data.get("url"):
            await page.goto(snapshot_data["url"], wait_until="networkidle")

            # Restore scroll position
            if snapshot_data.get("page_state", {}).get("scroll_position"):
                await page.evaluate(
                    """(pos) => {
                    window.scrollTo(pos.x, pos.y);
                }""",
                    snapshot_data["page_state"]["scroll_position"],
                )

        # Update last_used
        session = BrowserSession(
            session_id=session_id,
            browser_id=snapshot_data["browser_id"],
            created_at=datetime.fromisoformat(snapshot_data["created_at"]),
            last_used=datetime.utcnow(),
            cookies=snapshot_data.get("cookies", []),
            localStorage=snapshot_data.get("localStorage", {}),
            sessionStorage=snapshot_data.get("sessionStorage", {}),
            page_state=snapshot_data.get("page_state", {}),
        )

        # Update snapshot_data with new last_used timestamp
        snapshot_data["last_used"] = session.last_used.isoformat()

        # Persist update
        await self.snapshot_storage.save_snapshot(
            snapshot_id=session_id,
            browser_id=session.browser_id,
            snapshot_data=snapshot_data,
        )

        self._logger.info(
            "session_restored",
            session_id=session_id,
            browser_id=session.browser_id,
        )

        return session

    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions.

        Returns:
            int: Number of sessions cleaned up
        """
        count = await self.snapshot_storage.cleanup_expired_snapshots()

        self._logger.info("expired_sessions_cleaned", count=count)
        return count

    async def close(self) -> None:
        """Cleanup session manager resources."""
        await self.snapshot_storage.close()

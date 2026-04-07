"""Snapshot data models for LightPanda browser service.

Defines the data structures used for browser snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator


class SnapshotData(BaseModel):
    """Validated snapshot data model.
    
    Ensures snapshot data meets requirements before storage.
    """
    
    snapshot_id: str = Field(..., min_length=1, max_length=255)
    browser_id: str = Field(..., min_length=1, max_length=255)
    url: str | None = Field(None, max_length=2048)
    cookies: list[dict[str, Any]] = Field(default_factory=list)
    localStorage: dict[str, str] = Field(default_factory=dict)
    sessionStorage: dict[str, str] = Field(default_factory=dict)
    page_state: dict[str, Any] = Field(default_factory=dict)
    
    @validator("cookies")
    def validate_cookies(cls, v):
        """Validate cookies structure."""
        if not isinstance(v, list):
            raise ValueError("Cookies must be a list")
        for cookie in v:
            if not isinstance(cookie, dict):
                raise ValueError("Each cookie must be a dictionary")
            if "name" not in cookie:
                raise ValueError("Each cookie must have a 'name' field")
        return v
    
    @validator("localStorage", "sessionStorage")
    def validate_storage(cls, v):
        """Validate storage structure."""
        if not isinstance(v, dict):
            raise ValueError("Storage must be a dictionary")
        if len(v) > 10000:  # Reasonable limit
            raise ValueError("Storage exceeds maximum size")
        return v
    
    @validator("page_state")
    def validate_page_state(cls, v):
        """Validate page state structure."""
        if not isinstance(v, dict):
            raise ValueError("Page state must be a dictionary")
        return v


@dataclass
class Snapshot:
    """Represents a browser state snapshot.
    
    Contains the complete state of a browser instance at a point in time,
    including cookies, storage, and page state for rollback capabilities.
    """
    
    snapshot_id: str
    browser_id: str
    created_at: datetime
    url: str | None = None
    cookies: list[dict[str, Any]] | None = None
    localStorage: dict[str, Any] | None = None
    sessionStorage: dict[str, Any] | None = None
    page_state: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert snapshot to dictionary.
        
        Returns:
            Dictionary representation of the snapshot
        """
        return {
            "snapshot_id": self.snapshot_id,
            "browser_id": self.browser_id,
            "created_at": self.created_at.isoformat(),
            "url": self.url,
            "cookies": self.cookies or [],
            "localStorage": self.localStorage or {},
            "sessionStorage": self.sessionStorage or {},
            "page_state": self.page_state or {},
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Snapshot:
        """Create snapshot from dictionary.
        
        Args:
            data: Dictionary representation of snapshot
            
        Returns:
            Snapshot instance
        """
        return cls(
            snapshot_id=data["snapshot_id"],
            browser_id=data["browser_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            url=data.get("url"),
            cookies=data.get("cookies", []),
            localStorage=data.get("localStorage", {}),
            sessionStorage=data.get("sessionStorage", {}),
            page_state=data.get("page_state", {}),
        )
    
    def validate(self) -> SnapshotData:
        """Validate snapshot data using Pydantic model.
        
        Returns:
            Validated SnapshotData instance
            
        Raises:
            ValidationError: If validation fails
        """
        return SnapshotData(
            snapshot_id=self.snapshot_id,
            browser_id=self.browser_id,
            url=self.url,
            cookies=self.cookies or [],
            localStorage=self.localStorage or {},
            sessionStorage=self.sessionStorage or {},
            page_state=self.page_state or {},
        )

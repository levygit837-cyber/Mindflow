"""Durable session runtime state storage.

This service stores the minimum operational state needed to resume orchestration
and shell-tab workflows after a restart. It prefers the canonical database
backend, but falls back to an in-memory cache when persistence is unavailable.
"""

from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger
from sqlalchemy import select

_logger = get_logger(__name__)

_STATE_KEY_PREFIX = "session_runtime_state:"
_STATE_VERSION = 1


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _deep_merge(base: Any, patch: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(patch, dict):
        return copy.deepcopy(patch)

    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if key in merged:
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


@dataclass(slots=True)
class _StoredSessionState:
    session_id: str
    state: dict[str, Any]
    updated_at: str
    version: int = _STATE_VERSION


def _get_db_session_factory():
    from mindflow_backend.infra.database.connection import get_db_session

    return get_db_session


def _get_setting_model():
    from mindflow_backend.storage.postgresql.models import Setting

    return Setting


class _SettingRuntimeStateBackend:
    def __init__(self) -> None:
        self._memory_store: dict[str, _StoredSessionState] = {}
        self._lock = asyncio.Lock()

    async def save_session_state(self, session_id: str, state: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            current = await self.load_session_state(session_id) or {}
            merged = _deep_merge(current, state)
            stored = _StoredSessionState(
                session_id=session_id,
                state=copy.deepcopy(merged),
                updated_at=datetime.now(UTC).isoformat(),
            )

            payload = json.dumps(
                {
                    "session_id": stored.session_id,
                    "updated_at": stored.updated_at,
                    "version": stored.version,
                    "state": stored.state,
                },
                ensure_ascii=False,
                default=_json_default,
            )

            try:
                async with _get_db_session_factory()() as db:
                    Setting = _get_setting_model()
                    setting = await db.get(Setting, f"{_STATE_KEY_PREFIX}{session_id}")
                    if setting is None:
                        setting = Setting(key=f"{_STATE_KEY_PREFIX}{session_id}", value=payload)
                        db.add(setting)
                    else:
                        setting.value = payload
                    await db.commit()
                self._memory_store.pop(session_id, None)
            except Exception as exc:
                _logger.warning("session_runtime_state_persist_failed", session_id=session_id, error=str(exc))
                self._memory_store[session_id] = stored

            return copy.deepcopy(merged)

    async def load_session_state(self, session_id: str) -> dict[str, Any] | None:
        try:
            async with _get_db_session_factory()() as db:
                Setting = _get_setting_model()
                setting = await db.get(Setting, f"{_STATE_KEY_PREFIX}{session_id}")
                if setting is None:
                    raise LookupError(session_id)
                payload = json.loads(setting.value)
                state = payload.get("state", payload)
                if isinstance(state, dict):
                    return copy.deepcopy(state)
        except Exception:
            cached = self._memory_store.get(session_id)
            if cached is not None:
                return copy.deepcopy(cached.state)
        return None

    async def list_session_states(self) -> list[dict[str, Any]]:
        sessions: dict[str, dict[str, Any]] = {}

        try:
            async with _get_db_session_factory()() as db:
                Setting = _get_setting_model()
                rows = (await db.execute(select(Setting).where(Setting.key.like(f"{_STATE_KEY_PREFIX}%")))).scalars().all()
                for row in rows:
                    payload = json.loads(row.value)
                    state = payload.get("state", payload)
                    session_id = payload.get("session_id") or row.key.removeprefix(_STATE_KEY_PREFIX)
                    sessions[session_id] = {
                        "session_id": session_id,
                        "updated_at": payload.get("updated_at"),
                        **(state if isinstance(state, dict) else {}),
                    }
        except Exception:
            pass

        for session_id, cached in self._memory_store.items():
            sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "updated_at": cached.updated_at,
                    **copy.deepcopy(cached.state),
                },
            )

        return sorted(
            sessions.values(),
            key=lambda item: str(item.get("updated_at") or ""),
            reverse=True,
        )


class SessionRuntimeStateService:
    """Facade for saving and restoring session runtime state."""

    def __init__(self, *, backend: Any | None = None) -> None:
        self._backend = backend or _SettingRuntimeStateBackend()

    async def save_session_state(self, session_id: str, state: dict[str, Any]) -> dict[str, Any]:
        return await self._backend.save_session_state(session_id, state)

    async def load_session_state(self, session_id: str) -> dict[str, Any] | None:
        return await self._backend.load_session_state(session_id)

    async def list_session_states(self) -> list[dict[str, Any]]:
        return await self._backend.list_session_states()


__all__ = ["SessionRuntimeStateService"]

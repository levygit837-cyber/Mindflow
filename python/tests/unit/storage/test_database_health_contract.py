from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import TextClause

sys.modules.setdefault("asyncpg", ModuleType("asyncpg"))

from mindflow_backend.infra.database.connection import ConnectionMetrics, DatabaseManager
from mindflow_backend.infra.database.health import HealthCheckResult as DbHealthCheckResult
from mindflow_backend.infra.monitoring.health_checks import DatabaseHealthChecker, HealthStatus


def _pool_stub() -> MagicMock:
    pool = MagicMock()
    pool.size.return_value = 5
    pool.checkedin.return_value = 4
    pool.checkedout.return_value = 1
    pool.overflow.return_value = 0
    pool.invalid.return_value = 0
    return pool


@pytest.mark.asyncio
async def test_db_manager_health_check_executes_text_query() -> None:
    manager = DatabaseManager()
    manager._engine = MagicMock()
    manager._engine.pool = _pool_stub()
    manager._metrics = ConnectionMetrics()

    conn = AsyncMock()
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = conn
    begin_cm.__aexit__.return_value = False
    manager._engine.begin.return_value = begin_cm

    result = await manager.health_check()

    assert result["status"] == "healthy"
    statement = conn.execute.await_args.args[0]
    assert isinstance(statement, TextClause)


@pytest.mark.asyncio
async def test_monitoring_database_checker_accepts_healthcheckresult() -> None:
    checker = DatabaseHealthChecker()
    checker._db_health_checker = SimpleNamespace(
        check_health=AsyncMock(
            return_value=DbHealthCheckResult(
                status="healthy",
                latency_ms=10.0,
                details={"pool_utilization": 0.2},
            )
        )
    )

    result = await checker.check_health()

    assert result.status is HealthStatus.HEALTHY
    assert result.details["status"] == "healthy"
    assert result.details["latency_ms"] == 10.0

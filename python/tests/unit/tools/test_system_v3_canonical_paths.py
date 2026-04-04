from types import SimpleNamespace

import pytest

from mindflow_backend.agents.tools.system import process_manager_v3
from mindflow_backend.agents.tools.system import resource_monitor_v3
from mindflow_backend.agents.tools.system import system_info_v3
from mindflow_backend.schemas.tools.context import ToolContext


def _make_fake_legacy_builder(calls: dict[str, object], payload: dict[str, object]):
    class _FakeTool:
        async def execute(self, **kwargs):
            calls["kwargs"] = kwargs
            return {"success": True, "result": payload}

    def _builder(tool_cls, context):
        calls["tool_cls"] = tool_cls.__name__
        calls["context"] = context
        return _FakeTool()

    return _builder


@pytest.mark.asyncio
async def test_system_info_v3_delegates_to_canonical_tool(monkeypatch) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        system_info_v3,
        "build_legacy_tool",
        _make_fake_legacy_builder(calls, {"software": {"python": {"version": "3.13"}}}),
    )

    result = await system_info_v3.system_info_execute(
        system_info_v3.SystemInfoInput(info_type="software", include_sensitive=True),
        ToolContext(metadata={}),
    )

    assert calls["tool_cls"] == "SystemInfoTool"
    assert calls["kwargs"] == {"info_type": "software", "include_sensitive": True}
    assert result["success"] is True
    assert result["info_type"] == "software"


@pytest.mark.asyncio
async def test_process_manager_v3_delegates_to_canonical_tool(monkeypatch) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        process_manager_v3,
        "build_legacy_tool",
        _make_fake_legacy_builder(calls, {"killed": True, "signal": "SIGTERM"}),
    )

    result = await process_manager_v3.process_manager_execute(
        process_manager_v3.ProcessManagerInput(
            action="kill",
            pid=42,
            signal_name="SIGTERM",
            filter_name="python",
            filter_user="mindflow",
        ),
        ToolContext(metadata={}),
    )

    assert calls["tool_cls"] == "ProcessManagerTool"
    assert calls["kwargs"] == {
        "action": "kill",
        "pid": 42,
        "signal": "SIGTERM",
        "filter_name": "python",
        "filter_user": "mindflow",
    }
    assert result["success"] is True
    assert result["action"] == "kill"


@pytest.mark.asyncio
async def test_resource_monitor_v3_delegates_to_canonical_tool(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class _FakeMonitor:
        _monitoring = False
        _monitoring_task = None
        _history = {"cpu": [{"value": 50.0, "timestamp": 1.0}], "memory": [], "disk": [], "network": []}
        _alerts = []
        alert_thresholds = {"cpu": 90.0, "memory": 85.0, "disk": 90.0, "network": 1000000}
        history_size = 100

        async def execute(self, **kwargs):
            calls["kwargs"] = kwargs
            return {"success": True, "result": {"history": self._history}}

    monkeypatch.setattr(
        resource_monitor_v3,
        "_configure_resource_monitor",
        lambda context: _FakeMonitor(),
    )

    result = await resource_monitor_v3.resource_monitor_execute(
        resource_monitor_v3.ResourceMonitorInput(
            action="get_history",
            resources=["cpu"],
            duration=10,
            interval=2,
            alert_conditions={"cpu": 90.0},
        ),
        ToolContext(metadata={}),
    )

    assert calls["kwargs"] == {
        "action": "get_history",
        "resources": ["cpu"],
        "duration": 10,
        "interval": 2,
        "alert_conditions": {"cpu": 90.0},
    }
    assert result["success"] is True
    assert result["action"] == "get_history"

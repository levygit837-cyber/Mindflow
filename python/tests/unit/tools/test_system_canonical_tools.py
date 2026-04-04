import pytest

from mindflow_backend.agents.tools.system.shell_executor import ShellExecutorTool
from mindflow_backend.agents.tools.system.process_manager import ProcessManagerTool
from mindflow_backend.agents.tools.system.system_info import SystemInfoTool
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode
from mindflow_backend.security.policies.network_policy import NetworkAction


@pytest.mark.asyncio
async def test_system_info_tool_collects_requested_category() -> None:
    tool = SystemInfoTool()

    result = await tool.execute(info_type="software", include_sensitive=False)

    assert result["success"] is True
    assert "software" in result["result"]
    assert "python" in result["result"]["software"]


@pytest.mark.asyncio
async def test_process_manager_tool_allows_current_user(monkeypatch) -> None:
    monkeypatch.setenv("USER", "codex-user")
    tool = ProcessManagerTool()

    result = await tool.execute(action="list", filter_name="definitely-no-process-has-this-name")

    assert result["success"] is True
    assert result["result"]["count"] == 0


@pytest.mark.asyncio
async def test_shell_executor_tool_reports_semantic_metadata(tmp_path) -> None:
    tool = ShellExecutorTool()
    tool.root_dir = str(tmp_path)
    tool.sandbox_mode = SandboxMode.FULL

    result = await tool.execute(command="echo 'MindFlow'")

    assert result["success"] is True
    assert result["result"]["semantic_type"] == "system"
    assert result["result"]["security_level"] == "safe"


@pytest.mark.asyncio
async def test_shell_executor_tool_reports_search_semantics(tmp_path) -> None:
    tool = ShellExecutorTool()
    tool.root_dir = str(tmp_path)
    tool.sandbox_mode = SandboxMode.FULL

    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("MindFlow\n")

    result = await tool.execute(command="grep 'MindFlow' sample.txt")

    assert result["success"] is True
    assert result["result"]["semantic_type"] == "search"


class _FakeBackgroundTaskManager:
    def __init__(self) -> None:
        self.spawn_calls: list[dict[str, object]] = []
        self.status_calls: list[str] = []
        self.kill_calls: list[str] = []

    async def spawn(self, **kwargs):
        self.spawn_calls.append(kwargs)
        return type(
            "_Handle",
            (),
            {
                "background_task_id": "bg-123",
                "pid": 4567,
            },
        )()

    async def get_status(self, process_id: str):
        self.status_calls.append(process_id)
        return {
            "success": True,
            "background_task_id": process_id,
            "process_id": process_id,
            "pid": 4567,
            "status": "running",
        }

    async def kill(self, process_id: str):
        self.kill_calls.append(process_id)
        return {
            "success": True,
            "background_task_id": process_id,
            "process_id": process_id,
            "pid": 4567,
            "status": "killed",
        }


class _DenyNetworkPolicy:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate_command(self, command: str):
        self.calls.append(command)
        return NetworkAction.DENY, "Loopback access is forbidden"


class _AskNetworkPolicy:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate_command(self, command: str):
        self.calls.append(command)
        return NetworkAction.ASK, "External network access requires approval"


class _FakeSecurityLogger:
    def __init__(self) -> None:
        self.command_blocked_calls: list[dict[str, object]] = []
        self.network_blocked_calls: list[dict[str, object]] = []
        self.suspicious_activity_calls: list[dict[str, object]] = []

    def log_command_blocked(self, **kwargs) -> None:
        self.command_blocked_calls.append(kwargs)

    def log_network_blocked(self, **kwargs) -> None:
        self.network_blocked_calls.append(kwargs)

    def log_suspicious_activity(self, **kwargs) -> None:
        self.suspicious_activity_calls.append(kwargs)


@pytest.mark.asyncio
async def test_shell_executor_tool_supports_background_execution(tmp_path) -> None:
    manager = _FakeBackgroundTaskManager()
    tool = ShellExecutorTool(background_task_manager=manager)
    tool.root_dir = str(tmp_path)
    tool.sandbox_mode = SandboxMode.FULL

    result = await tool.execute(
        command="sleep 5",
        run_in_background=True,
        timeout=12,
        working_dir=".",
        session_id="session-1",
        task_id="task-1",
        tool_call_id="tool-call-1",
        description="Background shell test",
    )

    assert result["success"] is True
    assert result["result"]["background"] is True
    assert result["result"]["background_task_id"] == "bg-123"
    assert result["result"]["process_id"] == "bg-123"
    assert result["result"]["pid"] == 4567
    assert result["result"]["semantic_type"] == "system"
    assert result["result"]["security_level"] == "safe"
    assert len(manager.spawn_calls) == 1
    spawn_call = manager.spawn_calls[0]
    assert spawn_call["command"] == "sleep 5"
    assert spawn_call["cwd"] == str(tmp_path)
    assert spawn_call["description"] == "Background shell test"
    assert spawn_call["session_id"] == "session-1"
    assert spawn_call["task_id"] == "task-1"
    assert spawn_call["tool_call_id"] == "tool-call-1"
    assert isinstance(spawn_call["env"], dict)


@pytest.mark.asyncio
async def test_shell_executor_tool_exposes_background_lifecycle_methods() -> None:
    manager = _FakeBackgroundTaskManager()
    tool = ShellExecutorTool(background_task_manager=manager)

    status = await tool.get_background_status("bg-123")
    killed = await tool.kill_background_process("bg-123")

    assert status["success"] is True
    assert status["status"] == "running"
    assert killed["success"] is True
    assert killed["status"] == "killed"
    assert manager.status_calls == ["bg-123"]
    assert manager.kill_calls == ["bg-123"]


@pytest.mark.asyncio
async def test_shell_executor_tool_blocks_denied_network_and_audits() -> None:
    policy = _DenyNetworkPolicy()
    security_logger = _FakeSecurityLogger()
    tool = ShellExecutorTool(network_policy=policy, security_logger=security_logger)

    result = await tool.execute(command="curl http://127.0.0.1:8080/health")

    assert result["success"] is False
    assert result["error"] == "Network access denied: Loopback access is forbidden"
    assert policy.calls == ["curl http://127.0.0.1:8080/health"]
    assert security_logger.network_blocked_calls == [
        {
            "url": "",
            "reason": "Loopback access is forbidden",
            "command": "curl http://127.0.0.1:8080/health",
        }
    ]


@pytest.mark.asyncio
async def test_shell_executor_tool_routes_docker_requests_through_helper(monkeypatch, tmp_path) -> None:
    tool = ShellExecutorTool(network_policy=_AskNetworkPolicy(), security_logger=_FakeSecurityLogger())
    tool.root_dir = str(tmp_path)
    tool.sandbox_mode = SandboxMode.FULL

    monkeypatch.setattr(tool, "_can_use_docker", lambda: True)

    calls: list[dict[str, object]] = []

    async def _fake_execute_docker_foreground(**kwargs):
        calls.append(kwargs)
        return {
            "success": True,
            "stdout": "docker-path\n",
            "stderr": "",
            "exit_code": 0,
            "execution_time": 0.01,
            "sandbox_type": "docker",
        }

    monkeypatch.setattr(tool, "_execute_docker_foreground", _fake_execute_docker_foreground)

    result = await tool.execute(
        command="echo docker-path",
        use_docker=True,
        timeout=9,
        working_dir=".",
    )

    assert result["success"] is True
    assert result["result"]["output"] == "docker-path\n"
    assert result["result"]["sandbox_type"] == "docker"
    assert len(calls) == 1
    assert calls[0]["command"] == "echo docker-path"
    assert calls[0]["cwd"] == str(tmp_path)
    assert isinstance(calls[0]["env"], dict)

from __future__ import annotations

from mindflow_backend.agents.tools.system._shell_compat import (
    get_legacy_dangerous_command_error,
    normalize_legacy_shell_result,
    resolve_explicit_shell_working_dir,
)


def test_get_legacy_dangerous_command_error_blocks_known_pattern() -> None:
    error = get_legacy_dangerous_command_error("mkfs /dev/sda")

    assert error == {
        "success": False,
        "error": "Dangerous command pattern detected: mkfs",
        "error_code": "DANGEROUS_COMMAND",
        "command": "mkfs /dev/sda",
    }


def test_resolve_explicit_shell_working_dir_resolves_relative_path(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    resolved, error = resolve_explicit_shell_working_dir("workspace", root_dir=str(tmp_path))

    assert error is None
    assert resolved == str(workspace.resolve())


def test_normalize_legacy_shell_result_detects_command_not_found() -> None:
    normalized = normalize_legacy_shell_result(
        {
            "success": True,
            "output": "",
            "stderr": "missingcmd: not found",
            "return_code": 127,
            "timeout": False,
        },
        command="missingcmd",
        check_return_code=False,
    )

    assert normalized == {
        "success": False,
        "error": "missingcmd: not found",
        "error_code": "COMMAND_NOT_FOUND",
        "command": "missingcmd",
    }


def test_normalize_legacy_shell_result_applies_common_compatibility_shape() -> None:
    normalized = normalize_legacy_shell_result(
        {
            "success": True,
            "output": "hello\n...[truncated]",
            "stderr": "",
            "return_code": 1,
            "timeout": False,
        },
        command="echo hello",
        check_return_code=True,
    )

    assert normalized["success"] is False
    assert normalized["timed_out"] is False
    assert normalized["error_code"] == "EXECUTION_ERROR"
    assert normalized["output"].endswith("[output truncated]")
    assert normalized["command"] == "echo hello"

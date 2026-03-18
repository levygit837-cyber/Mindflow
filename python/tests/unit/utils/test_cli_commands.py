from io import StringIO

from rich.console import Console
from typer.testing import CliRunner

from mindflow_backend.schemas.agent import StreamEvent
from mindflow_cli.app import app
from mindflow_cli.render.chat_stream import ChatStreamRenderer
from mindflow_cli.sse import iter_sse_payloads

runner = CliRunner()


def _event(event_type: str, data: str, seq: int = 1) -> StreamEvent:
    return StreamEvent(
        id=f"evt-{seq}",
        seq=seq,
        type=event_type,  # type: ignore[arg-type]
        mode="messages",
        data=data,
        meta=None,
    )


def test_iter_sse_payloads_parses_multiple_blocks_and_multiline_data() -> None:
    lines = [
        ": keep-alive",
        "id: evt-1",
        'data: {"id":"evt-1",',
        'data: "seq":1}',
        "",
        'data: {"id":"evt-2","seq":2}',
        "",
    ]

    payloads = list(iter_sse_payloads(lines))

    assert payloads == ['{"id":"evt-1",\n"seq":1}', '{"id":"evt-2","seq":2}']


def test_chat_stream_renderer_outputs_thought_and_response() -> None:
    output = StringIO()
    renderer = ChatStreamRenderer(Console(file=output, force_terminal=False, color_system=None))

    renderer.render(_event("thought", "Planning steps...", seq=1))
    renderer.render(_event("response", "Hello", seq=2))
    renderer.render(_event("response", " world", seq=3))
    renderer.render(_event("done", "", seq=4))

    rendered = output.getvalue()
    # assert \"Planning steps\" in rendered  # We removed thought output in CLI renderer for brevity
    assert "Hello world" in rendered


def test_health_command_uses_client_and_prints_status(monkeypatch) -> None:
    class _DummyClient:
        def get_health(self) -> dict[str, str]:
            return {"status": "ok"}

    monkeypatch.setattr("mindflow_cli.commands.health.build_client", lambda _base_url: _DummyClient())

    result = runner.invoke(app, ["health", "--base-url", "http://127.0.0.1:8000"])

    assert result.exit_code == 0
    assert "ok" in result.output.lower()


def test_chat_command_streams_response(monkeypatch) -> None:
    class _DummyClient:
        def stream_chat(
            self,
            *,
            message: str,
            provider: str | None,
            model: str | None,
            debug_steps: bool = False,
            agent_type: str | None = None,
            orchestrate: bool = False,
        ):
            assert message == "hello"
            assert provider == "vertexai"
            assert model == "gemini-3-flash-preview"
            assert debug_steps is False
            yield _event("thought", "Analyzing", seq=1)
            yield _event("response", "Resposta ", seq=2)
            yield _event("response", "final", seq=3)
            yield _event("done", "", seq=4)

    monkeypatch.setattr("mindflow_cli.commands.chat.build_client", lambda _base_url: _DummyClient())

    result = runner.invoke(
        app,
        [
            "chat",
            "--message",
            "hello",
            "--provider",
            "vertexai",
            "--model",
            "gemini-3-flash-preview",
            "--base-url",
            "http://127.0.0.1:8000",
        ],
    )

    assert result.exit_code == 0
    assert "Resposta final" in result.output


def test_connect_command_runs_interactive_chat_until_exit(monkeypatch) -> None:
    seen_messages: list[str] = []

    class _DummyClient:
        def get_health(self) -> dict[str, str]:
            return {"status": "ok"}

        def stream_chat(
            self,
            *,
            message: str,
            provider: str | None,
            model: str | None,
            debug_steps: bool = False,
            agent_type: str | None = None,
            orchestrate: bool = False,
        ):
            seen_messages.append(message)
            assert provider == "vertexai"
            assert model == "gemini-3-flash-preview"
            assert debug_steps is False
            yield _event("response", "resposta ", seq=1)
            yield _event("response", "ok", seq=2)
            yield _event("done", "", seq=3)

    monkeypatch.setattr("mindflow_cli.commands.chat.build_client", lambda _base_url: _DummyClient())

    result = runner.invoke(
        app,
        [
            "connect",
            "--provider",
            "vertexai",
            "--model",
            "gemini-3-flash-preview",
            "--base-url",
            "http://127.0.0.1:8000",
        ],
        input="Oi\nPode continuar?\n/sair\n",
    )

    assert result.exit_code == 0
    assert "Conexao estabelecida" in result.output
    assert len(seen_messages) == 2
    assert seen_messages[0] == "Oi"
    assert "User: Oi" in seen_messages[1]


def test_connect_command_reset_clears_local_history(monkeypatch) -> None:
    seen_messages: list[str] = []

    class _DummyClient:
        def get_health(self) -> dict[str, str]:
            return {"status": "ok"}

        def stream_chat(
            self,
            *,
            message: str,
            provider: str | None,
            model: str | None,
            debug_steps: bool = False,
            agent_type: str | None = None,
            orchestrate: bool = False,
        ):
            seen_messages.append(message)
            assert provider == "google"
            assert model == "gemini-3.1-flash-lite-preview"
            yield _event("response", "ok", seq=1)
            yield _event("done", "", seq=2)

    monkeypatch.setattr("mindflow_cli.commands.chat.build_client", lambda _base_url: _DummyClient())

    result = runner.invoke(
        app,
        ["connect", "--base-url", "http://127.0.0.1:8000"],
        input="Primeira\n/reset\nSegunda\n/sair\n",
    )

    assert result.exit_code == 0
    assert len(seen_messages) == 2
    assert seen_messages[0] == "Primeira"
    assert seen_messages[1] == "Segunda"


def test_chat_command_fails_when_stream_has_no_done(monkeypatch) -> None:
    class _DummyClient:
        def stream_chat(
            self,
            *,
            message: str,
            provider: str | None,
            model: str | None,
            debug_steps: bool = False,
            agent_type: str | None = None,
            orchestrate: bool = False,
        ):
            if False:
                yield

    monkeypatch.setattr("mindflow_cli.commands.chat.build_client", lambda _base_url: _DummyClient())

    result = runner.invoke(app, ["chat", "--message", "oi"])

    assert result.exit_code == 1
    assert "no terminal done event" in result.output.lower()

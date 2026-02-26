from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict

from omnimind_agents import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    build_static_system_prompt,
    create_agent_chat_stream_normalizer,
    get_model_for_provider,
)
from omnimind_agents.deep_agent_config import create_omnimind_deep_agent


def _emit(event_type: str, data: str, mode: str, meta: Dict[str, Any] | None = None) -> None:
    payload = {
        "type": event_type,
        "data": data,
        "mode": mode,
        "meta": meta or {},
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


async def _iterate_stream(stream_obj: Any):
    if hasattr(stream_obj, "__aiter__"):
        async for item in stream_obj:
            yield item
        return

    if asyncio.iscoroutine(stream_obj):
        resolved = await stream_obj
        if hasattr(resolved, "__aiter__"):
            async for item in resolved:
                yield item
            return

    raise RuntimeError("Unsupported agent stream interface")


async def run() -> int:
    try:
        request = json.loads(sys.stdin.read() or "{}")
    except Exception as exc:
        _emit("error", f"Invalid JSON input: {exc}", "custom")
        return 1

    message = str(request.get("message", "")).strip()
    if not message:
        _emit("error", "Message is required", "custom")
        return 1

    provider = request.get("provider") or DEFAULT_PROVIDER
    model = request.get("model") or DEFAULT_MODEL
    conversation_id = request.get("conversationId") or "default"

    try:
        model_client = get_model_for_provider(provider, model)
        agent = create_omnimind_deep_agent(model=model_client, system_prompt=build_static_system_prompt())

        normalizer = create_agent_chat_stream_normalizer(
            provider=provider,
            emit=lambda event_type, data, mode, meta=None: _emit(event_type, data, mode, meta),
            emit_update_steps=True,
        )

        agent_stream = None
        if hasattr(agent, "astream"):
            agent_stream = agent.astream(
                {"messages": [{"role": "user", "content": message}]},
                {
                    "configurable": {"thread_id": conversation_id},
                    "stream_mode": ["messages", "updates", "values", "debug"],
                },
            )
        elif hasattr(agent, "stream"):
            agent_stream = agent.stream(
                {"messages": [{"role": "user", "content": message}]},
                {
                    "configurable": {"thread_id": conversation_id},
                    "stream_mode": ["messages", "updates", "values", "debug"],
                },
            )
        else:
            raise RuntimeError("Agent does not expose stream/astream")

        async for item in _iterate_stream(agent_stream):
            normalizer.process(item)

        normalizer.flush()
        _emit("done", "", "messages")
        return 0
    except Exception as exc:
        _emit("error", str(exc), "custom")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

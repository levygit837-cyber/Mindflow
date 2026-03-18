"""Shared runtime executor for explicit workflow steps."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
from mindflow_backend.agents.tools.base.tool_invocation import invoke_with_tools, stream_with_tools
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime import get_model_for_provider
from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode
from mindflow_backend.schemas.orchestration.workflow import WorkflowStep

_logger = get_logger(__name__)

ChunkDispatcher = Callable[[str], Awaitable[None]] | None
EventDispatcher = Callable[[str, dict[str, Any]], Awaitable[None]] | None


async def run_workflow_step(
    *,
    step: WorkflowStep,
    user_message: str,
    provider: str,
    model: str,
    session_id: str,
    folder_path: str | None = None,
    memory_context: str = "",
    memory_grounded: bool = False,
    conversation_history: list[dict[str, str]] | None = None,
    prior_context: str = "",
    chunk_dispatcher: ChunkDispatcher = None,
    event_dispatcher: EventDispatcher = None,
) -> dict[str, Any]:
    """Execute a single step using canonical agent identity resolution."""

    settings = get_settings()
    agent = get_agent(agent_id=step.agent_id)
    policy = get_agent_runtime_policy(agent_id=step.agent_id)

    messages: list[dict[str, str]] = [{"role": "system", "content": agent.system_prompt}]

    if memory_context.strip():
        messages.append(
            {
                "role": "system",
                "content": f"Memory Context (RAG from agent history):\n{memory_context}",
            }
        )
        if memory_grounded:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "MEMORY-GROUNDED TURN: responda primeiro usando o Memory Context. "
                        "Só use ferramentas se a memória for insuficiente ou ambígua."
                    ),
                }
            )

    if prior_context.strip():
        messages.append(
            {
                "role": "system",
                "content": f"Relevant context from previous workflow steps:\n{prior_context}",
            }
        )

    for item in conversation_history or []:
        messages.append({"role": item["role"], "content": item["content"]})

    messages.append(
        {
            "role": "user",
            "content": (
                f"OBJECTIVE: {step.objective or user_message}\n\n"
                f"STEP_ID: {step.step_id}\n"
                f"AGENT_ID: {step.agent_id}\n"
                f"SESSION_ID: {session_id or 'unknown'}\n\n"
                f"USER_REQUEST:\n{user_message}"
            ),
        }
    )

    sandbox_root = folder_path or getattr(agent, "root_dir", None) or getattr(settings, "working_path", None)
    sandbox = MindFlowSandbox(
        root_dir=sandbox_root,
        read_only=(agent.sandbox == SandboxMode.READ_ONLY),
    )
    registry = create_default_registry(sandbox, session_id=session_id)
    tools = registry.get_tools_for_agent(agent)

    if sandbox_root and tools:
        messages.insert(
            1,
            {
                "role": "system",
                "content": (
                    f"Your working directory (root_dir) is: {sandbox_root}\n"
                    "Use this path as the base for filesystem operations unless the user provides an absolute path."
                ),
            },
        )

    llm = get_model_for_provider(provider, model)

    try:
        if memory_grounded and tools and memory_context.strip():
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
            if not _needs_tool_follow_up(response_text):
                key_findings = response_text[:500] + "... [truncated]" if len(response_text) > 1000 else response_text
                return {
                    "agent_id": step.agent_id,
                    "agent_role": step.agent_role.value,
                    "specialist": step.specialist.value if step.specialist else None,
                    "status": "completed",
                    "key_findings": key_findings,
                    "full_output": response_text,
                    "error": None,
                }

        if tools:
            lc_tools = to_langchain_tools(tools)
            if lc_tools:
                llm_with_tools = llm.bind_tools(lc_tools)
                if chunk_dispatcher is not None:
                    response_text = await stream_with_tools(
                        llm=llm_with_tools,
                        messages=messages,
                        lc_tools=lc_tools,
                        chunk_dispatcher=chunk_dispatcher,
                        event_dispatcher=event_dispatcher,
                        max_iterations=policy.max_iterations,  # Use full iterations even with memory
                    )
                else:
                    response_text = await invoke_with_tools(
                        llm=llm_with_tools,
                        messages=messages,
                        lc_tools=lc_tools,
                        event_dispatcher=event_dispatcher,
                        max_iterations=policy.max_iterations,  # Use full iterations even with memory
                    )
            else:
                response = await llm.ainvoke(messages)
                response_text = response.content if hasattr(response, "content") else str(response)
        elif chunk_dispatcher is not None:
            full_response: list[str] = []
            async for chunk in llm.astream(messages):
                thought, texts = extract_chunk_parts(chunk)
                if thought and event_dispatcher is not None:
                    await event_dispatcher("agent_thought", {"thought": thought})
                for text in texts:
                    full_response.append(text)
                    await chunk_dispatcher(text)
            response_text = "".join(full_response)
        else:
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        _logger.error("workflow_step_failed", agent_id=step.agent_id, error=str(exc))
        return {
            "agent_id": step.agent_id,
            "agent_role": step.agent_role.value,
            "specialist": step.specialist.value if step.specialist else None,
            "status": "failed",
            "key_findings": "",
            "full_output": "",
            "error": str(exc),
        }

    key_findings = response_text[:500] + "... [truncated]" if len(response_text) > 1000 else response_text
    return {
        "agent_id": step.agent_id,
        "agent_role": step.agent_role.value,
        "specialist": step.specialist.value if step.specialist else None,
        "status": "completed",
        "key_findings": key_findings,
        "full_output": response_text,
        "error": None,
    }


def _needs_tool_follow_up(response_text: str) -> bool:
    normalized = (response_text or "").strip().lower()
    if not normalized:
        return True
    insufficiency_markers = (
        "não tenho contexto suficiente",
        "preciso investigar",
        "não encontrei",
        "não sei",
        "insufficient context",
        "need to inspect",
    )
    return any(marker in normalized for marker in insufficiency_markers)

import asyncio
import uuid
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage

from omnimind_backend.agents.normalizer import AgentChatStreamNormalizer
from omnimind_backend.agents.providers import get_model_for_provider
from omnimind_backend.agents.tools import search_web
from omnimind_backend.infra.config import get_settings
from omnimind_backend.schemas.agent import AgentChatRequest, StreamEvent, StreamEventMeta


SYSTEM_PROMPT = (
    "You are OmniMind, a pragmatic engineering assistant. "
    "Be concise, factual, and action-oriented. "
    "Always keep outputs clear and useful for software engineering context."
)


class AgentRuntime:
    async def stream_chat(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        settings = get_settings()
        provider = payload.provider or settings.default_provider
        model = payload.model or settings.default_model
        run_id = run_id or str(uuid.uuid4())

        normalizer = AgentChatStreamNormalizer(provider=provider, model=model, turn_run_id=session_id)
        seq = 0

        def next_seq() -> int:
            nonlocal seq
            seq += 1
            return seq

        yield normalizer.step_event(
            next_seq(),
            run_id=run_id,
            step_name="Analyze Request",
            detail="Parsing user intent and selecting execution strategy.",
            action="start",
            node="planner",
            node_category="LLM_INVOKE",
            user_visible=True,
        )
        yield normalizer.thought_event(next_seq(), "Analyzing request and preparing execution steps...", run_id=run_id)
        yield normalizer.step_event(
            next_seq(),
            run_id=run_id,
            step_name="Analyze Request",
            detail="Request analysis complete.",
            action="complete",
            node="planner",
            node_category="LLM_INVOKE",
            user_visible=True,
        )

        web_context = ""
        lower = payload.message.lower()
        should_search = any(token in lower for token in ["search", "latest", "news", "docs", "pesquise", "noticia"])

        if should_search:
            yield normalizer.step_event(
                next_seq(),
                run_id=run_id,
                step_name="Retrieve Context",
                detail="Running web retrieval for fresh context.",
                action="start",
                node="retrieval",
                node_category="TOOL_EXECUTION",
                user_visible=True,
            )

            tool_call_id = str(uuid.uuid4())
            yield normalizer.tool_call_event(
                next_seq(),
                tool_call_id=tool_call_id,
                name="search_web",
                args={"query": payload.message},
                run_id=run_id,
            )
            web_context = await search_web(payload.message)
            yield normalizer.tool_result_event(
                next_seq(),
                tool_call_id=tool_call_id,
                name="search_web",
                result=web_context,
                run_id=run_id,
            )

            yield normalizer.step_event(
                next_seq(),
                run_id=run_id,
                step_name="Retrieve Context",
                detail="Context retrieval complete.",
                action="complete",
                node="retrieval",
                node_category="TOOL_EXECUTION",
                user_visible=True,
            )

        yield normalizer.step_event(
            next_seq(),
            run_id=run_id,
            step_name="Synthesize Response",
            detail="Generating final answer.",
            action="start",
            node="response",
            node_category="LLM_INVOKE",
            user_visible=True,
        )

        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=payload.message)]
        if web_context:
            messages.append(HumanMessage(content=f"Web context:\n{web_context}"))

        assistant_text = ""
        try:
            llm = get_model_for_provider(provider, model)
            ai_message = await llm.ainvoke(messages)
            content = ai_message.content
            if isinstance(content, str):
                assistant_text = content
            elif isinstance(content, list):
                chunks: list[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        chunks.append(str(item.get("text", "")))
                    else:
                        chunks.append(str(item))
                assistant_text = "".join(chunks)
            else:
                assistant_text = str(content)

        except Exception as exc:
            yield StreamEvent(
                id=f"evt-{next_seq()}",
                seq=seq,
                type="error",
                mode="custom",
                data=str(exc),
                meta=StreamEventMeta(
                    provider=provider,
                    model=model,
                    runId=run_id,
                    turnRunId=session_id,
                    node="response",
                    nodeCategory="LLM_INVOKE",
                    userVisible=True,
                ),
            )
            yield StreamEvent(
                id=f"evt-{next_seq()}",
                seq=seq,
                type="done",
                mode="messages",
                data="",
                meta=StreamEventMeta(provider=provider, model=model, runId=run_id, turnRunId=session_id),
            )
            return

        if not assistant_text.strip():
            assistant_text = "No response generated."

        chunk_size = 64
        for index in range(0, len(assistant_text), chunk_size):
            piece = assistant_text[index : index + chunk_size]
            yield normalizer.response_event(next_seq(), piece, run_id=run_id)
            await asyncio.sleep(0)

        yield normalizer.step_event(
            next_seq(),
            run_id=run_id,
            step_name="Synthesize Response",
            detail="Final response delivered.",
            action="complete",
            node="response",
            node_category="LLM_INVOKE",
            user_visible=True,
        )

        yield StreamEvent(
            id=f"evt-{next_seq()}",
            seq=seq,
            type="done",
            mode="messages",
            data="",
            meta=StreamEventMeta(provider=provider, model=model, runId=run_id, turnRunId=session_id),
        )

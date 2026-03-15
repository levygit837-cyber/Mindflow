import json
from typing import Any

from mindflow_backend.runtime.output_categorizer import categorize_output
from mindflow_backend.runtime.stream_event_queue import StreamEventQueue
from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta


class AgentChatStreamNormalizer:
    def __init__(self, provider: str, model: str, turn_run_id: str | None = None) -> None:
        self.provider = provider
        self.model = model
        self.turn_run_id = turn_run_id
        self.event_queue = StreamEventQueue()

    def _meta(
        self,
        *,
        run_id: str | None,
        node: str | None = None,
        node_label: str | None = None,
        node_category: str | None = None,
        user_visible: bool | None = None,
        tool_call_id: str | None = None,
        status: str | None = None,
        extra_meta: dict[str, Any] | None = None,
    ) -> StreamEventMeta:
        meta = StreamEventMeta(
            runId=run_id,
            turnRunId=self.turn_run_id,
            node=node,
            nodeLabel=node_label,
            nodeCategory=node_category,
            userVisible=user_visible,
            toolCallId=tool_call_id,
            provider=self.provider,
            model=self.model,
            status=status,  # type: ignore[arg-type]
        )
        if extra_meta:
            for key, value in extra_meta.items():
                if hasattr(meta, key):
                    setattr(meta, key, value)
        return meta

    def response_event(
        self,
        seq: int,
        data: str,
        *,
        run_id: str | None = None,
        node: str | None = "agent_response",
        extra_meta: dict[str, Any] | None = None,
    ) -> StreamEvent:
        meta = self._meta(
            run_id=run_id, 
            node=node, 
            node_label="Response", 
            node_category="LLM_INVOKE", 
            user_visible=True,
            extra_meta=extra_meta
        )
        meta.category = categorize_output(data)

        if self.turn_run_id and not self.event_queue.has_first_response_marker():
            marker = self.event_queue.set_first_response_marker(self.turn_run_id)
            meta.firstResponseMarker = marker

        return StreamEvent(
            id=f"evt-{seq}",
            seq=seq,
            type="response",
            mode="messages",
            data=data,
            meta=meta,
        )

    def thought_event(
        self, 
        seq: int, 
        data: str, 
        *, 
        run_id: str | None = None,
        extra_meta: dict[str, Any] | None = None,
    ) -> StreamEvent:
        return StreamEvent(
            id=f"evt-{seq}",
            seq=seq,
            type="thought",
            mode="messages",
            data=data,
            meta=self._meta(
                run_id=run_id,
                node="agent_thinking",
                node_label="Thinking",
                node_category="LLM_INVOKE",
                user_visible=True,
                extra_meta=extra_meta,
            ),
        )

    def step_event(
        self,
        seq: int,
        *,
        run_id: str | None,
        step_name: str,
        detail: str,
        action: str,
        node: str,
        node_category: str,
        user_visible: bool,
        extra_meta: dict[str, Any] | None = None,
    ) -> StreamEvent:
        return StreamEvent(
            id=f"evt-{seq}",
            seq=seq,
            type="agent_step",
            mode="updates",
            data=json.dumps(
                {
                    "stepName": step_name,
                    "detail": detail,
                    "action": action,
                }
            ),
            meta=self._meta(
                run_id=run_id,
                node=node,
                node_label=step_name,
                node_category=node_category,
                user_visible=user_visible,
                status="update",
                extra_meta=extra_meta,
            ),
        )

    def tool_call_event(
        self,
        seq: int,
        tool_call_id: str,
        name: str,
        args: dict[str, Any],
        *,
        run_id: str | None = None,
        extra_meta: dict[str, Any] | None = None,
    ) -> StreamEvent:
        return StreamEvent(
            id=f"evt-{seq}",
            seq=seq,
            type="tool_call",
            mode="updates",
            data=json.dumps({"id": tool_call_id, "name": name, "args": args}),
            meta=self._meta(
                run_id=run_id,
                node="tool_call",
                node_label=name,
                node_category="TOOL_EXECUTION",
                user_visible=True,
                tool_call_id=tool_call_id,
                status="start",
                extra_meta=extra_meta,
            ),
        )

    def tool_result_event(
        self,
        seq: int,
        tool_call_id: str,
        name: str,
        result: str,
        *,
        run_id: str | None = None,
        extra_meta: dict[str, Any] | None = None,
    ) -> StreamEvent:
        return StreamEvent(
            id=f"evt-{seq}",
            seq=seq,
            type="tool_result",
            mode="updates",
            data=json.dumps({"id": tool_call_id, "name": name, "result": result}),
            meta=self._meta(
                run_id=run_id,
                node="tool_result",
                node_label=name,
                node_category="TOOL_EXECUTION",
                user_visible=True,
                tool_call_id=tool_call_id,
                status="end",
                extra_meta=extra_meta,
            ),
        )

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .node_registry import NodeCategory, classify_node, get_node_label, is_streamable_node
from .output_categorizer import categorize_output
from .stream_event_queue import StreamEventQueue

MetaDict = Dict[str, Any]
EmitFn = Callable[[str, str, str, Optional[MetaDict]], None]


@dataclass
class StreamTuple:
    mode: str
    payload: Any
    path: Optional[List[str]] = None


def is_record(value: Any) -> bool:
    return isinstance(value, dict)


def as_record(value: Any) -> Optional[Dict[str, Any]]:
    return value if is_record(value) else None


def safe_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def is_gemini_provider(provider: str) -> bool:
    return provider in {"google", "vertexai"}


def truncate_for_ui(value: str, limit: int = 2000) -> str:
    return value if len(value) <= limit else value[:limit] + "..."


def title_case(value: str) -> str:
    if not value:
        return "Tool"
    normalized = re.sub(r"[_-]+", " ", value).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return re.sub(r"\b\w", lambda m: m.group(0).upper(), normalized)


def normalize_tool_name(value: Any) -> str:
    name = safe_string(value).strip()
    if not name or name.lower() == "unknown":
        return "tool"
    return name


def serialize_args(args: Any) -> Dict[str, Any]:
    if is_record(args):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            if is_record(parsed):
                return parsed
            return {"value": parsed}
        except Exception:
            return {"value": args}
    if args is None:
        return {}
    return {"value": args}


def extract_nested_reasoning(value: Any, depth: int = 0) -> str:
    if depth > 4 or value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [extract_nested_reasoning(item, depth + 1) for item in value]
        return "\n".join([p for p in parts if p])
    if not is_record(value):
        return ""

    for key in ["thinking", "reasoning", "summary", "text", "content", "value"]:
        if key in value:
            nested = extract_nested_reasoning(value[key], depth + 1)
            if nested:
                return nested

    for nested_value in value.values():
        nested = extract_nested_reasoning(nested_value, depth + 1)
        if nested:
            return nested
    return ""


def content_block_text(block: Dict[str, Any]) -> Tuple[str, str]:
    block_type = safe_string(block.get("type")).lower()
    text_obj = as_record(block.get("text"))
    reasoning_obj = as_record(block.get("reasoning"))

    text = ""
    if isinstance(block.get("text"), str):
        text = block["text"]
    elif text_obj and isinstance(text_obj.get("value"), str):
        text = text_obj["value"]
    elif isinstance(block.get("value"), str):
        text = block["value"]
    elif isinstance(block.get("content"), str):
        text = block["content"]

    nested = extract_nested_reasoning(block.get("thinking") or block.get("reasoning") or block.get("summary"))
    non_std = extract_nested_reasoning(block.get("value")) if block_type == "non_standard" else ""

    thought = ""
    if isinstance(block.get("thinking"), str):
        thought = block["thinking"]
    elif isinstance(block.get("reasoning"), str):
        thought = block["reasoning"]
    elif reasoning_obj and isinstance(reasoning_obj.get("content"), str):
        thought = reasoning_obj["content"]
    elif isinstance(block.get("summary"), str):
        thought = block["summary"]
    else:
        thought = nested or non_std or (text if block_type in {"thinking", "reasoning"} else "")

    if "reasoning" in block_type or "thinking" in block_type:
        return "", thought or text
    if block_type in {"text", "output_text", "response_text"} or (not block_type and text):
        return text, ""
    if thought:
        return "", thought
    return "", ""


def extract_text_and_thought(content: Any) -> Tuple[str, str]:
    if isinstance(content, str):
        return content, ""
    if is_record(content):
        return content_block_text(content)
    if not isinstance(content, list):
        return "", ""

    text = ""
    thought = ""
    for item in content:
        if not is_record(item):
            continue
        t, th = content_block_text(item)
        text += t
        thought += th
    return text, thought


def message_kind(message: Dict[str, Any]) -> str:
    msg_type = safe_string(message.get("type")).lower()
    if msg_type == "ai" or "aimessage" in msg_type:
        return "ai"
    if msg_type == "tool" or "toolmessage" in msg_type:
        return "tool"

    ctor = safe_string(as_record(message.get("constructor") or {}) and message["constructor"].get("name")).lower()
    if "aimessage" in ctor:
        return "ai"
    if "toolmessage" in ctor:
        return "tool"
    return "other"


def extract_tool_calls_from_message(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    seen = set()
    message_id = safe_string(message.get("id")).strip() or "msg"

    def push_call(call_id: str, name: str, args: Dict[str, Any]) -> None:
        key = f"{call_id}:{name}:{json.dumps(args, sort_keys=True)}"
        if key in seen:
            return
        seen.add(key)
        calls.append({"id": call_id, "name": name, "args": args})

    from_tool_calls = message.get("tool_calls")
    if isinstance(from_tool_calls, list):
        for idx, tc in enumerate(from_tool_calls):
            item = as_record(tc)
            if not item:
                continue
            call_id = safe_string(item.get("id")).strip() or f"{message_id}-tool-{idx}"
            name = normalize_tool_name(item.get("name"))
            args = serialize_args(item.get("args"))
            push_call(call_id, name, args)

    from_chunks = message.get("tool_call_chunks")
    if isinstance(from_chunks, list):
        for tc in from_chunks:
            item = as_record(tc)
            if not item:
                continue
            call_id = safe_string(item.get("id")).strip()
            name = normalize_tool_name(item.get("name"))
            if not call_id or name == "tool":
                continue
            push_call(call_id, name, serialize_args(item.get("args")))

    kwargs = as_record(message.get("additional_kwargs"))
    raw_calls = kwargs.get("tool_calls") if kwargs else None
    if isinstance(raw_calls, list):
        for idx, tc in enumerate(raw_calls):
            item = as_record(tc)
            if not item:
                continue
            fn = as_record(item.get("function"))
            call_id = safe_string(item.get("id")).strip() or f"{message_id}-raw-tool-{idx}"
            name = normalize_tool_name((fn or {}).get("name") or item.get("name"))
            args = serialize_args((fn or {}).get("arguments") or item.get("args"))
            push_call(call_id, name, args)

    content = message.get("content")
    if isinstance(content, list):
        for idx, raw in enumerate(content):
            block = as_record(raw)
            if not block:
                continue
            block_type = safe_string(block.get("type")).lower()
            if block_type not in {"tool_use", "server_tool_use", "tool_call"}:
                continue
            call_id = safe_string(block.get("id")).strip() or f"{message_id}-block-tool-{idx}"
            name = normalize_tool_name(block.get("name"))
            args = serialize_args(block.get("input") or block.get("args"))
            push_call(call_id, name, args)

    return calls


def collect_messages_from_update(update: Any) -> List[Dict[str, Any]]:
    if not is_record(update):
        return []
    messages = update.get("messages")
    if not isinstance(messages, list):
        return []
    return [m for m in messages if is_record(m)]


def tool_result_text(message: Dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return truncate_for_ui(content)
    if isinstance(content, list):
        joined_parts = []
        for block in content:
            if not is_record(block):
                continue
            if isinstance(block.get("text"), str):
                joined_parts.append(block["text"])
            elif isinstance(block.get("content"), str):
                joined_parts.append(block["content"])
            else:
                joined_parts.append(json.dumps(block, ensure_ascii=False))
        joined = "\n".join(joined_parts).strip()
        if joined:
            return truncate_for_ui(joined)
    if content is not None:
        return truncate_for_ui(json.dumps(content, ensure_ascii=False))
    return "Done"


VALID_STREAM_MODES = {"messages", "updates", "custom", "values", "debug"}


def parse_stream_tuple(item: Any) -> Optional[StreamTuple]:
    if not isinstance(item, list):
        return None

    if len(item) == 2:
        first, second = item
        if isinstance(first, str) and first in VALID_STREAM_MODES:
            return StreamTuple(mode=first, payload=second)

        if isinstance(first, list) and isinstance(second, list) and len(second) == 2:
            return StreamTuple(mode="messages", payload=second, path=[str(x) for x in first])

        return StreamTuple(mode="messages", payload=item)

    if len(item) == 3 and isinstance(item[0], list) and isinstance(item[1], str):
        return StreamTuple(mode=item[1], payload=item[2], path=[str(x) for x in item[0]])

    return None


def split_gemini_think_tags(text: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    cursor = 0
    while cursor < len(text):
        open_idx = text.find("<think>", cursor)
        if open_idx == -1:
            tail = text[cursor:]
            if tail:
                out.append({"type": "response", "text": tail})
            break

        before = text[cursor:open_idx]
        if before:
            out.append({"type": "response", "text": before})

        think_start = open_idx + len("<think>")
        close_idx = text.find("</think>", think_start)
        if close_idx == -1:
            thought_tail = text[think_start:]
            if thought_tail:
                out.append({"type": "thought", "text": thought_tail})
            break

        thought = text[think_start:close_idx]
        if thought:
            out.append({"type": "thought", "text": thought})
        cursor = close_idx + len("</think>")

    return out


class ThinkTagParser:
    def __init__(self, send: Callable[[str, str, str], None]) -> None:
        self.send = send
        self.inside_think = False
        self.tag_buffer = ""

    def push(self, text: str) -> None:
        for ch in text:
            self.tag_buffer += ch
            if self.inside_think:
                close_tag = "</think>"
                if self.tag_buffer.endswith(close_tag):
                    content = self.tag_buffer[: -len(close_tag)]
                    if content:
                        self.send("thought", content, "messages")
                    self.tag_buffer = ""
                    self.inside_think = False
                elif len(self.tag_buffer) > len(close_tag):
                    safe = self.tag_buffer[: len(self.tag_buffer) - len(close_tag) + 1]
                    self.send("thought", safe, "messages")
                    self.tag_buffer = self.tag_buffer[len(safe) :]
            else:
                open_tag = "<think>"
                if self.tag_buffer.endswith(open_tag):
                    before = self.tag_buffer[: -len(open_tag)]
                    if before:
                        self.send("response", before, "messages")
                    self.tag_buffer = ""
                    self.inside_think = True
                elif len(self.tag_buffer) > len(open_tag):
                    safe = self.tag_buffer[: len(self.tag_buffer) - len(open_tag) + 1]
                    self.send("response", safe, "messages")
                    self.tag_buffer = self.tag_buffer[len(safe) :]

    def flush(self) -> None:
        if not self.tag_buffer:
            return
        self.send("thought" if self.inside_think else "response", self.tag_buffer, "messages")
        self.tag_buffer = ""


def extract_message_text_and_thought(message: Dict[str, Any]) -> Tuple[str, str]:
    parsed = extract_text_and_thought(message.get("content"))
    if parsed[0] or parsed[1]:
        return parsed

    maybe_content_blocks = message.get("contentBlocks")
    if maybe_content_blocks is not None:
        parsed = extract_text_and_thought(maybe_content_blocks)
        if parsed[0] or parsed[1]:
            return parsed

    lc_kwargs = as_record(message.get("lc_kwargs"))
    if lc_kwargs and "content" in lc_kwargs:
        parsed = extract_text_and_thought(lc_kwargs.get("content"))
        if parsed[0] or parsed[1]:
            return parsed

    if isinstance(message.get("text"), str):
        return message["text"], ""
    return "", ""


def extract_additional_kwargs(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    direct = as_record(message.get("additional_kwargs"))
    if direct:
        return direct
    lc_kwargs = as_record(message.get("lc_kwargs"))
    if lc_kwargs:
        return as_record(lc_kwargs.get("additional_kwargs"))
    return None


def unwrap_message_like(message: Dict[str, Any]) -> Dict[str, Any]:
    if message_kind(message) != "other":
        return message
    nested = as_record(message.get("message"))
    if nested and message_kind(nested) != "other":
        return nested
    return message


class ChatStreamNormalizer:
    def __init__(
        self,
        provider: str,
        emit: EmitFn,
        emit_update_steps: bool = True,
        current_turn_run_id: Optional[str] = None,
    ) -> None:
        self.provider = provider
        self.emit = emit
        self.emit_update_steps = emit_update_steps
        self.use_think_parser = is_gemini_provider(provider)
        self.has_message_response_output = False
        self.has_message_thought_output = False
        self.emitted_update_ai_messages = set()
        self.seen_tool_calls = set()
        self.seen_tool_results = set()
        self.pending_tools: Dict[str, Dict[str, Any]] = {}
        self.pending_by_name: Dict[str, List[str]] = {}
        self.current_turn_run_id = current_turn_run_id
        self.event_queue = StreamEventQueue()
        self.think_parser = ThinkTagParser(self._emit_think_event) if self.use_think_parser else None

    def _emit_think_event(self, event_type: str, data: str, mode: str) -> None:
        self.emit_event(event_type, data, mode, {})

    def emit_event(self, event_type: str, data: str, mode: str, meta: Optional[MetaDict] = None) -> None:
        if meta is None:
            meta = {}
        if mode == "messages" and event_type == "response":
            self.has_message_response_output = True
        if mode == "messages" and event_type == "thought":
            self.has_message_thought_output = True
        self.emit(event_type, data, mode, meta)

    def collect_kw_thoughts(self, kwargs: Optional[Dict[str, Any]]) -> List[str]:
        if not kwargs:
            return []
        thoughts: List[str] = []

        thinking = kwargs.get("thinking")
        if isinstance(thinking, str) and thinking:
            thoughts.append(thinking)
        elif thinking:
            nested = extract_nested_reasoning(thinking)
            if nested:
                thoughts.append(nested)

        for key in ["reasoning", "reasoning_content", "reasoningContent"]:
            if kwargs.get(key):
                nested = extract_nested_reasoning(kwargs[key])
                if nested:
                    thoughts.append(nested)

        return thoughts

    def push_pending(self, call_id: str, name: str, args: Dict[str, Any]) -> None:
        self.pending_tools[call_id] = {"name": name, "args": args}
        queue = self.pending_by_name.get(name, [])
        queue.append(call_id)
        self.pending_by_name[name] = queue

    def pop_pending_by_name(self, name: str) -> Optional[str]:
        queue = self.pending_by_name.get(name)
        if not queue:
            return None
        call_id = queue.pop(0)
        if queue:
            self.pending_by_name[name] = queue
        else:
            self.pending_by_name.pop(name, None)
        return call_id

    def remove_pending_by_id(self, name: str, call_id: str) -> None:
        queue = self.pending_by_name.get(name)
        if not queue:
            return
        filtered = [item for item in queue if item != call_id]
        if filtered:
            self.pending_by_name[name] = filtered
        else:
            self.pending_by_name.pop(name, None)

    def emit_text(self, text: str, mode: str, meta: Dict[str, Any]) -> None:
        if not text:
            return

        def enrich_response_meta(base_meta: Dict[str, Any]) -> Dict[str, Any]:
            enriched = dict(base_meta)
            enriched["category"] = categorize_output(text)
            if self.current_turn_run_id and not self.event_queue.has_first_response_marker():
                marker = self.event_queue.set_first_response_marker(self.current_turn_run_id)
                enriched["firstResponseMarker"] = marker
            return enriched

        if not self.use_think_parser:
            self.emit_event("response", text, mode, enrich_response_meta(meta))
            return

        if mode == "messages":
            assert self.think_parser is not None
            self.think_parser.push(text)
            return

        split = split_gemini_think_tags(text)
        if not split:
            self.emit_event("response", text, mode, enrich_response_meta(meta))
            return

        for part in split:
            if part["type"] == "response":
                self.emit_event(part["type"], part["text"], mode, enrich_response_meta(meta))
            else:
                self.emit_event(part["type"], part["text"], mode, meta)

    def emit_tool_calls_from_ai_message(
        self, message: Dict[str, Any], mode: str, node: str, path: Optional[List[str]] = None
    ) -> None:
        for tc in extract_tool_calls_from_message(message):
            if tc["id"] in self.seen_tool_calls:
                continue
            self.seen_tool_calls.add(tc["id"])
            self.push_pending(tc["id"], tc["name"], tc["args"])
            meta = {"node": node, "toolCallId": tc["id"], "path": path}
            data = json.dumps({"id": tc["id"], "name": tc["name"], "args": tc["args"]}, ensure_ascii=False)
            if mode == "updates":
                self.event_queue.enqueue("tool_call", data, mode, meta, True)
            else:
                self.emit_event("tool_call", data, mode, meta)

    def emit_tool_result_from_tool_message(
        self, message: Dict[str, Any], mode: str, node: str, path: Optional[List[str]] = None
    ) -> None:
        tool_call_id = safe_string(message.get("tool_call_id")).strip()
        tool_name = normalize_tool_name(message.get("name"))

        if not tool_call_id and tool_name and tool_name != "tool":
            maybe_id = self.pop_pending_by_name(tool_name)
            if maybe_id:
                tool_call_id = maybe_id

        if (not tool_name or tool_name == "tool") and tool_call_id:
            pending = self.pending_tools.get(tool_call_id)
            if pending and pending.get("name"):
                tool_name = pending["name"]

        if not tool_call_id:
            tool_call_id = f"tool-result-{random.random():.10f}".replace("0.", "")

        if tool_call_id in self.seen_tool_results:
            return
        self.seen_tool_results.add(tool_call_id)

        pending = self.pending_tools.pop(tool_call_id, None)
        resolved_name = (pending or {}).get("name") or tool_name or "tool"
        self.remove_pending_by_id(resolved_name, tool_call_id)

        result = tool_result_text(message)
        meta = {"node": node, "toolCallId": tool_call_id, "path": path}
        data = json.dumps({"id": tool_call_id, "name": resolved_name, "result": result}, ensure_ascii=False)
        if mode == "updates":
            self.event_queue.enqueue("tool_result", data, mode, meta, False)
        else:
            self.emit_event("tool_result", data, mode, meta)

    def emit_ai_fallback_from_update(
        self, message: Dict[str, Any], node: str, path: Optional[List[str]] = None
    ) -> None:
        msg_id = safe_string(message.get("id")) or "no-id"
        text, thought = extract_message_text_and_thought(message)
        kwargs = extract_additional_kwargs(message)
        kw_thoughts = self.collect_kw_thoughts(kwargs)

        fallback_thoughts = [] if self.has_message_thought_output else [x for x in [thought, *kw_thoughts] if x]
        fallback_text = "" if self.has_message_response_output else text

        if not fallback_thoughts and not fallback_text:
            return

        signature = f"{msg_id}|{'\\n'.join(fallback_thoughts)}|{fallback_text}"
        if signature in self.emitted_update_ai_messages:
            return
        self.emitted_update_ai_messages.add(signature)

        meta = {"node": node, "path": path}
        for thought_item in fallback_thoughts:
            self.emit_event("thought", thought_item, "updates", meta)
        if fallback_text:
            self.emit_text(fallback_text, "updates", meta)

    def process_message_mode(self, payload: Any, path: Optional[List[str]] = None) -> None:
        if not isinstance(payload, list) or len(payload) != 2:
            return
        raw_message, raw_metadata = payload
        metadata = as_record(raw_metadata) or {}

        event_run_id = safe_string(metadata.get("run_id"))
        if event_run_id and not self.current_turn_run_id:
            self.current_turn_run_id = event_run_id
            self.event_queue.reset()

        if self.current_turn_run_id and event_run_id and event_run_id != self.current_turn_run_id:
            return

        if isinstance(raw_message, str):
            node = safe_string(metadata.get("langgraph_node"))
            meta = {
                "node": node,
                "runId": event_run_id,
                "turnRunId": self.current_turn_run_id,
                "path": path,
            }
            self.emit_text(raw_message, "messages", meta)
            return

        message_record = as_record(raw_message)
        if not message_record:
            return
        message = unwrap_message_like(message_record)

        node = safe_string(metadata.get("langgraph_node"))
        meta = {
            "node": node,
            "runId": event_run_id,
            "turnRunId": self.current_turn_run_id,
            "path": path,
        }

        kind = message_kind(message)
        if kind == "ai":
            text, thought = extract_message_text_and_thought(message)
            kwargs = extract_additional_kwargs(message)
            if thought:
                self.emit_event("thought", thought, "messages", meta)
            for kw in self.collect_kw_thoughts(kwargs):
                self.emit_event("thought", kw, "messages", meta)
            if text:
                self.emit_text(text, "messages", meta)
            self.emit_tool_calls_from_ai_message(message, "messages", node, path)
            return

        if kind == "tool":
            self.emit_tool_result_from_tool_message(message, "messages", node, path)

    def process_updates_mode(self, payload: Any, path: Optional[List[str]] = None) -> None:
        if not is_record(payload):
            return

        for node_name, node_update in payload.items():
            if self.emit_update_steps and is_streamable_node(node_name):
                label = get_node_label(node_name)
                category = classify_node(node_name)
                step_payload = json.dumps(
                    {
                        "stepName": label,
                        "detail": f"Node: {node_name} [{category.value}]",
                        "action": "start",
                    },
                    ensure_ascii=False,
                )
                self.emit_event(
                    "agent_step",
                    step_payload,
                    "updates",
                    {"node": node_name, "nodeCategory": category.value, "path": path},
                )

            update_messages = collect_messages_from_update(node_update)
            for message in update_messages:
                kind = message_kind(message)
                if kind == "ai":
                    self.emit_tool_calls_from_ai_message(message, "updates", node_name, path)
                    self.emit_ai_fallback_from_update(message, node_name, path)
                elif kind == "tool":
                    self.emit_tool_result_from_tool_message(message, "updates", node_name, path)

    def process_custom_mode(self, payload: Any, path: Optional[List[str]] = None) -> None:
        data = payload if is_record(payload) else {"value": payload}
        label = (
            data.get("event")
            if isinstance(data.get("event"), str)
            else data.get("type")
            if isinstance(data.get("type"), str)
            else "custom"
        )
        self.emit_event(
            "step",
            f"Custom: {title_case(label)}",
            "custom",
            {"node": safe_string(data.get("node")), "path": path},
        )

    def process(self, item: Any) -> None:
        tuple_data = parse_stream_tuple(item)
        if not tuple_data:
            return

        if tuple_data.mode == "messages":
            self.process_message_mode(tuple_data.payload, tuple_data.path)
        elif tuple_data.mode == "updates":
            self.process_updates_mode(tuple_data.payload, tuple_data.path)
        elif tuple_data.mode == "custom":
            self.process_custom_mode(tuple_data.payload, tuple_data.path)

    def flush(self) -> None:
        if self.think_parser:
            self.think_parser.flush()
        self.event_queue.drain(self.emit_event)


def create_agent_chat_stream_normalizer(
    provider: str,
    emit: EmitFn,
    emit_update_steps: bool = True,
    current_turn_run_id: Optional[str] = None,
) -> ChatStreamNormalizer:
    return ChatStreamNormalizer(
        provider=provider,
        emit=emit,
        emit_update_steps=emit_update_steps,
        current_turn_run_id=current_turn_run_id,
    )

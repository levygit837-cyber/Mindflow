import type {
  LLMProvider,
  OutputCategory,
  StreamEvent,
  StreamEventType,
  StreamModeName,
} from "@/types/agent";
import { classifyNode, getNodeLabel, isStreamableNode, NodeCategory } from "./node-registry";
import { categorizeOutput } from "./output-categorizer";
import { StreamEventQueue } from "./stream-event-queue";

type UnknownRecord = Record<string, unknown>;

interface NormalizedToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
}

export interface StreamTuple {
  mode: StreamModeName;
  payload: unknown;
  path?: string[];
}

export interface ChatStreamNormalizerOptions {
  provider: LLMProvider;
  emitUpdateSteps?: boolean;
  emit: (
    type: StreamEventType,
    data: string,
    mode: StreamModeName,
    meta?: StreamEvent["meta"]
  ) => void;
  /** Optional: pass the run_id of the current turn to filter out replayed messages.
   *  If omitted, the normalizer auto-detects it from the first run_id seen in messages mode. */
  currentTurnRunId?: string;
}

export interface ChatStreamNormalizer {
  process: (item: unknown) => void;
  flush: () => void;
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asRecord(value: unknown): UnknownRecord | undefined {
  return isRecord(value) ? value : undefined;
}

function safeString(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  return String(value);
}

function isGeminiProvider(provider: string): boolean {
  return provider === "google" || provider === "vertexai";
}

function truncateForUI(value: string, limit = 2000): string {
  return value.length <= limit ? value : `${value.slice(0, limit)}...`;
}

function titleCase(value: string): string {
  if (!value) return "Tool";
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function normalizeToolName(value: unknown): string {
  const name = safeString(value).trim();
  if (!name || name.toLowerCase() === "unknown") return "tool";
  return name;
}

function serializeArgs(args: unknown): Record<string, unknown> {
  if (isRecord(args)) return args;

  if (typeof args === "string") {
    try {
      const parsed = JSON.parse(args) as unknown;
      return isRecord(parsed) ? parsed : { value: parsed };
    } catch {
      return { value: args };
    }
  }

  if (args == null) return {};
  return { value: args };
}

function contentBlockText(block: UnknownRecord): { text: string; thought: string } {
  const type = safeString(block.type).toLowerCase();

  const textObj = asRecord(block.text);
  const reasoningObj = asRecord(block.reasoning);

  const text =
    typeof block.text === "string"
      ? block.text
      : typeof textObj?.value === "string"
        ? textObj.value
        : typeof block.value === "string"
          ? block.value
          : typeof block.content === "string"
            ? block.content
            : "";

  const nestedThought = extractNestedReasoning(block.thinking ?? block.reasoning ?? block.summary);
  const nonStandardThought = type === "non_standard" ? extractNestedReasoning(block.value) : "";
  const thought =
    typeof block.thinking === "string"
      ? block.thinking
      : typeof block.reasoning === "string"
        ? block.reasoning
        : typeof reasoningObj?.content === "string"
          ? reasoningObj.content
          : typeof block.summary === "string"
            ? block.summary
            : nestedThought || nonStandardThought || (type === "thinking" || type === "reasoning" ? text : "");

  if (type.includes("reasoning") || type.includes("thinking")) {
    return { text: "", thought: thought || text };
  }

  if (type === "text" || type === "output_text" || type === "response_text" || (!type && text)) {
    return { text, thought: "" };
  }

  if (thought) return { text: "", thought };
  return { text: "", thought: "" };
}

function extractTextAndThought(content: unknown): { text: string; thought: string } {
  if (typeof content === "string") {
    return { text: content, thought: "" };
  }

  if (isRecord(content)) {
    return contentBlockText(content);
  }

  if (!Array.isArray(content)) {
    return { text: "", thought: "" };
  }

  let text = "";
  let thought = "";

  for (const item of content) {
    if (!isRecord(item)) continue;
    const part = contentBlockText(item);
    text += part.text;
    thought += part.thought;
  }

  return { text, thought };
}

function extractNestedReasoning(value: unknown, depth = 0): string {
  if (depth > 4 || value == null) return "";

  if (typeof value === "string") return value;

  if (Array.isArray(value)) {
    return value
      .map((item) => extractNestedReasoning(item, depth + 1))
      .filter(Boolean)
      .join("\n");
  }

  if (!isRecord(value)) return "";

  const preferredKeys = [
    "thinking",
    "reasoning",
    "summary",
    "text",
    "content",
    "value",
  ];

  for (const key of preferredKeys) {
    if (!(key in value)) continue;
    const nested = extractNestedReasoning(value[key], depth + 1);
    if (nested) return nested;
  }

  for (const nestedValue of Object.values(value)) {
    const nested = extractNestedReasoning(nestedValue, depth + 1);
    if (nested) return nested;
  }

  return "";
}

function messageKind(message: UnknownRecord): "ai" | "tool" | "other" {
  const type = safeString(message.type).toLowerCase();
  if (type === "ai" || type.includes("aimessage")) return "ai";
  if (type === "tool" || type.includes("toolmessage")) return "tool";

  const ctorName = safeString((message as { constructor?: { name?: string } }).constructor?.name).toLowerCase();
  if (ctorName.includes("aimessage")) return "ai";
  if (ctorName.includes("toolmessage")) return "tool";
  return "other";
}

function extractToolCallsFromMessage(message: UnknownRecord): NormalizedToolCall[] {
  const calls: NormalizedToolCall[] = [];
  const seen = new Set<string>();
  const messageId = safeString(message.id).trim() || "msg";

  const pushCall = (id: string, name: string, args: Record<string, unknown>) => {
    const key = `${id}:${name}:${JSON.stringify(args)}`;
    if (seen.has(key)) return;
    seen.add(key);
    calls.push({ id, name, args });
  };

  const fromToolCalls = message.tool_calls;
  if (Array.isArray(fromToolCalls)) {
    for (let i = 0; i < fromToolCalls.length; i++) {
      const tc = asRecord(fromToolCalls[i]);
      if (!tc) continue;
      const id = safeString(tc.id).trim() || `${messageId}-tool-${i}`;
      const name = normalizeToolName(tc.name);
      const args = serializeArgs(tc.args);
      pushCall(id, name, args);
    }
  }

  const fromToolCallChunks = message.tool_call_chunks;
  if (Array.isArray(fromToolCallChunks)) {
    for (let i = 0; i < fromToolCallChunks.length; i++) {
      const tc = asRecord(fromToolCallChunks[i]);
      if (!tc) continue;
      const id = safeString(tc.id).trim();
      const name = normalizeToolName(tc.name);
      if (!id || name === "tool") continue;
      const args = serializeArgs(tc.args);
      pushCall(id, name, args);
    }
  }

  const kwargs = asRecord(message.additional_kwargs);
  const rawToolCalls = kwargs?.tool_calls;
  if (Array.isArray(rawToolCalls)) {
    for (let i = 0; i < rawToolCalls.length; i++) {
      const tc = asRecord(rawToolCalls[i]);
      if (!tc) continue;
      const fn = asRecord(tc.function);
      const id = safeString(tc.id).trim() || `${messageId}-raw-tool-${i}`;
      const name = normalizeToolName(fn?.name ?? tc.name);
      const args = serializeArgs(fn?.arguments ?? tc.args);
      pushCall(id, name, args);
    }
  }

  const content = message.content;
  if (Array.isArray(content)) {
    for (let i = 0; i < content.length; i++) {
      const block = asRecord(content[i]);
      if (!block) continue;
      const type = safeString(block.type).toLowerCase();
      if (type !== "tool_use" && type !== "server_tool_use" && type !== "tool_call") continue;
      const id = safeString(block.id).trim() || `${messageId}-block-tool-${i}`;
      const name = normalizeToolName(block.name);
      const args = serializeArgs(block.input ?? block.args);
      pushCall(id, name, args);
    }
  }

  return calls;
}

function collectMessagesFromUpdate(update: unknown): UnknownRecord[] {
  if (!isRecord(update)) return [];
  const messages = update.messages;
  if (!Array.isArray(messages)) return [];
  return messages.filter(isRecord);
}

function toolResultText(message: UnknownRecord): string {
  const content = message.content;
  if (typeof content === "string") return truncateForUI(content);

  if (Array.isArray(content)) {
    const joined = content
      .filter(isRecord)
      .map((block) => {
        if (typeof block.text === "string") return block.text;
        if (typeof block.content === "string") return block.content;
        return JSON.stringify(block);
      })
      .join("\n")
      .trim();
    if (joined) return truncateForUI(joined);
  }

  if (content != null) {
    return truncateForUI(JSON.stringify(content));
  }

  return "Done";
}

const VALID_STREAM_MODES = new Set(["messages", "updates", "custom", "values", "debug"]);

function parseStreamTuple(item: unknown): StreamTuple | null {
  if (!Array.isArray(item)) return null;

  if (item.length === 2) {
    const first = item[0];
    const second = item[1];

    // Multi-mode wrapper: ["messages" | "updates" | "custom", payload]
    if (typeof first === "string" && VALID_STREAM_MODES.has(first)) {
      return { mode: first as StreamModeName, payload: second };
    }

    // Single-mode + subgraphs wrapper for messages: [path, [chunk, metadata]]
    if (Array.isArray(first) && Array.isArray(second) && second.length === 2) {
      return {
        mode: "messages",
        payload: second,
        path: first.map((x) => String(x)),
      };
    }

    // Single messages mode default shape: [chunk, metadata]
    return {
      mode: "messages",
      payload: item,
    };
  }

  if (item.length === 3 && Array.isArray(item[0]) && typeof item[1] === "string") {
    return {
      mode: item[1] as StreamModeName,
      payload: item[2],
      path: item[0].map((x) => String(x)),
    };
  }

  return null;
}

function splitGeminiThinkTags(text: string): Array<{ type: "response" | "thought"; text: string }> {
  const out: Array<{ type: "response" | "thought"; text: string }> = [];
  let cursor = 0;

  while (cursor < text.length) {
    const open = text.indexOf("<think>", cursor);
    if (open === -1) {
      const tail = text.slice(cursor);
      if (tail) out.push({ type: "response", text: tail });
      break;
    }

    const before = text.slice(cursor, open);
    if (before) out.push({ type: "response", text: before });

    const thinkStart = open + "<think>".length;
    const close = text.indexOf("</think>", thinkStart);

    if (close === -1) {
      const thoughtTail = text.slice(thinkStart);
      if (thoughtTail) out.push({ type: "thought", text: thoughtTail });
      break;
    }

    const thought = text.slice(thinkStart, close);
    if (thought) out.push({ type: "thought", text: thought });
    cursor = close + "</think>".length;
  }

  return out;
}

function createThinkTagParser(send: (type: StreamEventType, data: string, mode: StreamModeName) => void) {
  let insideThink = false;
  // Acumula apenas o mínimo necessário para detectar os tags (7 chars para "<think>" ou 8 para "</think>")
  let tagBuffer = "";

  return {
    push(text: string) {
      // Processa char por char para emitir o mais cedo possível
      for (const ch of text) {
        tagBuffer += ch;

        if (insideThink) {
          // Procura por "</think>" no buffer
          const closeTag = "</think>";
          if (tagBuffer.endsWith(closeTag)) {
            // Emite o conteúdo antes do close tag
            const content = tagBuffer.slice(0, -closeTag.length);
            if (content) send("thought", content, "messages");
            tagBuffer = "";
            insideThink = false;
          } else if (tagBuffer.length > closeTag.length) {
            // Pode emitir os chars que com certeza não fazem parte do tag
            const safe = tagBuffer.slice(0, tagBuffer.length - closeTag.length + 1);
            send("thought", safe, "messages");
            tagBuffer = tagBuffer.slice(safe.length);
          }
        } else {
          // Procura por "<think>" no buffer
          const openTag = "<think>";
          if (tagBuffer.endsWith(openTag)) {
            // Emite o que vem antes do tag como response
            const before = tagBuffer.slice(0, -openTag.length);
            if (before) send("response", before, "messages");
            tagBuffer = "";
            insideThink = true;
          } else if (tagBuffer.length > openTag.length) {
            // Emite chars que com certeza não fazem parte do tag
            const safe = tagBuffer.slice(0, tagBuffer.length - openTag.length + 1);
            send("response", safe, "messages");
            tagBuffer = tagBuffer.slice(safe.length);
          }
        }
      }
    },

    flush() {
      if (!tagBuffer) return;
      send(insideThink ? "thought" : "response", tagBuffer, "messages");
      tagBuffer = "";
    },
  };
}

function extractMessageTextAndThought(message: UnknownRecord): { text: string; thought: string } {
  let parsed = extractTextAndThought(message.content);
  if (parsed.text || parsed.thought) return parsed;

  // Some provider message chunks expose canonical blocks via getter.
  const maybeContentBlocks = (message as { contentBlocks?: unknown }).contentBlocks;
  if (maybeContentBlocks !== undefined) {
    parsed = extractTextAndThought(maybeContentBlocks);
    if (parsed.text || parsed.thought) return parsed;
  }

  // Some message classes keep raw payload in lc_kwargs.
  const lcKwargs = asRecord((message as { lc_kwargs?: unknown }).lc_kwargs);
  if (lcKwargs?.content !== undefined) {
    parsed = extractTextAndThought(lcKwargs.content);
    if (parsed.text || parsed.thought) return parsed;
  }

  if (typeof (message as { text?: unknown }).text === "string") {
    return { text: (message as { text: string }).text, thought: "" };
  }

  return { text: "", thought: "" };
}

function extractAdditionalKwargs(message: UnknownRecord): UnknownRecord | undefined {
  const direct = asRecord(message.additional_kwargs);
  if (direct) return direct;

  const lcKwargs = asRecord((message as { lc_kwargs?: unknown }).lc_kwargs);
  return asRecord(lcKwargs?.additional_kwargs);
}

function unwrapMessageLike(message: UnknownRecord): UnknownRecord {
  if (messageKind(message) !== "other") return message;

  const nested = asRecord(message.message);
  if (nested && messageKind(nested) !== "other") return nested;

  return message;
}

export function createAgentChatStreamNormalizer({
  provider,
  emitUpdateSteps = true,
  emit,
  currentTurnRunId: initialTurnRunId,
}: ChatStreamNormalizerOptions): ChatStreamNormalizer {
  const useThinkParser = isGeminiProvider(provider);

  let hasMessageResponseOutput = false;
  let hasMessageThoughtOutput = false;
  const emittedUpdateAIMessages = new Set<string>();

  const seenToolCalls = new Set<string>();
  const seenToolResults = new Set<string>();
  const pendingTools = new Map<string, { name: string; args: Record<string, unknown> }>();
  const pendingByName = new Map<string, string[]>();

  /** Turn filter: run_id of the current LangGraph turn. Auto-detected lazily. */
  let currentTurnRunId: string | null = initialTurnRunId ?? null;

  /** Deferred event queue for tool_calls / tool_results from updates mode. */
  const eventQueue = new StreamEventQueue();

  const emitEvent = (
    type: StreamEventType,
    data: string,
    mode: StreamModeName,
    meta: StreamEvent["meta"] = {}
  ) => {
    if (mode === "messages" && type === "response") {
      hasMessageResponseOutput = true;
    }
    if (mode === "messages" && type === "thought") {
      hasMessageThoughtOutput = true;
    }
    emit(type, data, mode, meta);
  };

  const thinkParser = useThinkParser ? createThinkTagParser(emitEvent) : null;

  const collectKwThoughts = (kwargs?: UnknownRecord): string[] => {
    if (!kwargs) return [];

    const thoughts: string[] = [];

    if (typeof kwargs.thinking === "string" && kwargs.thinking) {
      thoughts.push(kwargs.thinking);
    } else if (kwargs.thinking) {
      const nested = extractNestedReasoning(kwargs.thinking);
      if (nested) thoughts.push(nested);
    }

    for (const key of ["reasoning", "reasoning_content", "reasoningContent"] as const) {
      if (!kwargs[key]) continue;
      const nested = extractNestedReasoning(kwargs[key]);
      if (nested) thoughts.push(nested);
    }

    return thoughts;
  };

  const pushPending = (id: string, name: string, args: Record<string, unknown>) => {
    pendingTools.set(id, { name, args });
    const queue = pendingByName.get(name) ?? [];
    queue.push(id);
    pendingByName.set(name, queue);
  };

  const popPendingByName = (name: string): string | undefined => {
    const queue = pendingByName.get(name);
    if (!queue || queue.length === 0) return undefined;
    const id = queue.shift();
    if (queue.length === 0) pendingByName.delete(name);
    else pendingByName.set(name, queue);
    return id;
  };

  const removePendingById = (name: string, id: string) => {
    const queue = pendingByName.get(name);
    if (!queue || queue.length === 0) return;
    const filtered = queue.filter((x) => x !== id);
    if (filtered.length === 0) pendingByName.delete(name);
    else pendingByName.set(name, filtered);
  };

  const emitText = (text: string, mode: StreamModeName, meta: StreamEvent["meta"]) => {
    if (!text) return;

    // Attach category + firstResponseMarker on the first response emission
    const enrichResponseMeta = (baseMeta: StreamEvent["meta"]): StreamEvent["meta"] => {
      const category: OutputCategory = categorizeOutput(text);
      const enriched: StreamEvent["meta"] = { ...baseMeta, category };
      if (currentTurnRunId && !eventQueue.hasFirstResponseMarker()) {
        const marker = eventQueue.setFirstResponseMarker(currentTurnRunId);
        enriched.firstResponseMarker = marker;
      }
      return enriched;
    };

    if (!useThinkParser) {
      emitEvent("response", text, mode, enrichResponseMeta(meta));
      return;
    }

    if (mode === "messages") {
      thinkParser?.push(text);
      return;
    }

    const split = splitGeminiThinkTags(text);
    if (split.length === 0) {
      emitEvent("response", text, mode, enrichResponseMeta(meta));
      return;
    }

    for (const part of split) {
      if (part.type === "response") {
        emitEvent(part.type, part.text, mode, enrichResponseMeta(meta));
      } else {
        emitEvent(part.type, part.text, mode, meta);
      }
    }
  };

  const emitToolCallsFromAIMessage = (
    message: UnknownRecord,
    mode: StreamModeName,
    node: string,
    path?: string[]
  ) => {
    const toolCalls = extractToolCallsFromMessage(message);
    for (const tc of toolCalls) {
      if (seenToolCalls.has(tc.id)) continue;
      seenToolCalls.add(tc.id);
      pushPending(tc.id, tc.name, tc.args);

      const tcMeta: StreamEvent["meta"] = { node, toolCallId: tc.id, path };

      if (mode === "updates") {
        // Defer: will be emitted in flush() with insertBefore set
        eventQueue.enqueue(
          "tool_call",
          JSON.stringify({ id: tc.id, name: tc.name, args: tc.args }),
          mode,
          tcMeta,
          true // wantsInsertBefore
        );
      } else {
        emitEvent(
          "tool_call",
          JSON.stringify({ id: tc.id, name: tc.name, args: tc.args }),
          mode,
          tcMeta
        );
      }
    }
  };

  const emitToolResultFromToolMessage = (
    message: UnknownRecord,
    mode: StreamModeName,
    node: string,
    path?: string[]
  ) => {
    let toolCallId = safeString(message.tool_call_id).trim();
    let toolName = normalizeToolName(message.name);

    if (!toolCallId && toolName && toolName !== "tool") {
      const maybeId = popPendingByName(toolName);
      if (maybeId) toolCallId = maybeId;
    }

    if ((!toolName || toolName === "tool") && toolCallId) {
      const pending = pendingTools.get(toolCallId);
      if (pending?.name) toolName = pending.name;
    }

    if (!toolCallId) {
      toolCallId = `tool-result-${Math.random().toString(36).slice(2, 12)}`;
    }

    if (seenToolResults.has(toolCallId)) return;
    seenToolResults.add(toolCallId);

    const pending = pendingTools.get(toolCallId);
    const resolvedName = pending?.name ?? toolName ?? "tool";
    pendingTools.delete(toolCallId);
    removePendingById(resolvedName, toolCallId);

    const result = toolResultText(message);
    const trMeta: StreamEvent["meta"] = { node, toolCallId, path };

    if (mode === "updates") {
      // Defer tool_result alongside its tool_call
      eventQueue.enqueue(
        "tool_result",
        JSON.stringify({ id: toolCallId, name: resolvedName, result }),
        mode,
        trMeta,
        false // tool_result goes after tool_call, no insertBefore needed
      );
    } else {
      emitEvent(
        "tool_result",
        JSON.stringify({ id: toolCallId, name: resolvedName, result }),
        mode,
        trMeta
      );
    }
  };

  const emitAIFallbackFromUpdate = (
    message: UnknownRecord,
    node: string,
    path?: string[]
  ) => {
    const msgId = safeString(message.id) || "no-id";
    const { text, thought } = extractMessageTextAndThought(message);
    const kwargs = extractAdditionalKwargs(message);
    const kwThoughts = collectKwThoughts(kwargs);

    const fallbackThoughts = hasMessageThoughtOutput
      ? []
      : [thought, ...kwThoughts].filter((x) => typeof x === "string" && x.length > 0);
    const fallbackText = hasMessageResponseOutput ? "" : text;

    if (fallbackThoughts.length === 0 && !fallbackText) return;

    const signature = `${msgId}|${fallbackThoughts.join("\n")}|${fallbackText}`;
    if (emittedUpdateAIMessages.has(signature)) return;
    emittedUpdateAIMessages.add(signature);

    const meta = { node, path };

    for (const t of fallbackThoughts) {
      emitEvent("thought", t, "updates", meta);
    }
    if (fallbackText) emitText(fallbackText, "updates", meta);
  };

  const processMessageMode = (payload: unknown, path?: string[]) => {
    if (!Array.isArray(payload) || payload.length !== 2) return;
    const rawMessage = payload[0];
    const metadata = asRecord(payload[1]);

    const eventRunId = safeString(metadata?.run_id);

    // Lazy run_id detection: adopt the first run_id seen as the current turn's run_id
    if (eventRunId && !currentTurnRunId) {
      currentTurnRunId = eventRunId;
      eventQueue.reset(); // ensure fresh queue for this turn
    }

    // Turn filter: skip replayed messages from previous turns (log-only, no SSE)
    if (currentTurnRunId && eventRunId && eventRunId !== currentTurnRunId) {
      // Event belongs to a previous turn — silently discard from SSE stream.
      // The route.ts already published it to logBus before calling process().
      return;
    }

    // Handle raw string tokens directly (Gemini token-by-token)
    if (typeof rawMessage === "string") {
      const node = safeString(metadata?.langgraph_node);
      const meta: StreamEvent["meta"] = {
        node,
        runId: eventRunId,
        turnRunId: currentTurnRunId ?? undefined,
        path,
      };
      emitText(rawMessage, "messages", meta);
      return;
    }

    const messageRecord = asRecord(rawMessage);
    if (!messageRecord) return;
    const message = unwrapMessageLike(messageRecord);

    const node = safeString(metadata?.langgraph_node);
    const meta: StreamEvent["meta"] = {
      node,
      runId: eventRunId,
      turnRunId: currentTurnRunId ?? undefined,
      path,
    };

    const kind = messageKind(message);

    if (kind === "ai") {
      const { text, thought } = extractMessageTextAndThought(message);
      const kwargs = extractAdditionalKwargs(message);

      if (thought) emitEvent("thought", thought, "messages", meta);
      for (const t of collectKwThoughts(kwargs)) {
        emitEvent("thought", t, "messages", meta);
      }
      if (text) emitText(text, "messages", meta);

      emitToolCallsFromAIMessage(message, "messages", node, path);
      return;
    }

    if (kind === "tool") {
      emitToolResultFromToolMessage(message, "messages", node, path);
    }
  };

  const processUpdatesMode = (payload: unknown, path?: string[]) => {
    if (!isRecord(payload)) return;

    for (const [nodeName, nodeUpdate] of Object.entries(payload)) {
      if (emitUpdateSteps && isStreamableNode(nodeName)) {
        const label = getNodeLabel(nodeName);
        const category = classifyNode(nodeName);
        const stepPayload = JSON.stringify({
          stepName: label,
          detail: `Node: ${nodeName} [${category}]`,
          action: "start",
        });
        emitEvent("agent_step" as StreamEventType, stepPayload, "updates", {
          node: nodeName,
          nodeCategory: category,
          path,
        });
      }

      const updateMessages = collectMessagesFromUpdate(nodeUpdate);
      for (const message of updateMessages) {
        const kind = messageKind(message);
        if (kind === "ai") {
          emitToolCallsFromAIMessage(message, "updates", nodeName, path);
          emitAIFallbackFromUpdate(message, nodeName, path);
          continue;
        }

        if (kind === "tool") {
          emitToolResultFromToolMessage(message, "updates", nodeName, path);
        }
      }
    }
  };

  const processCustomMode = (payload: unknown, path?: string[]) => {
    const data = isRecord(payload) ? payload : { value: payload };
    const label =
      typeof data.event === "string"
        ? data.event
        : typeof data.type === "string"
          ? data.type
          : "custom";

    emitEvent("step", `Custom: ${titleCase(label)}`, "custom", {
      node: safeString(data.node),
      path,
    });
  };

  return {
    process(item: unknown) {
      const tuple = parseStreamTuple(item);
      if (!tuple) return;

      if (tuple.mode === "messages") {
        processMessageMode(tuple.payload, tuple.path);
        return;
      }

      if (tuple.mode === "updates") {
        processUpdatesMode(tuple.payload, tuple.path);
        return;
      }

      if (tuple.mode === "custom") {
        processCustomMode(tuple.payload, tuple.path);
        return;
      }

      // "values" and "debug" modes: logged by route.ts via logBus, ignored for SSE
    },

    flush() {
      thinkParser?.flush();
      // Drain deferred tool_calls / tool_results with insertBefore positioning
      eventQueue.drain(emitEvent);
    },
  };
}

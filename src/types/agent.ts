export type LLMProvider = "anthropic" | "openai" | "ollama" | "google" | "vertexai";

export interface LLMConfig {
  provider: LLMProvider;
  model: string;
  apiKey?: string;
  baseUrl?: string;
}

// -- Content Part types (ordered timeline) ---------------------------

export type NotifierType =
  | "state_change"
  | "graph_transition"
  | "sub_graph"
  | "agent_start"
  | "agent_end"
  | "error"
  | "warning";

export interface ThinkingPart {
  type: "thinking";
  id: string;
  content: string;
  isStreaming: boolean;
}

export interface TextPart {
  type: "text";
  id: string;
  content: string;
}

export interface ToolCallPart {
  type: "tool_call";
  id: string;
  toolCallId: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  status: "pending" | "running" | "success" | "error";
  startedAt: string;
  completedAt?: string;
}

export interface NotifierPart {
  type: "notifier";
  id: string;
  notifierType: NotifierType;
  label: string;
  detail?: string;
  timestamp: string;
}

export type ContentPart = ThinkingPart | TextPart | ToolCallPart | NotifierPart;

// -- Agent activity types (used by activity-stream) ------------------

export interface ToolActivity {
  id: string;
  type: "tool";
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

export interface ThinkingActivity {
  id: string;
  type: "thinking";
  text: string;
}

export type AgentActivity = ToolActivity | ThinkingActivity;

// -- Chat message ----------------------------------------------------

export interface ChatMessage {
  id: string;
  conversationId: string;
  role: "user" | "assistant";
  content: string;
  thoughts: string | null;
  toolCalls: ToolCallInfo[] | null;
  createdAt: string;
}

export interface ToolCallInfo {
  id?: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export type StreamModeName = "updates" | "messages" | "custom";

export type StreamEventType =
  | "thought"
  | "tool_call"
  | "tool_result"
  | "response"
  | "step"
  | "done"
  | "error"
  | "notifier";

export interface StreamEvent {
  id: string;
  seq: number;
  type: StreamEventType;
  mode: StreamModeName;
  data: string;
  meta?: {
    runId?: string;
    parentRunId?: string;
    node?: string;
    toolCallId?: string;
    provider?: LLMProvider;
    model?: string;
    status?: "start" | "update" | "end";
    path?: string[];
  };
}

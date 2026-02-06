export type LLMProvider = "anthropic" | "openai" | "ollama" | "google";

export interface LLMConfig {
  provider: LLMProvider;
  model: string;
  apiKey?: string;
  baseUrl?: string;
}

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

export interface StreamEvent {
  type: "thought" | "tool_call" | "tool_result" | "response" | "done" | "error";
  data: string;
}

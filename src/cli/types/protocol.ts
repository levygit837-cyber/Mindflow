/**
 * Protocol Types for MindFlow CLI
 * Based on NDJSON streaming protocol similar to Claude Code
 */

// Base message interface
export interface BaseMessage {
  type: string;
  timestamp: number;
  uuid: string;
  session_id?: string;
}

// User message
export interface UserMessage extends BaseMessage {
  type: 'user';
  content: string;
  parent_tool_use_id: string | null;
  attachments?: Attachment[];
}

// Attachment types
export interface Attachment {
  type: 'file' | 'image' | 'context';
  name: string;
  content?: string;
  path?: string;
}

// Assistant message
export interface AssistantMessage extends BaseMessage {
  type: 'assistant';
  content: string;
  stop_reason?: 'end_turn' | 'max_tokens' | 'stop_sequence' | 'tool_use';
  model?: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

// Thinking block
export interface ThinkingMessage extends BaseMessage {
  type: 'thinking';
  thinking: string;
  signature?: string;
  isStreaming?: boolean;
}

// Tool use message
export interface ToolUseMessage extends BaseMessage {
  type: 'tool_use';
  tool_use_id: string;
  name: string;
  input: Record<string, unknown>;
  status: 'queued' | 'running' | 'completed' | 'failed';
}

// Tool result message
export interface ToolResultMessage extends BaseMessage {
  type: 'tool_result';
  tool_use_id: string;
  output?: string;
  error?: string;
  is_error: boolean;
  images?: string[];
}

// Progress message for long-running tools
export interface ProgressMessage extends BaseMessage {
  type: 'progress';
  tool_use_id: string;
  content: string;
  percent?: number;
  metadata?: Record<string, unknown>;
}

// System message
export interface SystemMessage extends BaseMessage {
  type: 'system';
  subtype: 'status' | 'error' | 'warning' | 'info' | 'compact_boundary';
  content: string;
  metadata?: Record<string, unknown>;
}

// Control messages for permission prompts
export interface ControlRequest extends BaseMessage {
  type: 'control_request';
  request: {
    subtype: 'can_use_tool';
    tool_name: string;
    tool_use_id: string;
    input: Record<string, unknown>;
  };
}

export interface ControlResponse extends BaseMessage {
  type: 'control_response';
  request_id: string;
  response: {
    decision: 'allow' | 'deny' | 'ask';
    message?: string;
  };
}

// Union type for all messages
export type Message =
  | UserMessage
  | AssistantMessage
  | ThinkingMessage
  | ToolUseMessage
  | ToolResultMessage
  | ProgressMessage
  | SystemMessage
  | ControlRequest
  | ControlResponse;

// Message types discriminated by type field
export type MessageType = Message['type'];

// Tool definition
export interface Tool {
  name: string;
  description: string;
  input_schema: {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
  };
  userFacingName?: (input: Record<string, unknown>) => string;
  renderToolUse?: (props: ToolUseRenderProps) => React.ReactNode;
  renderToolResult?: (props: ToolResultRenderProps) => React.ReactNode;
}

export interface ToolUseRenderProps {
  tool: Tool;
  input: Record<string, unknown>;
  isInProgress: boolean;
  progressMessages: ProgressMessage[];
}

export interface ToolResultRenderProps {
  tool: Tool;
  result: ToolResultMessage;
  isError: boolean;
}

// Agent definition
export interface Agent {
  id: string;
  name: string;
  color: string;
  description: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  progress?: number;
  currentTask?: string;
}

// Session state
export interface SessionState {
  id: string;
  status: 'idle' | 'running' | 'paused' | 'error';
  permission_mode: 'default' | 'acceptEdits' | 'bypassPermissions' | 'plan';
}

// App state for Zustand store
export interface AppState {
  // Messages
  messages: Message[];
  visibleRange: { start: number; end: number };
  
  // Tool execution tracking
  inProgressToolUseIDs: Set<string>;
  resolvedToolUseIDs: Set<string>;
  erroredToolUseIDs: Set<string>;
  progressMessagesByToolUseID: Map<string, ProgressMessage[]>;
  
  // Agents
  agents: Map<string, Agent>;
  
  // Session
  session: SessionState;
  
  // UI state
  isLoading: boolean;
  expandedView: 'none' | 'agents' | 'tools' | 'thinking';
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  selectedMessageIndex: number | null;
  
  // Input
  inputValue: string;
  inputHistory: string[];
  historyIndex: number;
}

// Renderable message with computed properties
export type RenderableMessage = Message & {
  isStreaming?: boolean;
  displayIndex?: number;
};

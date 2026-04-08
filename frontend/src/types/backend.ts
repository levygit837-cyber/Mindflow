/**
 * Backend event types matching Python backend schemas
 */

export type AgentType = 'orchestrator' | 'analyst' | 'coder' | 'researcher';

export type StreamEventType =
  | 'thought'
  | 'tool_call'
  | 'tool_result'
  | 'response'
  | 'step'
  | 'agent_step'
  | 'done'
  | 'error'
  | 'notifier'
  | 'orchestrator_thinking_start'
  | 'orchestrator_thinking'
  | 'orchestrator_thinking_end'
  | 'reflection_mode_start'
  | 'reflection_mode_end'
  | 'orchestrator_decision'
  | 'agent_delegation_start'
  | 'agent_delegation_complete'
  | 'specialist_activation'
  | 'specialist_thinking'
  | 'orchestrator_step'
  | 'tool_operation_start'
  | 'tool_operation_update'
  | 'tool_operation_complete'
  | 'routing_analysis'
  | 'agent_execution_start';

export type StreamModeName = 'updates' | 'messages' | 'custom' | 'values' | 'debug';

export interface StreamEventMeta {
  runId?: string;
  parentRunId?: string;
  node?: string;
  nodeLabel?: string;
  nodeCategory?: string;
  userVisible?: boolean;
  toolCallId?: string;
  provider?: string;
  model?: string;
  status?: 'start' | 'update' | 'end';
  path?: string[];
  turnRunId?: string;
  insertBefore?: string;
  firstResponseMarker?: string;
  category?: string;
  agent?: AgentType;
}

export interface StreamEvent {
  id: string;
  seq: number;
  type: StreamEventType;
  mode: StreamModeName;
  data: string;
  meta?: StreamEventMeta;
}

export interface NotifierPayload {
  kind: string;
  message: string;
  details: Record<string, unknown>;
}

export interface ToolCallPayload {
  tool: string;
  args: Record<string, unknown>;
}

export interface ToolResultPayload {
  tool: string;
  result: string;
  error?: string;
}

export interface DelegationPayload {
  from_agent: AgentType;
  to_agent: AgentType;
  strategy: 'parallel' | 'sequential' | 'single';
  tools: string[];
  context: string;
  task_id?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  agentType?: AgentType;
  timestamp: Date;
  events?: StreamEvent[];
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messages: ChatMessage[];
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  agent_type?: AgentType;
  orchestrate?: boolean;
  provider?: string;
  model?: string;
  folder_path?: string;
  stream?: boolean;
}

export interface ThinkingEvent {
  id: string;
  agentType: AgentType;
  reasoning: string;
  isExpanded: boolean;
  timestamp: Date;
  status: 'start' | 'update' | 'end';
}

export interface ToolCallEvent {
  id: string;
  agentType: AgentType;
  toolName: string;
  status: 'pending' | 'running' | 'success' | 'error';
  input: Record<string, unknown>;
  output?: string;
  error?: string;
  timestamp: Date;
}

export interface DelegationEvent {
  id: string;
  fromAgent: AgentType;
  toAgent: AgentType;
  strategy: 'parallel' | 'sequential' | 'single';
  tools: string[];
  context: string;
  timestamp: Date;
}

export interface StreamingState {
  agentType: AgentType;
  text: string;
  progress?: number;
  isActive: boolean;
}

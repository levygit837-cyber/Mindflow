/**
 * Core type definitions for MindFlow CLI
 */

export type MessageType = 'user' | 'assistant' | 'agent' | 'system';

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: number;
  agentId?: string;
  agentName?: string;
}

export type AgentStatus = 'idle' | 'thinking' | 'executing' | 'error';

export interface AgentState {
  id: string;
  name: string;
  status: AgentStatus;
  currentTool?: string;
  progress?: number;
  parentId?: string;
  children?: string[];
}

export type ToolStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ToolCall {
  id: string;
  name: string;
  status: ToolStatus;
  startTime: number;
  endTime?: number;
  duration?: number;
  output?: string;
  error?: string;
  agentId: string;
}

export type ExpandedView = 'none' | 'agents' | 'tools';

export interface AppState {
  // Messages
  messages: Message[];

  // Agents
  agents: Record<string, AgentState>;

  // Tools
  toolCalls: Record<string, ToolCall>;

  // UI State
  isLoading: boolean;
  expandedView: ExpandedView;
  connectionStatus: 'connected' | 'reconnecting' | 'disconnected';

  // Actions
  addMessage: (message: Message) => void;
  updateAgent: (agentId: string, updates: Partial<AgentState>) => void;
  startToolCall: (toolCall: ToolCall) => void;
  completeToolCall: (toolCallId: string, output?: string, error?: string) => void;
  setExpandedView: (view: ExpandedView) => void;
  setConnectionStatus: (status: 'connected' | 'reconnecting' | 'disconnected') => void;
  clearMessages: () => void;
}

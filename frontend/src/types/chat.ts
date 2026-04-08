import { AgentType } from './agents';

export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  agentType?: AgentType;
  timestamp: Date;
  contextPaths?: string[];
  events?: ChatEvent[];
}

export type ChatEventType = 
  | 'thinking'
  | 'delegation'
  | 'tool_call'
  | 'streaming'
  | 'context_update';

export interface ChatEvent {
  id: string;
  type: ChatEventType;
  agentType: AgentType;
  data: unknown;
  timestamp: Date;
}

export interface FolderContext {
  path: string;
  name: string;
  isSelected: boolean;
}

export interface InputState {
  text: string;
  selectedAgent: AgentType | null;
  selectedFolder: string | null;
  contextPaths: string[];
  isOrchestrateMode: boolean;
}

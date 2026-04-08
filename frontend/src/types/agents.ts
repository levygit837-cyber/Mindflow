import { AGENTS } from '../lib/constants';

export type AgentType = keyof typeof AGENTS;

export interface AgentConfig {
  id: string;
  name: string;
  description: string;
  color: string;
  icon: string;
  gradient: string;
}

export interface AgentMessage {
  id: string;
  agentType: AgentType;
  content: string;
  timestamp: Date;
  status: 'thinking' | 'streaming' | 'complete' | 'error';
  metadata?: {
    tools?: string[];
    strategy?: string;
    reasoning?: string;
  };
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

export interface ToolCall {
  id: string;
  agentType: AgentType;
  toolName: string;
  status: 'pending' | 'running' | 'success' | 'error';
  input: Record<string, unknown>;
  output?: string;
  error?: string;
  timestamp: Date;
}

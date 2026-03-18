export type AgentType =
  | 'orchestrator'
  | 'coder'
  | 'analyst'
  | 'researcher'
  | 'architect'
  | 'critic'
  | 'creative'
  | 'security'
  | 'default';

export const AGENT_ACCENTS: Record<AgentType, string> = {
  orchestrator: '#0D6E6E',
  coder: '#C75D2C',
  analyst: '#5B6ABF',
  researcher: '#2D8F5E',
  architect: '#0D6E6E',
  critic: '#9B59B6',
  creative: '#E67E22',
  security: '#C0392B',
  default: '#0D6E6E',
};

export const AGENT_LABELS: Record<AgentType, string> = {
  orchestrator: 'ORCHESTRATOR',
  coder: 'CODER',
  analyst: 'ANALYST',
  researcher: 'RESEARCHER',
  architect: 'ARCHITECT',
  critic: 'CRITIC',
  creative: 'CREATIVE',
  security: 'SECURITY',
  default: 'AGENT',
};

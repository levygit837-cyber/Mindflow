/**
 * Chat Visualization V2 - Core Types
 * 
 * Centralized type definitions for the V2 chat visualization system.
 * These types support the new generation of components that improve
 * visual clarity and user experience.
 */

export type MindflowV2AgentType = 'orchestrator' | 'analyst' | 'coder' | 'researcher';

export type MindflowV2Tone = 'accent' | 'info' | 'success' | 'warning' | 'error' | 'neutral';

export type MindflowV2ComponentKey =
  | 'thinking-notifiers'
  | 'thought-blocks'
  | 'delegation-cards'
  | 'tool-calls-results'
  | 'stream-notifiers'
  | 'memory-components'
  | 'journey';

export interface MindflowV2AgentTheme {
  label: string;
  shortLabel: string;
  accent: string;
  soft: string;
  muted: string;
}

export interface MindflowV2ComponentMapping {
  key: MindflowV2ComponentKey;
  section: string;
  label: string;
  source: string;
  frontend: string[];
  variables: string[];
  variants: string[];
  purpose: string;
}

export const MINDFLOW_V2_AGENT_ORDER: MindflowV2AgentType[] = [
  'orchestrator',
  'analyst',
  'coder',
  'researcher',
];

export const MINDFLOW_V2_AGENT_THEME: Record<MindflowV2AgentType, MindflowV2AgentTheme> = {
  orchestrator: {
    label: 'Orchestrator',
    shortLabel: 'Orch',
    accent: '#0D6E6E',
    soft: '#E8F4F4',
    muted: '#0D2E2E',
  },
  analyst: {
    label: 'Analyst',
    shortLabel: 'Analyst',
    accent: '#5B6ABF',
    soft: '#EEF0FF',
    muted: '#202646',
  },
  coder: {
    label: 'Coder',
    shortLabel: 'Coder',
    accent: '#C75D2C',
    soft: '#FCEFE8',
    muted: '#4C2211',
  },
  researcher: {
    label: 'Research',
    shortLabel: 'Researcher',
    accent: '#2D8F5E',
    soft: '#EAF7EF',
    muted: '#173E2C',
  },
};

export const MINDFLOW_V2_COMPONENT_MAPPING: MindflowV2ComponentMapping[] = [
  {
    key: 'thinking-notifiers',
    section: 'Section 1 · Agent Indicators',
    label: 'Thinking Notifiers',
    source: 'ZXyKn / R6Uf0 + lPkCi',
    frontend: ['ThinkingNotifier', 'ThinkingNotifierRow'],
    variables: [
      '--agent-orchestrator-color',
      '--agent-analyst-color',
      '--agent-coder-color',
      '--agent-researcher-color',
      '--text-primary',
      '--text-meta',
    ],
    variants: ['Orchestrator', 'Analyst', 'Coder', 'Researcher'],
    purpose: 'Mostra quais agentes estão ativos ou esperando durante a execução.',
  },
  {
    key: 'thought-blocks',
    section: 'Section 2 · Thinking States',
    label: 'Thought Blocks',
    source: 'JI17t / 3XXjF',
    frontend: ['ThoughtBlock'],
    variables: [
      '--font-thought-name',
      '--font-thought-meta',
      '--line-primary',
      '--surface-elevated',
      '--text-secondary',
    ],
    variants: ['Collapsed', 'Expanded', 'Chat Chain', 'Summary'],
    purpose: 'Exibe o raciocínio resumido do agente com estado expansível.',
  },
  {
    key: 'delegation-cards',
    section: 'Section 4 · Delegation Cards',
    label: 'Delegation Cards',
    source: 'cmwVk / NZTyZ / HWv2m',
    frontend: ['DelegationCard', 'DelegationInspector'],
    variables: [
      '--font-brand',
      '--line-primary',
      '--surface',
      '--surface-elevated',
      '--signal-synapse',
    ],
    variants: ['Simple', 'Rich', 'Inspector'],
    purpose: 'Resume o trabalho delegado, o agente alvo e o estado da orquestração.',
  },
  {
    key: 'tool-calls-results',
    section: 'Section 3 · Tool Calls',
    label: 'Tool Calls / Tool Results',
    source: '3Iw2H',
    frontend: ['ToolEventCard'],
    variables: [
      '--state-success',
      '--state-warning',
      '--state-error',
      '--font-mono',
      '--line-primary',
    ],
    variants: ['Running', 'Completed', 'Error', 'Collapsed', 'Group'],
    purpose: 'Expõe chamadas de ferramenta, parâmetros e resultados em tempo real.',
  },
  {
    key: 'stream-notifiers',
    section: 'Section 5 · Notifier Pills',
    label: 'Notifiers',
    source: 'VZjuG / notifier pills',
    frontend: ['StreamNotifier'],
    variables: [
      '--state-success',
      '--state-warning',
      '--state-error',
      '--state-info',
      '--text-meta',
    ],
    variants: ['Routing', 'Tool Running', 'Completed', 'Error'],
    purpose: 'Mostra avisos de alto sinal, como roteamento, conclusão e falhas.',
  },
  {
    key: 'memory-components',
    section: 'w1y2N · Memory Recall',
    label: 'Memory Components',
    source: 'w1y2N',
    frontend: ['MemoryRecallCard'],
    variables: [
      '--state-info',
      '--state-success',
      '--line-primary',
      '--surface-glass',
      '--font-mono',
    ],
    variants: ['Vector Memory Recall', 'Database Memory Recall'],
    purpose: 'Mostra memória recuperada, referências de contexto e origem do recall.',
  },
  {
    key: 'journey',
    section: 'hwutp · Agent Journey',
    label: 'Journey',
    source: 'hwutp / HWv2m',
    frontend: ['JourneyTimeline'],
    variables: [
      '--font-brand',
      '--font-mono',
      '--state-success',
      '--state-warning',
      '--line-primary',
    ],
    variants: ['Single Agent Timeline', 'Multi Agent Timeline', 'Expanded Event', 'Summary Bar', 'Live Indicator'],
    purpose: 'Agrupa a jornada do trabalho em etapas, delegações e marcos da execução.',
  },
];

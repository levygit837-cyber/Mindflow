/**
 * MindFlow Design System Constants
 * Centralized source of truth for colors, spacing, and typography
 */

export const COLORS = {
  agents: {
    orchestrator: '#0D6E6E',
    analyst: '#5B6ABF',
    coder: '#C75D2C',
    researcher: '#2D8F5E',
  },
  surface: {
    primary: '#0a0a0a',
    secondary: '#1a1a1a',
    tertiary: '#2a2a2a',
    highlight: '#3a3a3a',
  },
  text: {
    primary: '#ffffff',
    secondary: '#b0b0b0',
    tertiary: '#707070',
    muted: '#505050',
  },
  border: {
    subtle: '#2a2a2a',
    standard: '#3a3a3a',
    emphasized: '#4a4a4a',
  },
  semantic: {
    success: '#2D8F5E',
    error: '#e74c3c',
    warning: '#f39c12',
    info: '#3498db',
  },
} as const;

export const AGENTS = {
  orchestrator: {
    id: 'orchestrator',
    name: 'Orchestrator',
    description: 'Coordinates multi-agent workflows',
    color: COLORS.agents.orchestrator,
    icon: 'Target',
    gradient: 'from-[#0D6E6E] to-[#0a5a5a]',
  },
  analyst: {
    id: 'analyst',
    name: 'Analyst',
    description: 'Extracts insights from data',
    color: COLORS.agents.analyst,
    icon: 'ChartBar',
    gradient: 'from-[#5B6ABF] to-[#4a5a9f]',
  },
  coder: {
    id: 'coder',
    name: 'Coder',
    description: 'Writes and executes code',
    color: COLORS.agents.coder,
    icon: 'BracketsCurly',
    gradient: 'from-[#C75D2C] to-[#a84d1c]',
  },
  researcher: {
    id: 'researcher',
    name: 'Researcher',
    description: 'Gathers information from web',
    color: COLORS.agents.researcher,
    icon: 'MagnifyingGlass',
    gradient: 'from-[#2D8F5E] to-[#1e7a4f]',
  },
} as const;

export type AgentType = keyof typeof AGENTS;

export const SPACING = {
  base: 8,
  scale: [4, 8, 12, 16, 24, 32, 48, 64, 96],
} as const;

export const TYPOGRAPHY = {
  fontFamily: {
    sans: "'Inter', system-ui, -apple-system, sans-serif",
    mono: "'Fira Code', ui-monospace, monospace",
  },
  sizes: {
    hero: '48px',
    section: '32px',
    subheading: '24px',
    title: '20px',
    bodyLarge: '16px',
    body: '14px',
    small: '12px',
    caption: '11px',
    label: '10px',
  },
} as const;

export const SHADOWS = {
  elevation1: '0 4px 12px rgba(0,0,0,0.3)',
  elevation2: '0 8px 30px rgba(0,0,0,0.5)',
} as const;

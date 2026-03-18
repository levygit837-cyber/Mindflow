/**
 * Chat Visualization V2 - Utility Functions
 * 
 * Helper functions for agent type resolution, theme management,
 * duration formatting, and value transformation.
 */

import {
  MindflowV2AgentType,
  MindflowV2AgentTheme,
  MindflowV2Tone,
  MINDFLOW_V2_AGENT_THEME,
} from './types';

/**
 * Resolve a raw string to a valid MindflowV2AgentType
 * Handles various aliases and normalizes to canonical agent types
 */
export function resolveMindflowV2AgentType(raw: string | null | undefined): MindflowV2AgentType {
  const normalized = String(raw ?? '').trim().toLowerCase();

  if (
    normalized === 'orchestrator' ||
    normalized === 'orch' ||
    normalized === 'router' ||
    normalized === 'routing'
  ) {
    return 'orchestrator';
  }

  if (normalized === 'analyst' || normalized === 'analysis' || normalized === 'analyzer') {
    return 'analyst';
  }

  if (normalized === 'coder' || normalized === 'code' || normalized === 'developer' || normalized === 'engineer') {
    return 'coder';
  }

  if (normalized === 'researcher' || normalized === 'research' || normalized === 'search') {
    return 'researcher';
  }

  return 'orchestrator';
}

/**
 * Get the theme configuration for a given agent type
 */
export function getMindflowV2AgentTheme(raw: string | null | undefined): MindflowV2AgentTheme {
  return MINDFLOW_V2_AGENT_THEME[resolveMindflowV2AgentType(raw)];
}

/**
 * Resolve a status/kind string to a visual tone
 * Used for StreamNotifier and other status-based components
 */
export function resolveMindflowV2Tone(kind: string | null | undefined): MindflowV2Tone {
  const normalized = String(kind ?? '').trim().toLowerCase();

  if (!normalized) return 'neutral';
  if (normalized.includes('error') || normalized.includes('fail') || normalized.includes('failure')) return 'error';
  if (
    normalized.includes('warn') ||
    normalized.includes('slow') ||
    normalized.includes('scope') ||
    normalized.includes('fallback')
  ) {
    return 'warning';
  }
  if (
    normalized.includes('complete') ||
    normalized.includes('done') ||
    normalized.includes('success') ||
    normalized.includes('loaded')
  ) {
    return 'success';
  }
  if (
    normalized.includes('routing') ||
    normalized.includes('decision') ||
    normalized.includes('thinking') ||
    normalized.includes('activate') ||
    normalized.includes('analysis')
  ) {
    return 'accent';
  }
  if (normalized.includes('memory') || normalized.includes('context')) {
    return 'info';
  }
  return 'neutral';
}

/**
 * Format milliseconds to human-readable duration (e.g., "1m 23s")
 */
export function formatMindflowV2Duration(milliseconds: number): string {
  if (!Number.isFinite(milliseconds) || milliseconds <= 0) {
    return '0s';
  }

  const totalSeconds = Math.max(1, Math.round(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  }

  return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
}

/**
 * Format any value to a string representation
 * Handles null, undefined, primitives, and objects
 */
export function formatMindflowV2Value(value: unknown): string {
  if (value === null || value === undefined) {
    return '—';
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : '—';
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

/**
 * Summarize a value to a maximum length with ellipsis
 * Useful for previews and collapsed states
 */
export function summarizeMindflowV2Value(value: unknown, maxLength = 180): string {
  const formatted = formatMindflowV2Value(value).replace(/\s+/g, ' ').trim();

  if (formatted.length <= maxLength) {
    return formatted;
  }

  return `${formatted.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

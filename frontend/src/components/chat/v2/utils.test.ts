/**
 * Chat Visualization V2 - Utility Functions Tests
 * 
 * Unit tests for agent type resolution, theme management,
 * duration formatting, and value transformation.
 */

import { describe, it, expect } from 'vitest';
import {
  resolveMindflowV2AgentType,
  getMindflowV2AgentTheme,
  resolveMindflowV2Tone,
  formatMindflowV2Duration,
  formatMindflowV2Value,
  summarizeMindflowV2Value,
} from './utils';

describe('resolveMindflowV2AgentType', () => {
  it('should resolve orchestrator aliases', () => {
    expect(resolveMindflowV2AgentType('orchestrator')).toBe('orchestrator');
    expect(resolveMindflowV2AgentType('orch')).toBe('orchestrator');
    expect(resolveMindflowV2AgentType('router')).toBe('orchestrator');
    expect(resolveMindflowV2AgentType('routing')).toBe('orchestrator');
    expect(resolveMindflowV2AgentType('ORCHESTRATOR')).toBe('orchestrator');
  });

  it('should resolve analyst aliases', () => {
    expect(resolveMindflowV2AgentType('analyst')).toBe('analyst');
    expect(resolveMindflowV2AgentType('analysis')).toBe('analyst');
    expect(resolveMindflowV2AgentType('analyzer')).toBe('analyst');
    expect(resolveMindflowV2AgentType('ANALYST')).toBe('analyst');
  });

  it('should resolve coder aliases', () => {
    expect(resolveMindflowV2AgentType('coder')).toBe('coder');
    expect(resolveMindflowV2AgentType('code')).toBe('coder');
    expect(resolveMindflowV2AgentType('developer')).toBe('coder');
    expect(resolveMindflowV2AgentType('engineer')).toBe('coder');
    expect(resolveMindflowV2AgentType('CODER')).toBe('coder');
  });

  it('should resolve researcher aliases', () => {
    expect(resolveMindflowV2AgentType('researcher')).toBe('researcher');
    expect(resolveMindflowV2AgentType('research')).toBe('researcher');
    expect(resolveMindflowV2AgentType('search')).toBe('researcher');
    expect(resolveMindflowV2AgentType('RESEARCHER')).toBe('researcher');
  });

  it('should default to orchestrator for unknown values', () => {
    expect(resolveMindflowV2AgentType('unknown')).toBe('orchestrator');
    expect(resolveMindflowV2AgentType('')).toBe('orchestrator');
    expect(resolveMindflowV2AgentType(null)).toBe('orchestrator');
    expect(resolveMindflowV2AgentType(undefined)).toBe('orchestrator');
  });

  it('should handle whitespace', () => {
    expect(resolveMindflowV2AgentType('  analyst  ')).toBe('analyst');
    expect(resolveMindflowV2AgentType('\tcoder\n')).toBe('coder');
  });
});

describe('getMindflowV2AgentTheme', () => {
  it('should return correct theme for orchestrator', () => {
    const theme = getMindflowV2AgentTheme('orchestrator');
    expect(theme.label).toBe('Orchestrator');
    expect(theme.shortLabel).toBe('Orch');
    expect(theme.accent).toBe('#0D6E6E');
    expect(theme.soft).toBe('#E8F4F4');
    expect(theme.muted).toBe('#0D2E2E');
  });

  it('should return correct theme for analyst', () => {
    const theme = getMindflowV2AgentTheme('analyst');
    expect(theme.label).toBe('Analyst');
    expect(theme.accent).toBe('#5B6ABF');
  });

  it('should return correct theme for coder', () => {
    const theme = getMindflowV2AgentTheme('coder');
    expect(theme.label).toBe('Coder');
    expect(theme.accent).toBe('#C75D2C');
  });

  it('should return correct theme for researcher', () => {
    const theme = getMindflowV2AgentTheme('researcher');
    expect(theme.label).toBe('Research');
    expect(theme.accent).toBe('#2D8F5E');
  });

  it('should handle aliases', () => {
    const theme = getMindflowV2AgentTheme('orch');
    expect(theme.label).toBe('Orchestrator');
  });
});

describe('resolveMindflowV2Tone', () => {
  it('should resolve error tone', () => {
    expect(resolveMindflowV2Tone('error')).toBe('error');
    expect(resolveMindflowV2Tone('fail')).toBe('error');
    expect(resolveMindflowV2Tone('failure')).toBe('error');
    expect(resolveMindflowV2Tone('something_error_happened')).toBe('error');
  });

  it('should resolve warning tone', () => {
    expect(resolveMindflowV2Tone('warn')).toBe('warning');
    expect(resolveMindflowV2Tone('warning')).toBe('warning');
    expect(resolveMindflowV2Tone('slow')).toBe('warning');
    expect(resolveMindflowV2Tone('scope')).toBe('warning');
    expect(resolveMindflowV2Tone('fallback')).toBe('warning');
  });

  it('should resolve success tone', () => {
    expect(resolveMindflowV2Tone('complete')).toBe('success');
    expect(resolveMindflowV2Tone('done')).toBe('success');
    expect(resolveMindflowV2Tone('success')).toBe('success');
    expect(resolveMindflowV2Tone('loaded')).toBe('success');
  });

  it('should resolve accent tone', () => {
    expect(resolveMindflowV2Tone('routing')).toBe('accent');
    expect(resolveMindflowV2Tone('decision')).toBe('accent');
    expect(resolveMindflowV2Tone('thinking')).toBe('accent');
    expect(resolveMindflowV2Tone('activate')).toBe('accent');
    expect(resolveMindflowV2Tone('analysis')).toBe('accent');
  });

  it('should resolve info tone', () => {
    expect(resolveMindflowV2Tone('memory')).toBe('info');
    expect(resolveMindflowV2Tone('context')).toBe('info');
  });

  it('should default to neutral', () => {
    expect(resolveMindflowV2Tone('unknown')).toBe('neutral');
    expect(resolveMindflowV2Tone('')).toBe('neutral');
    expect(resolveMindflowV2Tone(null)).toBe('neutral');
    expect(resolveMindflowV2Tone(undefined)).toBe('neutral');
  });
});

describe('formatMindflowV2Duration', () => {
  it('should format seconds only', () => {
    expect(formatMindflowV2Duration(1000)).toBe('1s');
    expect(formatMindflowV2Duration(5000)).toBe('5s');
    expect(formatMindflowV2Duration(59000)).toBe('59s');
  });

  it('should format minutes and seconds', () => {
    expect(formatMindflowV2Duration(60000)).toBe('1m 00s');
    expect(formatMindflowV2Duration(83000)).toBe('1m 23s');
    expect(formatMindflowV2Duration(125000)).toBe('2m 05s');
  });

  it('should round to nearest second', () => {
    expect(formatMindflowV2Duration(1499)).toBe('1s');
    expect(formatMindflowV2Duration(1500)).toBe('2s');
  });

  it('should handle edge cases', () => {
    expect(formatMindflowV2Duration(0)).toBe('0s');
    expect(formatMindflowV2Duration(-100)).toBe('0s');
    expect(formatMindflowV2Duration(Infinity)).toBe('0s');
    expect(formatMindflowV2Duration(NaN)).toBe('0s');
  });

  it('should handle large durations', () => {
    expect(formatMindflowV2Duration(3600000)).toBe('60m 00s');
    expect(formatMindflowV2Duration(3661000)).toBe('61m 01s');
  });
});

describe('formatMindflowV2Value', () => {
  it('should format null and undefined', () => {
    expect(formatMindflowV2Value(null)).toBe('—');
    expect(formatMindflowV2Value(undefined)).toBe('—');
  });

  it('should format strings', () => {
    expect(formatMindflowV2Value('hello')).toBe('hello');
    expect(formatMindflowV2Value('  trimmed  ')).toBe('trimmed');
    expect(formatMindflowV2Value('')).toBe('—');
    expect(formatMindflowV2Value('   ')).toBe('—');
  });

  it('should format numbers', () => {
    expect(formatMindflowV2Value(42)).toBe('42');
    expect(formatMindflowV2Value(0)).toBe('0');
    expect(formatMindflowV2Value(-1)).toBe('-1');
    expect(formatMindflowV2Value(3.14)).toBe('3.14');
  });

  it('should format booleans', () => {
    expect(formatMindflowV2Value(true)).toBe('true');
    expect(formatMindflowV2Value(false)).toBe('false');
  });

  it('should format objects', () => {
    const obj = { key: 'value', nested: { prop: 123 } };
    const formatted = formatMindflowV2Value(obj);
    expect(formatted).toContain('"key"');
    expect(formatted).toContain('"value"');
    expect(formatted).toContain('"nested"');
  });

  it('should format arrays', () => {
    const arr = [1, 2, 3];
    const formatted = formatMindflowV2Value(arr);
    expect(formatted).toContain('1');
    expect(formatted).toContain('2');
    expect(formatted).toContain('3');
  });

  it('should handle circular references gracefully', () => {
    const circular: any = { prop: 'value' };
    circular.self = circular;
    const formatted = formatMindflowV2Value(circular);
    expect(typeof formatted).toBe('string');
  });
});

describe('summarizeMindflowV2Value', () => {
  it('should not truncate short values', () => {
    expect(summarizeMindflowV2Value('short')).toBe('short');
    expect(summarizeMindflowV2Value('a'.repeat(180))).toBe('a'.repeat(180));
  });

  it('should truncate long values', () => {
    const long = 'a'.repeat(200);
    const summarized = summarizeMindflowV2Value(long);
    expect(summarized.length).toBeLessThan(long.length);
    expect(summarized).toMatch(/…$/);
  });

  it('should respect custom maxLength', () => {
    const text = 'a'.repeat(100);
    const summarized = summarizeMindflowV2Value(text, 50);
    expect(summarized.length).toBeLessThanOrEqual(50);
    expect(summarized).toMatch(/…$/);
  });

  it('should collapse whitespace', () => {
    const text = 'hello    world\n\ntab\there';
    const summarized = summarizeMindflowV2Value(text);
    expect(summarized).toBe('hello world tab here');
  });

  it('should handle null and undefined', () => {
    expect(summarizeMindflowV2Value(null)).toBe('—');
    expect(summarizeMindflowV2Value(undefined)).toBe('—');
  });

  it('should handle objects', () => {
    const obj = { key: 'value', another: 'property' };
    const summarized = summarizeMindflowV2Value(obj, 20);
    expect(summarized.length).toBeLessThanOrEqual(20);
    expect(summarized).toMatch(/…$/);
  });
});

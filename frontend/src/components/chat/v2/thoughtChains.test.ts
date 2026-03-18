/**
 * Unit Tests for Thought Chains
 *
 * Tests specific examples, edge cases, and concrete scenarios
 * for thought chain grouping and filtering logic.
 */

import { describe, it, expect } from 'vitest';
import {
  groupThoughtsIntoChains,
  filterThoughtContent,
  filterThoughtItem,
  shouldRenderAsChain,
  type ThoughtChainItem,
} from './thoughtChains';

describe('filterThoughtContent', () => {
  it('should remove "Delegated" indicator (case-insensitive)', () => {
    expect(filterThoughtContent('Task delegated to analyst')).toBe('Task to analyst');
    expect(filterThoughtContent('Task Delegated to analyst')).toBe('Task to analyst');
    expect(filterThoughtContent('Task DELEGATED to analyst')).toBe('Task to analyst');
  });

  it('should remove "Delegation" indicator', () => {
    expect(filterThoughtContent('Starting delegation process')).toBe('Starting process');
    expect(filterThoughtContent('Delegation complete')).toBe('complete');
  });

  it('should remove reasoning depth indicators', () => {
    expect(filterThoughtContent('Analyzing code. Depth: 2')).toBe('Analyzing code.');
    expect(filterThoughtContent('Reasoning depth: 3 for this task')).toBe('for this task');
    expect(filterThoughtContent('depth: 1 analysis')).toBe('analysis');
  });

  it('should remove thought summary markers', () => {
    expect(filterThoughtContent('Analysis complete. Summary: findings')).toBe(
      'Analysis complete. findings'
    );
    expect(filterThoughtContent('Thought Summary: key points')).toBe('key points');
    expect(filterThoughtContent('summary: test')).toBe('test');
  });

  it('should remove multiple indicators from same content', () => {
    const content = 'Task delegated. Depth: 2. Summary: complete';
    const filtered = filterThoughtContent(content);

    expect(filtered).not.toContain('delegated');
    expect(filtered).not.toMatch(/depth\s*:\s*\d+/i);
    expect(filtered).not.toMatch(/summary\s*:/i);
    expect(filtered).toContain('Task');
    expect(filtered).toContain('complete');
  });

  it('should normalize whitespace after filtering', () => {
    const content = 'Task    delegated    Depth: 2    Summary: done';
    const filtered = filterThoughtContent(content);

    expect(filtered).not.toMatch(/\s{2,}/); // No double spaces
    expect(filtered).toBe('Task done');
  });

  it('should handle empty content', () => {
    expect(filterThoughtContent('')).toBe('');
    expect(filterThoughtContent('   ')).toBe('');
  });

  it('should preserve content without indicators', () => {
    const content = 'Analyzing the codebase structure';
    expect(filterThoughtContent(content)).toBe(content);
  });
});

describe('filterThoughtItem', () => {
  it('should filter content and remove summary', () => {
    const item: ThoughtChainItem = {
      id: 'thought-1',
      agentType: 'orchestrator',
      content: 'Task delegated. Depth: 2',
      summary: 'Test summary',
      status: 'thinking',
    };

    const filtered = filterThoughtItem(item);

    expect(filtered.content).not.toContain('delegated');
    expect(filtered.content).not.toMatch(/depth\s*:\s*\d+/i);
    expect(filtered.summary).toBeUndefined();
  });

  it('should preserve other fields', () => {
    const item: ThoughtChainItem = {
      id: 'thought-1',
      agentType: 'analyst',
      title: 'Analysis',
      content: 'Analyzing code',
      status: 'thinking',
      defaultExpanded: true,
    };

    const filtered = filterThoughtItem(item);

    expect(filtered.id).toBe(item.id);
    expect(filtered.agentType).toBe(item.agentType);
    expect(filtered.title).toBe(item.title);
    expect(filtered.status).toBe(item.status);
    expect(filtered.defaultExpanded).toBe(item.defaultExpanded);
  });
});

describe('groupThoughtsIntoChains', () => {
  it('should group consecutive thoughts from same agent', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        content: 'First thought',
        status: 'thinking',
      },
      {
        id: 'thought-2',
        agentType: 'orchestrator',
        content: 'Second thought',
        status: 'thinking',
      },
      {
        id: 'thought-3',
        agentType: 'orchestrator',
        content: 'Third thought',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(1);
    expect(chains[0].items.length).toBe(3);
    expect(chains[0].agentType).toBe('orchestrator');
  });

  it('should separate thoughts from different agents', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        content: 'Orchestrator thought',
        status: 'thinking',
      },
      {
        id: 'thought-2',
        agentType: 'analyst',
        content: 'Analyst thought',
        status: 'thinking',
      },
      {
        id: 'thought-3',
        agentType: 'orchestrator',
        content: 'Another orchestrator thought',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(3);
    expect(chains[0].agentType).toBe('orchestrator');
    expect(chains[0].items.length).toBe(1);
    expect(chains[1].agentType).toBe('analyst');
    expect(chains[1].items.length).toBe(1);
    expect(chains[2].agentType).toBe('orchestrator');
    expect(chains[2].items.length).toBe(1);
  });

  it('should keep decisions as standalone chains', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        content: 'Thinking about routing',
        status: 'thinking',
      },
      {
        id: 'decision-1',
        agentType: 'orchestrator',
        content: 'Routing to analyst',
        status: 'decision',
      },
      {
        id: 'thought-2',
        agentType: 'orchestrator',
        content: 'After decision thought',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(3);

    // Decision should be in its own chain
    const decisionChain = chains[1];
    expect(decisionChain.items.length).toBe(1);
    expect(decisionChain.items[0].status).toBe('decision');
  });

  it('should filter content in all grouped thoughts', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        content: 'Task delegated. Depth: 2',
        summary: 'Summary 1',
        status: 'thinking',
      },
      {
        id: 'thought-2',
        agentType: 'orchestrator',
        content: 'Continuing analysis. Summary: test',
        summary: 'Summary 2',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(1);
    expect(chains[0].items.length).toBe(2);

    // All items should be filtered
    chains[0].items.forEach((item) => {
      expect(item.content).not.toContain('delegated');
      expect(item.content).not.toMatch(/depth\s*:\s*\d+/i);
      expect(item.content).not.toMatch(/summary\s*:/i);
      expect(item.summary).toBeUndefined();
    });
  });

  it('should handle empty array', () => {
    const chains = groupThoughtsIntoChains([]);
    expect(chains).toEqual([]);
  });

  it('should handle single thought', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        content: 'Single thought',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(1);
    expect(chains[0].items.length).toBe(1);
    expect(chains[0].items[0].id).toBe('thought-1');
  });

  it('should group thoughts with continuation markers', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        content: 'First step',
        status: 'thinking',
      },
      {
        id: 'thought-2',
        agentType: 'orchestrator',
        content: 'And then the second step',
        status: 'thinking',
      },
      {
        id: 'thought-3',
        agentType: 'orchestrator',
        content: 'Additionally, we need to check',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(1);
    expect(chains[0].items.length).toBe(3);
  });

  it('should group thoughts with numbered lists', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        content: '1. First item',
        status: 'thinking',
      },
      {
        id: 'thought-2',
        agentType: 'orchestrator',
        content: '2. Second item',
        status: 'thinking',
      },
      {
        id: 'thought-3',
        agentType: 'orchestrator',
        content: '3. Third item',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(1);
    expect(chains[0].items.length).toBe(3);
  });

  it('should group thoughts with bullet points', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        content: '- First point',
        status: 'thinking',
      },
      {
        id: 'thought-2',
        agentType: 'orchestrator',
        content: '• Second point',
        status: 'thinking',
      },
      {
        id: 'thought-3',
        agentType: 'orchestrator',
        content: '* Third point',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(1);
    expect(chains[0].items.length).toBe(3);
  });

  it('should preserve thought order within chains', () => {
    const thoughts: ThoughtChainItem[] = [
      { id: 'thought-1', agentType: 'orchestrator', content: 'First', status: 'thinking' },
      { id: 'thought-2', agentType: 'orchestrator', content: 'Second', status: 'thinking' },
      { id: 'thought-3', agentType: 'orchestrator', content: 'Third', status: 'thinking' },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains[0].items[0].id).toBe('thought-1');
    expect(chains[0].items[1].id).toBe('thought-2');
    expect(chains[0].items[2].id).toBe('thought-3');
  });

  it('should set chain title from first thought', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        title: 'Analysis Phase',
        content: 'First thought',
        status: 'thinking',
      },
      {
        id: 'thought-2',
        agentType: 'orchestrator',
        content: 'Second thought',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains[0].title).toBe('Analysis Phase');
  });

  it('should handle very short thoughts as continuations', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: 'thought-1',
        agentType: 'orchestrator',
        content: 'Yes',
        status: 'thinking',
      },
      {
        id: 'thought-2',
        agentType: 'orchestrator',
        content: 'This is the detailed explanation',
        status: 'thinking',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(1);
    expect(chains[0].items.length).toBe(2);
  });
});

describe('shouldRenderAsChain', () => {
  it('should return false for single-item chains', () => {
    const chain = {
      id: 'chain-1',
      agentType: 'orchestrator' as const,
      items: [
        {
          id: 'thought-1',
          agentType: 'orchestrator' as const,
          content: 'Single thought',
        },
      ],
    };

    expect(shouldRenderAsChain(chain)).toBe(false);
  });

  it('should return true for multi-item chains', () => {
    const chain = {
      id: 'chain-1',
      agentType: 'orchestrator' as const,
      items: [
        {
          id: 'thought-1',
          agentType: 'orchestrator' as const,
          content: 'First thought',
        },
        {
          id: 'thought-2',
          agentType: 'orchestrator' as const,
          content: 'Second thought',
        },
      ],
    };

    expect(shouldRenderAsChain(chain)).toBe(true);
  });

  it('should return true for chains with many items', () => {
    const chain = {
      id: 'chain-1',
      agentType: 'orchestrator' as const,
      items: Array.from({ length: 10 }, (_, i) => ({
        id: `thought-${i}`,
        agentType: 'orchestrator' as const,
        content: `Thought ${i}`,
      })),
    };

    expect(shouldRenderAsChain(chain)).toBe(true);
  });
});

describe('Edge cases and integration', () => {
  it('should handle mixed agent types and statuses', () => {
    const thoughts: ThoughtChainItem[] = [
      { id: '1', agentType: 'orchestrator', content: 'Orch 1', status: 'thinking' },
      { id: '2', agentType: 'orchestrator', content: 'Orch 2', status: 'thinking' },
      { id: '3', agentType: 'analyst', content: 'Analyst 1', status: 'analysis' },
      { id: '4', agentType: 'analyst', content: 'Analyst 2', status: 'analysis' },
      { id: '5', agentType: 'coder', content: 'Coder 1', status: 'thinking' },
      { id: '6', agentType: 'orchestrator', content: 'Decision', status: 'decision' },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(4);
    expect(chains[0].items.length).toBe(2); // Orch 1-2
    expect(chains[1].items.length).toBe(2); // Analyst 1-2
    expect(chains[2].items.length).toBe(1); // Coder 1
    expect(chains[3].items.length).toBe(1); // Decision (standalone)
  });

  it('should handle all content with indicators', () => {
    const thoughts: ThoughtChainItem[] = [
      {
        id: '1',
        agentType: 'orchestrator',
        content: 'Delegated task. Depth: 3. Summary: test',
        summary: 'Remove this',
      },
      {
        id: '2',
        agentType: 'orchestrator',
        content: 'Another delegated item. Reasoning depth: 2',
        summary: 'Remove this too',
      },
    ];

    const chains = groupThoughtsIntoChains(thoughts);

    expect(chains.length).toBe(1);
    chains[0].items.forEach((item) => {
      expect(item.content).not.toMatch(/delegat/i);
      expect(item.content).not.toMatch(/depth/i);
      expect(item.content).not.toMatch(/summary/i);
      expect(item.summary).toBeUndefined();
    });
  });
});

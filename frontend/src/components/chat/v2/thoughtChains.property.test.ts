/**
 * Property-Based Tests for Thought Chains
 * Feature: chat-visualization-v2
 *
 * Tests universal properties that should hold for all valid inputs.
 */

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  groupThoughtsIntoChains,
  filterThoughtContent,
  filterThoughtItem,
  shouldRenderAsChain,
  type ThoughtChainItem,
} from './thoughtChains';
import type { MindflowV2AgentType } from './types';

// Arbitraries for property-based testing
const agentTypeArb = fc.constantFrom<MindflowV2AgentType>(
  'orchestrator',
  'analyst',
  'coder',
  'researcher'
);

const thoughtStatusArb = fc.constantFrom(
  'thinking',
  'thought',
  'decision',
  'analysis',
  'planning'
);

const thoughtItemArb = fc.record({
  id: fc.string({ minLength: 1 }),
  agentType: agentTypeArb,
  title: fc.option(fc.string(), { nil: undefined }),
  status: fc.option(thoughtStatusArb, { nil: undefined }),
  content: fc.string({ minLength: 1 }),
  summary: fc.option(fc.string(), { nil: undefined }),
  defaultExpanded: fc.option(fc.boolean(), { nil: undefined }),
}) as fc.Arbitrary<ThoughtChainItem>;

/**
 * Feature: chat-visualization-v2, Property 27: Thought Chain Grouping
 *
 * For any sequence of related thought events, the thoughts should be
 * grouped together in a Thought Chain structure.
 *
 * Validates: Requirements 11.1
 */
describe('Property 27: Thought Chain Grouping', () => {
  it('should group consecutive thoughts from same agent', () => {
    fc.assert(
      fc.property(
        agentTypeArb,
        fc.array(fc.string({ minLength: 10 }), { minLength: 2, maxLength: 5 }),
        (agentType, contents) => {
          // Create consecutive thoughts from same agent
          const thoughts: ThoughtChainItem[] = contents.map((content, i) => ({
            id: `thought-${i}`,
            agentType,
            content,
            status: 'thinking',
          }));

          const chains = groupThoughtsIntoChains(thoughts);

          // Should create at least one chain
          expect(chains.length).toBeGreaterThan(0);

          // All thoughts should be included in chains
          const totalItems = chains.reduce((sum, chain) => sum + chain.items.length, 0);
          expect(totalItems).toBe(thoughts.length);

          // Each chain should have same agent type for all items
          chains.forEach((chain) => {
            const agentTypes = new Set(chain.items.map((item) => item.agentType));
            expect(agentTypes.size).toBe(1);
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should separate thoughts from different agents', () => {
    fc.assert(
      fc.property(
        fc.array(thoughtItemArb, { minLength: 2, maxLength: 10 }),
        (thoughts) => {
          const chains = groupThoughtsIntoChains(thoughts);

          // Each chain should only contain thoughts from one agent
          chains.forEach((chain) => {
            const agentTypes = new Set(chain.items.map((item) => item.agentType));
            expect(agentTypes.size).toBe(1);
            expect(chain.agentType).toBe(chain.items[0].agentType);
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should keep decisions as standalone chains', () => {
    fc.assert(
      fc.property(
        agentTypeArb,
        fc.string({ minLength: 10 }),
        fc.string({ minLength: 10 }),
        (agentType, content1, content2) => {
          const thoughts: ThoughtChainItem[] = [
            {
              id: 'thought-1',
              agentType,
              content: content1,
              status: 'thinking',
            },
            {
              id: 'decision-1',
              agentType,
              content: 'Decision content',
              status: 'decision',
            },
            {
              id: 'thought-2',
              agentType,
              content: content2,
              status: 'thinking',
            },
          ];

          const chains = groupThoughtsIntoChains(thoughts);

          // Decision should be in its own chain
          const decisionChain = chains.find((chain) =>
            chain.items.some((item) => item.status === 'decision')
          );

          if (decisionChain) {
            // Decision chain should only contain the decision
            expect(decisionChain.items.length).toBe(1);
            expect(decisionChain.items[0].status).toBe('decision');
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should preserve thought order within chains', () => {
    fc.assert(
      fc.property(
        fc.array(thoughtItemArb, { minLength: 1, maxLength: 10 }),
        (thoughts) => {
          const chains = groupThoughtsIntoChains(thoughts);

          // Reconstruct order from chains
          const reconstructed = chains.flatMap((chain) => chain.items);

          // IDs should match original order (after filtering)
          const originalIds = thoughts.map((t) => t.id);
          const reconstructedIds = reconstructed.map((t) => t.id);

          expect(reconstructedIds).toEqual(originalIds);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should handle empty input gracefully', () => {
    const chains = groupThoughtsIntoChains([]);
    expect(chains).toEqual([]);
  });

  it('should create chain with single thought for standalone thoughts', () => {
    fc.assert(
      fc.property(thoughtItemArb, (thought) => {
        const chains = groupThoughtsIntoChains([thought]);

        expect(chains.length).toBe(1);
        expect(chains[0].items.length).toBe(1);
        expect(chains[0].items[0].id).toBe(thought.id);
      }),
      { numRuns: 100 }
    );
  });
});

/**
 * Feature: chat-visualization-v2, Property 28: Thought Chain Content Filtering
 *
 * For any thought chain, the chain should not include "Delegated" indicators,
 * reasoning depth indicators, or thought summary elements.
 *
 * Validates: Requirements 11.3, 11.4, 11.5
 */
describe('Property 28: Thought Chain Content Filtering', () => {
  it('should remove "Delegated" indicators from content', () => {
    fc.assert(
      fc.property(
        fc.string(),
        fc.constantFrom('delegated', 'Delegated', 'DELEGATED', 'delegation', 'Delegation'),
        fc.string(),
        (prefix, indicator, suffix) => {
          const content = `${prefix} ${indicator} ${suffix}`;
          const filtered = filterThoughtContent(content);

          // Should not contain the indicator (case-insensitive)
          expect(filtered.toLowerCase()).not.toContain(indicator.toLowerCase());
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should remove reasoning depth indicators from content', () => {
    fc.assert(
      fc.property(
        fc.string(),
        fc.integer({ min: 1, max: 5 }),
        fc.string(),
        (prefix, depth, suffix) => {
          const patterns = [
            `${prefix} Depth: ${depth} ${suffix}`,
            `${prefix} depth: ${depth} ${suffix}`,
            `${prefix} Reasoning depth: ${depth} ${suffix}`,
            `${prefix} reasoning depth: ${depth} ${suffix}`,
          ];

          patterns.forEach((content) => {
            const filtered = filterThoughtContent(content);

            // Should not contain depth indicator
            expect(filtered.toLowerCase()).not.toMatch(/depth\s*:\s*\d+/);
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should remove thought summary markers from content', () => {
    fc.assert(
      fc.property(
        fc.string(),
        fc.string(),
        (prefix, suffix) => {
          const patterns = [
            `${prefix} Summary: ${suffix}`,
            `${prefix} summary: ${suffix}`,
            `${prefix} Thought Summary: ${suffix}`,
            `${prefix} thought summary: ${suffix}`,
          ];

          patterns.forEach((content) => {
            const filtered = filterThoughtContent(content);

            // Should not contain summary marker
            expect(filtered.toLowerCase()).not.toMatch(/(thought\s+)?summary\s*:/);
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should remove summary field from thought items', () => {
    fc.assert(
      fc.property(thoughtItemArb, (thought) => {
        const filtered = filterThoughtItem(thought);

        // Summary should be undefined
        expect(filtered.summary).toBeUndefined();
      }),
      { numRuns: 100 }
    );
  });

  it('should filter all items in grouped chains', () => {
    fc.assert(
      fc.property(
        fc.array(thoughtItemArb, { minLength: 1, maxLength: 10 }),
        (thoughts) => {
          // Add indicators to some thoughts
          const thoughtsWithIndicators = thoughts.map((t, i) => ({
            ...t,
            content:
              i % 2 === 0
                ? `${t.content} Delegated Depth: 2 Summary: test`
                : t.content,
            summary: i % 3 === 0 ? 'Test summary' : t.summary,
          }));

          const chains = groupThoughtsIntoChains(thoughtsWithIndicators);

          // All items in all chains should be filtered
          chains.forEach((chain) => {
            chain.items.forEach((item) => {
              expect(item.summary).toBeUndefined();
              expect(item.content.toLowerCase()).not.toContain('delegated');
              expect(item.content.toLowerCase()).not.toMatch(/depth\s*:\s*\d+/);
              expect(item.content.toLowerCase()).not.toMatch(/summary\s*:/);
            });
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should preserve other content while filtering', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 10 }).filter((s) => !s.toLowerCase().includes('delegated')),
        (content) => {
          const withIndicators = `${content} Delegated Depth: 3 Summary: test`;
          const filtered = filterThoughtContent(withIndicators);

          // Original content should still be present (after whitespace normalization)
          const normalizedContent = content.replace(/\s+/g, ' ').trim();
          const normalizedFiltered = filtered.replace(/\s+/g, ' ').trim();

          if (normalizedContent.length > 0) {
            expect(normalizedFiltered).toContain(normalizedContent);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should handle content with no indicators gracefully', () => {
    fc.assert(
      fc.property(
        fc
          .string({ minLength: 1 })
          .filter(
            (s) =>
              !s.toLowerCase().includes('delegated') &&
              !s.toLowerCase().includes('depth') &&
              !s.toLowerCase().includes('summary')
          ),
        (content) => {
          const filtered = filterThoughtContent(content);

          // Content should be mostly unchanged (except whitespace normalization)
          expect(filtered.replace(/\s+/g, ' ').trim()).toBe(
            content.replace(/\s+/g, ' ').trim()
          );
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Additional property: Chain rendering decision
 */
describe('Property: Chain Rendering Decision', () => {
  it('should render as chain only when multiple items exist', () => {
    fc.assert(
      fc.property(
        fc.array(thoughtItemArb, { minLength: 1, maxLength: 10 }),
        (thoughts) => {
          const chains = groupThoughtsIntoChains(thoughts);

          chains.forEach((chain) => {
            const shouldBeChain = shouldRenderAsChain(chain);

            if (chain.items.length === 1) {
              expect(shouldBeChain).toBe(false);
            } else {
              expect(shouldBeChain).toBe(true);
            }
          });
        }
      ),
      { numRuns: 100 }
    );
  });
});

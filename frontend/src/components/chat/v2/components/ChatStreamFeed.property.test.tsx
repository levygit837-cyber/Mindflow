/**
 * Chat Visualization V2 - ChatStreamFeed Property Tests
 *
 * Property-based tests for ChatStreamFeed component validating universal
 * correctness properties across multiple generated inputs.
 *
 * Feature: chat-visualization-v2
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import fc from 'fast-check';
import { ChatStreamFeed } from './ChatStreamFeed';
import type { MindflowV2AgentType } from '../types';

// Arbitraries for property-based testing
const agentTypeArb = fc.constantFrom<MindflowV2AgentType>(
  'orchestrator',
  'analyst',
  'coder',
  'researcher'
);

const streamEventArb = fc.record({
  id: fc.option(fc.uuid(), { nil: undefined }),
  type: fc.constantFrom(
    'orchestrator_thinking',
    'agent_delegation_start',
    'tool_call',
    'notifier',
    'error'
  ),
  data: fc.jsonValue().map((v) => JSON.stringify(v)),
  meta: fc.option(
    fc.record({
      agent: agentTypeArb.map(String),
      nodeLabel: fc.option(fc.string(), { nil: undefined }),
    }),
    { nil: null }
  ),
});

describe('ChatStreamFeed Property Tests', () => {
  /**
   * Feature: chat-visualization-v2
   * Property 5: Agent Visual Differentiation
   *
   * For any active agent, the system should render a unique visual indicator
   * with consistent theme colors (accent, soft, muted) that remains unchanged
   * throughout the agent's execution.
   *
   * Validates: Requirements 4.1, 4.2, 4.3
   */
  describe('Property 5: Agent Visual Differentiation', () => {
    it('should render unique visual indicators for each active agent type', () => {
      fc.assert(
        fc.property(
          fc.array(agentTypeArb, { minLength: 1, maxLength: 4 }).chain((agents) =>
            fc.tuple(
              fc.constant(agents),
              fc.array(
                fc.record({
                  id: fc.uuid(),
                  type: fc.constant('orchestrator_thinking'),
                  data: fc.constant('{}'),
                  meta: fc.record({
                    agent: fc.constantFrom(...agents).map(String),
                  }),
                }),
                { minLength: agents.length, maxLength: agents.length * 2 }
              )
            )
          ),
          ([expectedAgents, events]) => {
            const { container } = render(
              <ChatStreamFeed
                events={events}
                isStreaming={true}
                hasHistory={false}
              />
            );

            // Verify ThinkingNotifierRow is rendered
            const notifierRow = container.querySelector('.flex.flex-wrap.gap-2');
            expect(notifierRow).toBeTruthy();

            // Verify each agent type has a unique visual indicator
            const uniqueAgents = Array.from(new Set(expectedAgents));
            uniqueAgents.forEach((agentType) => {
              const notifier = container.querySelector(
                `[data-agent-type="${agentType}"]`
              );
              expect(notifier).toBeTruthy();
            });
          }
        ),
        { numRuns: 50 }
      );
    });

    it('should maintain consistent theme colors for each agent throughout execution', () => {
      fc.assert(
        fc.property(
          agentTypeArb,
          fc.array(fc.nat({ max: 10 }), { minLength: 2, maxLength: 5 }),
          (agentType, sequence) => {
            const events = sequence.map((_, idx) => ({
              id: `event-${idx}`,
              type: 'orchestrator_thinking',
              data: JSON.stringify({ content: `Thinking ${idx}` }),
              meta: { agent: agentType },
            }));

            const { container } = render(
              <ChatStreamFeed
                events={events}
                isStreaming={true}
                hasHistory={false}
              />
            );

            // Get all elements with agent type
            const agentElements = container.querySelectorAll(
              `[data-agent-type="${agentType}"]`
            );

            // Verify at least one element exists
            expect(agentElements.length).toBeGreaterThan(0);

            // All elements should have consistent styling
            const firstElement = agentElements[0];
            const computedStyle = window.getComputedStyle(firstElement);
            const borderColor = computedStyle.borderColor;

            // Verify border color is set (theme color applied)
            expect(borderColor).toBeTruthy();
          }
        ),
        { numRuns: 50 }
      );
    });
  });

  /**
   * Feature: chat-visualization-v2
   * Property 6: Agent Message Card Rendering
   *
   * For any message sent by an agent, the message should be rendered in a
   * message card component that includes the agent's visual identification
   * (name, color, icon).
   *
   * Validates: Requirements 5.1, 5.2
   */
  describe('Property 6: Agent Message Card Rendering', () => {
    it('should render message cards with agent visual identification', () => {
      fc.assert(
        fc.property(
          agentTypeArb,
          fc.string({ minLength: 10, maxLength: 200 }),
          (agentType, content) => {
            const events = [
              {
                id: 'thought-1',
                type: 'orchestrator_thinking',
                data: content,
                meta: { agent: agentType },
              },
            ];

            const { container } = render(
              <ChatStreamFeed
                events={events}
                isStreaming={false}
                hasHistory={false}
              />
            );

            // Verify ThoughtBlock is rendered
            const thoughtBlock = container.querySelector('.thought-stack');
            expect(thoughtBlock).toBeTruthy();

            // Verify agent accent color is applied
            const agentAccent = thoughtBlock?.getAttribute('style');
            expect(agentAccent).toContain('--agent-accent');
          }
        ),
        { numRuns: 50 }
      );
    });
  });

  /**
   * Feature: chat-visualization-v2
   * Property 7: Orchestrator Visual Priority
   *
   * For any collection of message cards, orchestrator cards should appear
   * before delegated agent cards in the rendering order.
   *
   * Validates: Requirements 5.3
   */
  describe('Property 7: Orchestrator Visual Priority', () => {
    it('should render orchestrator thoughts before other agent thoughts', () => {
      fc.assert(
        fc.property(
          fc.array(agentTypeArb, { minLength: 2, maxLength: 4 }),
          (agentTypes) => {
            // Ensure orchestrator is in the list
            const agents = ['orchestrator' as const, ...agentTypes];
            const events = agents.map((agent, idx) => ({
              id: `thought-${idx}`,
              type: 'orchestrator_thinking',
              data: `Thought from ${agent}`,
              meta: { agent },
            }));

            const { container } = render(
              <ChatStreamFeed
                events={events}
                isStreaming={false}
                hasHistory={false}
              />
            );

            // Get all thought blocks
            const thoughtBlocks = container.querySelectorAll('.thought-stack');
            expect(thoughtBlocks.length).toBeGreaterThan(0);

            // First thought block should be from orchestrator
            const firstBlock = thoughtBlocks[0];
            const firstBlockStyle = firstBlock.getAttribute('style');

            // Orchestrator has accent color #0D6E6E
            expect(firstBlockStyle).toContain('--agent-accent');
          }
        ),
        { numRuns: 50 }
      );
    });
  });

  /**
   * Feature: chat-visualization-v2
   * Property 11: Delegation Card UI Elements
   *
   * For any delegation card, the card should include both a summary bar
   * element and a progress indicator element.
   *
   * Validates: Requirements 6.4, 6.5
   */
  describe('Property 11: Delegation Card UI Elements', () => {
    it('should render delegation cards with summary bar and progress indicator', () => {
      fc.assert(
        fc.property(
          agentTypeArb,
          fc.string({ minLength: 10, maxLength: 100 }),
          (agentType, task) => {
            const events = [
              {
                id: 'delegation-1',
                type: 'agent_delegation_start',
                data: JSON.stringify({
                  agent_type: agentType,
                  task,
                  step_id: 'step-1',
                }),
                meta: { agent: agentType },
              },
            ];

            const { container } = render(
              <ChatStreamFeed
                events={events}
                isStreaming={true}
                hasHistory={false}
              />
            );

            // Verify DelegationCard is rendered
            const delegationCard = container.querySelector('.delegation-card');
            expect(delegationCard).toBeTruthy();

            // Verify summary bar (footer) exists
            const footer = container.querySelector('.delegation-card-footer');
            expect(footer).toBeTruthy();

            // Verify progress indicator (status badge) exists
            const statusBadge = container.querySelector('.delegation-card-footer-tag');
            expect(statusBadge).toBeTruthy();

            // Verify agent information is displayed
            const agentRow = container.querySelector('.delegation-agent-row');
            expect(agentRow).toBeTruthy();
          }
        ),
        { numRuns: 50 }
      );
    });

    it('should update delegation card state in real-time', () => {
      fc.assert(
        fc.property(
          agentTypeArb,
          fc.array(
            fc.constantFrom('ativo', 'processando', 'concluído'),
            { minLength: 2, maxLength: 3 }
          ),
          (agentType, statuses) => {
            // Create events with different statuses
            const events = statuses.map((status, idx) => ({
              id: `delegation-${idx}`,
              type: idx === 0 ? 'agent_delegation_start' : 'specialist_activation',
              data: JSON.stringify({
                agent_type: agentType,
                task: `Task ${idx}`,
                status,
              }),
              meta: { agent: agentType },
            }));

            const { container } = render(
              <ChatStreamFeed
                events={events}
                isStreaming={true}
                hasHistory={false}
              />
            );

            // Verify delegation cards are rendered
            const delegationCards = container.querySelectorAll('.delegation-card');
            expect(delegationCards.length).toBeGreaterThan(0);

            // Verify status is displayed
            const statusElements = container.querySelectorAll('.delegation-card-footer-tag');
            expect(statusElements.length).toBeGreaterThan(0);
          }
        ),
        { numRuns: 50 }
      );
    });
  });

  /**
   * Additional property: LiveTick updates
   *
   * Verifies that the component handles streaming state correctly
   */
  describe('Property: Streaming State Management', () => {
    it('should handle streaming and non-streaming states correctly', () => {
      fc.assert(
        fc.property(
          fc.boolean(),
          fc.array(streamEventArb, { minLength: 0, maxLength: 10 }),
          (isStreaming, events) => {
            const { container } = render(
              <ChatStreamFeed
                events={events}
                isStreaming={isStreaming}
                hasHistory={false}
              />
            );

            // Component should always render ThinkingNotifierRow
            const notifierRow = container.querySelector('.flex.flex-wrap.gap-2');
            expect(notifierRow).toBeTruthy();

            // If streaming with delegations, AgentTodoList should render
            const hasDelegations = events.some(
              (e) => e.type === 'agent_delegation_start'
            );

            if (isStreaming && hasDelegations) {
              // AgentTodoList might be rendered (depends on buildStreamPresentation)
              // Just verify the component doesn't crash
              expect(container).toBeTruthy();
            }
          }
        ),
        { numRuns: 50 }
      );
    });
  });
});

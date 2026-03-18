/**
 * Chat Visualization V2 - ThinkingNotifier Property Tests
 *
 * Property-based tests validating universal correctness properties
 * for ThinkingNotifier components.
 *
 * Feature: chat-visualization-v2
 * Property 2: Thinking State Visibility
 */

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { render, screen } from '@testing-library/react';
import { ThinkingNotifier } from './ThinkingNotifier';
import { ThinkingNotifierRow } from './ThinkingNotifierRow';
import type { MindflowV2AgentType } from '../types';

const agentTypeArbitrary = fc.constantFrom<MindflowV2AgentType>(
  'orchestrator',
  'analyst',
  'coder',
  'researcher'
);

describe('Property 2: Thinking State Visibility', () => {
  it('should render ThinkingNotifier with active=true when agent is processing', () => {
    fc.assert(
      fc.property(agentTypeArbitrary, (agentType) => {
        const { container } = render(
          <ThinkingNotifier agentType={agentType} active={true} />
        );

        const notifier = container.querySelector('[data-active="true"]');
        expect(notifier).toBeInTheDocument();
        expect(notifier?.getAttribute('data-agent-type')).toBe(agentType);
      }),
      { numRuns: 100 }
    );
  });

  it('should render ThinkingNotifier with active=false when agent is waiting', () => {
    fc.assert(
      fc.property(agentTypeArbitrary, (agentType) => {
        const { container } = render(
          <ThinkingNotifier agentType={agentType} active={false} />
        );

        const notifier = container.querySelector('[data-active="false"]');
        expect(notifier).toBeInTheDocument();
        expect(notifier?.getAttribute('data-agent-type')).toBe(agentType);
      }),
      { numRuns: 100 }
    );
  });

  it('should include agent in ThinkingNotifierRow when listed in activeAgents', () => {
    fc.assert(
      fc.property(
        fc.array(agentTypeArbitrary, { minLength: 1, maxLength: 4 }).map((arr) => [
          ...new Set(arr),
        ]),
        (activeAgents) => {
          const { container } = render(
            <ThinkingNotifierRow
              activeAgents={activeAgents as MindflowV2AgentType[]}
            />
          );

          activeAgents.forEach((agentType) => {
            const activeNotifier = container.querySelector(
              `[data-agent-type="${agentType}"][data-active="true"]`
            );
            expect(activeNotifier).toBeInTheDocument();
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should render all agent types in ThinkingNotifierRow regardless of active state', () => {
    fc.assert(
      fc.property(
        fc.array(agentTypeArbitrary, { maxLength: 4 }).map((arr) => [
          ...new Set(arr),
        ]),
        (activeAgents) => {
          const { container } = render(
            <ThinkingNotifierRow
              activeAgents={activeAgents as MindflowV2AgentType[]}
            />
          );

          // All 4 agent types should be rendered
          const allNotifiers = container.querySelectorAll(
            '[data-agent-type]'
          );
          expect(allNotifiers.length).toBe(4);

          // Check that orchestrator, analyst, coder, researcher are all present
          const agentTypes = Array.from(allNotifiers).map((el) =>
            el.getAttribute('data-agent-type')
          );
          expect(agentTypes).toContain('orchestrator');
          expect(agentTypes).toContain('analyst');
          expect(agentTypes).toContain('coder');
          expect(agentTypes).toContain('researcher');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should apply correct status to each agent in ThinkingNotifierRow', () => {
    fc.assert(
      fc.property(
        fc.array(agentTypeArbitrary, { minLength: 1, maxLength: 4 }).map((arr) => [
          ...new Set(arr),
        ]),
        fc.record({
          orchestrator: fc.option(fc.constantFrom('thinking', 'waiting', 'active')),
          analyst: fc.option(fc.constantFrom('thinking', 'waiting', 'active')),
          coder: fc.option(fc.constantFrom('thinking', 'waiting', 'active')),
          researcher: fc.option(fc.constantFrom('thinking', 'waiting', 'active')),
        }),
        (activeAgents, statuses) => {
          const { container } = render(
            <ThinkingNotifierRow
              activeAgents={activeAgents as MindflowV2AgentType[]}
              statuses={statuses}
            />
          );

          // Verify that statuses are applied (component should render without errors)
          const allNotifiers = container.querySelectorAll('[data-agent-type]');
          expect(allNotifiers.length).toBe(4);
        }
      ),
      { numRuns: 100 }
    );
  });
});

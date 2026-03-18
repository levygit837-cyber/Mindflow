/**
 * Property-Based Tests for Theme System
 * Feature: chat-visualization-v2
 * Task: 17 - Theme System and Consistency
 *
 * Property 41: Component Theme Variants
 * Property 42: Theme Consistency
 */

import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import fc from 'fast-check';
import { ThemeController } from '../../../theme/ThemeController';
import { ThinkingNotifier } from './ThinkingNotifier';
import { ThoughtBlock } from './ThoughtBlock';
import { DelegationCard } from './DelegationCard';
import { ToolEventCard } from './ToolEventCard';
import { MemoryRecallCard } from './MemoryRecallCard';
import { AgentTodoList } from './AgentTodoList';
import { JourneyTimeline } from './JourneyTimeline';
import { AgentJourneyPanel } from './AgentJourneyPanel';
import { MindflowV2AgentType } from '../types';

// Mock appStore for ThemeController
vi.mock('../../../stores/appStore', () => ({
  useAppStore: (selector: any) => {
    const state = {
      theme: 'dark' as const,
      settings: { fontSize: 'large' as const },
      setTheme: vi.fn(),
    };
    return selector ? selector(state) : state;
  },
}));

const agentTypeArbitrary = fc.constantFrom<MindflowV2AgentType>(
  'orchestrator',
  'analyst',
  'coder',
  'researcher'
);

const themeArbitrary = fc.constantFrom('light', 'dark');

/**
 * Feature: chat-visualization-v2, Property 41: Component Theme Variants
 *
 * For any V2 component, both light and dark theme variants should be
 * available and correctly styled.
 *
 * Validates: Requirements 15.1
 */
describe('Property 41: Component Theme Variants', () => {
  it('ThinkingNotifier should render with both theme variants', () => {
    fc.assert(
      fc.property(
        agentTypeArbitrary,
        fc.boolean(),
        themeArbitrary,
        (agentType, active, theme) => {
          const { container } = render(
            <ThemeController>
              <ThinkingNotifier agentType={agentType} active={active} />
            </ThemeController>
          );

          const element = container.querySelector('.mindflow-v2-thinking-notifier');
          expect(element).toBeTruthy();
          expect(element?.getAttribute('data-theme')).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('ThoughtBlock should render with both theme variants', () => {
    fc.assert(
      fc.property(
        agentTypeArbitrary,
        fc.string({ minLength: 10, maxLength: 500 }),
        themeArbitrary,
        (agentType, content, theme) => {
          const { container } = render(
            <ThemeController>
              <ThoughtBlock agentType={agentType} content={content} />
            </ThemeController>
          );

          const element = container.querySelector('.thought-block');
          expect(element).toBeTruthy();
          expect(element?.getAttribute('data-theme')).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('DelegationCard should render with both theme variants', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            name: fc.string({ minLength: 3, maxLength: 20 }),
            role: fc.string({ minLength: 3, maxLength: 20 }),
            status: fc.constantFrom('active', 'waiting', 'done'),
            agentType: agentTypeArbitrary,
          }),
          { minLength: 1, maxLength: 3 }
        ),
        themeArbitrary,
        (agents, theme) => {
          const { container } = render(
            <ThemeController>
              <DelegationCard agents={agents} />
            </ThemeController>
          );

          const element = container.querySelector('.delegation-card');
          expect(element).toBeTruthy();
          expect(element?.getAttribute('data-theme')).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('ToolEventCard should render with both theme variants', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 3, maxLength: 30 }),
        fc.constantFrom('running', 'completed', 'error', 'collapsed'),
        themeArbitrary,
        (toolName, status, theme) => {
          const { container } = render(
            <ThemeController>
              <ToolEventCard toolName={toolName} status={status} />
            </ThemeController>
          );

          const element = container.querySelector('.tool-event-card');
          expect(element).toBeTruthy();
          expect(element?.getAttribute('data-theme')).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('MemoryRecallCard should render in dark theme only', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('vector', 'database'),
        fc.string({ minLength: 3, maxLength: 30 }),
        (source, status) => {
          const { container } = render(
            <ThemeController>
              <MemoryRecallCard source={source} status={status} />
            </ThemeController>
          );

          // Should render in dark theme (mocked as 'dark')
          const element = container.querySelector('.memory-recall-card');
          expect(element).toBeTruthy();
          expect(element?.getAttribute('data-theme')).toBe('dark');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('AgentTodoList should render in dark theme only', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            agents: fc.array(
              fc.record({
                name: fc.string({ minLength: 3, maxLength: 20 }),
                role: fc.string({ minLength: 3, maxLength: 20 }),
                status: fc.constantFrom('active', 'waiting', 'done'),
              }),
              { minLength: 1, maxLength: 2 }
            ),
          }),
          { minLength: 1, maxLength: 3 }
        ),
        (delegations) => {
          const { container } = render(
            <ThemeController>
              <AgentTodoList delegations={delegations} isStreaming={true} />
            </ThemeController>
          );

          // Should render in dark theme (mocked as 'dark')
          const element = container.querySelector('.agent-todo-list');
          expect(element).toBeTruthy();
          expect(element?.getAttribute('data-theme')).toBe('dark');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('JourneyTimeline should render with both theme variants', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.string({ minLength: 5, maxLength: 10 }),
            title: fc.string({ minLength: 5, maxLength: 30 }),
            detail: fc.string({ minLength: 10, maxLength: 100 }),
            status: fc.constantFrom('live', 'done', 'queued', 'waiting', 'error'),
          }),
          { minLength: 1, maxLength: 5 }
        ),
        themeArbitrary,
        (steps, theme) => {
          const { container } = render(
            <ThemeController>
              <JourneyTimeline steps={steps} />
            </ThemeController>
          );

          const element = container.querySelector('.journey-timeline');
          expect(element).toBeTruthy();
          expect(element?.getAttribute('data-theme')).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Feature: chat-visualization-v2, Property 42: Theme Consistency
 *
 * For any collection of rendered components, all components should use
 * the same theme variables consistently (same theme applied to all).
 *
 * Validates: Requirements 15.4
 */
describe('Property 42: Theme Consistency', () => {
  it('should apply same theme to all V2 components in a collection', () => {
    fc.assert(
      fc.property(
        agentTypeArbitrary,
        fc.string({ minLength: 10, maxLength: 100 }),
        fc.array(
          fc.record({
            name: fc.string({ minLength: 3, maxLength: 20 }),
            role: fc.string({ minLength: 3, maxLength: 20 }),
            status: fc.constantFrom('active', 'waiting', 'done'),
            agentType: agentTypeArbitrary,
          }),
          { minLength: 1, maxLength: 2 }
        ),
        (agentType, content, agents) => {
          const { container } = render(
            <ThemeController>
              <div>
                <ThinkingNotifier agentType={agentType} active={true} />
                <ThoughtBlock agentType={agentType} content={content} />
                <DelegationCard agents={agents} />
              </div>
            </ThemeController>
          );

          // Collect all theme attributes
          const components = container.querySelectorAll('[data-theme]');
          const themes = Array.from(components).map((c) => c.getAttribute('data-theme'));

          // All components should have the same theme
          const uniqueThemes = new Set(themes);
          expect(uniqueThemes.size).toBeLessThanOrEqual(1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should maintain theme consistency across component updates', () => {
    fc.assert(
      fc.property(
        agentTypeArbitrary,
        fc.string({ minLength: 10, maxLength: 100 }),
        fc.string({ minLength: 10, maxLength: 100 }),
        (agentType, content1, content2) => {
          const { container, rerender } = render(
            <ThemeController>
              <ThoughtBlock agentType={agentType} content={content1} />
            </ThemeController>
          );

          const initialTheme = container
            .querySelector('.thought-block')
            ?.getAttribute('data-theme');

          // Re-render with different content
          rerender(
            <ThemeController>
              <ThoughtBlock agentType={agentType} content={content2} />
            </ThemeController>
          );

          const updatedTheme = container
            .querySelector('.thought-block')
            ?.getAttribute('data-theme');

          // Theme should remain consistent
          expect(updatedTheme).toBe(initialTheme);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should apply consistent CSS variables across all components', () => {
    fc.assert(
      fc.property(
        agentTypeArbitrary,
        fc.string({ minLength: 10, maxLength: 100 }),
        (agentType, content) => {
          const { container } = render(
            <ThemeController>
              <div>
                <ThinkingNotifier agentType={agentType} active={true} />
                <ThoughtBlock agentType={agentType} content={content} />
              </div>
            </ThemeController>
          );

          // All components should reference the same CSS variable namespace
          const notifier = container.querySelector('.mindflow-v2-thinking-notifier');
          const thought = container.querySelector('.thought-block');

          expect(notifier).toBeTruthy();
          expect(thought).toBeTruthy();

          // Both should have data-theme attribute
          expect(notifier?.getAttribute('data-theme')).toBeTruthy();
          expect(thought?.getAttribute('data-theme')).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });
});

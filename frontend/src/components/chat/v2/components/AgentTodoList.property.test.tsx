/**
 * Chat Visualization V2 - AgentTodoList Property Tests
 *
 * Property-based tests for AgentTodoList component validating universal
 * correctness properties across multiple generated inputs.
 *
 * Feature: chat-visualization-v2
 * Properties: 19, 20, 21, 22
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import fc from 'fast-check';
import { AgentTodoList } from './AgentTodoList';
import { DelegationCardProps } from './DelegationCard';
import { MindflowV2AgentType } from '../types';

describe('AgentTodoList Property Tests', () => {
  let originalTheme: string | null;

  beforeEach(() => {
    // Save original theme
    originalTheme = document.documentElement.getAttribute('data-theme');
  });

  afterEach(() => {
    // Restore original theme
    if (originalTheme) {
      document.documentElement.setAttribute('data-theme', originalTheme);
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  });

  /**
   * Property 19: Todo List Creation
   *
   * For any task plan creation event from the orchestrator,
   * an AgentTodoList component should be rendered.
   *
   * Validates: Requirements 9.1
   */
  describe('Property 19: Todo List Creation', () => {
    it('should render AgentTodoList when delegations exist and streaming', () => {
      // Set dark theme
      document.documentElement.setAttribute('data-theme', 'dark');

      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              agents: fc.array(
                fc.record({
                  name: fc.constantFrom('Analyst', 'Coder', 'Researcher'),
                  role: fc.constantFrom('Orchestrator', 'Specialist'),
                  status: fc.constantFrom('ativo', 'aguardando', 'concluído'),
                  agentType: fc.constantFrom<MindflowV2AgentType>(
                    'analyst',
                    'coder',
                    'researcher'
                  ),
                }),
                { minLength: 1, maxLength: 3 }
              ),
            }),
            { minLength: 1, maxLength: 5 }
          ),
          (delegations) => {
            const { container } = render(
              <AgentTodoList delegations={delegations} isStreaming={true} />
            );

            // Should render the todo list container
            const todoList = container.querySelector('.agent-todo-list');
            expect(todoList).toBeTruthy();

            // Should render header
            expect(container.textContent).toContain('Tarefas do Orquestrador');

            // Should render "ao vivo" badge
            expect(container.textContent).toContain('ao vivo');
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should render correct number of delegation cards', () => {
      document.documentElement.setAttribute('data-theme', 'dark');

      fc.assert(
        fc.property(
          fc.integer({ min: 1, max: 10 }).chain((count) =>
            fc.tuple(
              fc.constant(count),
              fc.array(
                fc.record({
                  agents: fc.array(
                    fc.record({
                      name: fc.string({ minLength: 1, maxLength: 20 }),
                      role: fc.string({ minLength: 1, maxLength: 20 }),
                      status: fc.string({ minLength: 1, maxLength: 20 }),
                    }),
                    { minLength: 1, maxLength: 2 }
                  ),
                }),
                { minLength: count, maxLength: count }
              )
            )
          ),
          ([expectedCount, delegations]) => {
            const { container } = render(
              <AgentTodoList delegations={delegations} isStreaming={true} />
            );

            // Count rendered delegation cards
            const cards = container.querySelectorAll('.simple-delegation-card');
            expect(cards.length).toBe(expectedCount);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Property 20: Todo List Dark Theme Support
   *
   * For any todo list component in dark theme,
   * the component should render with appropriate dark theme styling.
   *
   * Validates: Requirements 9.2
   */
  describe('Property 20: Todo List Dark Theme Support', () => {
    it('should render in dark theme with proper styling', () => {
      document.documentElement.setAttribute('data-theme', 'dark');

      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              agents: fc.array(
                fc.record({
                  name: fc.string({ minLength: 1, maxLength: 20 }),
                  role: fc.string({ minLength: 1, maxLength: 20 }),
                  status: fc.string({ minLength: 1, maxLength: 20 }),
                }),
                { minLength: 1, maxLength: 2 }
              ),
            }),
            { minLength: 1, maxLength: 5 }
          ),
          (delegations) => {
            const { container } = render(
              <AgentTodoList delegations={delegations} isStreaming={true} />
            );

            const todoList = container.querySelector('.agent-todo-list');
            expect(todoList).toBeTruthy();

            // Should have dark theme structure (header, badges, delegation cards)
            expect(todoList?.querySelector('h3')).toBeTruthy();
            expect(container.textContent).toContain('Tarefas do Orquestrador');
            expect(container.textContent).toContain('ao vivo');
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Property 21: Todo List Light Theme Exclusion
   *
   * For any task plan event when light theme is active,
   * no AgentTodoList component should be rendered.
   *
   * Validates: Requirements 9.3
   */
  describe('Property 21: Todo List Light Theme Exclusion', () => {
    it('should not render in light theme', () => {
      document.documentElement.setAttribute('data-theme', 'light');

      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              agents: fc.array(
                fc.record({
                  name: fc.string({ minLength: 1, maxLength: 20 }),
                  role: fc.string({ minLength: 1, maxLength: 20 }),
                  status: fc.string({ minLength: 1, maxLength: 20 }),
                }),
                { minLength: 1, maxLength: 2 }
              ),
            }),
            { minLength: 1, maxLength: 5 }
          ),
          fc.boolean(),
          (delegations, isStreaming) => {
            const { container } = render(
              <AgentTodoList delegations={delegations} isStreaming={isStreaming} />
            );

            // Should not render anything in light theme
            const todoList = container.querySelector('.agent-todo-list');
            expect(todoList).toBeFalsy();
            expect(container.firstChild).toBeFalsy();
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Property 22: Todo List Real-Time Updates
   *
   * For any todo list, when a task completion event occurs,
   * the todo list state should update to reflect the completion.
   *
   * Validates: Requirements 9.4
   */
  describe('Property 22: Todo List Real-Time Updates', () => {
    it('should update when delegations change', () => {
      document.documentElement.setAttribute('data-theme', 'dark');

      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              agents: fc.array(
                fc.record({
                  name: fc.string({ minLength: 1, maxLength: 20 }),
                  role: fc.string({ minLength: 1, maxLength: 20 }),
                  status: fc.constantFrom('ativo', 'aguardando'),
                }),
                { minLength: 1, maxLength: 2 }
              ),
            }),
            { minLength: 1, maxLength: 5 }
          ),
          (initialDelegations) => {
            const { container, rerender } = render(
              <AgentTodoList delegations={initialDelegations} isStreaming={true} />
            );

            const initialCards = container.querySelectorAll('.simple-delegation-card');
            const initialCount = initialCards.length;

            // Update delegations with completed status
            const updatedDelegations = initialDelegations.map((d) => ({
              ...d,
              agents: d.agents.map((a) => ({ ...a, status: 'concluído' })),
            }));

            rerender(
              <AgentTodoList delegations={updatedDelegations} isStreaming={true} />
            );

            // Should still render same number of cards
            const updatedCards = container.querySelectorAll('.simple-delegation-card');
            expect(updatedCards.length).toBe(initialCount);

            // Should show updated status
            expect(container.textContent).toContain('concluído');
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should hide when streaming stops', () => {
      document.documentElement.setAttribute('data-theme', 'dark');

      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              agents: fc.array(
                fc.record({
                  name: fc.string({ minLength: 1, maxLength: 20 }),
                  role: fc.string({ minLength: 1, maxLength: 20 }),
                  status: fc.string({ minLength: 1, maxLength: 20 }),
                }),
                { minLength: 1, maxLength: 2 }
              ),
            }),
            { minLength: 1, maxLength: 5 }
          ),
          (delegations) => {
            const { container, rerender } = render(
              <AgentTodoList delegations={delegations} isStreaming={true} />
            );

            // Should render initially
            expect(container.querySelector('.agent-todo-list')).toBeTruthy();

            // Stop streaming
            rerender(<AgentTodoList delegations={delegations} isStreaming={false} />);

            // Should not render when streaming stops
            expect(container.querySelector('.agent-todo-list')).toBeFalsy();
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should hide when delegations become empty', () => {
      document.documentElement.setAttribute('data-theme', 'dark');

      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              agents: fc.array(
                fc.record({
                  name: fc.string({ minLength: 1, maxLength: 20 }),
                  role: fc.string({ minLength: 1, maxLength: 20 }),
                  status: fc.string({ minLength: 1, maxLength: 20 }),
                }),
                { minLength: 1, maxLength: 2 }
              ),
            }),
            { minLength: 1, maxLength: 5 }
          ),
          (delegations) => {
            const { container, rerender } = render(
              <AgentTodoList delegations={delegations} isStreaming={true} />
            );

            // Should render initially
            expect(container.querySelector('.agent-todo-list')).toBeTruthy();

            // Clear delegations
            rerender(<AgentTodoList delegations={[]} isStreaming={true} />);

            // Should not render with empty delegations
            expect(container.querySelector('.agent-todo-list')).toBeFalsy();
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});

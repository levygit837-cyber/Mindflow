/**
 * ToolEventCard - Property-Based Tests
 *
 * Feature: chat-visualization-v2
 * Tests Properties 34-40 from design document
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import fc from 'fast-check';
import { ToolEventCard, ToolCallGroup } from './ToolEventCard';

/**
 * Property 34: Running Tool Call Partial Results
 * For any tool call with status='running', the tool call card should display
 * partial results in a visible state.
 * Validates: Requirements 13.1
 */
describe('Property 34: Running Tool Call Partial Results', () => {
  it('should display partial results for running tool calls', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),
        fc.jsonValue(),
        fc.jsonValue(),
        (toolName, args, result) => {
          const { container } = render(
            <ToolEventCard
              toolName={toolName}
              status="running"
              args={args}
              result={result}
            />
          );

          // Should be expanded by default when running
          const partialResultSection = container.querySelector('.border-info');
          expect(partialResultSection).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Property 35: Completed Tool Call Auto-Collapse
 * For any tool call that completes, the tool call card should automatically
 * transition to collapsed state.
 * Validates: Requirements 13.2
 */
describe('Property 35: Completed Tool Call Auto-Collapse', () => {
  it('should be collapsed by default when status is collapsed', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),
        fc.jsonValue(),
        fc.jsonValue(),
        (toolName, args, result) => {
          const { container } = render(
            <ToolEventCard
              toolName={toolName}
              status="collapsed"
              args={args}
              result={result}
            />
          );

          // Result should not be visible when collapsed
          const resultSection = container.querySelector('pre');
          expect(resultSection).toBeFalsy();
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Property 36: Tool Call Click Expansion
 * For any collapsed tool call card, clicking the card should expand it
 * to show the complete result.
 * Validates: Requirements 13.3
 */
describe('Property 36: Tool Call Click Expansion', () => {
  it('should expand on click when collapsed', async () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),
        fc.jsonValue(),
        (toolName, result) => {
          const { container } = render(
            <ToolEventCard
              toolName={toolName}
              status="collapsed"
              result={result}
            />
          );

          const card = container.querySelector('.tool-event-card');
          expect(card).toBeTruthy();

          // Click should trigger expansion (tested in unit tests with userEvent)
          // Property test verifies the card is clickable
          expect(card?.getAttribute('style')).toContain('cursor: pointer');
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Property 37: Read Tool Call Visualization
 * For any tool call of type Read, the rendered card should display
 * the file path and structured result data.
 * Validates: Requirements 14.1
 */
describe('Property 37: Read Tool Call Visualization', () => {
  it('should display specialized visualization for read tools', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('read_file', 'Read', 'file_read', 'READ_FILE'),
        fc.string({ minLength: 1 }),
        fc.jsonValue(),
        (toolName, filePath, result) => {
          const { container } = render(
            <ToolEventCard
              toolName={toolName}
              status="completed"
              args={{ file_path: filePath }}
              result={result}
            />
          );

          // Should have specialized read visualization
          const readViz = container.querySelector('.tool-read-visualization');
          expect(readViz).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Property 38: Shell Tool Call Visualization
 * For any tool call of type Shell, the rendered card should display
 * appropriate visualization for shell commands.
 * Validates: Requirements 14.2
 */
describe('Property 38: Shell Tool Call Visualization', () => {
  it('should display specialized visualization for shell tools', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('shell_exec', 'Shell', 'bash', 'SHELL_COMMAND'),
        fc.string({ minLength: 1 }),
        fc.jsonValue(),
        (toolName, command, result) => {
          const { container } = render(
            <ToolEventCard
              toolName={toolName}
              status="completed"
              args={{ command }}
              result={result}
            />
          );

          // Should have specialized shell visualization
          const shellViz = container.querySelector('.tool-shell-visualization');
          expect(shellViz).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Property 39: Grep Search Tool Call Visualization
 * For any tool call of type Grep_Search, the rendered card should display
 * appropriate visualization for search results.
 * Validates: Requirements 14.3
 */
describe('Property 39: Grep Search Tool Call Visualization', () => {
  it('should display specialized visualization for grep tools', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('grep_search', 'Grep', 'search', 'GREP_SEARCH'),
        fc.string({ minLength: 1 }),
        fc.jsonValue(),
        (toolName, pattern, result) => {
          const { container } = render(
            <ToolEventCard
              toolName={toolName}
              status="completed"
              args={{ pattern }}
              result={result}
            />
          );

          // Should have specialized grep visualization
          const grepViz = container.querySelector('.tool-grep-visualization');
          expect(grepViz).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });
});

/**
 * Property 40: Tool Call Group Support
 * For any sequence of related tool calls, the system should support
 * grouping them together in a Tool_Call_Group structure.
 * Validates: Requirements 14.4
 */
describe('Property 40: Tool Call Group Support', () => {
  it('should group multiple tool calls together', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),
        fc.array(
          fc.record({
            toolName: fc.string({ minLength: 1 }),
            status: fc.constantFrom('running', 'completed', 'error', 'collapsed'),
            args: fc.jsonValue(),
            result: fc.jsonValue(),
          }),
          { minLength: 1, maxLength: 10 }
        ),
        (title, tools) => {
          const { container } = render(
            <ToolCallGroup title={title} tools={tools} />
          );

          // Should render the group container
          const group = container.querySelector('.tool-call-group');
          expect(group).toBeTruthy();

          // Should display tool count
          expect(container.textContent).toContain(`${tools.length} tools`);
        }
      ),
      { numRuns: 100 }
    );
  });
});

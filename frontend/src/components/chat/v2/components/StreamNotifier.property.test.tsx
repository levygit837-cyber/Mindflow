/**
 * Chat Visualization V2 - StreamNotifier Property Tests
 *
 * Property-based tests for StreamNotifier component.
 * These tests validate universal correctness properties across
 * multiple generated inputs using fast-check.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import fc from 'fast-check';
import { StreamNotifier } from '../../streamComponents';
import { resolveMindflowV2Tone } from '../../mindflowV2';
import type { MindflowV2Tone } from '../../mindflowV2';

/**
 * Property 12: Routing Notifier State Transition
 *
 * For any routing event, a notifier pill should be created with
 * status "Routing" that transitions to "Delegated" when delegation occurs.
 *
 * Validates: Requirements 7.1
 */
describe('Property 12: Routing Notifier State Transition', () => {
  it('should render routing notifier with accent tone', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('Routing', 'Decision', 'Analysis'),
        fc.constantFrom('active', 'processing', 'in progress'),
        (title, status) => {
          const { container } = render(
            <StreamNotifier
              title={title}
              status={status}
              tone="accent"
            />
          );

          // Should render the notifier with accent tone
          expect(container.querySelector('.stream-notifier--accent')).toBeTruthy();
          expect(screen.getAllByText(title).length).toBeGreaterThan(0);
          expect(screen.getAllByText(status).length).toBeGreaterThan(0);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should transition from routing to delegated status', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('Routing', 'Decision', 'Analysis'),
        fc.tuple(
          fc.constantFrom('active', 'processing', 'analyzing'),
          fc.constantFrom('delegated', 'completed', 'done')
        ),
        (title, [initialStatus, finalStatus]) => {
          const { rerender, container } = render(
            <StreamNotifier
              title={title}
              status={initialStatus}
              tone="accent"
            />
          );

          // Initial status should be visible
          expect(screen.getAllByText(initialStatus).length).toBeGreaterThan(0);

          // Transition to final status
          rerender(
            <StreamNotifier
              title={title}
              status={finalStatus}
              tone="success"
            />
          );

          // Final status should be visible
          expect(screen.getAllByText(finalStatus).length).toBeGreaterThan(0);
          // Component should still render correctly
          expect(container.querySelector('.stream-notifier')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should use accent tone for routing-related operations', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('routing', 'decision', 'thinking', 'activate', 'analysis'),
        (kind) => {
          const tone = resolveMindflowV2Tone(kind);
          expect(tone).toBe('accent');

          const { container } = render(
            <StreamNotifier
              title={kind}
              status="active"
              tone={tone}
            />
          );

          // Should have accent tone class
          expect(container.querySelector('.stream-notifier--accent')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });
});

/**
 * Property 13: Read Operation Notifier
 *
 * For any read operation event, a notifier pill with status "Read"
 * should be rendered.
 *
 * Validates: Requirements 7.2
 */
describe('Property 13: Read Operation Notifier', () => {
  it('should render read operation notifier for any read event', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('Read', 'Loading', 'Fetching'),
        fc.constantFrom('file', 'data', 'content', 'document'),
        fc.constantFrom('neutral', 'info', 'accent') as fc.Arbitrary<MindflowV2Tone>,
        (title, status, tone) => {
          const { container } = render(
            <StreamNotifier
              title={title}
              status={status}
              tone={tone}
            />
          );

          // Should render the notifier
          expect(container.querySelector('.stream-notifier')).toBeTruthy();
          expect(screen.getAllByText(title).length).toBeGreaterThan(0);
          expect(screen.getAllByText(status).length).toBeGreaterThan(0);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should display read operation details when provided', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('Loading file', 'Reading data', 'Fetching content', 'Processing document'),
        fc.constantFrom('Operation in progress', 'Please wait', 'Loading...', 'Processing...'),
        (message, detail) => {
          const { container } = render(
            <StreamNotifier
              title="Read"
              status="completed"
              message={message}
              detail={detail}
              tone="info"
            />
          );

          // Message and detail should be visible
          expect(screen.getAllByText(message).length).toBeGreaterThan(0);
          expect(screen.getAllByText(detail).length).toBeGreaterThan(0);
          expect(container.querySelector('.stream-notifier-detail')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should handle read operations with various file types', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('.ts', '.tsx', '.js', '.json', '.md', '.py', '.txt'),
        fc.constantFrom('file1', 'file2', 'document', 'script', 'data'),
        (extension, filename) => {
          const fullPath = `${filename}${extension}`;
          const { container } = render(
            <StreamNotifier
              title="Read"
              status="completed"
              message={fullPath}
              tone="info"
            />
          );

          expect(screen.getAllByText(fullPath).length).toBeGreaterThan(0);
          expect(container.querySelector('.stream-notifier-detail')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });
});

/**
 * Property 14: Success Operation Notifier
 *
 * For any successful operation completion event, a notifier pill
 * with status "Success" should be rendered.
 *
 * Validates: Requirements 7.3
 */
describe('Property 14: Success Operation Notifier', () => {
  it('should render success notifier with success tone', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('Success', 'Complete', 'Done', 'Loaded'),
        fc.constantFrom('completed', 'finished', 'success', 'done'),
        (title, status) => {
          const { container } = render(
            <StreamNotifier
              title={title}
              status={status}
              tone="success"
            />
          );

          // Should render with success tone
          expect(container.querySelector('.stream-notifier--success')).toBeTruthy();
          expect(screen.getAllByText(title).length).toBeGreaterThan(0);
          expect(screen.getAllByText(status).length).toBeGreaterThan(0);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should resolve success tone for completion keywords', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('complete', 'done', 'success', 'loaded'),
        (kind) => {
          const tone = resolveMindflowV2Tone(kind);
          expect(tone).toBe('success');

          const { container } = render(
            <StreamNotifier
              title={kind}
              status="completed"
              tone={tone}
            />
          );

          expect(container.querySelector('.stream-notifier--success')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should display success message and detail', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('Operation completed', 'Task finished', 'Process done', 'Action successful'),
        fc.option(fc.constantFrom('All steps completed', 'No errors found', 'Ready to proceed', 'Success'), { nil: undefined }),
        (message, detail) => {
          const { container } = render(
            <StreamNotifier
              title="Success"
              status="completed"
              message={message}
              detail={detail}
              tone="success"
            />
          );

          expect(screen.getAllByText(message).length).toBeGreaterThan(0);
          if (detail) {
            expect(screen.getAllByText(detail).length).toBeGreaterThan(0);
          }
          expect(container.querySelector('.stream-notifier')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });
});

/**
 * Property 15: Error Operation Notifier
 *
 * For any error event, a notifier pill with status "Error"
 * should be rendered.
 *
 * Validates: Requirements 7.4
 */
describe('Property 15: Error Operation Notifier', () => {
  it('should render error notifier with error tone', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('Error', 'Failed', 'Failure'),
        fc.constantFrom('error', 'failed', 'failure', 'crashed'),
        (title, status) => {
          const { container } = render(
            <StreamNotifier
              title={title}
              status={status}
              tone="error"
            />
          );

          // Should render with error tone
          expect(container.querySelector('.stream-notifier--error')).toBeTruthy();
          expect(screen.getAllByText(title).length).toBeGreaterThan(0);
          expect(screen.getAllByText(status).length).toBeGreaterThan(0);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should resolve error tone for error keywords', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('error', 'fail', 'failure', 'failed'),
        (kind) => {
          const tone = resolveMindflowV2Tone(kind);
          expect(tone).toBe('error');

          const { container } = render(
            <StreamNotifier
              title={kind}
              status="error"
              tone={tone}
            />
          );

          expect(container.querySelector('.stream-notifier--error')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should display error message and detail', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('Connection failed', 'Operation failed', 'Request timeout', 'Invalid input'),
        fc.option(fc.constantFrom('Please try again', 'Check your connection', 'Contact support', 'Retry later'), { nil: undefined }),
        (message, detail) => {
          const { container } = render(
            <StreamNotifier
              title="Error"
              status="failed"
              message={message}
              detail={detail}
              tone="error"
            />
          );

          expect(screen.getAllByText(message).length).toBeGreaterThan(0);
          if (detail) {
            expect(screen.getAllByText(detail).length).toBeGreaterThan(0);
          }
          expect(container.querySelector('.stream-notifier--error')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should handle various error types', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          'Connection Error',
          'Timeout Error',
          'Parse Error',
          'Validation Error',
          'Network Error'
        ),
        fc.constantFrom('failed', 'error', 'crashed'),
        (title, status) => {
          const { container } = render(
            <StreamNotifier
              title={title}
              status={status}
              tone="error"
            />
          );

          expect(screen.getAllByText(title).length).toBeGreaterThan(0);
          expect(screen.getAllByText(status).length).toBeGreaterThan(0);
          expect(container.querySelector('.stream-notifier--error')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });
});

/**
 * Additional Property: Tone Consistency
 *
 * For any tone value, the component should apply the correct CSS class
 * and maintain visual consistency.
 */
describe('Additional Property: Tone Consistency', () => {
  it('should apply correct CSS class for any valid tone', () => {
    fc.assert(
      fc.property(
        fc.constantFrom<MindflowV2Tone>('accent', 'info', 'success', 'warning', 'error', 'neutral'),
        fc.constantFrom('Operation', 'Task', 'Process', 'Action'),
        fc.constantFrom('active', 'completed', 'pending', 'running'),
        (tone, title, status) => {
          const { container } = render(
            <StreamNotifier
              title={title}
              status={status}
              tone={tone}
            />
          );

          // Should have the correct tone class
          const expectedClass = `stream-notifier--${tone}`;
          expect(container.querySelector(`.${expectedClass}`)).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should maintain tone across re-renders', () => {
    fc.assert(
      fc.property(
        fc.constantFrom<MindflowV2Tone>('accent', 'info', 'success', 'warning', 'error', 'neutral'),
        fc.constantFrom('Operation', 'Task', 'Process'),
        (tone, title) => {
          const { container, rerender } = render(
            <StreamNotifier
              title={title}
              status="initial"
              tone={tone}
            />
          );

          const expectedClass = `stream-notifier--${tone}`;
          expect(container.querySelector(`.${expectedClass}`)).toBeTruthy();

          // Re-render with same tone
          rerender(
            <StreamNotifier
              title={title}
              status="updated"
              tone={tone}
            />
          );

          // Should still have the same tone class
          expect(container.querySelector(`.${expectedClass}`)).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });
});

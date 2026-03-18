/**
 * Chat Visualization V2 - Stream Event Processing Property Tests
 * 
 * Property-based tests for stream event filtering and processing.
 * These tests validate universal correctness properties across
 * multiple generated inputs using fast-check.
 */

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { buildStreamPresentation } from './streamPresentation';

/**
 * Property 1: Event Filtering During Message Sending
 * 
 * For any stream of events during message sending, unnecessary events
 * and notifiers should be filtered out and not rendered in the chat feed.
 * 
 * Validates: Requirements 1.3
 */
describe('Property 1: Event Filtering During Message Sending', () => {
  // Infrastructure step patterns that should be filtered
  const infraStepNames = [
    '__internal_route',
    '__check_permissions',
    'analyze_request',
    'orchestrator_init',
    'direct_agent:setup',
    'route_to_specialist',
    'dispatch_task',
    'initialize_context',
    'agent_route',
    'permission_check',
  ];

  // Business step names that should NOT be filtered
  const businessStepNames = [
    'Process User Request',
    'Generate Response',
    'Validate Input',
    'Execute Task',
    'Business Logic Step',
    'User Interaction',
  ];

  it('should filter out infrastructure steps from journey', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.oneof(
            // Infrastructure steps (should be filtered)
            fc.record({
              type: fc.constant('agent_step'),
              data: fc.constantFrom(...infraStepNames).map(name => 
                JSON.stringify({ stepName: name })
              ),
              meta: fc.record({ agent: fc.constant('orchestrator') }),
            }),
            // Business steps (should NOT be filtered)
            fc.record({
              type: fc.constant('agent_step'),
              data: fc.constantFrom(...businessStepNames).map(name =>
                JSON.stringify({ stepName: name })
              ),
              meta: fc.record({ agent: fc.constant('orchestrator') }),
            })
          ),
          { minLength: 1, maxLength: 20 }
        ),
        (events) => {
          const presentation = buildStreamPresentation(events, false);
          
          // All journey steps should be business steps only
          for (const step of presentation.journey.steps) {
            expect(infraStepNames).not.toContain(step.title);
          }
          
          // If there were any business steps in input, they should appear in journey
          const businessStepsInInput = events.filter(e => {
            try {
              const data = JSON.parse(e.data);
              return businessStepNames.includes(data.stepName);
            } catch {
              return false;
            }
          });
          
          if (businessStepsInInput.length > 0) {
            expect(presentation.journey.steps.length).toBeGreaterThan(0);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should deduplicate notifiers within 2s window', () => {
    fc.assert(
      fc.property(
        fc.tuple(
          fc.constantFrom('routing', 'loading', 'processing', 'complete'),
          fc.constantFrom('active', 'done', 'pending'),
          fc.integer({ min: 2, max: 10 })
        ),
        ([kind, status, count]) => {
          // Create multiple identical notifiers
          const events = Array.from({ length: count }, (_, i) => ({
            id: `notifier-${i}`,
            type: 'notifier',
            data: JSON.stringify({ kind, message: status }),
            meta: {},
          }));
          
          const presentation = buildStreamPresentation(events, false);
          
          // Should only have 1 notifier due to deduplication
          const matchingNotifiers = presentation.notifiers.filter(
            n => n.title.toLowerCase().includes(kind) && n.status === status
          );
          
          expect(matchingNotifiers.length).toBeLessThanOrEqual(1);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should apply notifier cap (max 6 notifiers)', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            type: fc.constant('notifier'),
            data: fc.record({
              kind: fc.constantFrom('routing', 'loading', 'processing', 'complete', 'error', 'warning', 'info', 'success'),
              message: fc.string({ minLength: 1, maxLength: 50 }),
            }).map(obj => JSON.stringify(obj)),
            meta: fc.record({}),
          }),
          { minLength: 10, maxLength: 30 }
        ),
        (events) => {
          // Add unique IDs to prevent deduplication
          const uniqueEvents = events.map((e, i) => ({
            ...e,
            id: `notifier-${i}`,
            data: JSON.parse(e.data),
          })).map(e => ({
            ...e,
            data: JSON.stringify({ ...e.data, message: `${e.data.message}-${e.id}` }),
          }));
          
          const presentation = buildStreamPresentation(uniqueEvents, false);
          
          // Should never exceed cap of 6
          expect(presentation.notifiers.length).toBeLessThanOrEqual(6);
          
          // If we had more than 6 unique notifiers, should keep the most recent 6
          if (uniqueEvents.length > 6) {
            expect(presentation.notifiers.length).toBe(6);
          }
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should filter out memory recall messages during message sending', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            type: fc.constant('notifier'),
            data: fc.record({
              kind: fc.constantFrom('context_loaded', 'memory_recall', 'memory_loaded'),
              message: fc.string({ minLength: 1, maxLength: 50 }),
              source: fc.constantFrom('database', 'vector', 'session'),
              count: fc.integer({ min: 1, max: 100 }),
            }).map(obj => JSON.stringify(obj)),
            meta: fc.record({ agent: fc.constant('researcher') }),
          }),
          { minLength: 1, maxLength: 10 }
        ),
        (events) => {
          const presentation = buildStreamPresentation(events, false);
          
          // Memory events should be in memoryEvents, not notifiers
          expect(presentation.memoryEvents.length).toBeGreaterThan(0);
          
          // Notifiers should not contain memory-related notifiers
          const memoryNotifiers = presentation.notifiers.filter(n =>
            n.title.toLowerCase().includes('memory') ||
            n.title.toLowerCase().includes('context')
          );
          
          expect(memoryNotifiers.length).toBe(0);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should handle empty events array gracefully', () => {
    fc.assert(
      fc.property(
        fc.boolean(),
        (isStreaming) => {
          const presentation = buildStreamPresentation([], isStreaming);
          
          // Should return valid structure with defaults
          // When streaming, orchestrator is added as default active agent
          if (isStreaming) {
            expect(presentation.activeAgents).toEqual(['orchestrator']);
          } else {
            expect(presentation.activeAgents).toEqual([]);
          }
          
          expect(presentation.thoughts).toEqual([]);
          expect(presentation.delegations).toEqual([]);
          expect(presentation.toolEvents).toEqual([]);
          expect(presentation.notifiers).toEqual([]);
          expect(presentation.memoryEvents).toEqual([]);
          expect(presentation.journey.steps).toEqual([]);
          expect(presentation.errors).toEqual([]);
          expect(presentation.diagnostics.scopeEscape).toBe(false);
        }
      ),
      { numRuns: 10 }
    );
  });

  it('should filter events consistently regardless of order', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.oneof(
            fc.record({
              type: fc.constant('agent_step'),
              data: fc.constantFrom(...infraStepNames).map(name =>
                JSON.stringify({ stepName: name })
              ),
              meta: fc.record({ agent: fc.constant('orchestrator') }),
            }),
            fc.record({
              type: fc.constant('agent_step'),
              data: fc.constantFrom(...businessStepNames).map(name =>
                JSON.stringify({ stepName: name })
              ),
              meta: fc.record({ agent: fc.constant('orchestrator') }),
            })
          ),
          { minLength: 5, maxLength: 15 }
        ),
        (events) => {
          // Process events in original order
          const presentation1 = buildStreamPresentation(events, false);
          
          // Process events in reversed order
          const presentation2 = buildStreamPresentation([...events].reverse(), false);
          
          // Both should filter the same number of infrastructure steps
          // (though order of journey steps may differ)
          const businessStepsCount = events.filter(e => {
            try {
              const data = JSON.parse(e.data);
              return businessStepNames.includes(data.stepName);
            } catch {
              return false;
            }
          }).length;
          
          expect(presentation1.journey.steps.length).toBe(businessStepsCount);
          expect(presentation2.journey.steps.length).toBe(businessStepsCount);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should handle malformed event data gracefully', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            type: fc.constantFrom('agent_step', 'notifier', 'tool_call'),
            data: fc.oneof(
              fc.constant(''),
              fc.constant('invalid json'),
              fc.constant('{}'),
              fc.constant('null'),
              fc.string({ minLength: 1, maxLength: 100 })
            ),
            meta: fc.option(fc.record({ agent: fc.string() }), { nil: null }),
          }),
          { minLength: 1, maxLength: 10 }
        ),
        (events) => {
          // Should not throw
          expect(() => {
            const presentation = buildStreamPresentation(events, false);
            
            // Should return valid structure
            expect(presentation).toBeDefined();
            expect(Array.isArray(presentation.activeAgents)).toBe(true);
            expect(Array.isArray(presentation.thoughts)).toBe(true);
            expect(Array.isArray(presentation.delegations)).toBe(true);
            expect(Array.isArray(presentation.toolEvents)).toBe(true);
            expect(Array.isArray(presentation.notifiers)).toBe(true);
            expect(Array.isArray(presentation.memoryEvents)).toBe(true);
            expect(Array.isArray(presentation.journey.steps)).toBe(true);
            expect(Array.isArray(presentation.errors)).toBe(true);
          }).not.toThrow();
        }
      ),
      { numRuns: 100 }
    );
  });
});

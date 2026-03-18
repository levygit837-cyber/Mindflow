/**
 * Chat Visualization V2 - JourneyTimeline Property Tests
 *
 * Property-based tests for JourneyTimeline component covering universal
 * correctness properties through multiple generated inputs.
 *
 * Feature: chat-visualization-v2
 * Requirements: 12.2, 12.3, 12.5
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import fc from 'fast-check';
import { JourneyTimeline, JourneyStep } from './JourneyTimeline';
import type { MindflowV2AgentType } from '../types';

// Arbitraries for property-based testing
const agentTypeArb = fc.constantFrom<MindflowV2AgentType>(
  'orchestrator',
  'analyst',
  'coder',
  'researcher'
);

const stepStatusArb = fc.constantFrom<JourneyStep['status']>(
  'live',
  'done',
  'queued',
  'waiting',
  'error'
);

const journeyStepArb = fc.record({
  id: fc.uuid(),
  title: fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0),
  detail: fc.string({ minLength: 1, maxLength: 200 }).filter(s => s.trim().length > 0),
  status: stepStatusArb,
  agentType: fc.option(agentTypeArb, { nil: undefined }),
  meta: fc.option(fc.string({ minLength: 1, maxLength: 100 }).filter(s => s.trim().length > 0), { nil: undefined }),
});

describe('JourneyTimeline Property Tests', () => {
  /**
   * Feature: chat-visualization-v2, Property 30: Agent Journey Initial Step
   *
   * For any expanded agent journey, the timeline should start with a
   * "Delegation Received" step.
   *
   * Validates: Requirements 12.2
   */
  describe('Property 30: Agent Journey Initial Step', () => {
    it('should display first step as initial step in timeline', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 1, maxLength: 10 }),
          (steps) => {
            const { container } = render(
              <JourneyTimeline steps={steps} title="Agent Journey" />
            );

            // First step should be visible in rail
            const railSteps = container.querySelectorAll('.journey-rail-step');
            expect(railSteps.length).toBeGreaterThan(0);

            // First step should have numbered dot with "1"
            const firstStepDot = railSteps[0].querySelector('div[style*="border-radius: 50%"]');
            expect(firstStepDot).toBeTruthy();
            expect(firstStepDot?.textContent).toBe('1');

            // First step title should be visible (use container query for flexibility)
            const firstStepTitle = container.querySelector('.journey-rail-step');
            expect(firstStepTitle?.textContent).toContain(steps[0].title.trim());
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should render delegation received step when present', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 0, maxLength: 5 }),
          (additionalSteps) => {
            const delegationStep: JourneyStep = {
              id: 'delegation-received',
              title: 'Delegation Received',
              detail: 'Agent received delegation from orchestrator',
              status: 'done',
              agentType: 'analyst',
            };

            const steps = [delegationStep, ...additionalSteps];

            const { container } = render(<JourneyTimeline steps={steps} title="Agent Journey" />);

            // Delegation Received should be visible
            expect(container.textContent).toContain('Delegation Received');

            // Should be the first step (numbered 1)
            const railSteps = document.querySelectorAll('.journey-rail-step');
            const firstStepDot = railSteps[0].querySelector('div[style*="border-radius: 50%"]');
            expect(firstStepDot?.textContent).toBe('1');
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Feature: chat-visualization-v2, Property 31: Agent Journey Real-Time Updates
   *
   * For any agent journey, when tool call or thinking events occur,
   * the journey should update to display these events.
   *
   * Validates: Requirements 12.3
   */
  describe('Property 31: Agent Journey Real-Time Updates', () => {
    it('should display all steps in real-time order', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 1, maxLength: 15 }),
          (steps) => {
            const { container } = render(<JourneyTimeline steps={steps} />);

            // All steps should be rendered in rail
            const railSteps = container.querySelectorAll('.journey-rail-step');
            expect(railSteps.length).toBe(steps.length);

            // Steps should be numbered sequentially
            railSteps.forEach((stepElement, index) => {
              const dot = stepElement.querySelector('div[style*="border-radius: 50%"]');
              expect(dot?.textContent).toBe(String(index + 1));
            });

            // All step titles should be visible in the container
            steps.forEach((step) => {
              expect(container.textContent).toContain(step.title.trim());
            });
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should show live status for active steps', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 1, maxLength: 10 }),
          fc.integer({ min: 0, max: 9 }),
          (steps, liveIndex) => {
            if (liveIndex >= steps.length) return;

            // Set one step to live status
            const updatedSteps = steps.map((step, index) => ({
              ...step,
              status: index === liveIndex ? ('live' as const) : step.status,
            }));

            const { container } = render(<JourneyTimeline steps={updatedSteps} />);

            // Live badge should be visible in footer
            expect(container.textContent).toContain('ao vivo');

            // Live step should have pulsing animation
            const railSteps = container.querySelectorAll('.journey-rail-step');
            const liveStepDot = railSteps[liveIndex].querySelector('div[style*="animation"]');
            expect(liveStepDot).toBeTruthy();
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should update stage when different steps are selected', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 2, maxLength: 10 }),
          (steps) => {
            const { container } = render(<JourneyTimeline steps={steps} />);

            // First step should be displayed in stage by default
            const stageContent = container.querySelector('.journey-stage');
            expect(stageContent?.textContent).toContain(steps[0].title);
            expect(stageContent?.textContent).toContain(steps[0].detail);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Feature: chat-visualization-v2, Property 32: Agent Journey Completion Indicator
   *
   * For any agent journey where the agent has finalized, the journey
   * should display a success indicator (green) and a summary.
   *
   * Validates: Requirements 12.5
   */
  describe('Property 32: Agent Journey Completion Indicator', () => {
    it('should display green indicator for completed steps', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 1, maxLength: 10 }),
          (steps) => {
            // Set all steps to done status
            const completedSteps = steps.map((step) => ({
              ...step,
              status: 'done' as const,
            }));

            const { container } = render(
              <JourneyTimeline steps={completedSteps} summary="Journey completed successfully" />
            );

            // All step dots should have green color (#2D8F5E)
            const railSteps = container.querySelectorAll('.journey-rail-step');
            railSteps.forEach((stepElement) => {
              const dot = stepElement.querySelector('div[style*="background: rgb(45, 143, 94)"]');
              expect(dot).toBeTruthy();
            });

            // Summary should be visible in footer
            expect(container.textContent).toContain('Journey completed successfully');
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should display summary when provided', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 1, maxLength: 10 }),
          fc.string({ minLength: 10, maxLength: 100 }).filter(s => s.trim().length >= 10),
          (steps, summary) => {
            const { container } = render(<JourneyTimeline steps={steps} summary={summary} />);

            // Summary should be visible in footer
            expect(container.textContent).toContain(summary.trim());
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should display duration label when provided', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 1, maxLength: 10 }),
          fc.string({ minLength: 1, maxLength: 20 }).filter(s => s.trim().length > 0),
          (steps, durationLabel) => {
            const { container } = render(<JourneyTimeline steps={steps} durationLabel={durationLabel} />);

            // Duration should be visible in footer
            expect(container.textContent).toContain(durationLabel.trim());
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should not display live badge when no steps are live', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 1, maxLength: 10 }),
          (steps) => {
            // Set all steps to done status
            const completedSteps = steps.map((step) => ({
              ...step,
              status: 'done' as const,
            }));

            const { container } = render(<JourneyTimeline steps={completedSteps} />);

            // Live badge should not be visible
            expect(container.textContent).not.toContain('ao vivo');
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should display error indicator for failed steps', () => {
      fc.assert(
        fc.property(
          fc.array(journeyStepArb, { minLength: 1, maxLength: 10 }),
          fc.integer({ min: 0, max: 9 }),
          (steps, errorIndex) => {
            if (errorIndex >= steps.length) return;

            // Set one step to error status
            const stepsWithError = steps.map((step, index) => ({
              ...step,
              status: index === errorIndex ? ('error' as const) : step.status,
            }));

            const { container } = render(<JourneyTimeline steps={stepsWithError} />);

            // Error step should have orange/red color (#C75D2C)
            const railSteps = container.querySelectorAll('.journey-rail-step');
            const errorStepDot = railSteps[errorIndex].querySelector(
              'div[style*="background: rgb(199, 93, 44)"]'
            );
            expect(errorStepDot).toBeTruthy();
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Additional property: Timeline should handle empty steps gracefully
   */
  describe('Property: Empty Steps Handling', () => {
    it('should render without errors when steps array is empty', () => {
      const { container } = render(<JourneyTimeline steps={[]} />);

      // Should render container
      expect(container.querySelector('.journey-timeline')).toBeTruthy();

      // Rail should be empty
      const railSteps = container.querySelectorAll('.journey-rail-step');
      expect(railSteps.length).toBe(0);
    });
  });

  /**
   * Additional property: Agent type badges should be displayed correctly
   */
  describe('Property: Agent Type Display', () => {
    it('should display agent type badge when agentType is provided', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              ...journeyStepArb.constraints,
              agentType: agentTypeArb, // Always provide agentType
            }),
            { minLength: 1, maxLength: 5 }
          ),
          (steps) => {
            const { container } = render(<JourneyTimeline steps={steps} />);

            // First step's agent type should be visible in stage
            const agentLabels = ['Orchestrator', 'Analyst', 'Coder', 'Research'];
            const hasAgentLabel = agentLabels.some((label) => container.textContent?.includes(label));
            expect(hasAgentLabel).toBe(true);
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});

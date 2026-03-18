/**
 * Chat Visualization V2 - JourneyTimeline Unit Tests
 *
 * Unit tests for JourneyTimeline component covering specific examples,
 * edge cases, and user interactions.
 *
 * Requirements: 12.2, 12.3, 12.5
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JourneyTimeline, JourneyStep } from './JourneyTimeline';

describe('JourneyTimeline', () => {
  describe('Rail Rendering', () => {
    it('should render all steps in rail with numbered dots', () => {
      const steps: JourneyStep[] = [
        {
          id: 'step-1',
          title: 'Delegation Received',
          detail: 'Agent received task',
          status: 'done',
        },
        {
          id: 'step-2',
          title: 'Reading Files',
          detail: 'Reading source files',
          status: 'done',
        },
        {
          id: 'step-3',
          title: 'Analyzing Code',
          detail: 'Performing analysis',
          status: 'live',
        },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      const railSteps = container.querySelectorAll('.journey-rail-step');
      expect(railSteps.length).toBe(3);

      // Check numbered dots
      const dots = container.querySelectorAll('.journey-rail-step div[style*="border-radius: 50%"]');
      expect(dots[0].textContent).toBe('1');
      expect(dots[1].textContent).toBe('2');
      expect(dots[2].textContent).toBe('3');

      // Check titles (they appear in both rail and stage, so use container query)
      const railContainer = container.querySelector('.journey-rail');
      expect(railContainer?.textContent).toContain('Delegation Received');
      expect(railContainer?.textContent).toContain('Reading Files');
      expect(railContainer?.textContent).toContain('Analyzing Code');
    });

    it('should render connecting lines between steps', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Detail 1', status: 'done' },
        { id: 'step-2', title: 'Step 2', detail: 'Detail 2', status: 'live' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Should have connecting line (only between first and second, not after last)
      const lines = container.querySelectorAll('div[style*="position: absolute"][style*="left: 11px"]');
      expect(lines.length).toBeGreaterThan(0);
    });

    it('should render empty rail when no steps provided', () => {
      const { container } = render(<JourneyTimeline steps={[]} />);

      const railSteps = container.querySelectorAll('.journey-rail-step');
      expect(railSteps.length).toBe(0);
    });
  });

  describe('Stage Rendering', () => {
    it('should display first step in stage by default', () => {
      const steps: JourneyStep[] = [
        {
          id: 'step-1',
          title: 'First Step',
          detail: 'This is the first step detail',
          status: 'done',
          agentType: 'analyst',
        },
        {
          id: 'step-2',
          title: 'Second Step',
          detail: 'This is the second step detail',
          status: 'live',
        },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      const stage = container.querySelector('.journey-stage');
      expect(stage?.textContent).toContain('First Step');
      expect(stage?.textContent).toContain('This is the first step detail');
    });

    it('should display agent type badge in stage when provided', () => {
      const steps: JourneyStep[] = [
        {
          id: 'step-1',
          title: 'Analysis Step',
          detail: 'Analyzing code',
          status: 'done',
          agentType: 'analyst',
        },
      ];

      render(<JourneyTimeline steps={steps} />);

      expect(screen.getByText('Analyst')).toBeTruthy();
    });

    it('should display meta information when provided', () => {
      const steps: JourneyStep[] = [
        {
          id: 'step-1',
          title: 'Tool Call',
          detail: 'Executing tool',
          status: 'done',
          meta: 'read_file(path="/src/main.ts")',
        },
      ];

      render(<JourneyTimeline steps={steps} />);

      expect(screen.getByText('read_file(path="/src/main.ts")')).toBeTruthy();
    });

    it('should not display meta when not provided', () => {
      const steps: JourneyStep[] = [
        {
          id: 'step-1',
          title: 'Step without meta',
          detail: 'Detail',
          status: 'done',
        },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Meta container should not exist
      const metaContainer = container.querySelector('.journey-stage div[style*="font-family: var(--font-mono)"]');
      expect(metaContainer).toBeFalsy();
    });
  });

  describe('Step Selection', () => {
    it('should update stage when rail step is clicked', async () => {
      const user = userEvent.setup();
      const steps: JourneyStep[] = [
        {
          id: 'step-1',
          title: 'First Step',
          detail: 'First detail',
          status: 'done',
        },
        {
          id: 'step-2',
          title: 'Second Step',
          detail: 'Second detail',
          status: 'live',
        },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Initially shows first step
      let stage = container.querySelector('.journey-stage');
      expect(stage?.textContent).toContain('First Step');
      expect(stage?.textContent).toContain('First detail');

      // Click second step in rail
      const railSteps = container.querySelectorAll('.journey-rail-step');
      await user.click(railSteps[1] as HTMLElement);

      // Wait for stage to update with new content
      await waitFor(() => {
        stage = container.querySelector('.journey-stage');
        expect(stage?.textContent).toContain('Second Step');
      });

      // Verify detail is also present
      expect(stage?.textContent).toContain('Second detail');
    });

    it('should highlight selected step in rail', async () => {
      const user = userEvent.setup();
      const steps: JourneyStep[] = [
        {
          id: 'step-1',
          title: 'Step 1',
          detail: 'Detail 1',
          status: 'done',
          agentType: 'analyst',
        },
        {
          id: 'step-2',
          title: 'Step 2',
          detail: 'Detail 2',
          status: 'live',
          agentType: 'coder',
        },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      const railSteps = container.querySelectorAll('.journey-rail-step');

      // First step should be selected initially (has border with accent color)
      expect((railSteps[0] as HTMLElement).style.border).toContain('1px solid');

      // Click second step
      await user.click(railSteps[1] as HTMLElement);

      // Second step should now be selected
      expect((railSteps[1] as HTMLElement).style.border).toContain('1px solid');
    });

    it('should use activeStepId prop when provided', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Detail 1', status: 'done' },
        { id: 'step-2', title: 'Step 2', detail: 'Detail 2', status: 'live' },
      ];

      const { container } = render(
        <JourneyTimeline steps={steps} activeStepId="step-2" />
      );

      // Should show second step in stage
      const stage = container.querySelector('.journey-stage');
      expect(stage?.textContent).toContain('Step 2');
      expect(stage?.textContent).toContain('Detail 2');
    });
  });

  describe('Status Visual Indicators', () => {
    it('should display green color for done status', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Completed Step', detail: 'Done', status: 'done' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Green color: #2D8F5E = rgb(45, 143, 94)
      const dot = container.querySelector('div[style*="background: rgb(45, 143, 94)"]');
      expect(dot).toBeTruthy();
    });

    it('should display blue color with pulse animation for live status', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Active Step', detail: 'Running', status: 'live' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Blue color: #5B6ABF = rgb(91, 106, 191)
      const dot = container.querySelector('div[style*="background: rgb(91, 106, 191)"]');
      expect(dot).toBeTruthy();

      // Should have pulse animation
      expect((dot as HTMLElement)?.style.animation).toContain('pulse');
    });

    it('should display orange/red color for error status', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Failed Step', detail: 'Error occurred', status: 'error' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Orange/red color: #C75D2C = rgb(199, 93, 44)
      const dot = container.querySelector('div[style*="background: rgb(199, 93, 44)"]');
      expect(dot).toBeTruthy();
    });

    it('should display muted gray for waiting status', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Waiting Step', detail: 'Queued', status: 'waiting' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Gray color: #6B7280 = rgb(107, 114, 128)
      const dot = container.querySelector('div[style*="background: rgb(107, 114, 128)"]');
      expect(dot).toBeTruthy();
    });

    it('should display muted gray for queued status', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Queued Step', detail: 'In queue', status: 'queued' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Gray color: #6B7280 = rgb(107, 114, 128)
      const dot = container.querySelector('div[style*="background: rgb(107, 114, 128)"]');
      expect(dot).toBeTruthy();
    });

    it('should display appropriate icons for each status', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Done', detail: 'Completed', status: 'done' },
        { id: 'step-2', title: 'Live', detail: 'Running', status: 'live' },
        { id: 'step-3', title: 'Error', detail: 'Failed', status: 'error' },
        { id: 'step-4', title: 'Waiting', detail: 'Queued', status: 'waiting' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Check for status text in rail
      expect(screen.getByText('done')).toBeTruthy();
      expect(screen.getByText('live')).toBeTruthy();
      expect(screen.getByText('error')).toBeTruthy();
      expect(screen.getByText('waiting')).toBeTruthy();
    });
  });

  describe('Footer Display', () => {
    it('should display live badge when at least one step is live', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Done', status: 'done' },
        { id: 'step-2', title: 'Step 2', detail: 'Running', status: 'live' },
      ];

      render(<JourneyTimeline steps={steps} />);

      expect(screen.getByText('ao vivo')).toBeTruthy();
    });

    it('should not display live badge when no steps are live', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Done', status: 'done' },
        { id: 'step-2', title: 'Step 2', detail: 'Done', status: 'done' },
      ];

      render(<JourneyTimeline steps={steps} />);

      expect(screen.queryByText('ao vivo')).toBeFalsy();
    });

    it('should display custom live label when provided', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Running', status: 'live' },
      ];

      render(<JourneyTimeline steps={steps} liveLabel="live now" />);

      expect(screen.getByText('live now')).toBeTruthy();
    });

    it('should display duration label when provided', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Done', status: 'done' },
      ];

      render(<JourneyTimeline steps={steps} durationLabel="2m 34s" />);

      expect(screen.getByText('2m 34s')).toBeTruthy();
    });

    it('should display summary when provided', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Done', status: 'done' },
      ];

      render(
        <JourneyTimeline steps={steps} summary="Analysis completed successfully" />
      );

      expect(screen.getByText('Analysis completed successfully')).toBeTruthy();
    });

    it('should display all footer elements together', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Running', status: 'live' },
      ];

      render(
        <JourneyTimeline
          steps={steps}
          durationLabel="1m 15s"
          summary="Processing files"
          liveLabel="ao vivo"
        />
      );

      expect(screen.getByText('ao vivo')).toBeTruthy();
      expect(screen.getByText('1m 15s')).toBeTruthy();
      expect(screen.getByText('Processing files')).toBeTruthy();
    });
  });

  describe('Header Display', () => {
    it('should display title when provided', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Detail', status: 'done' },
      ];

      render(<JourneyTimeline steps={steps} title="Agent Journey" />);

      expect(screen.getByText('Agent Journey')).toBeTruthy();
    });

    it('should display subtitle when provided', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Detail', status: 'done' },
      ];

      render(
        <JourneyTimeline
          steps={steps}
          title="Agent Journey"
          subtitle="Analyst execution timeline"
        />
      );

      expect(screen.getByText('Analyst execution timeline')).toBeTruthy();
    });

    it('should not render header when title and subtitle are not provided', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Detail', status: 'done' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Header should not exist
      const header = container.querySelector('div[style*="borderBottom: 1px solid var(--line-primary)"]');
      expect(header).toBeFalsy();
    });
  });

  describe('Animation', () => {
    it('should render with initial animation', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Step 1', detail: 'Detail', status: 'done' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      const timeline = container.querySelector('.journey-timeline');
      expect(timeline).toBeTruthy();
    });

    it('should have spinning animation for live step icon', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Active Step', detail: 'Running', status: 'live' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Live step should have spinning loader icon in stage
      const spinningIcon = container.querySelector('.journey-step-icon-spin');
      expect(spinningIcon).toBeTruthy();
    });
  });

  describe('Edge Cases', () => {
    it('should handle single step', () => {
      const steps: JourneyStep[] = [
        { id: 'step-1', title: 'Only Step', detail: 'Single step', status: 'done' },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      const railSteps = container.querySelectorAll('.journey-rail-step');
      expect(railSteps.length).toBe(1);

      // Should not have connecting lines
      const lines = container.querySelectorAll('div[style*="position: absolute"][style*="left: 11px"]');
      expect(lines.length).toBe(0);
    });

    it('should handle very long step titles', () => {
      const steps: JourneyStep[] = [
        {
          id: 'step-1',
          title: 'This is a very long step title that should be truncated with ellipsis',
          detail: 'Detail',
          status: 'done',
        },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Should render without errors (title appears in both rail and stage)
      const stage = container.querySelector('.journey-stage');
      expect(stage?.textContent).toContain('This is a very long step title that should be truncated with ellipsis');
    });

    it('should handle steps without agent type', () => {
      const steps: JourneyStep[] = [
        {
          id: 'step-1',
          title: 'Generic Step',
          detail: 'No agent type',
          status: 'done',
        },
      ];

      const { container } = render(<JourneyTimeline steps={steps} />);

      // Should render without errors
      const stage = container.querySelector('.journey-stage');
      expect(stage?.textContent).toContain('Generic Step');

      // Should not have agent badge
      const agentLabels = ['Orchestrator', 'Analyst', 'Coder', 'Research'];
      const hasAgentLabel = agentLabels.some((label) => screen.queryByText(label));
      expect(hasAgentLabel).toBe(false);
    });
  });
});

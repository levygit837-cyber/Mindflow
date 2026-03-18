/**
 * Unit tests for AgentJourneyPanel
 * Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgentJourneyPanel } from './AgentJourneyPanel';
import { DelegationCardProps } from './DelegationCard';
import { JourneyStep } from './JourneyTimeline';

describe('AgentJourneyPanel Unit Tests', () => {
  const mockDelegation: DelegationCardProps = {
    title: 'Test Delegation',
    subtitle: 'Test subtitle',
    agents: [
      { name: 'TestAgent', status: 'active', agentType: 'analyst' },
    ],
    summary: 'Test summary',
  };

  const mockSteps: JourneyStep[] = [
    {
      id: '1',
      title: 'Step 1',
      detail: 'Detail 1',
      status: 'done',
      agentType: 'analyst',
    },
    {
      id: '2',
      title: 'Step 2',
      detail: 'Detail 2',
      status: 'live',
      agentType: 'analyst',
    },
  ];

  describe('Panel Rendering', () => {
    it('should render panel with backdrop', () => {
      const { container } = render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      expect(container.querySelector('.agent-journey-panel')).toBeInTheDocument();
      expect(container.querySelector('.agent-journey-panel-container')).toBeInTheDocument();
    });

    it('should render delegation title and subtitle', () => {
      render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      expect(screen.getAllByText('Test Delegation').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Test subtitle').length).toBeGreaterThan(0);
    });

    it('should render agent list', () => {
      render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      expect(screen.getAllByText('TestAgent').length).toBeGreaterThan(0);
      expect(screen.getAllByText('active').length).toBeGreaterThan(0);
    });

    it('should render close button', () => {
      render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      const closeButton = screen.getByLabelText('Close journey panel');
      expect(closeButton).toBeInTheDocument();
    });

    it('should render JourneyTimeline component', () => {
      const { container } = render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      // JourneyTimeline should be present
      expect(container.querySelector('.journey-timeline')).toBeInTheDocument();
    });
  });

  describe('Animation', () => {
    it('should have slide-from-right animation styles', () => {
      const { container } = render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      const panel = container.querySelector('.agent-journey-panel') as HTMLElement;
      expect(panel).toBeInTheDocument();
      expect(panel.style.position).toBe('fixed');
      expect(panel.style.right).toBe('0px');
      expect(panel.style.width).toBe('380px');
    });

    it('should have backdrop with opacity animation', () => {
      const { container } = render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      const backdrop = container.querySelector('[style*="rgba(0, 0, 0, 0.3)"]');
      expect(backdrop).toBeInTheDocument();
    });
  });

  describe('Close Callback', () => {
    it('should call onClose when close button is clicked', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={onClose}
        />
      );

      const closeButton = screen.getByLabelText('Close journey panel');
      await user.click(closeButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('should call onClose when backdrop is clicked', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      const { container } = render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={onClose}
        />
      );

      const backdrop = container.querySelector('[style*="rgba(0, 0, 0, 0.3)"]') as HTMLElement;
      await user.click(backdrop);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Delegation Received Step', () => {
    it('should add "Delegation Received" as first step if not present', () => {
      render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      expect(screen.getAllByText('Delegation Received').length).toBeGreaterThan(0);
    });

    it('should not duplicate "Delegation Received" if already present', () => {
      const stepsWithDelegation: JourneyStep[] = [
        {
          id: 'delegation',
          title: 'Delegation Received',
          detail: 'Already present',
          status: 'done',
          agentType: 'analyst',
        },
        ...mockSteps,
      ];

      render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={stepsWithDelegation}
          onClose={() => {}}
        />
      );

      const delegationSteps = screen.getAllByText('Delegation Received');
      // Should not add duplicate - but may appear in rail and stage (2 places in timeline)
      expect(delegationSteps.length).toBeLessThanOrEqual(2);
    });
  });

  describe('Scrollable Area', () => {
    it('should have scrollable content area', () => {
      const { container } = render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      const contentArea = container.querySelector('.agent-journey-content') as HTMLElement;
      expect(contentArea).toBeInTheDocument();
      expect(contentArea.style.overflowY).toBe('auto');
    });
  });

  describe('Multiple Agents', () => {
    it('should render multiple agents in header', () => {
      const multiAgentDelegation: DelegationCardProps = {
        title: 'Multi-Agent Task',
        agents: [
          { name: 'Agent1', status: 'active', agentType: 'analyst' },
          { name: 'Agent2', status: 'waiting', agentType: 'coder' },
          { name: 'Agent3', status: 'done', agentType: 'researcher' },
        ],
      };

      render(
        <AgentJourneyPanel
          delegation={multiAgentDelegation}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      expect(screen.getAllByText('Agent1').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Agent2').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Agent3').length).toBeGreaterThan(0);
    });
  });

  describe('Streaming State', () => {
    it('should pass isStreaming to JourneyTimeline', () => {
      render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          isStreaming={true}
          onClose={() => {}}
        />
      );

      // "ao vivo" badge should be present when streaming (may appear multiple times)
      expect(screen.getAllByText('ao vivo').length).toBeGreaterThan(0);
    });

    it('should not show live badge when not streaming', () => {
      const nonLiveSteps: JourneyStep[] = [
        {
          id: '1',
          title: 'Step 1',
          detail: 'Detail 1',
          status: 'done',
          agentType: 'analyst',
        },
        {
          id: '2',
          title: 'Step 2',
          detail: 'Detail 2',
          status: 'done',
          agentType: 'analyst',
        },
      ];

      render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={nonLiveSteps}
          isStreaming={false}
          onClose={() => {}}
        />
      );

      expect(screen.queryByText('ao vivo')).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty steps array', () => {
      render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={[]}
          onClose={() => {}}
        />
      );

      // Should still render with "Delegation Received" step (may appear multiple times)
      expect(screen.getAllByText('Delegation Received').length).toBeGreaterThan(0);
    });

    it('should handle delegation without subtitle', () => {
      const delegationNoSubtitle: DelegationCardProps = {
        title: 'Test Delegation',
        agents: [{ name: 'Agent1', status: 'active', agentType: 'analyst' }],
      };

      render(
        <AgentJourneyPanel
          delegation={delegationNoSubtitle}
          steps={mockSteps}
          onClose={() => {}}
        />
      );

      expect(screen.getAllByText('Test Delegation').length).toBeGreaterThan(0);
    });

    it('should handle custom className', () => {
      const { container } = render(
        <AgentJourneyPanel
          delegation={mockDelegation}
          steps={mockSteps}
          onClose={() => {}}
          className="custom-class"
        />
      );

      expect(container.querySelector('.custom-class')).toBeInTheDocument();
    });
  });
});

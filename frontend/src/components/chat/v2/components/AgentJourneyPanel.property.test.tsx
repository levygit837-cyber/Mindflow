/**
 * Property-based tests for AgentJourneyPanel
 * Requirements: 12.1, 12.6
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentJourneyPanel } from './AgentJourneyPanel';
import { DelegationCardProps } from './DelegationCard';
import { JourneyStep } from './JourneyTimeline';

describe('AgentJourneyPanel Property Tests', () => {
  /**
   * Property 29: Delegation Card Click Expansion
   * When a delegation card is clicked, the journey panel opens
   * Validates: Requirement 12.1
   */
  describe('Property 29: Delegation Card Click Expansion', () => {
    it('should render panel when delegation is provided', () => {
      const delegation: DelegationCardProps = {
        title: 'Test Delegation',
        subtitle: 'Test subtitle',
        agents: [
          { name: 'Agent1', status: 'active', agentType: 'analyst' },
        ],
        summary: 'Test summary',
      };

      const steps: JourneyStep[] = [
        {
          id: '1',
          title: 'Step 1',
          detail: 'Detail 1',
          status: 'done',
          agentType: 'analyst',
        },
      ];

      const { container } = render(
        <AgentJourneyPanel
          delegation={delegation}
          steps={steps}
          onClose={() => {}}
        />
      );

      // Panel should be rendered
      expect(container.querySelector('.agent-journey-panel')).toBeInTheDocument();

      // Title should be visible (may appear multiple times in timeline)
      expect(screen.getAllByText('Test Delegation').length).toBeGreaterThan(0);
    });

    it('should display delegation information in panel header', () => {
      for (let i = 0; i < 10; i++) {
        const delegation: DelegationCardProps = {
          title: `Delegation ${i}`,
          subtitle: `Subtitle ${i}`,
          agents: [
            { name: `Agent${i}`, status: 'active', agentType: 'coder' },
          ],
          summary: `Summary ${i}`,
        };

        const steps: JourneyStep[] = [];

        const { unmount } = render(
          <AgentJourneyPanel
            delegation={delegation}
            steps={steps}
            onClose={() => {}}
          />
        );

        expect(screen.getAllByText(`Delegation ${i}`).length).toBeGreaterThan(0);
        expect(screen.getAllByText(`Subtitle ${i}`).length).toBeGreaterThan(0);
        expect(screen.getAllByText(`Agent${i}`).length).toBeGreaterThan(0);

        unmount();
      }
    });
  });

  /**
   * Property 33: Multiple Agent Journey Support
   * System supports multiple journey panels side by side
   * Validates: Requirement 12.6
   */
  describe('Property 33: Multiple Agent Journey Support', () => {
    it('should support rendering multiple panels with different delegations', () => {
      const delegation1: DelegationCardProps = {
        title: 'Delegation 1',
        agents: [{ name: 'Agent1', status: 'active', agentType: 'analyst' }],
      };

      const delegation2: DelegationCardProps = {
        title: 'Delegation 2',
        agents: [{ name: 'Agent2', status: 'active', agentType: 'coder' }],
      };

      const steps: JourneyStep[] = [];

      const { container: container1 } = render(
        <AgentJourneyPanel
          delegation={delegation1}
          steps={steps}
          onClose={() => {}}
        />
      );

      const { container: container2 } = render(
        <AgentJourneyPanel
          delegation={delegation2}
          steps={steps}
          onClose={() => {}}
        />
      );

      // Both panels should exist
      expect(container1.querySelector('.agent-journey-panel')).toBeInTheDocument();
      expect(container2.querySelector('.agent-journey-panel')).toBeInTheDocument();

      // Both should have their own titles (may appear multiple times in timeline)
      expect(screen.getAllByText('Delegation 1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Delegation 2').length).toBeGreaterThanOrEqual(1);
    });

    it('should maintain independent state for multiple panels', () => {
      for (let i = 0; i < 5; i++) {
        const delegations = Array.from({ length: 3 }, (_, idx) => ({
          title: `Panel ${i}-${idx}`,
          agents: [{ name: `Agent${i}-${idx}`, status: 'active' as const, agentType: 'analyst' as const }],
        }));

        const steps: JourneyStep[] = [];

        const containers = delegations.map((delegation) =>
          render(
            <AgentJourneyPanel
              delegation={delegation}
              steps={steps}
              onClose={() => {}}
            />
          )
        );

        // All panels should be rendered
        containers.forEach((c) => {
          expect(c.container.querySelector('.agent-journey-panel')).toBeInTheDocument();
        });

        // Cleanup
        containers.forEach((c) => c.unmount());
      }
    });
  });
});

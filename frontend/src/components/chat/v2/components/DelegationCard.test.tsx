/**
 * Chat Visualization V2 - DelegationCard Unit Tests
 *
 * Unit tests for DelegationCard component covering specific examples,
 * edge cases, and user interactions.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DelegationCard } from './DelegationCard';

describe('DelegationCard', () => {
  describe('Simple Variant', () => {
    it('should render simple variant with minimal props', () => {
      const agents = [
        { name: 'Analyst', role: 'Orchestrator', status: 'ativo' },
      ];

      const { container } = render(
        <DelegationCard variant="simple" agents={agents} />
      );

      expect(container.querySelector('.simple-delegation-card')).toBeTruthy();
      expect(screen.getByText('Analyst')).toBeTruthy();
      expect(screen.getByText('ativo')).toBeTruthy();
    });

    it('should display first agent in simple variant', () => {
      const agents = [
        { name: 'Analyst', role: 'Orchestrator', status: 'ativo' },
        { name: 'Coder', role: 'Specialist', status: 'aguardando' },
      ];

      render(<DelegationCard variant="simple" agents={agents} />);

      // Should show first agent
      expect(screen.getByText('Analyst')).toBeTruthy();
      // Should not show second agent in simple variant
      expect(screen.queryByText('Coder')).toBeFalsy();
    });

    it('should display origin role from first agent', () => {
      const agents = [
        { name: 'Analyst', role: 'Orchestrator', status: 'ativo' },
      ];

      render(<DelegationCard variant="simple" agents={agents} />);

      expect(screen.getByText('Orchestrator')).toBeTruthy();
    });

    it('should display agent status badge', () => {
      const agents = [
        { name: 'Analyst', role: 'Orchestrator', status: 'ativo' },
      ];

      render(<DelegationCard variant="simple" agents={agents} />);

      expect(screen.getByText('ativo')).toBeTruthy();
    });

    it('should return null for empty agents array', () => {
      const { container } = render(
        <DelegationCard variant="simple" agents={[]} />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe('Rich Variant', () => {
    it('should render rich variant with full details', () => {
      const agents = [
        { name: 'Analyst', role: 'Code Analysis', status: 'ativo' },
        { name: 'Coder', role: 'Implementation', status: 'aguardando' },
      ];

      const { container } = render(
        <DelegationCard
          variant="rich"
          agents={agents}
          title="Multi-Agent Task"
          subtitle="Complex delegation workflow"
          summary="Analyzing and implementing solution"
        />
      );

      expect(container.querySelector('.delegation-card')).toBeTruthy();
      expect(screen.getByText('Multi-Agent Task')).toBeTruthy();
      expect(screen.getByText('Complex delegation workflow')).toBeTruthy();
      expect(screen.getByText('Analyzing and implementing solution')).toBeTruthy();
    });

    it('should display all agents in rich variant', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'concluído' },
        { name: 'Coder', role: 'Coding', status: 'ativo' },
        { name: 'Researcher', role: 'Research', status: 'aguardando' },
      ];

      render(<DelegationCard variant="rich" agents={agents} />);

      expect(screen.getByText('Analyst')).toBeTruthy();
      expect(screen.getByText('Coder')).toBeTruthy();
      expect(screen.getByText('Researcher')).toBeTruthy();
    });

    it('should display agent roles and statuses', () => {
      const agents = [
        { name: 'Analyst', role: 'Code Analysis', status: 'concluído' },
      ];

      const { container } = render(<DelegationCard variant="rich" agents={agents} />);

      expect(screen.getByText('Code Analysis')).toBeTruthy();

      // Check status in agent row specifically
      const agentRow = container.querySelector('.delegation-agent-row');
      expect(agentRow).toBeTruthy();
      expect(agentRow?.textContent).toContain('concluído');
    });

    it('should render all agents in list', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
        { name: 'Coder', role: 'Coding', status: 'aguardando' },
        { name: 'Researcher', role: 'Research', status: 'concluído' },
      ];

      render(<DelegationCard variant="rich" agents={agents} />);

      expect(screen.getByText('Analyst')).toBeTruthy();
      expect(screen.getByText('Coder')).toBeTruthy();
      expect(screen.getByText('Researcher')).toBeTruthy();
    });

    it('should display custom title when provided', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];

      render(
        <DelegationCard
          variant="rich"
          agents={agents}
          title="Custom Title"
        />
      );

      expect(screen.getByText('Custom Title')).toBeTruthy();
    });

    it('should display custom subtitle when provided', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];

      render(
        <DelegationCard
          variant="rich"
          agents={agents}
          subtitle="Custom Subtitle"
        />
      );

      expect(screen.getByText('Custom Subtitle')).toBeTruthy();
    });
  });

  describe('Journey Button', () => {
    it('should render journey button when onOpenJourney is provided', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];
      const onOpenJourney = vi.fn();

      render(
        <DelegationCard
          variant="rich"
          agents={agents}
          onOpenJourney={onOpenJourney}
        />
      );

      expect(screen.getByText('percurso')).toBeTruthy();
    });

    it('should not render journey button when onOpenJourney is not provided', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];

      render(<DelegationCard variant="rich" agents={agents} />);

      expect(screen.queryByText('percurso')).toBeFalsy();
    });

    it('should call onOpenJourney when journey button is clicked', async () => {
      const user = userEvent.setup();
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];
      const onOpenJourney = vi.fn();

      render(
        <DelegationCard
          variant="rich"
          agents={agents}
          onOpenJourney={onOpenJourney}
        />
      );

      const button = screen.getByText('percurso');
      await user.click(button);

      expect(onOpenJourney).toHaveBeenCalledTimes(1);
    });

    it('should not render journey button in simple variant', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];
      const onOpenJourney = vi.fn();

      render(
        <DelegationCard
          variant="simple"
          agents={agents}
          onOpenJourney={onOpenJourney}
        />
      );

      expect(screen.queryByText('percurso')).toBeFalsy();
    });
  });

  describe('Agent List Display', () => {
    it('should apply custom accent color to agents', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo', accent: '#FF0000' },
      ];

      const { container } = render(
        <DelegationCard variant="rich" agents={agents} />
      );

      // Check that agent name is rendered with custom accent color
      const agentName = screen.getByText('Analyst');
      expect(agentName).toBeTruthy();
      const style = agentName.getAttribute('style');
      expect(style).toContain('#FF0000');
    });

    it('should fallback to card accent when agent accent is not provided', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];

      const { container } = render(
        <DelegationCard variant="rich" agents={agents} accent="#00FF00" />
      );

      // Check that agent name is rendered with card accent color
      const agentName = screen.getByText('Analyst');
      expect(agentName).toBeTruthy();
      const style = agentName.getAttribute('style');
      expect(style).toContain('#00FF00');
    });

    it('should render agent with agentType information', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo', agentType: 'analyst' as const },
      ];

      render(<DelegationCard variant="rich" agents={agents} />);

      expect(screen.getByText('Analyst')).toBeTruthy();
      expect(screen.getByText('Analysis')).toBeTruthy();
    });
  });

  describe('Styling and Animation', () => {
    it('should apply custom accent color to agent elements', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];

      const { container } = render(
        <DelegationCard variant="rich" agents={agents} accent="#123456" />
      );

      const card = container.querySelector('.delegation-card');
      expect(card).toBeTruthy();
      // Check that agent name uses the custom accent
      const agentName = screen.getByText('Analyst');
      const style = agentName.getAttribute('style');
      expect(style).toContain('#123456');
    });

    it('should use default accent color when not provided', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];

      const { container } = render(
        <DelegationCard variant="rich" agents={agents} />
      );

      const card = container.querySelector('.delegation-card');
      expect(card).toBeTruthy();
      // Check that agent name uses the default teal color
      const agentName = screen.getByText('Analyst');
      const style = agentName.getAttribute('style');
      expect(style).toContain('#0D6E6E'); // Default teal color
    });

    it('should apply custom className', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];

      const { container } = render(
        <DelegationCard
          variant="rich"
          agents={agents}
          className="custom-class"
        />
      );

      expect(container.querySelector('.custom-class')).toBeTruthy();
    });
  });

  describe('Edge Cases', () => {
    it('should handle very long agent names', () => {
      const agents = [
        {
          name: 'Very Long Agent Name That Exceeds Normal Length Expectations',
          role: 'Analysis',
          status: 'ativo',
        },
      ];

      render(<DelegationCard variant="rich" agents={agents} />);

      expect(screen.getByText('Very Long Agent Name That Exceeds Normal Length Expectations')).toBeTruthy();
    });

    it('should handle very long titles', () => {
      const agents = [
        { name: 'Analyst', role: 'Analysis', status: 'ativo' },
      ];

      const longTitle = 'This is a very long delegation title that might cause layout issues if not handled properly';

      render(
        <DelegationCard variant="rich" agents={agents} title={longTitle} />
      );

      expect(screen.getByText(longTitle)).toBeTruthy();
    });

    it('should handle special characters in agent names', () => {
      const agents = [
        { name: 'Analyst-v2.0', role: 'Analysis & Review', status: 'ativo' },
      ];

      render(<DelegationCard variant="rich" agents={agents} />);

      expect(screen.getByText('Analyst-v2.0')).toBeTruthy();
      expect(screen.getByText('Analysis & Review')).toBeTruthy();
    });

    it('should handle unicode characters', () => {
      const agents = [
        { name: 'Analista 🤖', role: 'Análise', status: 'ativo' },
      ];

      render(<DelegationCard variant="rich" agents={agents} />);

      expect(screen.getByText('Analista 🤖')).toBeTruthy();
      expect(screen.getByText('Análise')).toBeTruthy();
    });
  });
});

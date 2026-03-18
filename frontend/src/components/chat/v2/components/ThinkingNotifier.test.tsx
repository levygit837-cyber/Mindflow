/**
 * Chat Visualization V2 - ThinkingNotifier Unit Tests
 *
 * Unit tests for ThinkingNotifier and ThinkingNotifierRow components.
 * Tests active/inactive states, status formatting, and theme application.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThinkingNotifier } from './ThinkingNotifier';
import { ThinkingNotifierRow } from './ThinkingNotifierRow';
import type { MindflowV2AgentType } from '../types';

describe('ThinkingNotifier', () => {
  describe('Active/Inactive States', () => {
    it('should render active state with pulse animation', () => {
      const { container } = render(
        <ThinkingNotifier agentType="orchestrator" active={true} />
      );

      const notifier = container.querySelector('[data-active="true"]');
      expect(notifier).toBeInTheDocument();

      // Check for pulse animation class
      const pulseDot = container.querySelector('.mindflow-v2-pulse');
      expect(pulseDot).toBeInTheDocument();
    });

    it('should render inactive state without pulse animation', () => {
      const { container } = render(
        <ThinkingNotifier agentType="orchestrator" active={false} />
      );

      const notifier = container.querySelector('[data-active="false"]');
      expect(notifier).toBeInTheDocument();

      // Pulse animation should not be present
      const pulseDot = container.querySelector('.mindflow-v2-pulse');
      expect(pulseDot).not.toBeInTheDocument();
    });

    it('should default to inactive when active prop is not provided', () => {
      const { container } = render(
        <ThinkingNotifier agentType="analyst" />
      );

      const notifier = container.querySelector('[data-active="false"]');
      expect(notifier).toBeInTheDocument();
    });

    it('should render inactive state with correct data attribute', () => {
      const { container } = render(
        <ThinkingNotifier agentType="coder" active={false} />
      );

      const notifier = container.querySelector('[data-active="false"]') as HTMLElement;
      expect(notifier).toBeInTheDocument();
      expect(notifier.getAttribute('data-active')).toBe('false');
    });

    it('should render active state with correct data attribute', () => {
      const { container } = render(
        <ThinkingNotifier agentType="researcher" active={true} />
      );

      const notifier = container.querySelector('[data-active="true"]') as HTMLElement;
      expect(notifier).toBeInTheDocument();
      expect(notifier.getAttribute('data-active')).toBe('true');
    });
  });

  describe('Status Formatting', () => {
    it('should format "thinking" status to "pensando"', () => {
      const { container } = render(
        <ThinkingNotifier agentType="orchestrator" active={true} status="thinking" />
      );

      expect(container.textContent).toContain('pensando');
    });

    it('should format "waiting" status to "aguardando"', () => {
      const { container } = render(
        <ThinkingNotifier agentType="analyst" active={false} status="waiting" />
      );

      expect(container.textContent).toContain('aguardando');
    });

    it('should format "active" status to "ativo"', () => {
      const { container } = render(
        <ThinkingNotifier agentType="coder" active={true} status="active" />
      );

      expect(container.textContent).toContain('ativo');
    });

    it('should format "done" status to "concluído"', () => {
      const { container } = render(
        <ThinkingNotifier agentType="researcher" active={false} status="done" />
      );

      expect(container.textContent).toContain('concluído');
    });

    it('should default to "pensando" when active and no status provided', () => {
      const { container } = render(
        <ThinkingNotifier agentType="orchestrator" active={true} />
      );

      expect(container.textContent).toContain('pensando');
    });

    it('should default to "aguardando" when inactive and no status provided', () => {
      const { container } = render(
        <ThinkingNotifier agentType="analyst" active={false} />
      );

      expect(container.textContent).toContain('aguardando');
    });

    it('should preserve custom status text when not matching known patterns', () => {
      const { container } = render(
        <ThinkingNotifier agentType="coder" active={true} status="custom status" />
      );

      expect(container.textContent).toContain('custom status');
    });

    it('should handle case-insensitive status matching', () => {
      const { container } = render(
        <ThinkingNotifier agentType="orchestrator" active={true} status="THINKING" />
      );

      expect(container.textContent).toContain('pensando');
    });
  });

  describe('Theme Application', () => {
    it('should apply orchestrator theme colors', () => {
      const { container } = render(
        <ThinkingNotifier agentType="orchestrator" active={true} />
      );

      const notifier = container.querySelector('[data-agent-type="orchestrator"]');
      expect(notifier).toBeInTheDocument();
      expect(notifier?.getAttribute('data-agent-type')).toBe('orchestrator');
    });

    it('should apply analyst theme colors', () => {
      const { container } = render(
        <ThinkingNotifier agentType="analyst" active={true} />
      );

      const notifier = container.querySelector('[data-agent-type="analyst"]');
      expect(notifier).toBeInTheDocument();
      expect(notifier?.getAttribute('data-agent-type')).toBe('analyst');
    });

    it('should apply coder theme colors', () => {
      const { container } = render(
        <ThinkingNotifier agentType="coder" active={true} />
      );

      const notifier = container.querySelector('[data-agent-type="coder"]');
      expect(notifier).toBeInTheDocument();
      expect(notifier?.getAttribute('data-agent-type')).toBe('coder');
    });

    it('should apply researcher theme colors', () => {
      const { container } = render(
        <ThinkingNotifier agentType="researcher" active={true} />
      );

      const notifier = container.querySelector('[data-agent-type="researcher"]');
      expect(notifier).toBeInTheDocument();
      expect(notifier?.getAttribute('data-agent-type')).toBe('researcher');
    });

    it('should display correct short label for each agent type', () => {
      const agents: Array<{ type: MindflowV2AgentType; label: string }> = [
        { type: 'orchestrator', label: 'Orch' },
        { type: 'analyst', label: 'Analyst' },
        { type: 'coder', label: 'Coder' },
        { type: 'researcher', label: 'Researcher' },
      ];

      agents.forEach(({ type, label }) => {
        const { container } = render(
          <ThinkingNotifier agentType={type} active={true} />
        );
        expect(container.textContent).toContain(label);
      });
    });
  });
});

describe('ThinkingNotifierRow', () => {
  describe('Layout and Rendering', () => {
    it('should render all four agent types', () => {
      const { container } = render(
        <ThinkingNotifierRow activeAgents={['orchestrator']} />
      );

      const notifiers = container.querySelectorAll('[data-agent-type]');
      expect(notifiers.length).toBe(4);

      const agentTypes = Array.from(notifiers).map((el) =>
        el.getAttribute('data-agent-type')
      );
      expect(agentTypes).toContain('orchestrator');
      expect(agentTypes).toContain('analyst');
      expect(agentTypes).toContain('coder');
      expect(agentTypes).toContain('researcher');
    });

    it('should mark specified agents as active', () => {
      const { container } = render(
        <ThinkingNotifierRow activeAgents={['orchestrator', 'analyst']} />
      );

      const orchestratorNotifier = container.querySelector(
        '[data-agent-type="orchestrator"]'
      );
      const analystNotifier = container.querySelector('[data-agent-type="analyst"]');
      const coderNotifier = container.querySelector('[data-agent-type="coder"]');

      expect(orchestratorNotifier?.getAttribute('data-active')).toBe('true');
      expect(analystNotifier?.getAttribute('data-active')).toBe('true');
      expect(coderNotifier?.getAttribute('data-active')).toBe('false');
    });

    it('should handle empty activeAgents array', () => {
      const { container } = render(<ThinkingNotifierRow activeAgents={[]} />);

      const notifiers = container.querySelectorAll('[data-active="true"]');
      expect(notifiers.length).toBe(0);

      const inactiveNotifiers = container.querySelectorAll('[data-active="false"]');
      expect(inactiveNotifiers.length).toBe(4);
    });

    it('should handle all agents active', () => {
      const { container } = render(
        <ThinkingNotifierRow
          activeAgents={['orchestrator', 'analyst', 'coder', 'researcher']}
        />
      );

      const activeNotifiers = container.querySelectorAll('[data-active="true"]');
      expect(activeNotifiers.length).toBe(4);
    });

    it('should apply custom className', () => {
      const { container } = render(
        <ThinkingNotifierRow
          activeAgents={['orchestrator']}
          className="custom-class"
        />
      );

      const row = container.querySelector('.custom-class');
      expect(row).toBeInTheDocument();
    });
  });

  describe('Status Management', () => {
    it('should apply individual statuses to each agent', () => {
      const { container } = render(
        <ThinkingNotifierRow
          activeAgents={['orchestrator', 'analyst']}
          statuses={{
            orchestrator: 'thinking',
            analyst: 'active',
            coder: 'waiting',
          }}
        />
      );

      expect(container.textContent).toContain('pensando');
      expect(container.textContent).toContain('ativo');
      expect(container.textContent).toContain('aguardando');
    });

    it('should handle missing statuses gracefully', () => {
      const { container } = render(
        <ThinkingNotifierRow
          activeAgents={['orchestrator']}
          statuses={{}}
        />
      );

      // Should render without errors
      const notifiers = container.querySelectorAll('[data-agent-type]');
      expect(notifiers.length).toBe(4);
    });

    it('should handle partial status object', () => {
      const { container } = render(
        <ThinkingNotifierRow
          activeAgents={['orchestrator', 'analyst']}
          statuses={{
            orchestrator: 'thinking',
            // analyst status missing
          }}
        />
      );

      // Should render without errors
      const notifiers = container.querySelectorAll('[data-agent-type]');
      expect(notifiers.length).toBe(4);
    });
  });

  describe('Agent Order', () => {
    it('should render agents in consistent order', () => {
      const { container } = render(
        <ThinkingNotifierRow activeAgents={['researcher', 'orchestrator']} />
      );

      const notifiers = container.querySelectorAll('[data-agent-type]');
      const agentTypes = Array.from(notifiers).map((el) =>
        el.getAttribute('data-agent-type')
      );

      // Should follow MINDFLOW_V2_AGENT_ORDER: orchestrator, analyst, coder, researcher
      expect(agentTypes).toEqual(['orchestrator', 'analyst', 'coder', 'researcher']);
    });
  });
});

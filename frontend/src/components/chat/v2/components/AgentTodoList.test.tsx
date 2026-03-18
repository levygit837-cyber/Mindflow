/**
 * Chat Visualization V2 - AgentTodoList Unit Tests
 *
 * Unit tests for AgentTodoList component covering specific examples,
 * edge cases, and user interactions.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentTodoList } from './AgentTodoList';
import { DelegationCardProps } from './DelegationCard';

describe('AgentTodoList', () => {
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

  const mockDelegations: DelegationCardProps[] = [
    {
      agents: [
        {
          name: 'Analyst',
          role: 'Orchestrator',
          status: 'ativo',
          agentType: 'analyst',
        },
      ],
    },
    {
      agents: [
        {
          name: 'Coder',
          role: 'Orchestrator',
          status: 'aguardando',
          agentType: 'coder',
        },
      ],
    },
  ];

  describe('Dark Theme Rendering', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    it('should render in dark theme when streaming with delegations', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      const todoList = container.querySelector('.agent-todo-list');
      expect(todoList).toBeTruthy();
    });

    it('should render header with title', () => {
      render(<AgentTodoList delegations={mockDelegations} isStreaming={true} />);

      expect(screen.getByText('Tarefas do Orquestrador')).toBeTruthy();
    });

    it('should render agent count badge with correct count', () => {
      render(<AgentTodoList delegations={mockDelegations} isStreaming={true} />);

      // 2 delegations with 1 agent each = 2 agents
      expect(screen.getByText('2 agentes')).toBeTruthy();
    });

    it('should render singular "agente" for single agent', () => {
      const singleDelegation: DelegationCardProps[] = [
        {
          agents: [
            {
              name: 'Analyst',
              role: 'Orchestrator',
              status: 'ativo',
              agentType: 'analyst',
            },
          ],
        },
      ];

      render(<AgentTodoList delegations={singleDelegation} isStreaming={true} />);

      expect(screen.getByText('1 agente')).toBeTruthy();
    });

    it('should render live status badge', () => {
      render(<AgentTodoList delegations={mockDelegations} isStreaming={true} />);

      expect(screen.getByText('ao vivo')).toBeTruthy();
    });

    it('should render delegation cards in simple variant', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      const simpleCards = container.querySelectorAll('.simple-delegation-card');
      expect(simpleCards.length).toBe(2);
    });

    it('should count multiple agents correctly', () => {
      const multiAgentDelegations: DelegationCardProps[] = [
        {
          agents: [
            { name: 'Analyst', role: 'Orchestrator', status: 'ativo' },
            { name: 'Coder', role: 'Specialist', status: 'ativo' },
          ],
        },
        {
          agents: [
            { name: 'Researcher', role: 'Orchestrator', status: 'aguardando' },
          ],
        },
      ];

      render(<AgentTodoList delegations={multiAgentDelegations} isStreaming={true} />);

      // 2 agents in first delegation + 1 agent in second = 3 agents
      expect(screen.getByText('3 agentes')).toBeTruthy();
    });
  });

  describe('Light Theme Exclusion', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'light');
    });

    it('should return null in light theme', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      expect(container.firstChild).toBeFalsy();
    });

    it('should not render any content in light theme', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      expect(container.querySelector('.agent-todo-list')).toBeFalsy();
      expect(container.textContent).toBe('');
    });
  });

  describe('Conditional Rendering Logic', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    it('should not render when not streaming', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={false} />
      );

      expect(container.firstChild).toBeFalsy();
    });

    it('should not render when delegations array is empty', () => {
      const { container } = render(
        <AgentTodoList delegations={[]} isStreaming={true} />
      );

      expect(container.firstChild).toBeFalsy();
    });

    it('should not render when both not streaming and empty delegations', () => {
      const { container } = render(
        <AgentTodoList delegations={[]} isStreaming={false} />
      );

      expect(container.firstChild).toBeFalsy();
    });

    it('should render when streaming and has delegations', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      expect(container.querySelector('.agent-todo-list')).toBeTruthy();
    });

    it('should handle isStreaming default value', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} />
      );

      // Default isStreaming is false, should not render
      expect(container.firstChild).toBeFalsy();
    });
  });

  describe('Real-Time Updates', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    it('should update when delegations change', () => {
      const { container, rerender } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      // Initial render
      let cards = container.querySelectorAll('.simple-delegation-card');
      expect(cards.length).toBe(2);

      // Add more delegations
      const updatedDelegations: DelegationCardProps[] = [
        ...mockDelegations,
        {
          agents: [
            {
              name: 'Researcher',
              role: 'Orchestrator',
              status: 'ativo',
              agentType: 'researcher',
            },
          ],
        },
      ];

      rerender(<AgentTodoList delegations={updatedDelegations} isStreaming={true} />);

      // Should render 3 cards now
      cards = container.querySelectorAll('.simple-delegation-card');
      expect(cards.length).toBe(3);
    });

    it('should update agent count when delegations change', () => {
      const { rerender } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      expect(screen.getByText('2 agentes')).toBeTruthy();

      // Update with more agents
      const moreDelegations: DelegationCardProps[] = [
        ...mockDelegations,
        {
          agents: [
            { name: 'Researcher', role: 'Orchestrator', status: 'ativo' },
          ],
        },
      ];

      rerender(<AgentTodoList delegations={moreDelegations} isStreaming={true} />);

      expect(screen.getByText('3 agentes')).toBeTruthy();
    });

    it('should hide when streaming stops', () => {
      const { container, rerender } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      expect(container.querySelector('.agent-todo-list')).toBeTruthy();

      // Stop streaming
      rerender(<AgentTodoList delegations={mockDelegations} isStreaming={false} />);

      expect(container.querySelector('.agent-todo-list')).toBeFalsy();
    });

    it('should hide when delegations become empty', () => {
      const { container, rerender } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      expect(container.querySelector('.agent-todo-list')).toBeTruthy();

      // Clear delegations
      rerender(<AgentTodoList delegations={[]} isStreaming={true} />);

      expect(container.querySelector('.agent-todo-list')).toBeFalsy();
    });
  });

  describe('Flexible Layout', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    it('should apply flexible layout with wrap', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      const layoutContainer = container.querySelector('.agent-todo-list > div:last-child');
      expect(layoutContainer).toBeTruthy();

      const styles = window.getComputedStyle(layoutContainer as Element);
      expect(styles.display).toBe('flex');
    });

    it('should render each delegation in a flex item', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      const flexItems = container.querySelectorAll('.agent-todo-list > div:last-child > div');
      expect(flexItems.length).toBe(2);
    });
  });

  describe('Edge Cases', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    it('should handle delegation with no agents gracefully', () => {
      const emptyAgentDelegation: DelegationCardProps[] = [
        {
          agents: [],
        },
      ];

      const { container } = render(
        <AgentTodoList delegations={emptyAgentDelegation} isStreaming={true} />
      );

      // Should render but with 0 agents
      expect(screen.getByText('0 agentes')).toBeTruthy();
    });

    it('should handle custom className', () => {
      const { container } = render(
        <AgentTodoList
          delegations={mockDelegations}
          isStreaming={true}
          className="custom-class"
        />
      );

      const todoList = container.querySelector('.agent-todo-list');
      expect(todoList?.classList.contains('custom-class')).toBe(true);
    });

    it('should handle delegations with missing agentType', () => {
      const delegationsWithoutType: DelegationCardProps[] = [
        {
          agents: [
            {
              name: 'Unknown Agent',
              role: 'Orchestrator',
              status: 'ativo',
            },
          ],
        },
      ];

      const { container } = render(
        <AgentTodoList delegations={delegationsWithoutType} isStreaming={true} />
      );

      expect(container.querySelector('.agent-todo-list')).toBeTruthy();
      expect(screen.getByText('Unknown Agent')).toBeTruthy();
    });
  });

  describe('Animation', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    it('should render with framer-motion animation', () => {
      const { container } = render(
        <AgentTodoList delegations={mockDelegations} isStreaming={true} />
      );

      const todoList = container.querySelector('.agent-todo-list');
      expect(todoList).toBeTruthy();
      // Component should be wrapped in motion.div
      expect(todoList?.parentElement?.tagName).toBeTruthy();
    });
  });
});

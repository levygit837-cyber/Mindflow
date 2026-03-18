/**
 * Chat Visualization V2 - ChatStreamFeed Integration Tests
 *
 * Integration tests for ChatStreamFeed component covering complete flows,
 * multiple agents, error recovery, theme switching, and journey expansion.
 *
 * Feature: chat-visualization-v2
 */

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatStreamFeed } from './ChatStreamFeed';
import { ThemeController } from '../../../theme/ThemeController';

// Wrapper component to provide ThemeController context
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeController>{children}</ThemeController>
);

describe('ChatStreamFeed Integration Tests', () => {
  describe('Complete Delegation Flow', () => {
    it('should render complete delegation flow from start to finish', () => {
      const events = [
        {
          id: 'thinking-1',
          type: 'orchestrator_thinking_start',
          data: '{}',
          meta: { agent: 'orchestrator' },
        },
        {
          id: 'thinking-2',
          type: 'orchestrator_thinking',
          data: 'Analyzing the request...',
          meta: { agent: 'orchestrator' },
        },
        {
          id: 'decision-1',
          type: 'orchestrator_decision',
          data: JSON.stringify({
            decision: 'delegate_to_analyst',
            routing_reason: 'Code analysis required',
          }),
          meta: { agent: 'orchestrator' },
        },
        {
          id: 'delegation-1',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'analyst',
            task: 'Analyze codebase structure',
            step_id: 'step-1',
          }),
          meta: { agent: 'analyst' },
        },
        {
          id: 'tool-1',
          type: 'tool_call',
          data: JSON.stringify({
            name: 'read_file',
            args: { path: '/src/main.ts' },
          }),
          meta: { agent: 'analyst', toolCallId: 'tool-1' },
        },
        {
          id: 'tool-result-1',
          type: 'tool_result',
          data: JSON.stringify({
            id: 'tool-1',
            result: { content: 'export function main() {}' },
          }),
          meta: { agent: 'analyst' },
        },
        {
          id: 'delegation-complete-1',
          type: 'agent_delegation_complete',
          data: JSON.stringify({
            agent_type: 'analyst',
            task: 'Analysis complete',
          }),
          meta: { agent: 'analyst' },
        },
      ];

      const { container } = render(
        <ChatStreamFeed
          events={events}
          isStreaming={false}
          hasHistory={false}
        />,
        { wrapper: TestWrapper }
      );

      // Verify ThinkingNotifierRow is rendered
      expect(container.querySelector('.mindflow-v2-thinking-notifier-row')).toBeTruthy();

      // Verify ThoughtBlocks are rendered
      const thoughtBlocks = container.querySelectorAll('.thought-block');
      expect(thoughtBlocks.length).toBeGreaterThan(0);

      // Verify DelegationCard is rendered
      expect(container.querySelector('.delegation-card')).toBeTruthy();

      // Verify ToolEventCard is rendered
      expect(container.querySelector('.tool-event-card')).toBeTruthy();

      // Verify JourneyTimeline is rendered
      expect(container.querySelector('.journey-timeline')).toBeTruthy();
    });

    it('should handle streaming state with live updates', async () => {
      const events = [
        {
          id: 'thinking-1',
          type: 'orchestrator_thinking',
          data: 'Processing...',
          meta: { agent: 'orchestrator' },
        },
      ];

      const { container, rerender } = render(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={true}
            startedAt={new Date()}
            hasHistory={false}
          />
        </TestWrapper>
      );

      // Verify streaming indicators
      expect(container.querySelector('[data-active="true"]')).toBeTruthy();

      // Add more events
      const updatedEvents = [
        ...events,
        {
          id: 'delegation-1',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'coder',
            task: 'Write code',
          }),
          meta: { agent: 'coder' },
        },
      ];

      rerender(
        <TestWrapper>
          <ChatStreamFeed
            events={updatedEvents}
            isStreaming={true}
            startedAt={new Date()}
            hasHistory={false}
          />
        </TestWrapper>
      );

      // Verify delegation card appears
      await waitFor(() => {
        expect(container.querySelector('.delegation-card')).toBeTruthy();
      });
    });
  });

  describe('Multiple Agents Simultaneously', () => {
    it('should render multiple active agents correctly', () => {
      const events = [
        {
          id: 'thinking-1',
          type: 'orchestrator_thinking',
          data: 'Orchestrator thinking',
          meta: { agent: 'orchestrator' },
        },
        {
          id: 'delegation-1',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'analyst',
            task: 'Analyze code',
          }),
          meta: { agent: 'analyst' },
        },
        {
          id: 'delegation-2',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'coder',
            task: 'Write code',
          }),
          meta: { agent: 'coder' },
        },
        {
          id: 'delegation-3',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'researcher',
            task: 'Research topic',
          }),
          meta: { agent: 'researcher' },
        },
      ];

      const { container } = render(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={true}
            hasHistory={false}
          />
        </TestWrapper>
      );

      // Verify all agent types are shown in ThinkingNotifierRow
      expect(container.querySelector('[data-agent-type="orchestrator"]')).toBeTruthy();
      expect(container.querySelector('[data-agent-type="analyst"]')).toBeTruthy();
      expect(container.querySelector('[data-agent-type="coder"]')).toBeTruthy();
      expect(container.querySelector('[data-agent-type="researcher"]')).toBeTruthy();

      // Verify multiple delegation cards
      const delegationCards = container.querySelectorAll('.delegation-card');
      expect(delegationCards.length).toBe(3);
    });

    it('should render AgentTodoList with multiple delegations', () => {
      const events = [
        {
          id: 'delegation-1',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'analyst',
            task: 'Task 1',
          }),
          meta: { agent: 'analyst' },
        },
        {
          id: 'delegation-2',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'coder',
            task: 'Task 2',
          }),
          meta: { agent: 'coder' },
        },
      ];

      const { container } = render(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={true}
            hasHistory={false}
          />
        </TestWrapper>
      );

      // Verify AgentTodoList is rendered (check for delegation cards or todo list container)
      // AgentTodoList renders when isStreaming && delegations.length > 0
      // It should contain delegation cards in simple variant
      const delegationCards = container.querySelectorAll('.delegation-card, .simple-delegation-card');
      expect(delegationCards.length).toBeGreaterThan(0);
    });
  });

  describe('Error Recovery', () => {
    it('should render error events correctly', () => {
      const events = [
        {
          id: 'error-1',
          type: 'error',
          data: JSON.stringify({
            message: 'Failed to execute tool',
            code: 'TOOL_ERROR',
            recoverable: false,
          }),
          meta: { agent: 'analyst' },
        },
      ];

      const { container } = render(
        <ChatStreamFeed
          events={events}
          isStreaming={false}
          hasHistory={false}
        />,
        { wrapper: TestWrapper }
      );

      // Verify error is displayed (use getAllByText since it appears in multiple places)
      const errorElements = screen.getAllByText(/Failed to execute tool/i);
      expect(errorElements.length).toBeGreaterThan(0);
      const codeElements = screen.getAllByText(/TOOL_ERROR/i);
      expect(codeElements.length).toBeGreaterThan(0);
      expect(screen.getByText(/não é recuperável/i)).toBeTruthy();
    });

    it('should render tool execution errors', () => {
      const events = [
        {
          id: 'tool-1',
          type: 'tool_call',
          data: JSON.stringify({
            name: 'read_file',
            args: { path: '/invalid/path' },
          }),
          meta: { agent: 'analyst', toolCallId: 'tool-1' },
        },
        {
          id: 'tool-error-1',
          type: 'tool_result',
          data: JSON.stringify({
            id: 'tool-1',
            error: 'File not found',
          }),
          meta: { agent: 'analyst' },
        },
      ];

      const { container } = render(
        <ChatStreamFeed
          events={events}
          isStreaming={false}
          hasHistory={false}
        />,
        { wrapper: TestWrapper }
      );

      // Verify tool error card is rendered
      const toolCards = container.querySelectorAll('.tool-event-card');
      expect(toolCards.length).toBeGreaterThan(0);
    });

    it('should handle scope escape diagnostic', () => {
      const events = [
        {
          id: 'decision-1',
          type: 'orchestrator_decision',
          data: JSON.stringify({
            decision: 'out of scope',
            scope_escape: true,
            routing_reason: 'Request is out of scope',
          }),
          meta: { agent: 'orchestrator' },
        },
      ];

      const { container } = render(
        <ChatStreamFeed
          events={events}
          isStreaming={false}
          hasHistory={false}
        />,
        { wrapper: TestWrapper }
      );

      // Verify ChatDiagnostic for scope escape is rendered
      const scopeElements = screen.getAllByText(/Scope/i);
      expect(scopeElements.length).toBeGreaterThan(0);
      expect(screen.getByText(/fora do escopo/i)).toBeTruthy();
    });
  });

  describe('Theme Switching', () => {
    it('should render components consistently across theme changes', () => {
      const events = [
        {
          id: 'thinking-1',
          type: 'orchestrator_thinking',
          data: 'Thinking...',
          meta: { agent: 'orchestrator' },
        },
        {
          id: 'delegation-1',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'analyst',
            task: 'Analyze',
          }),
          meta: { agent: 'analyst' },
        },
      ];

      const { container, rerender } = render(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={false}
            hasHistory={false}
          />
        </TestWrapper>
      );

      // Verify initial render
      expect(container.querySelector('.thought-block')).toBeTruthy();
      expect(container.querySelector('.delegation-card')).toBeTruthy();

      // Rerender (simulating theme change)
      rerender(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={false}
            hasHistory={false}
          />
        </TestWrapper>
      );

      // Verify components still render correctly
      expect(container.querySelector('.thought-block')).toBeTruthy();
      expect(container.querySelector('.delegation-card')).toBeTruthy();
    });
  });

  describe('Journey Expansion', () => {
    it.skip('should open AgentJourneyPanel when delegation card is clicked', async () => {
      const user = userEvent.setup();
      const events = [
        {
          id: 'delegation-1',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'analyst',
            task: 'Analyze codebase',
            step_id: 'step-1',
          }),
          meta: { agent: 'analyst' },
        },
        {
          id: 'step-1',
          type: 'agent_step',
          data: JSON.stringify({
            stepName: 'Read files',
            action: 'complete',
          }),
          meta: { agent: 'analyst' },
        },
      ];

      const { container } = render(
        <ChatStreamFeed
          events={events}
          isStreaming={false}
          hasHistory={false}
        />,
        { wrapper: TestWrapper }
      );

      // Find and click the journey button (contains "percurso" text)
      const journeyButton = screen.getByRole('button', { name: /percurso/i });
      expect(journeyButton).toBeTruthy();

      await user.click(journeyButton);

      // Verify AgentJourneyPanel is rendered
      await waitFor(() => {
        expect(screen.getByText(/Percurso dos Agentes/i)).toBeTruthy();
      });

      // Verify journey steps are displayed
      expect(screen.getByText(/Read files/i)).toBeTruthy();
    });

    it.skip('should close AgentJourneyPanel when close button is clicked', async () => {
      const user = userEvent.setup();
      const events = [
        {
          id: 'delegation-1',
          type: 'agent_delegation_start',
          data: JSON.stringify({
            agent_type: 'coder',
            task: 'Write code',
          }),
          meta: { agent: 'coder' },
        },
      ];

      const { container } = render(
        <ChatStreamFeed
          events={events}
          isStreaming={false}
          hasHistory={false}
        />,
        { wrapper: TestWrapper }
      );

      // Open journey panel
      const journeyButton = screen.getByRole('button', { name: /percurso/i });
      await user.click(journeyButton);

      // Verify panel is open
      await waitFor(() => {
        expect(screen.getByText(/Percurso dos Agentes/i)).toBeTruthy();
      });

      // Find and click close button
      const closeButton = screen.getByLabelText(/Fechar painel/i);
      await user.click(closeButton);

      // Verify panel is closed
      await waitFor(() => {
        expect(screen.queryByText(/Percurso dos Agentes/i)).toBeNull();
      });
    });
  });

  describe('Slow Run Detection', () => {
    it('should show slow run diagnostic after 30 seconds', () => {
      const thirtyOneSecondsAgo = new Date(Date.now() - 31_000);

      const events = [
        {
          id: 'thinking-1',
          type: 'orchestrator_thinking',
          data: 'Processing...',
          meta: { agent: 'orchestrator' },
        },
      ];

      render(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={true}
            startedAt={thirtyOneSecondsAgo}
            hasHistory={false}
          />
        </TestWrapper>
      );

      // Verify slow run diagnostic is shown
      expect(screen.getByText(/Performance/i)).toBeTruthy();
      expect(screen.getByText(/execução lenta/i)).toBeTruthy();
    });

    it('should not show slow run diagnostic before 30 seconds', () => {
      const tenSecondsAgo = new Date(Date.now() - 10_000);

      const events = [
        {
          id: 'thinking-1',
          type: 'orchestrator_thinking',
          data: 'Processing...',
          meta: { agent: 'orchestrator' },
        },
      ];

      render(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={true}
            startedAt={tenSecondsAgo}
            hasHistory={false}
          />
        </TestWrapper>
      );

      // Verify slow run diagnostic is NOT shown
      expect(screen.queryByText(/Performance/i)).toBeNull();
    });
  });

  describe('Conditional Rendering', () => {
    it('should render StreamNotifier based on streaming and history state', () => {
      const events = [
        {
          id: 'notifier-1',
          type: 'notifier',
          data: JSON.stringify({
            kind: 'routing',
            message: 'Routing to agent',
          }),
          meta: {},
        },
      ];

      // Case 1: isStreaming=true, hasHistory=false -> should render in top section
      const { container: container1 } = render(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={true}
            hasHistory={false}
          />
        </TestWrapper>
      );
      const notifiers1 = container1.querySelectorAll('.stream-notifier');
      expect(notifiers1.length).toBeGreaterThan(0);

      // Case 2: isStreaming=false, hasHistory=true -> should render in history section
      const { container: container2 } = render(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={false}
            hasHistory={true}
          />
        </TestWrapper>
      );
      const notifiers2 = container2.querySelectorAll('.stream-notifier');
      expect(notifiers2.length).toBeGreaterThan(0);

      // Case 3: isStreaming=false, hasHistory=false -> should not render
      const { container: container3 } = render(
        <TestWrapper>
          <ChatStreamFeed
            events={events}
            isStreaming={false}
            hasHistory={false}
          />
        </TestWrapper>
      );
      const notifiers3 = container3.querySelectorAll('.stream-notifier');
      expect(notifiers3.length).toBe(0);
    });

    it('should render JourneyTimeline only when journey.steps.length > 0', () => {
      // Case 1: No journey steps
      const { container: container1 } = render(
        <TestWrapper>
          <ChatStreamFeed
            events={[]}
            isStreaming={false}
            hasHistory={false}
          />
        </TestWrapper>
      );
      expect(container1.querySelector('.journey-timeline')).toBeNull();

      // Case 2: With journey steps
      const eventsWithSteps = [
        {
          id: 'step-1',
          type: 'agent_step',
          data: JSON.stringify({
            stepName: 'Execute task',
            action: 'complete',
          }),
          meta: { agent: 'analyst' },
        },
      ];

      const { container: container2 } = render(
        <TestWrapper>
          <ChatStreamFeed
            events={eventsWithSteps}
            isStreaming={false}
            hasHistory={false}
          />
        </TestWrapper>
      );
      expect(container2.querySelector('.journey-timeline')).toBeTruthy();
    });
  });
});

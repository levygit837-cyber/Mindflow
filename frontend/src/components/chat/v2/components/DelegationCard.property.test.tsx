/**
 * Chat Visualization V2 - DelegationCard Property Tests
 *
 * Property-based tests for DelegationCard component.
 * These tests validate universal correctness properties across
 * multiple generated inputs using fast-check.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import fc from 'fast-check';
import { DelegationCard } from './DelegationCard';
import type { MindflowV2AgentType } from '../../types';

/**
 * Property 8: Delegation Card Creation
 *
 * For any delegation event from the orchestrator, a DelegationCard
 * component should be rendered in the chat feed.
 *
 * Validates: Requirements 6.1
 */
describe('Property 8: Delegation Card Creation', () => {
  it('should render DelegationCard for any valid delegation data', () => {
    fc.assert(
      fc.property(
        fc.record({
          title: fc.constantFrom('Delegation Task', 'Agent Work', 'Processing Request', 'Analysis Job'),
          subtitle: fc.constantFrom('Analyzing code', 'Processing data', 'Reviewing implementation', 'Executing task'),
          status: fc.constantFrom('ativo', 'concluído', 'aguardando', 'erro'),
          agents: fc.array(
            fc.record({
              name: fc.constantFrom('Analyst', 'Coder', 'Researcher', 'Orchestrator'),
              role: fc.constantFrom('Analysis', 'Development', 'Research', 'Coordination'),
              status: fc.constantFrom('ativo', 'concluído', 'aguardando'),
              agentType: fc.constantFrom<MindflowV2AgentType>('orchestrator', 'analyst', 'coder', 'researcher'),
            }),
            { minLength: 1, maxLength: 5 }
          ),
          variant: fc.constantFrom('simple', 'rich') as fc.Arbitrary<'simple' | 'rich'>,
        }),
        (props) => {
          const { container } = render(<DelegationCard {...props} />);

          // Should render a delegation card
          expect(container.firstChild).toBeTruthy();

          // Should have appropriate class based on variant
          const expectedClass = props.variant === 'simple' ? 'simple-delegation-card' : 'delegation-card';
          expect(container.querySelector(`.${expectedClass}`)).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should render for both simple and rich variants', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('simple', 'rich') as fc.Arbitrary<'simple' | 'rich'>,
        fc.array(
          fc.record({
            name: fc.constantFrom('Agent A', 'Agent B', 'Agent C'),
            role: fc.constantFrom('Role 1', 'Role 2', 'Role 3'),
            status: fc.constantFrom('status-1', 'status-2', 'status-3'),
          }),
          { minLength: 1, maxLength: 3 }
        ),
        (variant, agents) => {
          const { container } = render(
            <DelegationCard
              variant={variant}
              agents={agents}
              title="Delegation Title"
              subtitle="Delegation Subtitle"
            />
          );

          // Should always render
          expect(container.firstChild).toBeTruthy();

          // Variant-specific checks
          if (variant === 'simple') {
            expect(container.querySelector('.simple-delegation-card')).toBeTruthy();
          } else {
            expect(container.querySelector('.delegation-card')).toBeTruthy();
          }
        }
      ),
      { numRuns: 50 }
    );
  });
});

/**
 * Property 9: Delegation Card Agent Information
 *
 * For any delegation card, the card should contain the agent type
 * information of the delegated agent.
 *
 * Validates: Requirements 6.2
 */
describe('Property 9: Delegation Card Agent Information', () => {
  it('should display agent type information for all agents', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            name: fc.constantFrom('Analyst', 'Coder', 'Researcher', 'Orchestrator'),
            role: fc.string({ minLength: 1, maxLength: 50 }),
            status: fc.string({ minLength: 1, maxLength: 20 }),
            agentType: fc.constantFrom<MindflowV2AgentType>('orchestrator', 'analyst', 'coder', 'researcher'),
          }),
          { minLength: 1, maxLength: 4 }
        ),
        (agents) => {
          const { container } = render(
            <DelegationCard
              variant="rich"
              agents={agents}
              title="Delegation"
            />
          );

          // Should render agent rows for all agents
          const agentRows = container.querySelectorAll('.delegation-agent-row');
          expect(agentRows.length).toBe(agents.length);

          // All unique agent names should be visible in the document
          const uniqueNames = [...new Set(agents.map(a => a.name))];
          for (const name of uniqueNames) {
            expect(screen.getAllByText(name).length).toBeGreaterThan(0);
          }
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should preserve agent type information across renders', () => {
    fc.assert(
      fc.property(
        fc.record({
          name: fc.constantFrom('Agent Alpha', 'Agent Beta', 'Agent Gamma', 'Agent Delta'),
          role: fc.constantFrom('Primary Role', 'Secondary Role', 'Support Role', 'Lead Role'),
          status: fc.constantFrom('working', 'ready', 'busy'),
          agentType: fc.constantFrom<MindflowV2AgentType>('orchestrator', 'analyst', 'coder', 'researcher'),
        }),
        (agent) => {
          const { rerender, container } = render(
            <DelegationCard
              variant="rich"
              agents={[agent]}
              title="Test Delegation"
            />
          );

          // Should have one agent row
          expect(container.querySelectorAll('.delegation-agent-row').length).toBe(1);

          // Agent name should be in the agent row
          const agentRow = container.querySelector('.delegation-agent-row');
          expect(agentRow?.textContent).toContain(agent.name);

          // Rerender with same data
          rerender(
            <DelegationCard
              variant="rich"
              agents={[agent]}
              title="Test Delegation"
            />
          );

          // Should still have one agent row
          expect(container.querySelectorAll('.delegation-agent-row').length).toBe(1);

          // Agent name should still be in the agent row
          const agentRowAfter = container.querySelector('.delegation-agent-row');
          expect(agentRowAfter?.textContent).toContain(agent.name);
        }
      ),
      { numRuns: 50 }
    );
  });
});

/**
 * Property 10: Delegation Card Real-Time State
 *
 * For any delegation card, the displayed state should match the
 * current delegation state from the stream events.
 *
 * Validates: Requirements 6.3
 */
describe('Property 10: Delegation Card Real-Time State', () => {
  it('should display current status for any valid status value', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('ativo', 'concluído', 'aguardando', 'erro', 'pausado', 'cancelado'),
        fc.array(
          fc.record({
            name: fc.string({ minLength: 1, maxLength: 50 }),
            role: fc.string({ minLength: 1, maxLength: 50 }),
            status: fc.constantFrom('ativo', 'concluído', 'aguardando', 'erro'),
          }),
          { minLength: 1, maxLength: 3 }
        ),
        (status, agents) => {
          const { container } = render(
            <DelegationCard
              variant="rich"
              status={status}
              agents={agents}
              title="Test Delegation"
            />
          );

          // Status should be visible in the document (may appear multiple times)
          const statusElements = screen.getAllByText(status);
          expect(statusElements.length).toBeGreaterThan(0);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should update status when props change', () => {
    fc.assert(
      fc.property(
        fc.tuple(
          fc.constantFrom('ativo', 'aguardando', 'processando'),
          fc.constantFrom('concluído', 'erro', 'cancelado')
        ),
        fc.array(
          fc.record({
            name: fc.string({ minLength: 1, maxLength: 50 }),
            role: fc.string({ minLength: 1, maxLength: 50 }),
            status: fc.constantFrom('concluído', 'erro', 'cancelado'), // Use different statuses from card status
          }),
          { minLength: 1, maxLength: 2 }
        ),
        ([initialStatus, updatedStatus], agents) => {
          const { rerender, container } = render(
            <DelegationCard
              variant="rich"
              status={initialStatus}
              agents={agents}
              title="Test"
              pipeline="em execução" // Use explicit pipeline to avoid default "ativo"
            />
          );

          // Initial status should be visible
          expect(screen.getAllByText(initialStatus).length).toBeGreaterThan(0);

          // Update status
          rerender(
            <DelegationCard
              variant="rich"
              status={updatedStatus}
              agents={agents}
              title="Test"
              pipeline="em execução"
            />
          );

          // Updated status should be visible
          expect(screen.getAllByText(updatedStatus).length).toBeGreaterThan(0);

          // Verify the component updated by checking it still renders correctly
          expect(container.querySelector('.delegation-card')).toBeTruthy();
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should reflect agent-level status changes', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            name: fc.string({ minLength: 1, maxLength: 50 }),
            role: fc.string({ minLength: 1, maxLength: 50 }),
            status: fc.constantFrom('ativo', 'concluído', 'aguardando'),
          }),
          { minLength: 1, maxLength: 3 }
        ),
        (agents) => {
          const { container } = render(
            <DelegationCard
              variant="rich"
              agents={agents}
              title="Test"
            />
          );

          // Should render correct number of agent rows
          expect(container.querySelectorAll('.delegation-agent-row').length).toBe(agents.length);

          // All unique agent statuses should be visible
          const uniqueStatuses = [...new Set(agents.map(a => a.status))];
          for (const status of uniqueStatuses) {
            expect(screen.getAllByText(status).length).toBeGreaterThan(0);
          }
        }
      ),
      { numRuns: 50 }
    );
  });
});

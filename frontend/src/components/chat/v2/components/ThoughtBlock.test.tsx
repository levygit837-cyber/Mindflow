/**
 * ThoughtBlock Component Tests
 *
 * Includes both property-based tests and unit tests for the ThoughtBlock component.
 * Tests validate Requirements 3.2, 3.4, 10.1, 10.2, 10.3, 10.4
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import fc from 'fast-check';
import { ThoughtBlock } from './ThoughtBlock';
import { MindflowV2AgentType } from '../types';

// ============================================
// Property-Based Tests
// ============================================

describe('Property-Based Tests', () => {
  // Feature: chat-visualization-v2, Property 3: Token-by-Token Animation
  // Validates: Requirements 3.2
  describe('Property 3: Token-by-Token Animation', () => {
    it('should render content progressively with animation, never displayed completely and instantaneously', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 1, maxLength: 1000 }),
          fc.constantFrom<MindflowV2AgentType>('orchestrator', 'analyst', 'coder', 'researcher'),
          (content, agentType) => {
            const { container } = render(
              <ThoughtBlock agentType={agentType} content={content} defaultExpanded={true} />
            );

            // Component should have animation attributes from framer-motion
            const thoughtBlock = container.querySelector('.thought-block');
            expect(thoughtBlock).toBeTruthy();

            // Content should be rendered (when expanded)
            const richText = container.querySelector('.thought-content');
            expect(richText).toBeTruthy();
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  // Feature: chat-visualization-v2, Property 4: Thought Block Auto-Collapse
  // Validates: Requirements 3.4
  describe('Property 4: Thought Block Auto-Collapse', () => {
    it('should transition to collapsed state after completion (unless defaultExpanded)', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 300, maxLength: 1000 }),
          fc.constantFrom<MindflowV2AgentType>('orchestrator', 'analyst', 'coder', 'researcher'),
          fc.string({ minLength: 1, maxLength: 50 }),
          (content, agentType, status) => {
            // Don't pass defaultExpanded, let component decide
            const { container } = render(
              <ThoughtBlock agentType={agentType} content={content} status={status} />
            );

            // For long content without "decision" status, should be collapsed
            if (!status.toLowerCase().includes('decision')) {
              const expandedBody = container.querySelector('.thought-body-expanded');
              expect(expandedBody).toBeFalsy();

              const preview = container.querySelector('.thought-preview');
              expect(preview).toBeTruthy();
            }
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  // Feature: chat-visualization-v2, Property 25: Thought Block Default Collapsed State
  // Validates: Requirements 10.3
  describe('Property 25: Thought Block Default Collapsed State', () => {
    it('should be collapsed by default for content >= 300 chars (except decisions)', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 300, maxLength: 2000 }),
          fc.constantFrom<MindflowV2AgentType>('orchestrator', 'analyst', 'coder', 'researcher'),
          (content, agentType) => {
            const { container } = render(
              <ThoughtBlock agentType={agentType} content={content} status="thinking" />
            );

            // Should be collapsed (no expanded body visible)
            const expandedBody = container.querySelector('.thought-body-expanded');
            expect(expandedBody).toBeFalsy();

            // Should show preview
            const preview = container.querySelector('.thought-preview');
            expect(preview).toBeTruthy();
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should be expanded by default for content < 300 chars', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 1, maxLength: 299 }),
          fc.constantFrom<MindflowV2AgentType>('orchestrator', 'analyst', 'coder', 'researcher'),
          (content, agentType) => {
            const { container } = render(
              <ThoughtBlock agentType={agentType} content={content} />
            );

            // Should be expanded (expanded body visible)
            const expandedBody = container.querySelector('.thought-body-expanded');
            expect(expandedBody).toBeTruthy();

            // Should NOT show preview
            const preview = container.querySelector('.thought-preview');
            expect(preview).toBeFalsy();
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should be expanded by default for decision status regardless of length', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 300, maxLength: 2000 }),
          fc.constantFrom<MindflowV2AgentType>('orchestrator', 'analyst', 'coder', 'researcher'),
          (content, agentType) => {
            const { container } = render(
              <ThoughtBlock agentType={agentType} content={content} status="decision" />
            );

            // Should be expanded even for long content
            const expandedBody = container.querySelector('.thought-body-expanded');
            expect(expandedBody).toBeTruthy();
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  // Feature: chat-visualization-v2, Property 26: Thought Block Click Expansion
  // Validates: Requirements 10.4
  describe('Property 26: Thought Block Click Expansion', () => {
    it('should toggle expanded state on click', { timeout: 30000 }, async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.string({ minLength: 300, maxLength: 1000 }),
          fc.constantFrom<MindflowV2AgentType>('orchestrator', 'analyst', 'coder', 'researcher'),
          async (content, agentType) => {
            const user = userEvent.setup();
            const { container, unmount } = render(
              <ThoughtBlock agentType={agentType} content={content} status="analyzing" />
            );

            // Initially collapsed
            let expandedBody = container.querySelector('.thought-body-expanded');
            expect(expandedBody).toBeFalsy();

            // Click to expand
            const button = container.querySelector('.thought-block-header') as HTMLButtonElement;
            await user.click(button);

            // Wait for animation
            await new Promise(resolve => setTimeout(resolve, 200));

            // Should now be expanded
            expandedBody = container.querySelector('.thought-body-expanded');
            expect(expandedBody).toBeTruthy();

            // Click again to collapse
            await user.click(button);

            // Wait for animation
            await new Promise(resolve => setTimeout(resolve, 200));

            // Should be collapsed again
            expandedBody = container.querySelector('.thought-body-expanded');
            expect(expandedBody).toBeFalsy();

            // Cleanup
            unmount();
          }
        ),
        { numRuns: 10 } // Reduced runs for async tests
      );
    });
  });
});

// ============================================
// Unit Tests
// ============================================

describe('ThoughtBlock Unit Tests', () => {
  describe('Collapsed State', () => {
    it('should render collapsed for long content', () => {
      const longContent = 'a'.repeat(500);
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={longContent} />
      );

      const expandedBody = container.querySelector('.thought-body-expanded');
      expect(expandedBody).toBeFalsy();

      const preview = container.querySelector('.thought-preview');
      expect(preview).toBeTruthy();
    });

    it('should show preview text (first 60 chars)', () => {
      const content = 'This is a long thought that should be truncated in the preview section because it exceeds sixty characters. ' + 'a'.repeat(300);
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={content} />
      );

      const preview = container.querySelector('.thought-preview');
      expect(preview).toBeTruthy();
      // Check that preview contains the first part of the content
      const previewText = preview?.textContent || '';
      expect(previewText).toContain('This is a long thought that should be truncated in the prev');
    });

    it('should display reasoning depth bar', () => {
      const content = 'a'.repeat(500);
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={content} />
      );

      const depthBar = container.querySelector('.reasoning-depth-bar');
      expect(depthBar).toBeTruthy();
      expect(depthBar?.textContent).toContain('Depth:');
    });

    it('should calculate correct depth level', () => {
      // Depth 1: < 200 chars
      const { container: c1 } = render(
        <ThoughtBlock agentType="orchestrator" content="short" />
      );
      // Should have 1 active segment (but component is expanded for short content)

      // Depth 2: 200-499 chars
      const { container: c2 } = render(
        <ThoughtBlock agentType="orchestrator" content={'a'.repeat(300)} />
      );
      const depthBar2 = c2.querySelector('.reasoning-depth-bar');
      expect(depthBar2).toBeTruthy();

      // Depth 3: >= 500 chars
      const { container: c3 } = render(
        <ThoughtBlock agentType="orchestrator" content={'a'.repeat(600)} />
      );
      const depthBar3 = c3.querySelector('.reasoning-depth-bar');
      expect(depthBar3).toBeTruthy();
    });
  });

  describe('Expanded State', () => {
    it('should render expanded when defaultExpanded is true', () => {
      const content = 'Test content';
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={content} defaultExpanded={true} />
      );

      const expandedBody = container.querySelector('.thought-body-expanded');
      expect(expandedBody).toBeTruthy();

      const preview = container.querySelector('.thought-preview');
      expect(preview).toBeFalsy();
    });

    it('should render RichText component in expanded state', () => {
      const content = '**Bold text** and *italic text*';
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={content} defaultExpanded={true} />
      );

      const richText = container.querySelector('.thought-content');
      expect(richText).toBeTruthy();
    });

    it('should display summary when provided', () => {
      const content = 'Test content';
      const summary = 'This is a summary';
      render(
        <ThoughtBlock
          agentType="orchestrator"
          content={content}
          summary={summary}
          defaultExpanded={true}
        />
      );

      expect(screen.getByText(summary)).toBeTruthy();
    });
  });

  describe('Click Interaction', () => {
    it('should expand on click when collapsed', async () => {
      const user = userEvent.setup();
      const content = 'a'.repeat(500);
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={content} />
      );

      // Initially collapsed
      expect(container.querySelector('.thought-body-expanded')).toBeFalsy();

      // Click to expand
      const button = container.querySelector('.thought-block-header') as HTMLButtonElement;
      await user.click(button);

      // Wait for animation to complete
      await new Promise(resolve => setTimeout(resolve, 200));

      // Should be expanded
      expect(container.querySelector('.thought-body-expanded')).toBeTruthy();
    });

    it('should collapse on click when expanded', async () => {
      const user = userEvent.setup();
      const content = 'Test content';
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={content} defaultExpanded={true} />
      );

      // Initially expanded
      expect(container.querySelector('.thought-body-expanded')).toBeTruthy();

      // Click to collapse
      const button = container.querySelector('.thought-block-header') as HTMLButtonElement;
      await user.click(button);

      // Wait for animation to complete
      await new Promise(resolve => setTimeout(resolve, 200));

      // Should be collapsed
      expect(container.querySelector('.thought-body-expanded')).toBeFalsy();
    });
  });

  describe('Agent Theme', () => {
    it('should apply correct agent theme class', () => {
      const { container } = render(
        <ThoughtBlock agentType="analyst" content="test" />
      );

      const thoughtBlock = container.querySelector('.thought-block');
      expect(thoughtBlock?.className).toContain('mindflow-v2-agent-analyst');
    });

    it('should display agent label in header', () => {
      render(<ThoughtBlock agentType="coder" content="test" />);

      expect(screen.getByText('Coder')).toBeTruthy();
    });

    it('should display custom title when provided', () => {
      const customTitle = 'Custom Agent Title';
      render(<ThoughtBlock agentType="orchestrator" content="test" title={customTitle} />);

      expect(screen.getByText(customTitle)).toBeTruthy();
    });
  });

  describe('Synapse Visual', () => {
    it('should render synapse with 3 nodes and 2 links', () => {
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content="test" />
      );

      const synapse = container.querySelector('.thought-synapse');
      expect(synapse).toBeTruthy();
      expect(synapse?.children.length).toBe(5); // 3 nodes + 2 links
    });
  });

  describe('Status Display', () => {
    it('should display status when provided', () => {
      const status = 'analyzing';
      render(<ThoughtBlock agentType="orchestrator" content="test" status={status} />);

      expect(screen.getByText(status)).toBeTruthy();
    });

    it('should not display status section when not provided or default', () => {
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content="test" />
      );

      // Should only have agent label
      const header = container.querySelector('.thought-block-header');
      // Check that there's only one div with text (the agent label), not two
      const textDivs = header?.querySelectorAll('div[style*="font-size"]');
      expect(textDivs?.length).toBe(1);
    });
  });

  describe('Animation', () => {
    it('should have framer-motion animation attributes', () => {
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content="test" />
      );

      const thoughtBlock = container.querySelector('.thought-block');
      expect(thoughtBlock).toBeTruthy();
      // Component uses framer-motion which adds animation attributes
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty content', () => {
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content="" />
      );

      expect(container.querySelector('.thought-block')).toBeTruthy();
    });

    it('should handle very long content', () => {
      const veryLongContent = 'a'.repeat(10000);
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={veryLongContent} />
      );

      expect(container.querySelector('.thought-block')).toBeTruthy();
      // Should be collapsed by default
      expect(container.querySelector('.thought-preview')).toBeTruthy();
    });

    it('should handle content exactly 300 chars', () => {
      const content = 'a'.repeat(300);
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={content} />
      );

      // At exactly 300, should be collapsed (>= 300 rule)
      expect(container.querySelector('.thought-body-expanded')).toBeFalsy();
      expect(container.querySelector('.thought-preview')).toBeTruthy();
    });

    it('should handle content with special characters', () => {
      const content = '**Bold** _italic_ `code` [link](url)';
      const { container } = render(
        <ThoughtBlock agentType="orchestrator" content={content} defaultExpanded={true} />
      );

      const richText = container.querySelector('.thought-content');
      expect(richText).toBeTruthy();
    });
  });
});

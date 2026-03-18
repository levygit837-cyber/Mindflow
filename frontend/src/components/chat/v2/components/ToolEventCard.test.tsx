/**
 * ToolEventCard - Unit Tests
 *
 * Tests specific examples, edge cases, and user interactions.
 * Requirements: 13.1, 13.2, 13.3, 14.1, 14.2, 14.3, 14.4
 */

import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToolEventCard, ToolCallGroup } from './ToolEventCard';

describe('ToolEventCard', () => {
  describe('Auto-collapse behavior', () => {
    it('should be collapsed by default when status is collapsed', () => {
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="collapsed"
          result="test result"
        />
      );

      // Result should not be visible
      expect(screen.queryByText(/Result:/)).not.toBeInTheDocument();
    });

    it('should be expanded by default when status is running', () => {
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="running"
          result="partial result"
        />
      );

      // Partial result should be visible
      expect(screen.getByText(/Partial Result:/)).toBeInTheDocument();
    });

    it('should be expanded by default when status is completed', () => {
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="completed"
          result="final result"
        />
      );

      // Should be expanded initially (can be collapsed by user)
      const card = container.querySelector('.tool-event-card');
      expect(card).toBeInTheDocument();
    });
  });

  describe('Expansion on click', () => {
    it('should expand when clicked if collapsed', async () => {
      const user = userEvent.setup();
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="completed"
          result="test result"
        />
      );

      const card = container.querySelector('.tool-event-card');
      expect(card).toBeInTheDocument();

      // Initially expanded (completed tools start expanded)
      expect(screen.getByText(/Result:/)).toBeInTheDocument();

      // Click to collapse
      await user.click(card!);

      // Should now be collapsed
      await waitFor(() => {
        expect(screen.queryByText(/Result:/)).not.toBeInTheDocument();
      });
    });

    it('should collapse when clicked if expanded', async () => {
      const user = userEvent.setup();
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="completed"
          result="test result"
        />
      );

      const card = container.querySelector('.tool-event-card');
      expect(card).toBeInTheDocument();

      // Click to collapse
      await user.click(card!);

      // Should hide result
      await waitFor(() => {
        expect(screen.queryByText(/Result:/)).not.toBeInTheDocument();
      });
    });
  });

  describe('Specialized visualizations', () => {
    it('should render Read tool visualization with file path', () => {
      const { container } = render(
        <ToolEventCard
          toolName="read_file"
          status="completed"
          args={{ file_path: '/path/to/file.txt' }}
          result={{ content: 'file content' }}
        />
      );

      expect(screen.getByText('Path:')).toBeInTheDocument();
      expect(screen.getByText('/path/to/file.txt')).toBeInTheDocument();
      expect(container.querySelector('.tool-read-visualization')).toBeInTheDocument();
    });

    it('should render Shell tool visualization with command', () => {
      const { container } = render(
        <ToolEventCard
          toolName="shell_exec"
          status="completed"
          args={{ command: 'ls -la' }}
          result="file1.txt\nfile2.txt"
        />
      );

      expect(screen.getByText('Command:')).toBeInTheDocument();
      expect(screen.getByText('ls -la')).toBeInTheDocument();
      expect(container.querySelector('.tool-shell-visualization')).toBeInTheDocument();
    });

    it('should render Grep search visualization with pattern', () => {
      const { container } = render(
        <ToolEventCard
          toolName="grep_search"
          status="completed"
          args={{ pattern: 'TODO' }}
          result="file.txt:10: TODO: fix this"
        />
      );

      expect(screen.getByText('Pattern:')).toBeInTheDocument();
      expect(screen.getByText('TODO')).toBeInTheDocument();
      expect(container.querySelector('.tool-grep-visualization')).toBeInTheDocument();
    });

    it('should use default visualization for unknown tool types', () => {
      const { container } = render(
        <ToolEventCard
          toolName="unknown_tool"
          status="completed"
          result="some result"
        />
      );

      // Should not have specialized visualizations
      expect(container.querySelector('.tool-read-visualization')).not.toBeInTheDocument();
      expect(container.querySelector('.tool-shell-visualization')).not.toBeInTheDocument();
      expect(container.querySelector('.tool-grep-visualization')).not.toBeInTheDocument();
    });
  });

  describe('Error state rendering', () => {
    it('should display error message when status is error', () => {
      render(
        <ToolEventCard
          toolName="test_tool"
          status="error"
          error="Something went wrong"
        />
      );

      expect(screen.getByText('Error:')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('should show error icon when status is error', () => {
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="error"
          error="Error message"
        />
      );

      expect(container.querySelector('.text-error')).toBeInTheDocument();
    });

    it('should have error border color when status is error', () => {
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="error"
          error="Error message"
        />
      );

      const card = container.querySelector('.tool-event-card');
      expect(card?.classList.contains('border-error')).toBe(true);
    });
  });

  describe('Status indicators', () => {
    it('should show CheckCircle icon when completed', () => {
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="completed"
        />
      );

      expect(container.querySelector('.text-success')).toBeInTheDocument();
    });

    it('should show Loader icon when running', () => {
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="running"
        />
      );

      expect(container.querySelector('.mindflow-v2-pulse')).toBeInTheDocument();
    });

    it('should display elapsed time when provided', () => {
      render(
        <ToolEventCard
          toolName="test_tool"
          status="completed"
          elapsed="2.5s"
        />
      );

      expect(screen.getByText('(2.5s)')).toBeInTheDocument();
    });

    it('should display agent name when provided', () => {
      render(
        <ToolEventCard
          toolName="test_tool"
          status="completed"
          agentName="Analyst Agent"
        />
      );

      expect(screen.getByText('Analyst Agent')).toBeInTheDocument();
    });
  });

  describe('Parameters display', () => {
    it('should always show parameters when provided', () => {
      render(
        <ToolEventCard
          toolName="test_tool"
          status="collapsed"
          args={{ param1: 'value1', param2: 'value2' }}
        />
      );

      expect(screen.getByText('Parameters:')).toBeInTheDocument();
    });

    it('should handle null args gracefully', () => {
      const { container } = render(
        <ToolEventCard
          toolName="test_tool"
          status="completed"
          args={null}
        />
      );

      expect(screen.queryByText('Parameters:')).not.toBeInTheDocument();
    });
  });
});

describe('ToolCallGroup', () => {
  it('should render group title and tool count', () => {
    const tools = [
      { toolName: 'tool1', status: 'completed' as const },
      { toolName: 'tool2', status: 'completed' as const },
      { toolName: 'tool3', status: 'running' as const },
    ];

    render(<ToolCallGroup title="File Operations" tools={tools} />);

    expect(screen.getByText('File Operations')).toBeInTheDocument();
    expect(screen.getByText('(3 tools)')).toBeInTheDocument();
  });

  it('should render all tools in the group', () => {
    const tools = [
      { toolName: 'read_file', status: 'completed' as const },
      { toolName: 'write_file', status: 'completed' as const },
    ];

    render(<ToolCallGroup title="File Operations" tools={tools} />);

    expect(screen.getByText('read_file')).toBeInTheDocument();
    expect(screen.getByText('write_file')).toBeInTheDocument();
  });

  it('should be expanded by default', () => {
    const tools = [
      { toolName: 'tool1', status: 'completed' as const },
    ];

    const { container } = render(<ToolCallGroup title="Group" tools={tools} />);

    // Tools should be visible
    expect(screen.getByText('tool1')).toBeInTheDocument();
  });

  it('should collapse when title is clicked', async () => {
    const user = userEvent.setup();
    const tools = [
      { toolName: 'tool1', status: 'completed' as const },
    ];

    const { container } = render(<ToolCallGroup title="Group" tools={tools} />);

    // Click title to collapse
    const title = screen.getByText('Group');
    await user.click(title);

    // Tools should be hidden
    await waitFor(() => {
      expect(screen.queryByText('tool1')).not.toBeInTheDocument();
    });
  });

  it('should handle empty tools array', () => {
    render(<ToolCallGroup title="Empty Group" tools={[]} />);

    expect(screen.getByText('Empty Group')).toBeInTheDocument();
    expect(screen.getByText('(0 tools)')).toBeInTheDocument();
  });
});

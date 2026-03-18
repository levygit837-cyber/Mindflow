/**
 * Chat Visualization V2 - StreamNotifier Unit Tests
 *
 * Unit tests for StreamNotifier component covering specific examples,
 * edge cases, and visual behavior.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StreamNotifier } from '../../streamComponents';

describe('StreamNotifier', () => {
  describe('Basic Rendering', () => {
    it('should render with minimal props', () => {
      const { container } = render(
        <StreamNotifier title="Test" status="active" />
      );

      expect(container.querySelector('.stream-notifier')).toBeTruthy();
      expect(screen.getByText('Test')).toBeTruthy();
      expect(screen.getByText('active')).toBeTruthy();
    });

    it('should render title and status', () => {
      render(
        <StreamNotifier title="Processing" status="in progress" />
      );

      expect(screen.getByText('Processing')).toBeTruthy();
      expect(screen.getByText('in progress')).toBeTruthy();
    });

    it('should render with message', () => {
      render(
        <StreamNotifier
          title="Loading"
          status="active"
          message="Loading user data..."
        />
      );

      expect(screen.getByText('Loading user data...')).toBeTruthy();
    });

    it('should render with detail', () => {
      render(
        <StreamNotifier
          title="Complete"
          status="done"
          detail="Operation completed successfully"
        />
      );

      expect(screen.getByText('Operation completed successfully')).toBeTruthy();
    });

    it('should render both message and detail', () => {
      render(
        <StreamNotifier
          title="Error"
          status="failed"
          message="Connection failed"
          detail="Unable to reach server at localhost:8000"
        />
      );

      expect(screen.getByText('Connection failed')).toBeTruthy();
      expect(screen.getByText('Unable to reach server at localhost:8000')).toBeTruthy();
    });

    it('should not render detail section when no message or detail', () => {
      const { container } = render(
        <StreamNotifier title="Test" status="active" />
      );

      expect(container.querySelector('.stream-notifier-detail')).toBeFalsy();
    });
  });

  describe('Tone Color Mapping', () => {
    it('should apply accent tone class', () => {
      const { container } = render(
        <StreamNotifier title="Routing" status="active" tone="accent" />
      );

      expect(container.querySelector('.stream-notifier--accent')).toBeTruthy();
    });

    it('should apply info tone class', () => {
      const { container } = render(
        <StreamNotifier title="Memory" status="loaded" tone="info" />
      );

      expect(container.querySelector('.stream-notifier--info')).toBeTruthy();
    });

    it('should apply success tone class', () => {
      const { container } = render(
        <StreamNotifier title="Complete" status="done" tone="success" />
      );

      expect(container.querySelector('.stream-notifier--success')).toBeTruthy();
    });

    it('should apply warning tone class', () => {
      const { container } = render(
        <StreamNotifier title="Slow" status="warning" tone="warning" />
      );

      expect(container.querySelector('.stream-notifier--warning')).toBeTruthy();
    });

    it('should apply error tone class', () => {
      const { container } = render(
        <StreamNotifier title="Error" status="failed" tone="error" />
      );

      expect(container.querySelector('.stream-notifier--error')).toBeTruthy();
    });

    it('should apply neutral tone class', () => {
      const { container } = render(
        <StreamNotifier title="Info" status="active" tone="neutral" />
      );

      expect(container.querySelector('.stream-notifier--neutral')).toBeTruthy();
    });

    it('should default to neutral tone when not specified', () => {
      const { container } = render(
        <StreamNotifier title="Test" status="active" />
      );

      expect(container.querySelector('.stream-notifier--neutral')).toBeTruthy();
    });
  });

  describe('Pulse Animation', () => {
    it('should render pulse indicator', () => {
      const { container } = render(
        <StreamNotifier title="Processing" status="active" />
      );

      expect(container.querySelector('.stream-notifier-pulse')).toBeTruthy();
    });

    it('should render lead indicator', () => {
      const { container } = render(
        <StreamNotifier title="Processing" status="active" />
      );

      expect(container.querySelector('.stream-notifier-lead')).toBeTruthy();
    });
  });

  describe('Message Display', () => {
    it('should display short message', () => {
      render(
        <StreamNotifier
          title="Read"
          status="completed"
          message="File loaded"
        />
      );

      expect(screen.getByText('File loaded')).toBeTruthy();
    });

    it('should display long message', () => {
      const longMessage = 'This is a very long message that contains detailed information about the operation that was performed and its results';

      render(
        <StreamNotifier
          title="Operation"
          status="completed"
          message={longMessage}
        />
      );

      expect(screen.getByText(longMessage)).toBeTruthy();
    });

    it('should display message with special characters', () => {
      render(
        <StreamNotifier
          title="Read"
          status="completed"
          message="File: /path/to/file.ts (123 lines)"
        />
      );

      expect(screen.getByText('File: /path/to/file.ts (123 lines)')).toBeTruthy();
    });

    it('should display message with unicode characters', () => {
      render(
        <StreamNotifier
          title="Success"
          status="completed"
          message="Operação concluída com sucesso ✓"
        />
      );

      expect(screen.getByText('Operação concluída com sucesso ✓')).toBeTruthy();
    });

    it('should display detail below message', () => {
      const { container } = render(
        <StreamNotifier
          title="Error"
          status="failed"
          message="Connection failed"
          detail="Timeout after 30 seconds"
        />
      );

      const detailSection = container.querySelector('.stream-notifier-detail');
      expect(detailSection).toBeTruthy();

      // Both message and detail should be in the detail section
      expect(screen.getByText('Connection failed')).toBeTruthy();
      expect(screen.getByText('Timeout after 30 seconds')).toBeTruthy();
    });

    it('should render detail with mt-2 class when both message and detail exist', () => {
      const { container } = render(
        <StreamNotifier
          title="Info"
          status="active"
          message="First message"
          detail="Second detail"
        />
      );

      const detailCopies = container.querySelectorAll('.stream-notifier-detail-copy');
      expect(detailCopies.length).toBe(2);

      // Second copy should have mt-2 class
      expect(detailCopies[1].classList.contains('mt-2')).toBe(true);
    });
  });

  describe('Styling and Layout', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <StreamNotifier
          title="Test"
          status="active"
          className="custom-class"
        />
      );

      expect(container.querySelector('.custom-class')).toBeTruthy();
    });

    it('should have stream-notifier base class', () => {
      const { container } = render(
        <StreamNotifier title="Test" status="active" />
      );

      expect(container.querySelector('.stream-notifier')).toBeTruthy();
    });

    it('should render header with lead, copy, and pulse', () => {
      const { container } = render(
        <StreamNotifier title="Test" status="active" />
      );

      expect(container.querySelector('.stream-notifier-header')).toBeTruthy();
      expect(container.querySelector('.stream-notifier-lead')).toBeTruthy();
      expect(container.querySelector('.stream-notifier-copy')).toBeTruthy();
      expect(container.querySelector('.stream-notifier-pulse')).toBeTruthy();
    });

    it('should render title, separator, and status in copy section', () => {
      const { container } = render(
        <StreamNotifier title="Processing" status="active" />
      );

      const copy = container.querySelector('.stream-notifier-copy');
      expect(copy).toBeTruthy();
      expect(copy?.querySelector('.stream-notifier-title')).toBeTruthy();
      expect(copy?.querySelector('.stream-notifier-sep')).toBeTruthy();
      expect(copy?.querySelector('.stream-notifier-status')).toBeTruthy();
    });

    it('should render separator with "/" character', () => {
      render(
        <StreamNotifier title="Test" status="active" />
      );

      const separator = screen.getByText('/');
      expect(separator).toBeTruthy();
      expect(separator.classList.contains('stream-notifier-sep')).toBe(true);
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty title', () => {
      render(
        <StreamNotifier title="" status="active" />
      );

      expect(screen.getByText('active')).toBeTruthy();
    });

    it('should handle empty status', () => {
      render(
        <StreamNotifier title="Test" status="" />
      );

      expect(screen.getByText('Test')).toBeTruthy();
    });

    it('should handle very long title', () => {
      const longTitle = 'This is a very long title that might cause layout issues if not handled properly in the component';

      render(
        <StreamNotifier title={longTitle} status="active" />
      );

      expect(screen.getByText(longTitle)).toBeTruthy();
    });

    it('should handle very long status', () => {
      const longStatus = 'this is a very long status text that should still be displayed correctly';

      render(
        <StreamNotifier title="Test" status={longStatus} />
      );

      expect(screen.getByText(longStatus)).toBeTruthy();
    });

    it('should handle null message gracefully', () => {
      const { container } = render(
        <StreamNotifier
          title="Test"
          status="active"
          message={undefined}
        />
      );

      // Should not render detail section
      expect(container.querySelector('.stream-notifier-detail')).toBeFalsy();
    });

    it('should handle null detail gracefully', () => {
      const { container } = render(
        <StreamNotifier
          title="Test"
          status="active"
          detail={undefined}
        />
      );

      // Should not render detail section
      expect(container.querySelector('.stream-notifier-detail')).toBeFalsy();
    });

    it('should handle message without detail', () => {
      render(
        <StreamNotifier
          title="Test"
          status="active"
          message="Only message"
        />
      );

      expect(screen.getByText('Only message')).toBeTruthy();
    });

    it('should handle detail without message', () => {
      render(
        <StreamNotifier
          title="Test"
          status="active"
          detail="Only detail"
        />
      );

      expect(screen.getByText('Only detail')).toBeTruthy();
    });

    it('should handle whitespace-only message', () => {
      const { container } = render(
        <StreamNotifier
          title="Test"
          status="active"
          message="   "
        />
      );

      // Should still render detail section even with whitespace
      expect(container.querySelector('.stream-notifier-detail')).toBeTruthy();
    });
  });

  describe('Real-world Scenarios', () => {
    it('should render routing notifier', () => {
      const { container } = render(
        <StreamNotifier
          title="Routing"
          status="active"
          message="Analyzing request and selecting appropriate agent"
          tone="accent"
        />
      );

      expect(container.querySelector('.stream-notifier--accent')).toBeTruthy();
      expect(screen.getByText('Routing')).toBeTruthy();
      expect(screen.getByText('active')).toBeTruthy();
      expect(screen.getByText('Analyzing request and selecting appropriate agent')).toBeTruthy();
    });

    it('should render read operation notifier', () => {
      const { container } = render(
        <StreamNotifier
          title="Read"
          status="completed"
          message="src/components/chat/streamComponents.tsx"
          detail="976 lines read"
          tone="info"
        />
      );

      expect(container.querySelector('.stream-notifier--info')).toBeTruthy();
      expect(screen.getByText('Read')).toBeTruthy();
      expect(screen.getByText('completed')).toBeTruthy();
      expect(screen.getByText('src/components/chat/streamComponents.tsx')).toBeTruthy();
      expect(screen.getByText('976 lines read')).toBeTruthy();
    });

    it('should render success notifier', () => {
      const { container } = render(
        <StreamNotifier
          title="Complete"
          status="done"
          message="Task completed successfully"
          tone="success"
        />
      );

      expect(container.querySelector('.stream-notifier--success')).toBeTruthy();
      expect(screen.getByText('Complete')).toBeTruthy();
      expect(screen.getByText('done')).toBeTruthy();
      expect(screen.getByText('Task completed successfully')).toBeTruthy();
    });

    it('should render error notifier', () => {
      const { container } = render(
        <StreamNotifier
          title="Error"
          status="failed"
          message="Connection timeout"
          detail="Unable to connect to backend server after 30 seconds"
          tone="error"
        />
      );

      expect(container.querySelector('.stream-notifier--error')).toBeTruthy();
      expect(screen.getByText('Error')).toBeTruthy();
      expect(screen.getByText('failed')).toBeTruthy();
      expect(screen.getByText('Connection timeout')).toBeTruthy();
      expect(screen.getByText('Unable to connect to backend server after 30 seconds')).toBeTruthy();
    });

    it('should render warning notifier', () => {
      const { container } = render(
        <StreamNotifier
          title="Slow Run"
          status="warning"
          message="Execution taking longer than expected"
          detail="Current duration: 45 seconds"
          tone="warning"
        />
      );

      expect(container.querySelector('.stream-notifier--warning')).toBeTruthy();
      expect(screen.getByText('Slow Run')).toBeTruthy();
      expect(screen.getByText('warning')).toBeTruthy();
      expect(screen.getByText('Execution taking longer than expected')).toBeTruthy();
      expect(screen.getByText('Current duration: 45 seconds')).toBeTruthy();
    });
  });
});

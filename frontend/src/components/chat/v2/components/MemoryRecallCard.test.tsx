/**
 * MemoryRecallCard - Unit Tests
 *
 * Tests specific examples, edge cases, and theme behavior.
 * Requirements: 8.1, 8.2, 8.3
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRecallCard } from './MemoryRecallCard';

describe('MemoryRecallCard', () => {
  describe('Dark theme rendering', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    afterEach(() => {
      document.documentElement.removeAttribute('data-theme');
    });

    it('should render in dark theme', () => {
      const { container } = render(
        <MemoryRecallCard
          source="database"
          status="Retrieving context"
        />
      );

      const card = container.querySelector('.memory-recall-card');
      expect(card).toBeInTheDocument();
    });

    it('should display default label for database source', () => {
      render(
        <MemoryRecallCard
          source="database"
          status="Retrieving context"
        />
      );

      expect(screen.getByText('Database Recall')).toBeInTheDocument();
    });

    it('should display default label for vector source', () => {
      render(
        <MemoryRecallCard
          source="vector"
          status="Searching memory"
        />
      );

      expect(screen.getByText('Vector Search')).toBeInTheDocument();
    });

    it('should display custom label when provided', () => {
      render(
        <MemoryRecallCard
          source="database"
          status="Loading"
          label="Custom Memory Label"
        />
      );

      expect(screen.getByText('Custom Memory Label')).toBeInTheDocument();
    });

    it('should display status text', () => {
      render(
        <MemoryRecallCard
          source="database"
          status="Retrieving 10 records"
        />
      );

      expect(screen.getByText('Retrieving 10 records')).toBeInTheDocument();
    });

    it('should display agent name when provided', () => {
      render(
        <MemoryRecallCard
          source="vector"
          status="Searching"
          agentName="Analyst Agent"
        />
      );

      expect(screen.getByText(/Analyst Agent/)).toBeInTheDocument();
    });
  });

  describe('Light theme exclusion', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'light');
    });

    afterEach(() => {
      document.documentElement.removeAttribute('data-theme');
    });

    it('should return null in light theme', () => {
      const { container } = render(
        <MemoryRecallCard
          source="database"
          status="Retrieving context"
        />
      );

      const card = container.querySelector('.memory-recall-card');
      expect(card).not.toBeInTheDocument();
    });

    it('should not render any content in light theme', () => {
      const { container } = render(
        <MemoryRecallCard
          source="vector"
          status="Searching"
          label="Test Label"
          count={5}
        />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe('Source icon mapping', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    afterEach(() => {
      document.documentElement.removeAttribute('data-theme');
    });

    it('should use Database icon for database source', () => {
      const { container } = render(
        <MemoryRecallCard
          source="database"
          status="Loading"
        />
      );

      // Database icon should be present (lucide-react renders as svg)
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should use Search icon for vector source', () => {
      const { container } = render(
        <MemoryRecallCard
          source="vector"
          status="Searching"
        />
      );

      // Search icon should be present
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should apply info tone for database source', () => {
      const { container } = render(
        <MemoryRecallCard
          source="database"
          status="Loading"
        />
      );

      const card = container.querySelector('.memory-recall-card');
      expect(card?.classList.contains('mindflow-v2-tone-info')).toBe(true);
    });

    it('should apply accent tone for vector source', () => {
      const { container } = render(
        <MemoryRecallCard
          source="vector"
          status="Searching"
        />
      );

      const card = container.querySelector('.memory-recall-card');
      expect(card?.classList.contains('mindflow-v2-tone-accent')).toBe(true);
    });
  });

  describe('Count display', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    afterEach(() => {
      document.documentElement.removeAttribute('data-theme');
    });

    it('should display count when provided and greater than 0', () => {
      render(
        <MemoryRecallCard
          source="database"
          status="Retrieved"
          count={42}
        />
      );

      expect(screen.getByText('42')).toBeInTheDocument();
    });

    it('should not display count when 0', () => {
      render(
        <MemoryRecallCard
          source="database"
          status="Retrieved"
          count={0}
        />
      );

      expect(screen.queryByText('0')).not.toBeInTheDocument();
    });

    it('should not display count when undefined', () => {
      const { container } = render(
        <MemoryRecallCard
          source="database"
          status="Retrieved"
        />
      );

      // Count badge should not be present
      const countBadge = container.querySelector('.font-mono');
      expect(countBadge).not.toBeInTheDocument();
    });
  });

  describe('Detail preview', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    afterEach(() => {
      document.documentElement.removeAttribute('data-theme');
    });

    it('should display detail text when provided', () => {
      render(
        <MemoryRecallCard
          source="vector"
          status="Complete"
          detail="Found 5 relevant memory fragments from previous conversations"
        />
      );

      expect(screen.getByText(/Found 5 relevant memory fragments/)).toBeInTheDocument();
    });

    it('should not display detail section when not provided', () => {
      const { container } = render(
        <MemoryRecallCard
          source="vector"
          status="Complete"
        />
      );

      // Detail should not be present
      const detail = container.querySelector('.mt-2.text-sm');
      expect(detail).not.toBeInTheDocument();
    });
  });

  describe('Done indicator', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    afterEach(() => {
      document.documentElement.removeAttribute('data-theme');
    });

    it('should show done indicator when done is true', () => {
      const { container } = render(
        <MemoryRecallCard
          source="database"
          status="Complete"
          done={true}
        />
      );

      const doneIndicator = container.querySelector('.rounded-full');
      expect(doneIndicator).toBeInTheDocument();
    });

    it('should not show done indicator when done is false', () => {
      const { container } = render(
        <MemoryRecallCard
          source="database"
          status="Loading"
          done={false}
        />
      );

      const doneIndicator = container.querySelector('.rounded-full');
      expect(doneIndicator).not.toBeInTheDocument();
    });

    it('should not show done indicator by default', () => {
      const { container } = render(
        <MemoryRecallCard
          source="database"
          status="Loading"
        />
      );

      const doneIndicator = container.querySelector('.rounded-full');
      expect(doneIndicator).not.toBeInTheDocument();
    });
  });

  describe('Edge cases', () => {
    beforeEach(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });

    afterEach(() => {
      document.documentElement.removeAttribute('data-theme');
    });

    it('should handle empty status string', () => {
      render(
        <MemoryRecallCard
          source="database"
          status=""
        />
      );

      // Should still render the card
      expect(screen.getByText('Database Recall')).toBeInTheDocument();
    });

    it('should handle all props together', () => {
      render(
        <MemoryRecallCard
          source="vector"
          status="Search complete"
          label="Memory Search"
          count={15}
          detail="Retrieved from long-term memory"
          agentName="Research Agent"
          done={true}
          className="custom-class"
        />
      );

      expect(screen.getByText('Memory Search')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument();
      expect(screen.getByText(/Retrieved from long-term memory/)).toBeInTheDocument();
      expect(screen.getByText(/Research Agent/)).toBeInTheDocument();
    });
  });
});

/**
 * Spinner - MindFlow CLI Loading Indicator
 * Custom spinner with Teal Professional identity
 * Uses: ◐ ◓ ◑ ◒ (diferente do Claude que usa dots)
 */

import React, { useEffect, useState } from 'react';
import { Box, Text } from 'ink';
import chalk from 'chalk';

// Spinner frames - MindFlow identity: quadrants rotating
const SPINNER_FRAMES = ['◐', '◓', '◑', '◒'];

// Animation interval in ms
const SPINNER_INTERVAL = 120;

// Colors for different spinner states (Teal Professional palette)
const SPINNER_COLORS = {
  processing: '#0D6E6E',    // Teal Dark - Primary
  waiting: '#737373',       // Gray - Muted
  success: '#22C55E',       // Green
  error: '#EF4444',         // Red
  warning: '#F59E0B',       // Amber
};

export type SpinnerState = 'processing' | 'waiting' | 'success' | 'error' | 'warning';

interface SpinnerProps {
  state?: SpinnerState;
  text?: string;
  shouldAnimate?: boolean;
  prefix?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  state = 'processing',
  text,
  shouldAnimate = true,
  prefix,
}) => {
  const [frameIndex, setFrameIndex] = useState(0);

  useEffect(() => {
    if (!shouldAnimate || state !== 'processing') {
      return;
    }

    const interval = setInterval(() => {
      setFrameIndex((prev) => (prev + 1) % SPINNER_FRAMES.length);
    }, SPINNER_INTERVAL);

    return () => clearInterval(interval);
  }, [shouldAnimate, state]);

  // Get current frame or static symbol based on state
  const getSymbol = (): string => {
    switch (state) {
      case 'success':
        return '✓';
      case 'error':
        return '✗';
      case 'warning':
        return '⚠';
      case 'waiting':
        return '○';
      case 'processing':
      default:
        return SPINNER_FRAMES[frameIndex];
    }
  };

  // Get color based on state
  const getColor = (): string => {
    return SPINNER_COLORS[state];
  };

  const symbol = getSymbol();
  const color = getColor();
  const chalkColor = chalk.hex(color);

  return (
    <Box>
      {prefix && (
        <Text color="gray" dimColor>
          {prefix}{' '}
        </Text>
      )}
      <Text color={color}>{chalkColor(symbol)}</Text>
      {text && (
        <Text color="gray" dimColor>
          {' '}{text}
        </Text>
      )}
    </Box>
  );
};

// Tool execution spinner - shows progress with label
interface ToolSpinnerProps {
  toolName: string;
  isInProgress: boolean;
  isError?: boolean;
  isResolved?: boolean;
  progressText?: string;
}

export const ToolSpinner: React.FC<ToolSpinnerProps> = ({
  toolName,
  isInProgress,
  isError = false,
  isResolved = false,
  progressText,
}) => {
  const getState = (): SpinnerState => {
    if (isError) return 'error';
    if (isResolved) return 'success';
    if (isInProgress) return 'processing';
    return 'waiting';
  };

  const getText = (): string => {
    if (progressText) return progressText;
    if (isError) return `${toolName} failed`;
    if (isResolved) return `${toolName} completed`;
    if (isInProgress) return `${toolName}...`;
    return `${toolName} queued`;
  };

  return (
    <Box>
      <Spinner
        state={getState()}
        text={getText()}
        shouldAnimate={isInProgress}
      />
    </Box>
  );
};

// Processing indicator for above input bar
interface ProcessingIndicatorProps {
  isProcessing: boolean;
  processingText?: string;
  toolCount?: number;
}

export const ProcessingIndicator: React.FC<ProcessingIndicatorProps> = ({
  isProcessing,
  processingText = 'Processing',
  toolCount,
}) => {
  if (!isProcessing) {
    return null;
  }

  const text = toolCount && toolCount > 0
    ? `${processingText} (${toolCount} tools)...`
    : `${processingText}...`;

  return (
    <Box marginBottom={1}>
      <Spinner
        state="processing"
        text={text}
        shouldAnimate={true}
        prefix="◉"
      />
    </Box>
  );
};

// Multi-tool progress indicator
interface MultiToolProgressProps {
  total: number;
  completed: number;
  failed: number;
  inProgress: number;
}

export const MultiToolProgress: React.FC<MultiToolProgressProps> = ({
  total,
  completed,
  failed,
  inProgress,
}) => {
  if (total === 0) return null;

  const progressBar = '█'.repeat(completed) + '▓'.repeat(inProgress) + '░'.repeat(total - completed - inProgress - failed) + '✗'.repeat(failed);
  const percent = Math.round(((completed + failed) / total) * 100);

  return (
    <Box flexDirection="column" marginY={1}>
      <Box>
        <Text color="gray">Progress: </Text>
        <Text color="#0D6E6E">{progressBar}</Text>
        <Text color="gray"> {percent}%</Text>
      </Box>
      <Box>
        <Text color="green">✓ {completed}</Text>
        <Text color="gray"> | </Text>
        <Text color="#0D6E6E">◉ {inProgress}</Text>
        <Text color="gray"> | </Text>
        <Text color="red">✗ {failed}</Text>
        <Text color="gray"> | </Text>
        <Text color="gray">Total: {total}</Text>
      </Box>
    </Box>
  );
};

// Blinking cursor for input
interface BlinkingCursorProps {
  isBlinking?: boolean;
}

export const BlinkingCursor: React.FC<BlinkingCursorProps> = ({
  isBlinking = true,
}) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (!isBlinking) {
      setVisible(true);
      return;
    }

    const interval = setInterval(() => {
      setVisible((v) => !v);
    }, 530); // Blink every 530ms

    return () => clearInterval(interval);
  }, [isBlinking]);

  return (
    <Text color="#0D6E6E">{visible ? '▋' : ' '}</Text>
  );
};

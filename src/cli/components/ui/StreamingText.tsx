/**
 * StreamingText - Component for streaming text display
 * Shows text appearing character by character
 */

import React, { useState, useEffect } from 'react';
import { Text } from 'ink';

interface StreamingTextProps {
  text: string;
  isStreaming?: boolean;
  speed?: number; // characters per second
  onComplete?: () => void;
}

export const StreamingText: React.FC<StreamingTextProps> = ({
  text,
  isStreaming = true,
  speed = 50,
  onComplete,
}) => {
  const [displayedLength, setDisplayedLength] = useState(0);

  useEffect(() => {
    if (!isStreaming) {
      setDisplayedLength(text.length);
      return;
    }

    const interval = setInterval(() => {
      setDisplayedLength((prev) => {
        if (prev >= text.length) {
          clearInterval(interval);
          onComplete?.();
          return text.length;
        }
        return prev + 1;
      });
    }, 1000 / speed);

    return () => clearInterval(interval);
  }, [text, isStreaming, speed, onComplete]);

  return (
    <Text>
      {text.slice(0, displayedLength)}
      {isStreaming && displayedLength < text.length && (
        <Text color="#0D6E6E">▋</Text>
      )}
    </Text>
  );
};

// Streaming indicator
interface StreamingIndicatorProps {
  isStreaming: boolean;
  text?: string;
}

export const StreamingIndicator: React.FC<StreamingIndicatorProps> = ({
  isStreaming,
  text = 'Streaming',
}) => {
  const [dots, setDots] = useState(1);

  useEffect(() => {
    if (!isStreaming) return;

    const interval = setInterval(() => {
      setDots((prev) => (prev % 3) + 1);
    }, 500);

    return () => clearInterval(interval);
  }, [isStreaming]);

  if (!isStreaming) return null;

  return (
    <Text color="#0D6E6E" dimColor>
      {text}{'.'.repeat(dots)}{' '.repeat(3 - dots)}
    </Text>
  );
};

export default StreamingText;

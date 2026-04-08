/**
 * ThinkingMessage - Display thinking/reasoning blocks
 * Collapsible by default, can be expanded to show reasoning
 */

import React, { useState } from 'react';
import { Box, Text } from 'ink';

import type { ThinkingMessage as ThinkingMessageType } from '../../types/protocol.js';
import { Spinner } from '../ui/Spinner.js';

interface ThinkingMessageProps {
  message: ThinkingMessageType;
  isSelected?: boolean;
  isLast?: boolean;
  index: number;
}

export const ThinkingMessage: React.FC<ThinkingMessageProps> = ({
  message,
  isSelected = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const timestamp = new Date(message.timestamp).toLocaleTimeString();
  const borderColor = isSelected ? '#0D6E6E' : undefined;

  return (
    <Box
      flexDirection="column"
      marginY={0.5}
      paddingX={1}
      borderStyle={isSelected ? "single" : undefined}
      borderColor={borderColor}

    >
      {/* Collapsible header */}
      <Box>
        <Text color="gray" dimColor>[{timestamp}]</Text>
        <Text color="#5EEAD4">{' ▶ '}</Text>
        {message.isStreaming ? (
          <>
            <Spinner state="processing" shouldAnimate={true} />
            <Text color="#5EEAD4" dimColor>{' '}Thinking...</Text>
          </>
        ) : (
          <Text color="#5EEAD4" dimColor>
            {isExpanded ? '▼ Thinking (expanded)' : '▶ Thinking (Press Enter to expand)'}
          </Text>
        )}
      </Box>

      {/* Expanded content */}
      {isExpanded && (
        <Box 
          flexDirection="column" 
          marginTop={1} 
          paddingLeft={2}
          paddingX={1}
          borderStyle="single"
          borderColor="#0D6E6E"
          
        >
          <Text color="gray" dimColor italic>
            {message.thinking}
          </Text>
          
          {message.signature && (
            <Box marginTop={1}>
              <Text color="gray" dimColor>
                Signature: {message.signature.slice(0, 16)}...
              </Text>
            </Box>
          )}
        </Box>
      )}

      {/* Preview when collapsed (last 50 chars) */}
      {!isExpanded && !message.isStreaming && (
        <Box marginTop={1} paddingLeft={2}>
          <Text color="gray" dimColor>
            {message.thinking.slice(0, 50)}{message.thinking.length > 50 ? '...' : ''}
          </Text>
        </Box>
      )}
    </Box>
  );
};

export default ThinkingMessage;

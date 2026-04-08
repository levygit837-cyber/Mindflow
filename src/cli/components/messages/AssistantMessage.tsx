/**
 * AssistantMessage - Display assistant messages in MindFlow CLI
 * Includes support for markdown rendering
 */

import React from 'react';
import { Box, Text } from 'ink';

import type { AssistantMessage as AssistantMessageType } from '../../types/protocol.js';

interface AssistantMessageProps {
  message: AssistantMessageType;
  isSelected?: boolean;
  isLast?: boolean;
  index: number;
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({
  message,
  isSelected = false,
}) => {
  const timestamp = new Date(message.timestamp).toLocaleTimeString();
  
  const borderColor = isSelected ? '#0D6E6E' : undefined;

  return (
    <Box 
      flexDirection="column" 
      marginY={1}
      paddingX={1}
      borderStyle={isSelected ? "single" : undefined}
      borderColor={borderColor}
      
    >
      {/* Header with timestamp and indicator */}
      <Box marginBottom={1}>
        <Text color="gray" dimColor>[{timestamp}]</Text>
        <Text color="#0D6E6E" bold>{' ◆ '}</Text>
        <Text color="#0D6E6E" bold>MindFlow</Text>
        {message.model && (
          <Text color="gray" dimColor>{' • '}{message.model}</Text>
        )}
      </Box>

      {/* Message content */}
      <Box paddingLeft={2}>
        <Text color="white">{message.content}</Text>
      </Box>

      {/* Usage info if available */}
      {message.usage && (
        <Box marginTop={1} paddingLeft={2}>
          <Text color="gray" dimColor>
            Tokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out
          </Text>
        </Box>
      )}
    </Box>
  );
};

export default AssistantMessage;

/**
 * ToolResultMessage - Display tool execution results
 */

import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';

import type { ToolResultMessage as ToolResultMessageType } from '../../types/protocol.js';

interface ToolResultMessageProps {
  message: ToolResultMessageType;
  isSelected?: boolean;
  isLast?: boolean;
  index: number;
}

const MAX_PREVIEW_LENGTH = 150;

export const ToolResultMessage: React.FC<ToolResultMessageProps> = ({
  message,
  isSelected = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const timestamp = new Date(message.timestamp).toLocaleTimeString();
  const borderColor = isSelected ? '#0D6E6E' : undefined;

  // Handle keyboard input for expanding/collapsing
  useInput((input, key) => {
    if (isSelected && (key.return || input === ' ')) {
      setIsExpanded(!isExpanded);
    }
  });

  // Determine status and styling
  const isError = message.is_error;
  const hasOutput = message.output && message.output.length > 0;
  const output = message.output || '';
  const isTruncated = output.length > MAX_PREVIEW_LENGTH;
  const displayOutput = isExpanded 
    ? output 
    : output.slice(0, MAX_PREVIEW_LENGTH);

  return (
    <Box 
      flexDirection="column" 
      marginY={1}
      paddingX={1}
      borderStyle={isSelected ? "single" : undefined}
      borderColor={isError ? 'red' : borderColor}
      
    >
      {/* Header */}
      <Box marginBottom={1}>
        <Text color="gray" dimColor>[{timestamp}]</Text>
        <Text color={isError ? 'red' : 'green'}>
          {isError ? ' ✗ Result' : ' ✓ Result'}
        </Text>
        {isSelected && (
          <Text color="gray" dimColor>
            {' • '}Press Enter to {isExpanded ? 'collapse' : 'expand'}
          </Text>
        )}
      </Box>

      {/* Output content */}
      {hasOutput && (
        <Box 
          flexDirection="column" 
          paddingLeft={2}
          paddingX={1}
          borderStyle="single"
          borderColor={isError ? 'red' : 'gray'}
          
        >
          <Text color={isError ? 'red' : 'white'}>
            {displayOutput}
          </Text>
          
          {isTruncated && !isExpanded && (
            <Box marginTop={1}>
              <Text color="gray" dimColor>
                ... ({output.length - MAX_PREVIEW_LENGTH} more chars)
              </Text>
            </Box>
          )}
        </Box>
      )}

      {/* Error message */}
      {message.error && (
        <Box 
          flexDirection="column" 
          marginTop={1}
          paddingLeft={2}
          paddingX={1}
          borderStyle="single"
          borderColor="red"
          
        >
          <Text color="red" bold>Error:</Text>
          <Text color="red">{message.error}</Text>
        </Box>
      )}

      {/* Images if any */}
      {message.images && message.images.length > 0 && (
        <Box marginTop={1} paddingLeft={2}>
          <Text color="gray" dimColor>
            📷 {message.images.length} image{message.images.length > 1 ? 's' : ''} attached
          </Text>
        </Box>
      )}
    </Box>
  );
};

export default ToolResultMessage;

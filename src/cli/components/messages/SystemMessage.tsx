/**
 * SystemMessage - Display system messages and notifications
 */

import React from 'react';
import { Box, Text } from 'ink';

import type { SystemMessage as SystemMessageType } from '../../types/protocol.js';

interface SystemMessageProps {
  message: SystemMessageType;
  isSelected?: boolean;
  isLast?: boolean;
  index: number;
}

export const SystemMessage: React.FC<SystemMessageProps> = ({
  message,
  isSelected = false,
}) => {
  const timestamp = new Date(message.timestamp).toLocaleTimeString();
  
  // Determine color based on subtype
  const getColors = () => {
    switch (message.subtype) {
      case 'error':
        return { border: 'red', text: 'red', icon: '✗' };
      case 'warning':
        return { border: '#F59E0B', text: '#F59E0B', icon: '⚠' };
      case 'status':
        return { border: '#0D6E6E', text: '#14B8A6', icon: '◉' };
      case 'info':
        return { border: 'gray', text: 'gray', icon: 'ℹ' };
      case 'compact_boundary':
        return { border: 'gray', text: 'gray', icon: '─' };
      default:
        return { border: 'gray', text: 'white', icon: '•' };
    }
  };

  const colors = getColors();

  return (
    <Box 
      flexDirection="column" 
      marginY={1}
      paddingX={1}
      borderStyle={isSelected ? "single" : undefined}
      borderColor={colors.border}
    >
      {/* Header */}
      <Box marginBottom={message.subtype === 'compact_boundary' ? 0 : 1}>
        {message.subtype !== 'compact_boundary' && (
          <Text color="gray" dimColor>[{timestamp}]</Text>
        )}
        <Text color={colors.text}>
          {message.subtype === 'compact_boundary' 
            ? '' 
            : ` ${colors.icon} System`
          }
        </Text>
        {message.subtype && message.subtype !== 'compact_boundary' && (
          <Text color="gray" dimColor>{' • '}{message.subtype}</Text>
        )}
      </Box>

      {/* Content */}
      {message.subtype === 'compact_boundary' ? (
        <Box>
          <Text color="gray">
            {'─'.repeat(50)}
          </Text>
          <Text color="gray" dimColor>
            {' '}Context compacted
          </Text>
          <Text color="gray">
            {'─'.repeat(50)}
          </Text>
        </Box>
      ) : (
        <Box paddingLeft={2}>
          <Text color={colors.text}>{message.content}</Text>
        </Box>
      )}

      {/* Metadata if available */}
      {message.metadata && Object.keys(message.metadata).length > 0 && (
        <Box marginTop={1} paddingLeft={2}>
          <Text color="gray" dimColor>
            Metadata: {JSON.stringify(message.metadata).slice(0, 100)}
          </Text>
        </Box>
      )}
    </Box>
  );
};

export default SystemMessage;

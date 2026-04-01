import React from 'react';
import { Box, Text } from 'ink';
import { format } from 'date-fns';
import type { Message } from '../../types/index.js';

interface MessageRowProps {
  message: Message;
}

const MessageRow: React.FC<MessageRowProps> = ({ message }) => {
  const getMessageColor = () => {
    switch (message.type) {
      case 'user':
        return 'green';
      case 'assistant':
        return 'blue';
      case 'agent':
        return 'cyan';
      case 'system':
        return 'yellow';
      default:
        return 'white';
    }
  };

  const getMessageIcon = () => {
    switch (message.type) {
      case 'user':
        return '›';
      case 'assistant':
        return '◆';
      case 'agent':
        return '●';
      case 'system':
        return '⚠';
      default:
        return '•';
    }
  };

  const timestamp = format(message.timestamp, 'HH:mm:ss');

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color="gray">[{timestamp}] </Text>
        <Text color={getMessageColor()} bold>
          {getMessageIcon()}{' '}
        </Text>
        {message.agentName && (
          <Text color="cyan" dimColor>
            {message.agentName}:{' '}
          </Text>
        )}
        <Text color={getMessageColor()}>{message.content}</Text>
      </Box>
    </Box>
  );
};

export default MessageRow;

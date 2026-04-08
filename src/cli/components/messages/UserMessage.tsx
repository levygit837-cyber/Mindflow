/**
 * UserMessage - Display user messages in MindFlow CLI
 */

import React from 'react';
import { Box, Text } from 'ink';
import type { UserMessage as UserMessageType } from '../../types/protocol.js';

interface UserMessageProps {
  message: UserMessageType;
  isSelected?: boolean;
  isLast?: boolean;
  index: number;
}

export const UserMessage: React.FC<UserMessageProps> = ({
  message,
  isSelected = false,
}) => {
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
      {/* Header with timestamp and indicator */}
      <Box marginBottom={1}>
        <Text color="gray" dimColor>[{timestamp}]</Text>
        <Text color="#14B8A6" bold>{' › '}</Text>
        <Text color="#14B8A6" bold>You</Text>
        {message.attachments && message.attachments.length > 0 && (
          <Text color="gray">{' '}({message.attachments.length} attachment{message.attachments.length > 1 ? 's' : ''})</Text>
        )}
      </Box>

      {/* Message content */}
      <Box paddingLeft={2}>
        <Text color="white">{message.content}</Text>
      </Box>

      {/* Show attachments if any */}
      {message.attachments && message.attachments.length > 0 && (
        <Box flexDirection="column" marginTop={1} paddingLeft={2}>
          {message.attachments.map((att, idx) => (
            <Box key={idx}>
              <Text color="gray" dimColor>
                📎 {att.name} ({att.type})
              </Text>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default UserMessage;

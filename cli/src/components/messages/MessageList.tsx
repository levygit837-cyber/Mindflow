import React from 'react';
import { Box, Text } from 'ink';
import { useMessages } from '../../state/store.js';
import MessageRow from './MessageRow.js';

const MessageList: React.FC = () => {
  const messages = useMessages();

  if (messages.length === 0) {
    return (
      <Box flexDirection="column" paddingX={1} paddingY={1}>
        <Box>
          <Text bold color="cyan">Welcome to MindFlow CLI</Text>
        </Box>
        <Box marginTop={1}>
          <Text color="gray">Type a message to start chatting with agents...</Text>
        </Box>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" paddingX={1}>
      {messages.map((message) => (
        <MessageRow key={message.id} message={message} />
      ))}
    </Box>
  );
};

export default MessageList;

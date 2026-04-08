#!/usr/bin/env node
/**
 * MindFlow CLI Demo
 * Simple demo of the CLI without full backend integration
 */

import React, { useState } from 'react';
import { render, Box, Text, useInput, useApp } from 'ink';

// Demo app
const DemoApp: React.FC = () => {
  const { exit } = useApp();
  const [messages, setMessages] = useState<Array<{type: string, content: string}>>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useInput((value, key) => {
    if (key.return && input.trim()) {
      // Add user message
      setMessages(prev => [...prev, { type: 'user', content: input }]);
      setInput('');
      setIsLoading(true);

      // Simulate response after delay
      setTimeout(() => {
        setMessages(prev => [...prev, { 
          type: 'assistant', 
          content: `Received: ${input}\n\nThis is a demo response. The full CLI is at /src/cli/` 
        }]);
        setIsLoading(false);
      }, 1500);
    } else if (key.backspace || key.delete) {
      setInput(prev => prev.slice(0, -1));
    } else if (!key.ctrl && !key.meta && value) {
      setInput(prev => prev + value);
    }

    if (key.ctrl && value === 'c') {
      exit();
    }
  });

  return (
    <Box flexDirection="column" padding={1}>
      {/* Header */}
      <Box marginBottom={1}>
        <Text color="#0D6E6E" bold>◈ MindFlow CLI Demo</Text>
        <Text color="gray"> v0.1.0</Text>
      </Box>

      {/* Messages */}
      <Box flexDirection="column" marginY={1}>
        {messages.map((msg, idx) => (
          <Box key={idx} marginY={1}>
            {msg.type === 'user' ? (
              <>
                <Text color="#14B8A6" bold>› You:</Text>
                <Text color="white"> {msg.content}</Text>
              </>
            ) : (
              <>
                <Text color="#0D6E6E" bold>◆ MindFlow:</Text>
                <Text color="white"> {msg.content}</Text>
              </>
            )}
          </Box>
        ))}
        {isLoading && (
          <Box>
            <Text color="#0D6E6E">◉ Processing...</Text>
          </Box>
        )}
      </Box>

      {/* Input */}
      <Box marginTop={1} borderStyle="single" borderColor="#0D6E6E" paddingX={1}>
        <Box>
          <Text color="#0D6E6E" bold>{'> '}</Text>
          <Text>{input}</Text>
          <Text color="#0D6E6E">▋</Text>
        </Box>
      </Box>

      {/* Help */}
      <Box marginTop={1}>
        <Text color="gray" dimColor>Enter to send • Ctrl+C to quit</Text>
      </Box>
    </Box>
  );
};

// Run demo
render(<DemoApp />);

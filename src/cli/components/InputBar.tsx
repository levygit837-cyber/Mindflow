/**
 * InputBar - MindFlow CLI Input Component
 * Features: Spinner above input, history navigation, submit handling
 * Uses Claude-style text input with viewport management and dynamic height
 */

import React, { useState, useEffect } from 'react';
import { Box, Text, useStdout } from 'ink';
import { ProcessingIndicator } from './ui/Spinner.js';
import { useMessageStore } from '../core/MessageStore.js';
import { TextInput } from './TextInput.js';

interface InputBarProps {
  onSubmit: (input: string) => void;
  placeholder?: string;
  showProcessingIndicator?: boolean;
  processingText?: string;
}

export const InputBar: React.FC<InputBarProps> = ({
  onSubmit,
  placeholder = 'Type your message...',
  showProcessingIndicator = true,
  processingText = 'Processing',
}) => {
  const [input, setInput] = useState('');
  
  const { 
    isLoading, 
    inProgressToolUseIDs,
    inputHistory,
    setInputValue,
  } = useMessageStore();

  const { stdout } = useStdout();
  const columns = stdout.columns || 80;
  const rows = stdout.rows || 24;
  const inProgressCount = inProgressToolUseIDs.size;

  // Dynamic height calculation based on terminal size
  const PROMPT_FOOTER_LINES = 5;
  const MIN_INPUT_VIEWPORT_LINES = 3;
  const maxVisibleLines = Math.max(
    MIN_INPUT_VIEWPORT_LINES,
    Math.floor(rows / 2) - PROMPT_FOOTER_LINES
  );

  const handleSubmit = (value: string) => {
    if (value.trim()) {
      onSubmit(value);
      // Add to history
      if (!inputHistory.length || inputHistory[inputHistory.length - 1] !== value) {
        useMessageStore.setState((state: { inputHistory: string[] }) => ({
          inputHistory: [...state.inputHistory, value],
        }));
      }
      setInput('');
    }
  };

  // Update store with current input value
  useEffect(() => {
    setInputValue(input);
  }, [input, setInputValue]);

  return (
    <Box flexDirection="column" marginTop={1}>
      {/* Processing indicator above input - fixed height to prevent layout shifts */}
      <Box height={1}>
        {showProcessingIndicator && (
          <ProcessingIndicator
            isProcessing={isLoading || inProgressCount > 0}
            processingText={processingText}
            toolCount={inProgressCount > 0 ? inProgressCount : undefined}
          />
        )}
      </Box>

      {/* Input container with flexible height */}
      <Box
        flexDirection="column"
        borderStyle="single"
        borderColor={isLoading ? "gray" : "#0D6E6E"}
        paddingX={1}
        paddingY={1}
        flexGrow={1}
        flexShrink={1}
      >
        {/* Input line with prompt */}
        <Box flexDirection="row">
          <Text color="#0D6E6E" bold>{'> '}</Text>
          <Box flexGrow={1} flexShrink={1}>
            <TextInput
              value={input}
              onChange={setInput}
              onSubmit={handleSubmit}
              onExit={() => process.exit(0)}
              placeholder={placeholder}
              columns={columns - 4} // Account for prompt and padding
              maxVisibleLines={maxVisibleLines}
              cursorChar="▋"
            />
          </Box>
        </Box>
      </Box>

      {/* Keyboard hints */}
      <Box marginTop={1}>
        <Text color="gray" dimColor>
          ↑↓ history • Enter submit • Ctrl+C quit • Ctrl+L clear
        </Text>
      </Box>
    </Box>
  );
};

export default InputBar;

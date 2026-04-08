import React from 'react';
import { Box, Text, useInput } from 'ink';
import chalk from 'chalk';
import { useTextInput } from '../hooks/useTextInput.js';

export type BaseTextInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: (value: string) => void;
  onExit?: () => void;
  placeholder?: string;
  columns: number;
  maxVisibleLines?: number;
  dimColor?: boolean;
  cursorChar?: string;
  mask?: string;
};

export function BaseTextInput(props: BaseTextInputProps): React.ReactNode {
  const {
    value,
    onChange,
    onSubmit,
    onExit,
    placeholder = 'Type your message...',
    columns,
    maxVisibleLines,
    dimColor = false,
    cursorChar = '▋',
    mask = '',
  } = props;

  const textInputState = useTextInput({
    value,
    onChange,
    onSubmit,
    onExit,
    columns,
    maxVisibleLines,
    cursorChar,
    mask,
    invert: chalk.inverse,
  });

  const { onInput, renderedValue } = textInputState;

  console.log('BaseTextInput registering useInput with onInput:', !!onInput);

  // Register input handler with ink
  useInput(onInput);

  const showPlaceholder = !value && placeholder;

  return (
    <Box>
      {showPlaceholder ? (
        <Text dimColor>{placeholder}</Text>
      ) : (
        <Text dimColor={dimColor}>{renderedValue}</Text>
      )}
    </Box>
  );
}

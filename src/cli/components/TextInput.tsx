import React from 'react';
import { Box } from 'ink';
import { BaseTextInput, BaseTextInputProps } from './BaseTextInput.js';

export type TextInputProps = BaseTextInputProps;

export function TextInput(props: TextInputProps): React.ReactNode {
  return (
    <Box>
      <BaseTextInput {...props} />
    </Box>
  );
}

import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';

interface InputBarProps {
  onSubmit: (message: string) => void;
}

const InputBar: React.FC<InputBarProps> = ({ onSubmit }) => {
  const [input, setInput] = useState('');

  useInput((inputChar, key) => {
    if (key.return) {
      if (input.trim()) {
        onSubmit(input.trim());
        setInput('');
      }
    } else if (key.backspace || key.delete) {
      setInput((prev) => prev.slice(0, -1));
    } else if (!key.ctrl && !key.meta && inputChar) {
      setInput((prev) => prev + inputChar);
    }
  });

  return (
    <Box borderStyle="single" borderColor="gray" paddingX={1}>
      <Text color="green">› </Text>
      <Text>{input}</Text>
      <Text color="gray">█</Text>
    </Box>
  );
};

export default InputBar;

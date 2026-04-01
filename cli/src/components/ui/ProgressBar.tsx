import React from 'react';
import { Box, Text } from 'ink';

interface ProgressBarProps {
  progress: number; // 0-100
  width?: number;
  color?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  width = 20,
  color = 'green'
}) => {
  const filled = Math.round((progress / 100) * width);
  const empty = width - filled;

  return (
    <Box>
      <Text color={color}>{'█'.repeat(filled)}</Text>
      <Text color="gray">{'░'.repeat(empty)}</Text>
      <Text color="gray"> {progress}%</Text>
    </Box>
  );
};

export default ProgressBar;

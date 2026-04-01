import React from 'react';
import { Box, Text } from 'ink';
import { format } from 'date-fns';
import type { ToolCall } from '../../types/index.js';

interface ToolExecutionViewProps {
  toolCall: ToolCall;
}

const ToolExecutionView: React.FC<ToolExecutionViewProps> = ({ toolCall }) => {
  const getStatusIcon = () => {
    switch (toolCall.status) {
      case 'pending':
        return <Text color="gray">○</Text>;
      case 'running':
        return <Text color="cyan">⟳</Text>;
      case 'completed':
        return <Text color="green">✓</Text>;
      case 'failed':
        return <Text color="red">✖</Text>;
    }
  };

  const getStatusColor = () => {
    switch (toolCall.status) {
      case 'pending':
        return 'gray';
      case 'running':
        return 'cyan';
      case 'completed':
        return 'green';
      case 'failed':
        return 'red';
    }
  };

  const duration = toolCall.duration
    ? `${toolCall.duration}ms`
    : toolCall.status === 'running'
    ? `${Date.now() - toolCall.startTime}ms`
    : '';

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        {getStatusIcon()}
        <Text color={getStatusColor()} bold>
          {' '}
          {toolCall.name}
        </Text>
        {duration && <Text color="gray"> ({duration})</Text>}
      </Box>
      {toolCall.output && (
        <Box marginLeft={2}>
          <Text color="gray" dimColor>
            {toolCall.output.length > 100
              ? toolCall.output.substring(0, 100) + '...'
              : toolCall.output}
          </Text>
        </Box>
      )}
      {toolCall.error && (
        <Box marginLeft={2}>
          <Text color="red">{toolCall.error}</Text>
        </Box>
      )}
    </Box>
  );
};

export default ToolExecutionView;

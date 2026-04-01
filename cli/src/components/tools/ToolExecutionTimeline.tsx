import React from 'react';
import { Box, Text } from 'ink';
import { useToolCalls } from '../../state/store.js';
import ToolExecutionView from './ToolExecutionView.js';

const ToolExecutionTimeline: React.FC = () => {
  const toolCalls = useToolCalls();
  const toolCallList = Object.values(toolCalls).sort(
    (a, b) => b.startTime - a.startTime
  );

  if (toolCallList.length === 0) {
    return (
      <Box borderStyle="single" borderColor="yellow" paddingX={1} flexDirection="column">
        <Text bold color="yellow">
          Tool Executions
        </Text>
        <Text color="gray" dimColor>
          No tool calls yet
        </Text>
      </Box>
    );
  }

  const runningCount = toolCallList.filter((t) => t.status === 'running').length;

  return (
    <Box borderStyle="single" borderColor="yellow" paddingX={1} flexDirection="column">
      <Box marginBottom={1}>
        <Text bold color="yellow">
          Tool Executions
        </Text>
        {runningCount > 0 && (
          <Text color="cyan"> ({runningCount} running)</Text>
        )}
      </Box>
      {toolCallList.slice(0, 10).map((toolCall) => (
        <ToolExecutionView key={toolCall.id} toolCall={toolCall} />
      ))}
      {toolCallList.length > 10 && (
        <Text color="gray" dimColor>
          ... and {toolCallList.length - 10} more
        </Text>
      )}
    </Box>
  );
};

export default ToolExecutionTimeline;

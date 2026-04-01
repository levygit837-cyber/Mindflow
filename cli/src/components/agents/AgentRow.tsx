import React from 'react';
import { Box, Text } from 'ink';
import Spinner from '../ui/Spinner.js';
import ProgressBar from '../ui/ProgressBar.js';
import type { AgentState } from '../../types/index.js';

interface AgentRowProps {
  agent: AgentState;
}

const AgentRow: React.FC<AgentRowProps> = ({ agent }) => {
  const getStatusColor = () => {
    switch (agent.status) {
      case 'idle':
        return 'gray';
      case 'thinking':
        return 'yellow';
      case 'executing':
        return 'cyan';
      case 'error':
        return 'red';
      default:
        return 'white';
    }
  };

  const getStatusIcon = () => {
    if (agent.status === 'idle') {
      return <Text color="gray">○</Text>;
    }
    return <Spinner color={getStatusColor()} />;
  };

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        {getStatusIcon()}
        <Text color={getStatusColor()} bold>
          {' '}
          {agent.name}
        </Text>
        {agent.currentTool && (
          <Text color="yellow"> → {agent.currentTool}</Text>
        )}
      </Box>
      {agent.progress !== undefined && agent.progress > 0 && (
        <Box marginLeft={2}>
          <ProgressBar progress={agent.progress} width={15} />
        </Box>
      )}
    </Box>
  );
};

export default AgentRow;

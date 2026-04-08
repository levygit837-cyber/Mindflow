/**
 * AgentProgress - Track and display active agents
 * Shows agent status, progress, and current task
 */

import React from 'react';
import { Box, Text } from 'ink';
import { useMessageStore } from '../../core/MessageStore.js';
import type { Agent } from '../../types/protocol.js';

interface AgentProgressProps {
  maxHeight?: number;
}

export const AgentProgress: React.FC<AgentProgressProps> = ({
  maxHeight = 15,
}) => {
  const { agents } = useMessageStore();
  const agentList = Array.from(agents.values());

  if (agentList.length === 0) {
    return (
      <Box flexDirection="column" paddingX={1}>
        <Text color="gray" dimColor>No active agents</Text>
      </Box>
    );
  }

  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'idle': return 'gray';
      case 'running': return '#0D6E6E';
      case 'completed': return 'green';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  const getStatusIcon = (status: Agent['status']) => {
    switch (status) {
      case 'idle': return '○';
      case 'running': return '◉';
      case 'completed': return '✓';
      case 'error': return '✗';
      default: return '•';
    }
  };

  // Progress bar for agents with progress
  const renderProgressBar = (progress?: number) => {
    if (progress === undefined) return null;
    
    const width = 20;
    const filled = Math.round((progress / 100) * width);
    const empty = width - filled;
    
    return (
      <Box>
        <Text color="#0D6E6E">{'█'.repeat(filled)}</Text>
        <Text color="gray">{'░'.repeat(empty)}</Text>
        <Text color="gray" dimColor>{' '}{progress}%</Text>
      </Box>
    );
  };

  return (
    <Box flexDirection="column" paddingX={1} height={maxHeight}>
      <Box marginBottom={1}>
        <Text color="#0D6E6E" bold>Active Agents ({agentList.length})</Text>
      </Box>

      {agentList.slice(0, maxHeight - 2).map((agent) => (
        <Box 
          key={agent.id} 
          flexDirection="column" 
          marginY={1}
          borderStyle="single"
          borderColor={getStatusColor(agent.status)}
          paddingX={1}
        >
          <Box justifyContent="space-between">
            <Box>
              <Text color={getStatusColor(agent.status)}>
                {getStatusIcon(agent.status)}{' '}
              </Text>
              <Text color={agent.color} bold>{agent.name}</Text>
            </Box>
            <Box>
              <Text color="gray" dimColor>{agent.status}</Text>
            </Box>
          </Box>

          {agent.currentTask && (
            <Box marginTop={1}>
              <Text color="gray" dimColor>Task: </Text>
              <Text color="white">{agent.currentTask}</Text>
            </Box>
          )}

          {agent.progress !== undefined && (
            <Box marginTop={1}>
              {renderProgressBar(agent.progress)}
            </Box>
          )}

          {agent.description && (
            <Box marginTop={1}>
              <Text color="gray" dimColor>{agent.description}</Text>
            </Box>
          )}
        </Box>
      ))}

      {agentList.length > maxHeight - 2 && (
        <Box marginTop={1}>
          <Text color="gray" dimColor>
            ... and {agentList.length - maxHeight + 2} more
          </Text>
        </Box>
      )}
    </Box>
  );
};

// Compact agent status line
interface AgentStatusLineProps {
  showCount?: boolean;
}

export const AgentStatusLine: React.FC<AgentStatusLineProps> = ({
  showCount = true,
}) => {
  const { agents } = useMessageStore();
  const agentList = Array.from(agents.values());

  const running = agentList.filter(a => a.status === 'running').length;
  const completed = agentList.filter(a => a.status === 'completed').length;
  const errored = agentList.filter(a => a.status === 'error').length;

  return (
    <Box>
      {showCount && agentList.length > 0 && (
        <>
          <Text color="#0D6E6E" bold>Agents: </Text>
          {running > 0 && (
            <Text color="#0D6E6E">◉{running} </Text>
          )}
          {completed > 0 && (
            <Text color="green">✓{completed} </Text>
          )}
          {errored > 0 && (
            <Text color="red">✗{errored} </Text>
          )}
          <Text color="gray" dimColor>({agentList.length} total)</Text>
        </>
      )}
    </Box>
  );
};

export default AgentProgress;

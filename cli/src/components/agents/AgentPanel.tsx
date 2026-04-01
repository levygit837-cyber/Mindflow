import React from 'react';
import { Box, Text } from 'ink';
import { useAgents } from '../../state/store.js';
import AgentRow from './AgentRow.js';

const AgentPanel: React.FC = () => {
  const agents = useAgents();
  const agentList = Object.values(agents);

  if (agentList.length === 0) {
    return (
      <Box borderStyle="single" borderColor="cyan" paddingX={1} flexDirection="column">
        <Text bold color="cyan">
          Agents
        </Text>
        <Text color="gray" dimColor>
          No active agents
        </Text>
      </Box>
    );
  }

  const activeCount = agentList.filter((a) => a.status !== 'idle').length;

  return (
    <Box borderStyle="single" borderColor="cyan" paddingX={1} flexDirection="column">
      <Box marginBottom={1}>
        <Text bold color="cyan">
          Agents
        </Text>
        <Text color="gray"> ({activeCount} active)</Text>
      </Box>
      {agentList.map((agent) => (
        <AgentRow key={agent.id} agent={agent} />
      ))}
    </Box>
  );
};

export default AgentPanel;

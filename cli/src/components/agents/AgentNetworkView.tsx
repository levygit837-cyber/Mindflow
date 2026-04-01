import React from 'react';
import { Box, Text } from 'ink';
import { useAgents } from '../../state/store.js';
import type { AgentState } from '../../types/index.js';

const AgentNetworkView: React.FC = () => {
  const agents = useAgents();
  const agentList = Object.values(agents);

  // Build tree structure
  const rootAgents = agentList.filter((a) => !a.parentId);

  const renderAgentTree = (agent: AgentState, isLast: boolean, prefix: string = ''): React.ReactNode => {
    const children = agentList.filter((a) => a.parentId === agent.id);
    const hasChildren = children.length > 0;

    const connector = isLast ? '└─' : '├─';
    const childPrefix = prefix + (isLast ? '  ' : '│ ');

    const statusColor = agent.status === 'idle' ? 'gray' : 'cyan';

    return (
      <Box key={agent.id} flexDirection="column">
        <Box>
          <Text color="gray">{prefix}{connector} </Text>
          <Text color={statusColor}>{agent.name}</Text>
          {agent.currentTool && (
            <Text color="yellow"> [{agent.currentTool}]</Text>
          )}
        </Box>
        {hasChildren && children.map((child, idx) =>
          renderAgentTree(child, idx === children.length - 1, childPrefix)
        )}
      </Box>
    );
  };

  if (agentList.length === 0) {
    return (
      <Box borderStyle="single" borderColor="cyan" paddingX={1} flexDirection="column">
        <Text bold color="cyan">Agent Network</Text>
        <Text color="gray" dimColor>No agents active</Text>
      </Box>
    );
  }

  return (
    <Box borderStyle="single" borderColor="cyan" paddingX={1} flexDirection="column">
      <Box marginBottom={1}>
        <Text bold color="cyan">Agent Network</Text>
      </Box>
      {rootAgents.map((agent, idx) =>
        renderAgentTree(agent, idx === rootAgents.length - 1)
      )}
    </Box>
  );
};

export default AgentNetworkView;

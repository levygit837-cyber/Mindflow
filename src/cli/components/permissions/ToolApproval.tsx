/**
 * ToolApproval - Permission prompt UI for MindFlow CLI
 * Similar to Claude Code permission requests
 */

import React, { useState } from 'react';
import { Box, Text } from 'ink';
import type { ControlRequest } from '../../types/protocol.js';

interface ToolApprovalProps {
  request: ControlRequest;
  onApprove: () => void;
  onDeny: () => void;
  onAsk: () => void;
}

export const ToolApproval: React.FC<ToolApprovalProps> = ({
  request,
  onApprove,
  onDeny,
  onAsk,
}) => {
  const [selectedOption, setSelectedOption] = useState<'allow' | 'deny' | 'ask'>('allow');

  const { tool_name, input } = request.request;

  // Format input for display
  const formatInput = (): string => {
    if (typeof input === 'object') {
      // Extract key info
      if ('file_path' in input) return `File: ${input.file_path}`;
      if ('command' in input) return `Command: ${input.command}`;
      if ('query' in input) return `Query: ${input.query}`;
      if ('url' in input) return `URL: ${input.url}`;
      
      // Generic
      const entries = Object.entries(input);
      if (entries.length > 0) {
        const [key, value] = entries[0];
        return `${key}: ${String(value).slice(0, 50)}`;
      }
    }
    return JSON.stringify(input).slice(0, 100);
  };

  // Get risk level for tool
  const getRiskLevel = (): { level: 'low' | 'medium' | 'high'; color: string } => {
    const highRiskTools = ['BashTool', 'FileWriteTool', 'FileEditTool'];
    const mediumRiskTools = ['WebFetchTool', 'BrowserSearchCallable'];
    
    if (highRiskTools.some(t => tool_name.includes(t))) {
      return { level: 'high', color: 'red' };
    }
    if (mediumRiskTools.some(t => tool_name.includes(t))) {
      return { level: 'medium', color: '#F59E0B' };
    }
    return { level: 'low', color: 'green' };
  };

  const risk = getRiskLevel();

  return (
    <Box 
      flexDirection="column" 
      marginY={1}
      paddingX={1}
      borderStyle="double"
      borderColor={risk.color}
    >
      {/* Header */}
      <Box marginBottom={1}>
        <Text color={risk.color} bold>
          ⚠ Permission Request
        </Text>
        <Text color="gray">{' • '}</Text>
        <Text color={risk.color}>{risk.level.toUpperCase()} RISK</Text>
      </Box>

      {/* Tool info */}
      <Box flexDirection="column" marginY={1}>
        <Box>
          <Text color="gray">Tool: </Text>
          <Text color="#14B8A6" bold>{tool_name}</Text>
        </Box>
        <Box marginTop={1}>
          <Text color="gray">Input: </Text>
          <Text color="white">{formatInput()}</Text>
        </Box>
      </Box>

      {/* Options */}
      <Box marginY={1} flexDirection="column">
        <Box>
          <Text color={selectedOption === 'allow' ? '#0D6E6E' : 'gray'}>
            {selectedOption === 'allow' ? '▶ ' : '  '}
            <Text bold={selectedOption === 'allow'}>
              [Y] Allow
            </Text>
          </Text>
        </Box>
        <Box>
          <Text color={selectedOption === 'deny' ? '#0D6E6E' : 'gray'}>
            {selectedOption === 'deny' ? '▶ ' : '  '}
            <Text bold={selectedOption === 'deny'}>
              [N] Deny
            </Text>
          </Text>
        </Box>
        <Box>
          <Text color={selectedOption === 'ask' ? '#0D6E6E' : 'gray'}>
            {selectedOption === 'ask' ? '▶ ' : '  '}
            <Text bold={selectedOption === 'ask'}>
              [?] Ask Later
            </Text>
          </Text>
        </Box>
      </Box>

      {/* Instructions */}
      <Box marginTop={1}>
        <Text color="gray" dimColor>
          Use ← → to select, Enter to confirm
        </Text>
      </Box>
    </Box>
  );
};

// Multiple tool approval (for batch operations)
interface BatchToolApprovalProps {
  requests: ControlRequest[];
  onApprove: (approvedIds: string[]) => void;
  onDeny: () => void;
}

export const BatchToolApproval: React.FC<BatchToolApprovalProps> = ({
  requests,
  onApprove,
  onDeny,
}) => {
  const [approved] = useState<Set<string>>(new Set());

  // Toggle function available for future use but currently not needed
  // const toggleApproval = (id: string) => { ... };

  return (
    <Box 
      flexDirection="column" 
      borderStyle="double"
      borderColor="#F59E0B"
      paddingX={2}
      paddingY={1}
    >
      <Box marginBottom={1}>
        <Text color="#F59E0B" bold>
          ⚠ Multiple Tools Requested
        </Text>
      </Box>

      <Text color="gray">
        {requests.length} tools need approval
      </Text>

      <Box marginY={1} flexDirection="column">
        {requests.slice(0, 5).map((req, _idx) => (
          <Box key={req.uuid} marginY={1}>
            <Text color={approved.has(req.uuid) ? 'green' : 'gray'}>
              {approved.has(req.uuid) ? '✓' : '○'}{' '}
            </Text>
            <Text color="#14B8A6">{req.request.tool_name}</Text>
            <Text color="gray" dimColor>
              {' • '}{JSON.stringify(req.request.input).slice(0, 30)}...
            </Text>
          </Box>
        ))}
        {requests.length > 5 && (
          <Box>
            <Text color="gray" dimColor>
              ... and {requests.length - 5} more
            </Text>
          </Box>
        )}
      </Box>

      <Box marginTop={1}>
        <Text color="gray" dimColor>
          [Y] Approve All • [N] Deny All • [Enter] Approve Selected
        </Text>
      </Box>
    </Box>
  );
};

export default ToolApproval;

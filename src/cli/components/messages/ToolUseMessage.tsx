/**
 * ToolUseMessage - Display tool execution in MindFlow CLI
 * Shows tool name, input, and progress
 */

import React from 'react';
import { Box, Text } from 'ink';

import type { ToolUseMessage as ToolUseMessageType } from '../../types/protocol.js';
import { useMessageStore } from '../../core/MessageStore.js';
import { Spinner } from '../ui/Spinner.js';

interface ToolUseMessageProps {
  message: ToolUseMessageType;
  isSelected?: boolean;
  isLast?: boolean;
  index: number;
}

export const ToolUseMessage: React.FC<ToolUseMessageProps> = ({
  message,
  isSelected = false,
}) => {
  const timestamp = new Date(message.timestamp).toLocaleTimeString();
  const { isToolInProgress, isToolResolved, isToolErrored, getProgressMessages } = useMessageStore();
  
  const isInProgress = isToolInProgress(message.tool_use_id);
  const isResolved = isToolResolved(message.tool_use_id);
  const isError = isToolErrored(message.tool_use_id);
  const progressMessages = getProgressMessages(message.tool_use_id);
  const borderColor = isSelected ? '#0D6E6E' : undefined;

  // Get display name for tool
  const getToolDisplayName = (): string => {
    // Map internal tool names to user-friendly names
    const toolNameMap: Record<string, string> = {
      'FileReadTool': 'Reading file',
      'FileWriteTool': 'Writing file',
      'FileEditTool': 'Editing file',
      'BashTool': 'Running command',
      'SearchTool': 'Searching',
      'WebFetchTool': 'Fetching web page',
      'BrowserSearchCallable': 'Browser search',
      'DeepPageScraperCallable': 'Scraping page',
      'MultiTabSearchCallable': 'Multi-tab search',
      'LLMResearchSynthesisCallable': 'Synthesizing research',
      'LLMQueryRefinementCallable': 'Refining query',
    };
    
    return toolNameMap[message.name] || message.name;
  };

  // Get color based on status
  const getStatusColor = (): string => {
    if (isError) return 'red';
    if (isResolved) return 'green';
    if (isInProgress) return '#0D6E6E';
    return 'gray';
  };

  // Format input for display
  const formatInput = (): string => {
    const input = message.input;
    if (typeof input === 'object') {
      // Extract key info based on tool type
      if ('file_path' in input) return String(input.file_path);
      if ('command' in input) return String(input.command);
      if ('query' in input) return String(input.query);
      if ('url' in input) return String(input.url);
      
      // Generic: show first key-value pair
      const entries = Object.entries(input);
      if (entries.length > 0) {
        const [key, value] = entries[0];
        return `${key}: ${String(value).slice(0, 30)}`;
      }
    }
    return JSON.stringify(input).slice(0, 50);
  };

  return (
    <Box
      flexDirection="column"
      marginY={0.5}
      paddingX={1}
      borderStyle={isSelected ? "single" : undefined}
      borderColor={borderColor}

    >
      {/* Header with timestamp and spinner */}
      <Box marginBottom={1}>
        <Text color="gray" dimColor>[{timestamp}]</Text>
        <Text color={getStatusColor()}>{' ◉ '}</Text>
        
        {/* Spinner for in-progress */}
        {isInProgress && (
          <Spinner 
            state="processing" 
            shouldAnimate={true}
            text={getToolDisplayName()}
          />
        )}
        
        {/* Completed/Error/Queued state */}
        {!isInProgress && (
          <Text color={getStatusColor()}>
            {getToolDisplayName()}
            {isResolved && ' ✓'}
            {isError && ' ✗'}
            {!isResolved && !isError && ' ○'}
          </Text>
        )}
      </Box>

      {/* Tool input preview */}
      <Box paddingLeft={2}>
        <Text color="gray" dimColor>
          {formatInput()}
        </Text>
      </Box>

      {/* Progress messages */}
      {progressMessages.length > 0 && (
        <Box flexDirection="column" marginTop={1} paddingLeft={2}>
          {progressMessages.slice(-3).map((progress, idx) => (
            <Box key={idx}>
              <Text color="gray" dimColor>
                {progress.percent !== undefined && (
                  <Text color="#0D6E6E">{progress.percent}% </Text>
                )}
                {progress.content}
              </Text>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default ToolUseMessage;

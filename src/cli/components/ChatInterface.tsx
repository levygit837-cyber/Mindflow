/**
 * ChatInterface - Main container for MindFlow CLI chat
 * Fully integrated with MindFlow backend API
 */

import React, { useCallback, useState } from 'react';
import { Box, Text, useStdout } from 'ink';
import { MessageList } from './MessageList.js';
import { InputBar } from './InputBar.js';
import { useMessageStore, useIsLoading } from '../core/MessageStore.js';
import { Spinner } from './ui/Spinner.js';
import { useMindFlowAPI } from '../hooks/useMindFlowAPI.js';
import { AgentProgress } from './agents/AgentProgress.js';
import type { ControlRequest } from '../types/protocol.js';

interface ChatInterfaceProps {
  title?: string;
  version?: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  title = 'MindFlow CLI',
  version = 'v0.1.0',
}) => {
  const { stdout } = useStdout();
  const [pendingRequest, setPendingRequest] = useState<ControlRequest | null>(null);
  
  const isLoading = useIsLoading();
  const { addMessage } = useMessageStore();

  // Get terminal dimensions
  const columns = stdout.columns || 80;
  const rows = stdout.rows || 24;

  // Calculate heights - flexible layout for dynamic input
  const headerHeight = 2;
  const spacing = 1;
  const agentsPanelHeight = 10; // Always reserve space for agents panel
  const PROMPT_FOOTER_LINES = 5;
  const MIN_INPUT_VIEWPORT_LINES = 3;
  const inputAreaHeight = Math.max(
    MIN_INPUT_VIEWPORT_LINES + 2, // +2 for padding and border
    Math.floor(rows / 2) - PROMPT_FOOTER_LINES
  );
  const messageListHeight = Math.max(5, rows - headerHeight - spacing - inputAreaHeight - agentsPanelHeight - 2); // -2 for keyboard hints

  // Connect to MindFlow backend
  const {
    isConnected,
    isConnecting,
    sessionId,
    sendMessage,
    executeCommand,
    sessionState,
    availableCommands,
  } = useMindFlowAPI({
    autoConnect: true,
    onError: (error) => {
      addMessage({
        type: 'system',
        subtype: 'error',
        content: `Connection error: ${error.message}`,
        timestamp: Date.now(),
        uuid: crypto.randomUUID(),
      });
    },
    onControlRequest: (request) => {
      setPendingRequest(request);
    },
  });

  // Handle message submission
  const handleSubmit = useCallback(async (input: string) => {
    if (!input.trim()) return;

    // Check for commands
    if (input.startsWith('/')) {
      const parts = input.slice(1).split(' ');
      const commandName = parts[0];
      const args = parts.slice(1);
      
      const command = availableCommands.find(
        c => c.name === commandName || c.aliases.includes(commandName)
      );
      
      if (command) {
        try {
          await executeCommand(commandName, args);
        } catch (error) {
          addMessage({
            type: 'system',
            subtype: 'error',
            content: `Command failed: ${(error as Error).message}`,
            timestamp: Date.now(),
            uuid: crypto.randomUUID(),
          });
        }
      } else {
        addMessage({
          type: 'system',
          subtype: 'error',
          content: `Unknown command: ${commandName}. Type /help for available commands.`,
          timestamp: Date.now(),
          uuid: crypto.randomUUID(),
        });
      }
      return;
    }

    // Send regular message to LLM
    if (!isConnected) {
      addMessage({
        type: 'system',
        subtype: 'error',
        content: 'Not connected to MindFlow backend. Please wait for connection...',
        timestamp: Date.now(),
        uuid: crypto.randomUUID(),
      });
      return;
    }

    try {
      await sendMessage(input);
    } catch (error) {
      addMessage({
        type: 'system',
        subtype: 'error',
        content: `Failed to send message: ${(error as Error).message}`,
        timestamp: Date.now(),
        uuid: crypto.randomUUID(),
      });
    }
  }, [isConnected, sendMessage, executeCommand, availableCommands, addMessage]);

  // Memoize connection indicator to prevent constant re-renders
  const connectionIndicator = React.useMemo(() => {
    if (isConnecting) {
      return <Spinner state="processing" shouldAnimate={true} text="Connecting..." />;
    }
    if (isConnected) {
      return <Text color="green">● Connected</Text>;
    }
    return <Text color="red">○ Disconnected</Text>;
  }, [isConnecting, isConnected]);

  // Memoize session status
  const sessionStatus = React.useMemo(() => {
    if (isLoading) return 'processing';
    if (sessionState?.permission_mode && sessionState.permission_mode !== 'default') {
      return sessionState.permission_mode;
    }
    return sessionState?.status || 'idle';
  }, [isLoading, sessionState]);

  return (
    <Box flexDirection="column" height={rows} width={columns}>
      {/* Header */}
      <Box 
        height={headerHeight} 
        borderStyle="single" 
        borderColor="#0D6E6E"
        paddingX={1}
        justifyContent="space-between"
      >
        <Box>
          <Text color="#0D6E6E" bold>◈ {title}</Text>
          <Text color="gray"> {version}</Text>
          <Box marginLeft={2}>
            {connectionIndicator}
          </Box>
          {sessionId && (
            <Box marginLeft={2}>
              <Text color="gray" dimColor>Session: {sessionId.slice(0, 8)}</Text>
            </Box>
          )}
        </Box>

        <Box>
          <Text color="gray" dimColor>
            {sessionStatus}
          </Text>
        </Box>
      </Box>

      {/* Agents Panel - always reserve space to prevent layout shifts */}
      <Box height={10} borderStyle="single" borderColor="#14B8A6" paddingX={1}>
        <AgentProgress maxHeight={8} />
      </Box>

      {/* Message List */}
      <Box flexGrow={1} overflow="hidden">
        <MessageList 
          height={messageListHeight} 
          width={columns}
        />
      </Box>

      {/* Permission Request */}
      {pendingRequest && (
        <Box 
          borderStyle="double" 
          borderColor="#F59E0B" 
          paddingX={2}
          marginY={1}
        >
          <Text color="#F59E0B" bold>⚠ Permission Request</Text>
          <Text>Tool: {pendingRequest.request.tool_name}</Text>
          <Box marginTop={1}>
            <Text color="gray">[Y] Allow  [N] Deny  [?] Ask Later</Text>
          </Box>
        </Box>
      )}

      {/* Divider */}
      <Box marginY={1}>
        <Text color="#0D6E6E">
          {'─'.repeat(columns - 2)}
        </Text>
      </Box>

      {/* Input Bar */}
      <InputBar 
        onSubmit={handleSubmit}
        showProcessingIndicator={true}
        processingText={isLoading ? 'Thinking' : 'Processing'}
      />

      {/* Help */}
      <Box marginTop={1}>
        <Text color="gray" dimColor>
          Enter send • /commands • [a] agents • Ctrl+C quit
        </Text>
      </Box>
    </Box>
  );
};

export default ChatInterface;

import React from 'react';
import { Box } from 'ink';
import Header from '../ui/Header.js';
import InputBar from '../ui/InputBar.js';
import MessageList from '../messages/MessageList.js';
import AgentPanel from '../agents/AgentPanel.js';
import ToolExecutionTimeline from '../tools/ToolExecutionTimeline.js';
import { useAppStore } from '../../state/store.js';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts.js';
import { apiService } from '../../services/api.js';

const MainLayout: React.FC = () => {
  const { addMessage, expandedView } = useAppStore();

  // Enable keyboard shortcuts
  useKeyboardShortcuts();

  const handleSubmit = async (message: string) => {
    // Add user message
    addMessage({
      id: Date.now().toString(),
      type: 'user',
      content: message,
      timestamp: Date.now(),
    });

    try {
      // Send to backend API
      await apiService.sendMessage(message);
    } catch (error) {
      addMessage({
        id: Date.now().toString(),
        type: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}`,
        timestamp: Date.now(),
      });
    }
  };

  return (
    <Box flexDirection="column" height="100%">
      <Header />
      <Box flexGrow={1}>
        <Box flexGrow={1} flexDirection="column">
          <MessageList />
        </Box>
        {expandedView === 'agents' && (
          <Box width={40} flexShrink={0}>
            <AgentPanel />
          </Box>
        )}
        {expandedView === 'tools' && (
          <Box width={40} flexShrink={0}>
            <ToolExecutionTimeline />
          </Box>
        )}
      </Box>
      <InputBar onSubmit={handleSubmit} />
    </Box>
  );
};

export default MainLayout;

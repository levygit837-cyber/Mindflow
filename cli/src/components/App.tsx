import React, { useEffect } from 'react';
import { Box } from 'ink';
import MainLayout from './layouts/MainLayout.js';
import { connectWebSocket, disconnectWebSocket } from '../services/websocket.js';

const App: React.FC = () => {
  useEffect(() => {
    // Connect to WebSocket on mount
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      disconnectWebSocket();
    };
  }, []);

  return (
    <Box flexDirection="column" height="100%">
      <MainLayout />
    </Box>
  );
};

export default App;

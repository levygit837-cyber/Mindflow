import React from 'react';
import { Box, Text } from 'ink';
import { useConnectionStatus } from '../../state/store.js';

const Header: React.FC = () => {
  const connectionStatus = useConnectionStatus();

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'green';
      case 'reconnecting':
        return 'yellow';
      case 'disconnected':
        return 'red';
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return '● Connected';
      case 'reconnecting':
        return '◐ Reconnecting...';
      case 'disconnected':
        return '○ Disconnected';
    }
  };

  return (
    <Box borderStyle="single" borderColor="cyan" paddingX={1}>
      <Box flexGrow={1}>
        <Text bold color="cyan">
          MindFlow CLI
        </Text>
      </Box>
      <Box>
        <Text color={getStatusColor()}>{getStatusText()}</Text>
      </Box>
    </Box>
  );
};

export default Header;

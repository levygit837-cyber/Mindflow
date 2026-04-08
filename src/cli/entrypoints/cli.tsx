#!/usr/bin/env node
/**
 * MindFlow CLI Entry Point
 * Modern terminal interface with streaming support
 */

import React from 'react';
import { render } from 'ink';
import { ChatInterface } from '../components/ChatInterface.js';
import { StructuredIO } from '../core/StructuredIO.js';
import { useMessageStore } from '../core/MessageStore.js';
import type { Message } from '../types/protocol.js';

// Version from package.json
const VERSION = '0.1.0';

// Main CLI App component
const App: React.FC = () => {
  const structuredIO = React.useMemo(() => new StructuredIO(), []);
  const { addMessage, startToolUse, completeToolUse, addProgressMessage, setLoading } = useMessageStore();

  // Handle incoming messages from backend
  React.useEffect(() => {
    const processMessages = async () => {
      for await (const message of structuredIO.read()) {
        handleIncomingMessage(message);
      }
    };

    processMessages().catch(console.error);

    return () => {
      structuredIO.close();
    };
  }, [structuredIO]);

  // Handle different message types
  const handleIncomingMessage = (message: Message) => {
    switch (message.type) {
      case 'assistant':
        addMessage(message);
        setLoading(false);
        break;
      
      case 'thinking':
        addMessage(message);
        break;
      
      case 'tool_use':
        addMessage(message);
        startToolUse(message);
        break;
      
      case 'tool_result':
        addMessage(message);
        completeToolUse(message);
        break;
      
      case 'progress':
        addProgressMessage(message);
        break;
      
      case 'system':
        addMessage(message);
        break;
      
      default:
        // Unknown message type, still add it
        addMessage(message);
    }
  };

  return (
    <ChatInterface
      title="MindFlow CLI"
      version={`v${VERSION}`}
    />
  );
};

// Parse command line arguments
const parseArgs = () => {
  const args = process.argv.slice(2);
  
  if (args.includes('--version') || args.includes('-v')) {
    console.log(VERSION);
    process.exit(0);
  }
  
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
MindFlow CLI ${VERSION}

Usage:
  mindflow-cli [options]

Options:
  -v, --version     Show version number
  -h, --help        Show this help message

Keyboard Shortcuts:
  Enter             Submit message
  ↑/↓               Navigate input history
  Ctrl+C            Quit
  Ctrl+L            Clear screen
  Tab               Navigate UI elements

For more information, visit: https://mindflow.dev
    `);
    process.exit(0);
  }
};

// Main entry point
const main = () => {
  parseArgs();
  
  // Check if stdin is a TTY
  if (!process.stdin.isTTY) {
    console.error('Error: MindFlow CLI requires an interactive terminal');
    process.exit(1);
  }

  // Render the app
  render(<App />);
};

// Run main
main();

/**
 * MessageList - Virtualized message list for MindFlow CLI
 * Displays messages with proper scrolling and virtualization
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Box, Text } from 'ink';
import { useMessageStore, useMessages, useVisibleRange } from '../core/MessageStore.js';
import type { Message } from '../types/protocol.js';
import { UserMessage } from './messages/UserMessage.js';
import { AssistantMessage } from './messages/AssistantMessage.js';
import { ToolUseMessage } from './messages/ToolUseMessage.js';
import { ToolResultMessage } from './messages/ToolResultMessage.js';
import { SystemMessage } from './messages/SystemMessage.js';
import { ThinkingMessage } from './messages/ThinkingMessage.js';

// Constants for virtualization
const MESSAGE_HEIGHT_ESTIMATE = 3; // Average lines per message
const OVERSCAN_COUNT = 5; // Number of messages to render outside viewport

interface MessageListProps {
  height?: number;
  width?: number;
}

export const MessageList: React.FC<MessageListProps> = ({
  height = 20,
}) => {
  const messages = useMessages();
  const visibleRange = useVisibleRange();
  const { setVisibleRange, selectedMessageIndex } = useMessageStore();
  
  const [scrollOffset, setScrollOffset] = useState(0);

  // Calculate visible messages based on scroll position - memoized
  const calculateVisibleRange = useCallback(() => {
    const startIdx = Math.max(0, Math.floor(scrollOffset / MESSAGE_HEIGHT_ESTIMATE) - OVERSCAN_COUNT);
    const endIdx = Math.min(
      messages.length,
      Math.ceil((scrollOffset + height) / MESSAGE_HEIGHT_ESTIMATE) + OVERSCAN_COUNT
    );
    
    const newRange = { start: startIdx, end: endIdx };
    // Only update if range actually changed
    if (newRange.start !== visibleRange.start || newRange.end !== visibleRange.end) {
      setVisibleRange(newRange);
    }
    return newRange;
  }, [scrollOffset, height, messages.length, visibleRange.start, visibleRange.end, setVisibleRange]);


  // Auto-scroll to bottom on new messages - only if user is near bottom
  const lastScrollOffsetRef = useRef(0);
  useEffect(() => {
    const maxScroll = Math.max(0, messages.length * MESSAGE_HEIGHT_ESTIMATE - height);
    // Only auto-scroll if user was already near bottom (within 5 lines)
    if (lastScrollOffsetRef.current >= maxScroll - 5 || messages.length <= 1) {
      setScrollOffset(maxScroll);
    }
    lastScrollOffsetRef.current = scrollOffset;
  }, [messages.length, height, scrollOffset]);

  // Render individual message based on type
  const renderMessage = (message: Message, index: number) => {
    const isSelected = selectedMessageIndex === index;
    const isLast = index === messages.length - 1;
    
    const commonProps = {
      key: message.uuid,
      message,
      isSelected,
      isLast,
      index,
    };

    switch (message.type) {
      case 'user':
        return <UserMessage {...commonProps} message={message as import('../types/protocol.js').UserMessage} />;
      case 'assistant':
        return <AssistantMessage {...commonProps} message={message as import('../types/protocol.js').AssistantMessage} />;
      case 'thinking':
        return <ThinkingMessage {...commonProps} message={message as import('../types/protocol.js').ThinkingMessage} />;
      case 'tool_use':
        return <ToolUseMessage {...commonProps} message={message as import('../types/protocol.js').ToolUseMessage} />;
      case 'tool_result':
        return <ToolResultMessage {...commonProps} message={message as import('../types/protocol.js').ToolResultMessage} />;
      case 'system':
        return <SystemMessage {...commonProps} message={message as import('../types/protocol.js').SystemMessage} />;
      case 'progress':
        // Progress messages are handled within ToolUseMessage
        return null;
      default:
        return null;
    }
  };

  // Calculate visible range on each render
  calculateVisibleRange();

  // Get visible messages
  const visibleMessages = messages.slice(visibleRange.start, visibleRange.end);

  // Empty state
  if (messages.length === 0) {
    return (
      <Box 
        flexDirection="column" 
        height={height} 
        justifyContent="center" 
        alignItems="center"
      >
        <Box marginBottom={1}>
          <Text color="#0D6E6E" bold>◈ MindFlow CLI</Text>
        </Box>
        <Text color="gray">Welcome! Type your message below to start.</Text>
        <Box marginTop={1}>
          <Text color="gray" dimColor>
            Press Ctrl+C to quit • Ctrl+L to clear
          </Text>
        </Box>
      </Box>
    );
  }

  return (
    <Box 
      flexDirection="column" 
      height={height}
      overflow="hidden"
    >
      {/* Scroll indicator */}
      {scrollOffset > 0 && (
        <Box justifyContent="center" marginBottom={1}>
          <Text color="gray" dimColor>▲ Scroll up to see more</Text>
        </Box>
      )}

      {/* Message container */}
      <Box flexDirection="column" flexGrow={1}>
        {visibleMessages.map((msg, idx) => (
          <Box key={msg.uuid}>
            {renderMessage(msg, visibleRange.start + idx)}
          </Box>
        ))}
      </Box>

      {/* Bottom scroll indicator */}
      {scrollOffset < messages.length * MESSAGE_HEIGHT_ESTIMATE - height && (
        <Box justifyContent="center" marginTop={1}>
          <Text color="gray" dimColor>▼ More messages below</Text>
        </Box>
      )}
    </Box>
  );
};

export default MessageList;

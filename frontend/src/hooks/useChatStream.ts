import { useCallback, useRef, useState } from 'react';
import { ApiError, chatApi } from '../lib/api';
import { useChatStore } from '../stores/chatStore';
import { AgentType, ChatMessage } from '../types/backend';

interface UseChatStreamOptions {
  sessionId?: string;
  agentType?: AgentType;
  orchestrate?: boolean;
  folderPath?: string;
}

interface UseChatStreamReturn {
  isStreaming: boolean;
  error: string | null;
  messages: ChatMessage[];
  sendMessage: (content: string, sessionId?: string) => Promise<void>;
  stopStreaming: () => void;
}

export function useChatStream(options: UseChatStreamOptions = {}): UseChatStreamReturn {
  const abortControllerRef = useRef<AbortController | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const {
    messages,
    isStreaming,
    error: storeError,
    addMessage,
    handleStreamEvent,
    setIsStreaming,
    setError,
    clearEvents,
  } = useChatStore();

  const sendMessage = useCallback(
    async (content: string, sessionId?: string) => {
      const effectiveSessionId = sessionId ?? options.sessionId;
      // Clear previous events for new conversation
      clearEvents();
      setLocalError(null);
      setError(null);

      // Add user message
      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}-user`,
        role: 'user',
        content,
        timestamp: new Date(),
      };
      addMessage(userMessage);

      // Create placeholder for assistant response
      const assistantMessageId = `msg-${Date.now()}-assistant`;
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        agentType: options.agentType,
        timestamp: new Date(),
        events: [],
      };
      addMessage(assistantMessage);

      setIsStreaming(true);

      // Create abort controller for cancellation
      abortControllerRef.current = new AbortController();

      try {
        let fullContent = '';
        for await (const event of chatApi.streamChatEvents(
          {
            message: content,
            session_id: effectiveSessionId,
            agent_type: options.agentType,
            orchestrate: options.orchestrate,
            folder_path: options.folderPath,
            stream: true,
          },
          abortControllerRef.current.signal
        )) {
          handleStreamEvent(event);

          if (event.type === 'response') {
            fullContent += event.data;
            const currentEvents = useChatStore.getState().messages.find(
              (m) => m.id === assistantMessageId
            )?.events || [];

            useChatStore.getState().updateMessage(assistantMessageId, {
              content: fullContent,
              events: [...currentEvents, event],
            });
          }

          if (
            event.type !== 'response' &&
            event.type !== 'done' &&
            event.type !== 'error'
          ) {
            const currentEvents = useChatStore.getState().messages.find(
              (m) => m.id === assistantMessageId
            )?.events || [];

            useChatStore.getState().updateMessage(assistantMessageId, {
              events: [...currentEvents, event],
            });
          }
        }

        setIsStreaming(false);
      } catch (err) {
        const errorMessage = err instanceof ApiError ? err.message : 'Failed to send message';
        setLocalError(errorMessage);
        setError(errorMessage);
        setIsStreaming(false);

        // Update the assistant message with error
        useChatStore.getState().updateMessage(assistantMessageId, {
          content: `Error: ${errorMessage}`,
        });

        if (err instanceof Error && err.name !== 'AbortError') {
          console.error('Chat stream error:', err);
        }
      }
    },
    [
      options.sessionId,
      options.agentType,
      options.orchestrate,
      options.folderPath,
      addMessage,
      handleStreamEvent,
      setIsStreaming,
      setError,
      clearEvents,
    ]
  );

  const stopStreaming = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    abortControllerRef.current?.abort();
    setIsStreaming(false);
  }, [setIsStreaming]);

  return {
    isStreaming,
    error: localError || storeError,
    messages,
    sendMessage,
    stopStreaming,
  };
}

export default useChatStream;

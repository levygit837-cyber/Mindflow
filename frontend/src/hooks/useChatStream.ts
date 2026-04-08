import { useCallback, useRef, useState } from 'react';
import { ApiError } from '../lib/api';
import { useChatStore } from '../stores/chatStore';
import { AgentType, ChatMessage, StreamEvent } from '../types/backend';

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
  sendMessage: (content: string) => Promise<void>;
  stopStreaming: () => void;
}

export function useChatStream(options: UseChatStreamOptions = {}): UseChatStreamReturn {
  const abortControllerRef = useRef<AbortController | null>(null);
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
    async (content: string) => {
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
        const response = await fetch(`/api/v1/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({
            message: {
              type: 'user',
              content: content,
            },
            session_id: options.sessionId,
            agent_type: options.agentType,
            orchestrate: options.orchestrate,
            folder_path: options.folderPath,
            stream: true,
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new ApiError(`Streaming error: ${response.status}`, response.status);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new ApiError('No response body available');
        }

        const decoder = new TextDecoder();
        let buffer = '';
        let fullContent = '';

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') continue;

                try {
                  const event: StreamEvent = JSON.parse(data);

                  // Handle the event in the store
                  handleStreamEvent(event);

                  // Collect response content
                  if (event.type === 'response') {
                    fullContent += event.data;
                    // Update the assistant message with accumulated content
                    const currentEvents = useChatStore.getState().messages.find(
                      (m) => m.id === assistantMessageId
                    )?.events || [];

                    useChatStore.getState().updateMessage(assistantMessageId, {
                      content: fullContent,
                      events: [...currentEvents, event],
                    });
                  }

                  // Append other events to the message
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
                } catch (e) {
                  console.warn('Failed to parse SSE event:', data, e);
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
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

import { useState, useCallback } from 'react';

export type EventType =
  | 'user'
  | 'thought'
  | 'response'
  | 'tool_call'
  | 'tool_result'
  | 'step'
  | 'agent_step'
  | 'error'
  | 'done'
  // Orchestrator lifecycle events
  | 'orchestrator_thinking'
  | 'orchestrator_thinking_start'
  | 'orchestrator_thinking_end'
  | 'orchestrator_decision'
  | 'reflection_mode_start'
  | 'reflection_mode_end'
  | 'agent_delegation_start'
  | 'agent_delegation_complete'
  | 'specialist_activation'
  | 'notifier'
  | (string & {});

export interface StreamEvent {
  id?: string;
  seq?: number;
  type: EventType;
  data: string;
  meta?: Record<string, any>;
}

/** Read the API key from Vite env or window config. Empty string = no auth header sent. */
const getApiKey = (): string =>
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_KEY) || '';

const buildAuthHeaders = (): Record<string, string> => {
  const key = getApiKey();
  return key ? { 'Authorization': `Bearer ${key}` } : {};
};

export const useOmniStream = (url: string) => {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearEvents = useCallback(() => setEvents([]), []);

  const startStream = useCallback(async (body: {
    message: string,
    session_id?: string,
    provider?: string,
    model?: string,
    orchestrate?: boolean,
    agent?: string,
    folder_path?: string,
    execution_id?: string,
  }) => {
    setIsStreaming(true);
    setError(null);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        const newEvents: StreamEvent[] = [];
        for (const line of lines) {
          if (line.trim().startsWith('data: ')) {
            try {
              const event: StreamEvent = JSON.parse(line.trim().slice(6));
              newEvents.push(event);
            } catch (e) {
              console.error('Failed to parse SSE event', e);
            }
          }
        }
        if (newEvents.length > 0) {
          setEvents(prev => [...prev, ...newEvents]);
        }
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsStreaming(false);
    }
  }, [url]);

  return { events, isStreaming, error, startStream, clearEvents };
};

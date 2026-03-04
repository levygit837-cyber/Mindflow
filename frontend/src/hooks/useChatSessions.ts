import { useState, useCallback, useEffect } from 'react';

export type ChatMessage = {
  id?: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  provider?: string;
  model?: string;
  created_at?: string;
};

export type ChatSession = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
};

export function useChatSessions(baseUrl: string) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${baseUrl}/v1/chat/sessions`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (err) {
      console.error('Failed to fetch sessions', err);
    } finally {
      setIsLoading(false);
    }
  }, [baseUrl]);

  const getSessionHistory = useCallback(async (sessionId: string): Promise<ChatSession | null> => {
    try {
      const response = await fetch(`${baseUrl}/v1/chat/sessions/${sessionId}`);
      if (response.ok) {
        return await response.json();
      }
    } catch (err) {
      console.error('Failed to fetch session history', err);
    }
    return null;
  }, [baseUrl]);

  useEffect(() => {
    fetchSessions();
  }, []);

  return {
    sessions,
    currentSessionId,
    setCurrentSessionId,
    isLoading,
    fetchSessions,
    getSessionHistory
  };
}

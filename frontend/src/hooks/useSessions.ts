import { useCallback, useEffect, useRef } from 'react';
import { chatApi } from '../lib/api';
import { useChatStore } from '../stores/chatStore';

export function useSessions() {
  const {
    sessions,
    currentSessionId,
    setSessions,
    setCurrentSession,
    setIsLoading,
    setError,
  } = useChatStore();

  const loadedRef = useRef(false);

  const loadSessions = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await chatApi.listSessions();
      // Normalize date strings to Date objects
      const normalized = data.map((s) => ({
        ...s,
        createdAt: new Date((s as unknown as Record<string, string>).created_at || s.createdAt),
        updatedAt: new Date((s as unknown as Record<string, string>).updated_at || s.updatedAt),
        messages: (s as unknown as Record<string, unknown[]>).messages ?? [],
      }));
      setSessions(normalized as typeof data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setIsLoading(false);
    }
  }, [setSessions, setIsLoading, setError]);

  // Load sessions once on mount
  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    loadSessions();
  }, [loadSessions]);

  const createSession = useCallback(
    async (title?: string): Promise<string> => {
      const data = await chatApi.createSession(title);
      const session = {
        ...data,
        createdAt: new Date((data as unknown as Record<string, string>).created_at || data.createdAt),
        updatedAt: new Date((data as unknown as Record<string, string>).updated_at || data.updatedAt),
        messages: [],
      };
      setSessions([session as typeof data, ...sessions]);
      return data.id;
    },
    [sessions, setSessions]
  );

  const selectSession = useCallback(
    async (sessionId: string) => {
      if (sessionId === currentSessionId) return;
      setCurrentSession(sessionId);
      setIsLoading(true);
      try {
        const data = await chatApi.getSession(sessionId);
        // Map backend messages to frontend ChatMessage shape
        const messages = ((data as unknown as Record<string, unknown[]>).messages ?? []).map((m) => {
          const msg = m as Record<string, unknown>;
          return {
            id: String(msg.id),
            role: msg.role as 'user' | 'assistant' | 'system',
            content: msg.content as string,
            timestamp: new Date(msg.created_at as string),
            events: [],
          };
        });
        useChatStore.getState().setMessages(messages);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load session');
      } finally {
        setIsLoading(false);
      }
    },
    [currentSessionId, setCurrentSession, setIsLoading, setError]
  );

  const deleteSession = useCallback(
    async (sessionId: string) => {
      try {
        await chatApi.deleteSession(sessionId);
        const updated = sessions.filter((s) => s.id !== sessionId);
        setSessions(updated);
        if (currentSessionId === sessionId) {
          // Switch to the next available session or clear
          if (updated.length > 0) {
            await selectSession(updated[0].id);
          } else {
            useChatStore.setState({ currentSessionId: null, messages: [] });
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete session');
      }
    },
    [sessions, currentSessionId, setSessions, selectSession, setError]
  );

  const renameSession = useCallback(
    async (sessionId: string, title: string) => {
      try {
        await chatApi.renameSession(sessionId, title);
        setSessions(
          sessions.map((s) => (s.id === sessionId ? { ...s, title } : s))
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to rename session');
      }
    },
    [sessions, setSessions, setError]
  );

  return {
    sessions,
    currentSessionId,
    loadSessions,
    createSession,
    selectSession,
    deleteSession,
    renameSession,
  };
}

export default useSessions;

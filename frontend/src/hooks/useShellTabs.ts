import { useCallback, useEffect, useRef, useState } from 'react';

export interface ShellTabView {
  tab_id: string;
  session_id: string;
  cwd: string;
  title: string;
  pid?: number | null;
  state: 'idle' | 'running' | 'completed' | 'failed' | 'terminated';
  last_command?: string | null;
  last_exit_code?: number | null;
  stdout_buffer?: string;
  stderr_buffer?: string;
  updated_at?: string;
}

export const useShellTabs = (sessionId: string, pollMs = 2500) => {
  const [tabs, setTabs] = useState<ShellTabView[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const refresh = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    try {
      const response = await fetch(`/v1/agent/shell-tabs/${sessionId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      setTabs(Array.isArray(payload) ? payload : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao carregar shell tabs');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void refresh();
    if (!pollMs) return undefined;

    const timer = window.setInterval(() => {
      void refresh();
    }, pollMs);

    return () => window.clearInterval(timer);
  }, [pollMs, refresh]);

  useEffect(() => {
    if (!sessionId || typeof window === 'undefined' || typeof EventSource === 'undefined') {
      return undefined;
    }

    const source = new EventSource(`/v1/agent/shell-tabs/${sessionId}/events`);
    eventSourceRef.current = source;

    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string; tabs?: ShellTabView[] };
        if (payload.type === 'snapshot' && Array.isArray(payload.tabs)) {
          setTabs(payload.tabs);
          setError(null);
          return;
        }
        if (payload.type !== 'keepalive') {
          void refresh();
        }
      } catch {
        void refresh();
      }
    };

    source.onerror = () => {
      setError((current) => current ?? 'Falha na atualização em tempo real das shell tabs');
    };

    return () => {
      source.close();
      if (eventSourceRef.current === source) {
        eventSourceRef.current = null;
      }
    };
  }, [refresh, sessionId]);

  return { tabs, isLoading, error, refresh };
};

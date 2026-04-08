/// <reference types="vite/client" />

/**
 * API service for connecting to MindFlow backend
 */

import { ChatRequest, ChatSession, StreamEvent } from '../types/backend';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchWithError<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }
    throw new ApiError(
      `API Error: ${response.status} ${response.statusText}`,
      response.status,
      errorData
    );
  }

  return response.json() as T;
}

export const chatApi = {
  /**
   * Create a new chat session
   */
  async createSession(title?: string): Promise<ChatSession> {
    return fetchWithError(`${API_BASE_URL}/chat/sessions`, {
      method: 'POST',
      body: JSON.stringify({ title: title || 'New Chat' }),
    });
  },

  /**
   * List all chat sessions
   */
  async listSessions(): Promise<ChatSession[]> {
    return fetchWithError(`${API_BASE_URL}/chat/sessions`);
  },

  /**
   * Get a specific session with messages
   */
  async getSession(sessionId: string): Promise<ChatSession> {
    return fetchWithError(`${API_BASE_URL}/chat/sessions/${sessionId}`);
  },

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<void> {
    await fetchWithError(`${API_BASE_URL}/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Save a message to a session
   */
  async saveMessage(
    sessionId: string,
    role: 'user' | 'assistant',
    content: string,
    model?: string,
    provider?: string
  ): Promise<{ success: boolean; id: string }> {
    return fetchWithError(`${API_BASE_URL}/chat/sessions/${sessionId}/save-message`, {
      method: 'POST',
      body: JSON.stringify({ role, content, model, provider }),
    });
  },

  /**
   * Generate session title using AI
   */
  async generateTitle(sessionId: string, message: string): Promise<{ title: string }> {
    return fetchWithError(`${API_BASE_URL}/chat/sessions/${sessionId}/generate-title`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },

  /**
   * Stream chat using fetch with ReadableStream for better control
   */
  async *streamChatEvents(
    request: ChatRequest
  ): AsyncGenerator<StreamEvent, void, unknown> {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        message: {
          type: 'user',
          content: request.message,
        },
        session_id: request.session_id,
        agent_type: request.agent_type,
        orchestrate: request.orchestrate,
        provider: request.provider,
        model: request.model,
        folder_path: request.folder_path,
        stream: true,
      }),
    });

    if (!response.ok) {
      throw new ApiError(
        `Streaming error: ${response.status}`,
        response.status
      );
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new ApiError('No response body available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

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
            if (data === '[DONE]') return;

            try {
              const event: StreamEvent = JSON.parse(data);
              yield event;
            } catch (e) {
              console.warn('Failed to parse SSE event:', data, e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
};

export default chatApi;

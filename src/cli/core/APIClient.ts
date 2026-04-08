/**
 * MindFlowAPIClient - Real backend integration for MindFlow CLI
 * Connects to FastAPI backend with WebSocket streaming
 */

import type { Message, UserMessage, AssistantMessage, SessionState } from '../types/protocol.js';

// Configuration for API client
export interface APIClientConfig {
  baseURL: string;
  apiKey?: string;
  timeout?: number;
  retries?: number;
}

// Default config
const DEFAULT_CONFIG: APIClientConfig = {
  baseURL: process.env.MINDFLOW_API_URL || 'http://localhost:8000',
  timeout: 30000,
  retries: 3,
};

// API Response types
interface ChatResponse {
  message: AssistantMessage;
  session_id: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

interface SessionResponse {
  session_id: string;
  status: SessionState['status'];
  created_at: string;
  updated_at: string;
}

interface CommandResponse {
  success: boolean;
  message: string;
  data?: Record<string, unknown>;
  error?: string;
}

interface AgentListResponse {
  agents: Array<{
    id: string;
    name: string;
    description: string;
    status: string;
    capabilities: string[];
  }>;
}

interface ProviderListResponse {
  providers: Array<{
    provider_id: string;
    name: string;
    status: string;
    models: string[];
  }>;
}

// Task update from WebSocket
type TaskUpdate = {
  event_type: 'task_created' | 'task_updated' | 'task_completed';
  task_id: number;
  task_list_id: string;
  subject: string;
  status: string;
  owner: string;
  session_id: string;
  timestamp: string;
};

export class MindFlowAPIClient {
  private config: APIClientConfig;
  private sessionId: string | null = null;
  private ws: WebSocket | null = null;
  private wsReconnectAttempts = 0;
  private maxWsReconnectAttempts = 5;
  private messageHandlers: Array<(message: Message) => void> = [];
  private taskHandlers: Array<(update: TaskUpdate) => void> = [];
  private connectionHandlers: Array<(connected: boolean) => void> = [];

  constructor(config: Partial<APIClientConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  // HTTP request helper
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.config.baseURL}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (this.config.apiKey) {
      headers['Authorization'] = `Bearer ${this.config.apiKey}`;
    }

    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API Error ${response.status}: ${error}`);
    }

    return response.json() as Promise<T>;
  }

  // Initialize session
  async initSession(): Promise<string> {
    try {
      const response = await this.request<SessionResponse>('/v1/sessions', {
        method: 'POST',
      });
      this.sessionId = response.session_id;
      return response.session_id;
    } catch (error) {
      // Fallback: generate local session ID
      this.sessionId = crypto.randomUUID();
      return this.sessionId;
    }
  }

  // Get current session ID
  getSessionId(): string | null {
    return this.sessionId;
  }

  // Set session ID
  setSessionId(sessionId: string): void {
    this.sessionId = sessionId;
  }

  // Chat with LLM
  async chat(
    content: string,
    options: {
      model?: string;
      provider?: string;
      stream?: boolean;
      parentToolUseId?: string | null;
      attachments?: Array<{ type: 'file' | 'image' | 'context'; name: string; content?: string }>;
    } = {}
  ): Promise<AssistantMessage> {
    const message: UserMessage = {
      type: 'user',
      content,
      timestamp: Date.now(),
      uuid: crypto.randomUUID(),
      parent_tool_use_id: options.parentToolUseId || null,
      attachments: options.attachments,
      session_id: this.sessionId || undefined,
    };

    if (options.stream) {
      // For streaming, use WebSocket
      this.sendMessage(message);
      // Return a placeholder that will be updated via WebSocket
      return {
        type: 'assistant',
        content: '',
        timestamp: Date.now(),
        uuid: crypto.randomUUID(),
        session_id: this.sessionId || undefined,
      };
    }

    const response = await this.request<ChatResponse>('/v1/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        session_id: this.sessionId,
        model: options.model,
        provider: options.provider,
        stream: false,
      }),
    });

    return response.message;
  }

  // Execute command
  async executeCommand(
    commandName: string,
    args: string[] = [],
    metadata?: Record<string, unknown>
  ): Promise<CommandResponse> {
    return this.request<CommandResponse>('/v1/commands/execute', {
      method: 'POST',
      body: JSON.stringify({
        command: commandName,
        args,
        session_id: this.sessionId,
        metadata,
      }),
    });
  }

  // List available commands
  async listCommands(): Promise<Array<{ name: string; description: string; aliases: string[] }>> {
    try {
      const response = await this.request<{ commands: Array<{ name: string; description: string; aliases: string[] }> }>('/v1/commands');
      return response.commands;
    } catch {
      // Fallback: return common MindFlow commands
      return [
        { name: 'help', description: 'Show help information', aliases: ['h'] },
        { name: 'clear', description: 'Clear conversation history', aliases: ['cls'] },
        { name: 'reset', description: 'Reset session', aliases: [] },
        { name: 'models', description: 'List available models', aliases: [] },
        { name: 'providers', description: 'List LLM providers', aliases: [] },
        { name: 'agents', description: 'List available agents', aliases: [] },
        { name: 'mode', description: 'Set execution mode', aliases: [] },
        { name: 'settings', description: 'View/change settings', aliases: ['config'] },
        { name: 'export', description: 'Export conversation', aliases: [] },
        { name: 'import', description: 'Import conversation', aliases: [] },
      ];
    }
  }

  // List agents
  async listAgents(): Promise<AgentListResponse> {
    return this.request<AgentListResponse>('/v1/agents');
  }

  // List providers
  async listProviders(): Promise<ProviderListResponse> {
    return this.request<ProviderListResponse>('/v1/providers');
  }

  // Get session status
  async getSessionStatus(): Promise<SessionState> {
    if (!this.sessionId) {
      throw new Error('No active session');
    }
    
    try {
      const response = await this.request<{ status: SessionState['status']; mode: string }>(`/v1/sessions/${this.sessionId}`);
      return {
        id: this.sessionId,
        status: response.status,
        permission_mode: response.mode as SessionState['permission_mode'],
      };
    } catch {
      // Fallback
      return {
        id: this.sessionId,
        status: 'idle',
        permission_mode: 'default',
      };
    }
  }

  // Update session settings
  async updateSessionSettings(settings: {
    permission_mode?: SessionState['permission_mode'];
    model?: string;
    provider?: string;
  }): Promise<void> {
    if (!this.sessionId) {
      throw new Error('No active session');
    }

    await this.request(`/v1/sessions/${this.sessionId}/settings`, {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }

  // Send permission response
  async sendPermissionResponse(
    requestId: string,
    decision: 'allow' | 'deny' | 'ask',
    message?: string
  ): Promise<void> {
    await this.request('/v1/permissions/response', {
      method: 'POST',
      body: JSON.stringify({
        request_id: requestId,
        decision,
        message,
        session_id: this.sessionId,
      }),
    });
  }

  private manualDisconnect = false;

  // WebSocket connection
  connectWebSocket(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    // Don't reconnect if manually disconnected or max attempts reached
    if (this.manualDisconnect || this.wsReconnectAttempts >= this.maxWsReconnectAttempts) {
      return;
    }

    const wsUrl = this.config.baseURL.replace('http', 'ws') + '/ws/tasks/updates';
    const url = this.sessionId 
      ? `${wsUrl}?session_id=${this.sessionId}` 
      : wsUrl;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.wsReconnectAttempts = 0;
      this.connectionHandlers.forEach(h => h(true));
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle task updates
        if (data.event_type) {
          this.taskHandlers.forEach(h => h(data as TaskUpdate));
        }
        
        // Handle messages
        if (data.type && ['user', 'assistant', 'tool_use', 'tool_result', 'thinking', 'system'].includes(data.type)) {
          this.messageHandlers.forEach(h => h(data as Message));
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      this.connectionHandlers.forEach(h => h(false));
      // Only attempt reconnect if not manually disconnected
      if (!this.manualDisconnect) {
        this.attemptReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.connectionHandlers.forEach(h => h(false));
    };
  }

  // Send message via WebSocket
  sendMessage(message: Message): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      throw new Error('WebSocket not connected');
    }
  }

  // Attempt to reconnect WebSocket
  private attemptReconnect(): void {
    if (this.manualDisconnect) {
      return;
    }

    if (this.wsReconnectAttempts >= this.maxWsReconnectAttempts) {
      console.error('Max WebSocket reconnection attempts reached');
      return;
    }

    this.wsReconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.wsReconnectAttempts), 30000);
    
    console.log(`Attempting WebSocket reconnect ${this.wsReconnectAttempts}/${this.maxWsReconnectAttempts} in ${delay}ms...`);
    
    setTimeout(() => {
      this.connectWebSocket();
    }, delay);
  }

  // Disconnect WebSocket
  disconnect(): void {
    this.manualDisconnect = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  // Subscribe to messages
  onMessage(handler: (message: Message) => void): () => void {
    this.messageHandlers.push(handler);
    return () => {
      const index = this.messageHandlers.indexOf(handler);
      if (index > -1) {
        this.messageHandlers.splice(index, 1);
      }
    };
  }

  // Subscribe to task updates
  onTaskUpdate(handler: (update: TaskUpdate) => void): () => void {
    this.taskHandlers.push(handler);
    return () => {
      const index = this.taskHandlers.indexOf(handler);
      if (index > -1) {
        this.taskHandlers.splice(index, 1);
      }
    };
  }

  // Subscribe to connection status
  onConnectionChange(handler: (connected: boolean) => void): () => void {
    this.connectionHandlers.push(handler);
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index > -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }

  // Check if connected
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Create singleton instance
let apiClient: MindFlowAPIClient | null = null;

export function getAPIClient(config?: Partial<APIClientConfig>): MindFlowAPIClient {
  if (!apiClient) {
    apiClient = new MindFlowAPIClient(config);
  }
  return apiClient;
}

export function resetAPIClient(): void {
  apiClient = null;
}

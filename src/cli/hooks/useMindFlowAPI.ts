/**
 * useMindFlowAPI - React hook for MindFlow API integration
 * Provides real backend connectivity with streaming support
 */

import { useEffect, useCallback, useRef, useState } from 'react';
import { getAPIClient, MindFlowAPIClient } from '../core/APIClient.js';
import { useMessageStore } from '../core/MessageStore.js';
import type { Message, UserMessage, SessionState } from '../types/protocol.js';

export interface UseMindFlowAPIOptions {
  autoConnect?: boolean;
  onMessage?: (message: Message) => void;
  onError?: (error: Error) => void;
  onControlRequest?: (request: import('../types/protocol.js').ControlRequest) => void;
}

export interface UseMindFlowAPIReturn {
  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  sessionId: string | null;
  
  // Actions
  connect: () => Promise<void>;
  disconnect: () => void;
  sendMessage: (content: string, options?: {
    model?: string;
    provider?: string;
    attachments?: Array<{ type: 'file' | 'image' | 'context'; name: string; content?: string }>;
  }) => Promise<void>;
  executeCommand: (commandName: string, args: string[]) => Promise<void>;
  sendPermissionResponse: (requestId: string, decision: 'allow' | 'deny' | 'ask') => Promise<void>;
  
  // Session management
  sessionState: SessionState | null;
  refreshSession: () => Promise<void>;
  
  // Available options
  availableCommands: Array<{ name: string; description: string; aliases: string[] }>;
  availableProviders: Array<{ provider_id: string; name: string; models: string[] }>;
  availableAgents: Array<{ id: string; name: string; description: string }>;
  
  // Permission handling
  onControlRequest?: (request: import('../types/protocol.js').ControlRequest) => void;
}

export function useMindFlowAPI(options: UseMindFlowAPIOptions = {}): UseMindFlowAPIReturn {
  const { autoConnect = true, onMessage, onError, onControlRequest } = options;
  
  const clientRef = useRef<MindFlowAPIClient>(getAPIClient());
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [availableCommands, setAvailableCommands] = useState<Array<{ name: string; description: string; aliases: string[] }>>([]);
  const [availableProviders, setAvailableProviders] = useState<Array<{ provider_id: string; name: string; models: string[] }>>([]);
  const [availableAgents, setAvailableAgents] = useState<Array<{ id: string; name: string; description: string }>>([]);
  
  const {
    addMessage,
    setLoading,
    updateSession,
    startToolUse,
    completeToolUse,
    addProgressMessage,
  } = useMessageStore();

  // Ref to track if connection is in progress
  const connectionAttemptRef = useRef(false);

  // Connect to backend
  const connect = useCallback(async () => {
    if (connectionAttemptRef.current || isConnected) return;
    
    connectionAttemptRef.current = true;
    setIsConnecting(true);
    
    try {
      // Initialize session
      const session = await clientRef.current.initSession();
      setSessionId(session);
      
      // Connect WebSocket
      clientRef.current.connectWebSocket();
      
      // Load available resources
      const [commands, providers, agents] = await Promise.all([
        clientRef.current.listCommands(),
        clientRef.current.listProviders().then(r => r.providers).catch(() => []),
        clientRef.current.listAgents().then(r => r.agents).catch(() => []),
      ]);
      
      setAvailableCommands(commands);
      setAvailableProviders(providers);
      setAvailableAgents(agents.map(a => ({ id: a.id, name: a.name, description: a.description })));
      
      // Get session status
      const status = await clientRef.current.getSessionStatus();
      setSessionState(status);
      updateSession(status);
      
    } catch (error) {
      console.error('Failed to connect:', error);
      onError?.(error as Error);
    } finally {
      setIsConnecting(false);
      connectionAttemptRef.current = false;
    }
  }, [isConnected, onError]);

  // Disconnect
  const disconnect = useCallback(() => {
    clientRef.current.disconnect();
    setIsConnected(false);
  }, []);

  // Send message to LLM
  const sendMessage = useCallback(async (
    content: string,
    messageOptions: {
      model?: string;
      provider?: string;
      attachments?: Array<{ type: 'file' | 'image' | 'context'; name: string; content?: string }>;
    } = {}
  ) => {
    if (!isConnected) {
      throw new Error('Not connected to backend');
    }

    // Add user message locally
    const userMessage: UserMessage = {
      type: 'user',
      content,
      timestamp: Date.now(),
      uuid: crypto.randomUUID(),
      parent_tool_use_id: null,
      attachments: messageOptions.attachments,
      session_id: sessionId || undefined,
    };
    
    addMessage(userMessage);
    setLoading(true);

    try {
      // Send via API
      await clientRef.current.chat(content, {
        ...messageOptions,
        stream: true,
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      setLoading(false);
      onError?.(error as Error);
      throw error;
    }
  }, [isConnected, sessionId, addMessage, setLoading, onError]);

  // Execute command
  const executeCommand = useCallback(async (commandName: string, args: string[]) => {
    if (!isConnected) {
      throw new Error('Not connected to backend');
    }

    // Add system message showing command execution
    addMessage({
      type: 'system',
      subtype: 'info',
      content: `Executing command: /${commandName} ${args.join(' ')}`,
      timestamp: Date.now(),
      uuid: crypto.randomUUID(),
      session_id: sessionId || undefined,
    });

    setLoading(true);

    try {
      const result = await clientRef.current.executeCommand(commandName, args);
      
      // Add result message
      addMessage({
        type: 'system',
        subtype: result.success ? 'status' : 'error',
        content: result.message,
        timestamp: Date.now(),
        uuid: crypto.randomUUID(),
        metadata: result.data,
        session_id: sessionId || undefined,
      });
    } catch (error) {
      console.error('Command execution failed:', error);
      addMessage({
        type: 'system',
        subtype: 'error',
        content: `Command failed: ${(error as Error).message}`,
        timestamp: Date.now(),
        uuid: crypto.randomUUID(),
        session_id: sessionId || undefined,
      });
      onError?.(error as Error);
    } finally {
      setLoading(false);
    }
  }, [isConnected, sessionId, addMessage, setLoading, onError]);

  // Refresh session state
  const refreshSession = useCallback(async () => {
    if (!isConnected) return;
    
    try {
      const status = await clientRef.current.getSessionStatus();
      setSessionState(status);
      updateSession(status);
    } catch (error) {
      console.error('Failed to refresh session:', error);
    }
  }, [isConnected, updateSession]);

  // Send permission response
  const sendPermissionResponse = useCallback(async (
    requestId: string,
    decision: 'allow' | 'deny' | 'ask'
  ) => {
    try {
      await clientRef.current.sendPermissionResponse(requestId, decision);
    } catch (error) {
      console.error('Failed to send permission response:', error);
      onError?.(error as Error);
      throw error;
    }
  }, [onError]);

  // Setup WebSocket handlers
  useEffect(() => {
    const client = clientRef.current;
    
    // Handle incoming messages
    const unsubscribeMessage = client.onMessage((message) => {
      addMessage(message);
      
      // Handle specific message types
      if (message.type === 'assistant') {
        setLoading(false);
      } else if (message.type === 'tool_use') {
        startToolUse(message);
      } else if (message.type === 'tool_result') {
        completeToolUse(message);
      } else if (message.type === 'progress') {
        addProgressMessage(message);
      } else if (message.type === 'control_request') {
        onControlRequest?.(message as import('../types/protocol.js').ControlRequest);
      }
      
      onMessage?.(message);
    });

    // Handle connection changes
    const unsubscribeConnection = client.onConnectionChange((connected) => {
      setIsConnected(connected);
    });

    // Handle task updates
    const unsubscribeTasks = client.onTaskUpdate((update) => {
      console.log('Task update:', update);
      // Could update task-related state here
    });

    return () => {
      unsubscribeMessage();
      unsubscribeConnection();
      unsubscribeTasks();
    };
  }, [addMessage, setLoading, startToolUse, completeToolUse, addProgressMessage, onMessage, onControlRequest]);

  // Auto-connect on mount - only once
  const hasConnectedRef = useRef(false);
  useEffect(() => {
    if (autoConnect && !hasConnectedRef.current) {
      hasConnectedRef.current = true;
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, []); // Empty deps - only run on mount

  return {
    isConnected,
    isConnecting,
    sessionId,
    connect,
    disconnect,
    sendMessage,
    executeCommand,
    sendPermissionResponse,
    sessionState,
    refreshSession,
    availableCommands,
    availableProviders,
    availableAgents,
  };
}

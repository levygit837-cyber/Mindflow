import WebSocket from 'ws';
import { useAppStore } from '../state/store.js';

const WS_URL = process.env.MINDFLOW_WS_URL || 'ws://localhost:8000/ws';

let ws: WebSocket | null = null;
let reconnectTimeout: NodeJS.Timeout | null = null;

export function connectWebSocket() {
  const { updateAgent, addMessage, startToolCall, completeToolCall, setConnectionStatus } =
    useAppStore.getState();

  if (ws?.readyState === WebSocket.OPEN) {
    return;
  }

  setConnectionStatus('reconnecting');

  ws = new WebSocket(WS_URL);

  ws.on('open', () => {
    setConnectionStatus('connected');
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
  });

  ws.on('message', (data: Buffer) => {
    try {
      const event = JSON.parse(data.toString());
      handleWebSocketEvent(event);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  });

  ws.on('close', () => {
    setConnectionStatus('disconnected');
    // Reconnect after 5 seconds
    reconnectTimeout = setTimeout(() => {
      connectWebSocket();
    }, 5000);
  });

  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
    setConnectionStatus('disconnected');
  });
}

function handleWebSocketEvent(event: any) {
  const { updateAgent, addMessage, startToolCall, completeToolCall } =
    useAppStore.getState();

  switch (event.type) {
    case 'agent_status':
      updateAgent(event.agentId, {
        id: event.agentId,
        name: event.agentName || event.agentId,
        status: event.status,
        currentTool: event.currentTool,
        progress: event.progress,
      });
      break;

    case 'agent_message':
      addMessage({
        id: event.id || Date.now().toString(),
        type: 'agent',
        content: event.content,
        timestamp: event.timestamp || Date.now(),
        agentId: event.agentId,
        agentName: event.agentName,
      });
      break;

    case 'tool_call_start':
      startToolCall({
        id: event.toolCallId,
        name: event.toolName,
        status: 'running',
        startTime: event.timestamp || Date.now(),
        agentId: event.agentId,
      });
      updateAgent(event.agentId, {
        currentTool: event.toolName,
        status: 'executing',
      });
      break;

    case 'tool_call_complete':
      completeToolCall(event.toolCallId, event.output, event.error);
      updateAgent(event.agentId, {
        currentTool: undefined,
        status: event.error ? 'error' : 'thinking',
      });
      break;

    case 'assistant_message':
      addMessage({
        id: event.id || Date.now().toString(),
        type: 'assistant',
        content: event.content,
        timestamp: event.timestamp || Date.now(),
      });
      break;

    case 'system_message':
      addMessage({
        id: event.id || Date.now().toString(),
        type: 'system',
        content: event.content,
        timestamp: event.timestamp || Date.now(),
      });
      break;
  }
}

export function disconnectWebSocket() {
  if (ws) {
    ws.close();
    ws = null;
  }
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
}

export function sendWebSocketMessage(message: any) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
}

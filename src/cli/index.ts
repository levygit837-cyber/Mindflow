// Export all core modules
export { StructuredIO, MessageStream, createStructuredIO } from './core/StructuredIO.js';
export { 
  useMessageStore, 
  useMessages, 
  useVisibleRange,
  useInProgressToolUseIDs,
  useAgents,
  useSession,
  useIsLoading,
  useExpandedView,
  useConnectionStatus,
  useSelectedMessageIndex,
  useInputValue,
  type MessageStore,
  type MessageStoreActions
} from './core/MessageStore.js';

// Export types (as types to avoid naming conflicts)
export type {
  Message,
  UserMessage,
  AssistantMessage,
  ThinkingMessage,
  ToolUseMessage,
  ToolResultMessage,
  SystemMessage,
  ProgressMessage,
  ControlRequest,
  ControlResponse,
  AppState,
  SessionState,
  Agent,
  Tool,
  RenderableMessage,
} from './types/protocol.js';

// Export components (they have different names from types)
export * from './components/index.js';

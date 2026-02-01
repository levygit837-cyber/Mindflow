/**
 * Core type definitions for OmniMind Backend
 *
 * This file contains shared types, interfaces, and enums used throughout the application.
 */

import { BaseMessage } from "@langchain/core/messages";

// ============================================================================
// Agent Types
// ============================================================================

/**
 * Agent execution modes
 */
export enum AgentMode {
  CHAT = 'chat',
  ANALYSIS = 'analysis',
  TASK = 'task',
  RESEARCH = 'research',
}

/**
 * Agent state interface for LangGraph workflows
 */
export interface AgentState {
  messages: BaseMessage[];
  currentStep: string;
  context?: Record<string, any>;
  error?: string;
  metadata?: AgentMetadata;
}

/**
 * Agent metadata for tracking execution
 */
export interface AgentMetadata {
  sessionId?: string;
  userId?: string;
  startTime?: string;
  endTime?: string;
  duration?: number;
  tokensUsed?: number;
  model?: string;
}

/**
 * Agent configuration options
 */
export interface AgentConfig {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  frequencyPenalty?: number;
  presencePenalty?: number;
  stream?: boolean;
  tools?: AgentTool[];
}

/**
 * Agent tool definition
 */
export interface AgentTool {
  name: string;
  description: string;
  parameters: Record<string, any>;
  execute: (input: any) => Promise<any>;
}

// ============================================================================
// API Types
// ============================================================================

/**
 * Standard API response wrapper
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
  metadata?: ResponseMetadata;
}

/**
 * API error structure
 */
export interface ApiError {
  code: string;
  message: string;
  details?: any;
  timestamp?: string;
}

/**
 * Response metadata
 */
export interface ResponseMetadata {
  timestamp: string;
  requestId?: string;
  duration?: number;
}

/**
 * Pagination parameters
 */
export interface PaginationParams {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  items: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// ============================================================================
// Chat Types
// ============================================================================

/**
 * Chat message role
 */
export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
  FUNCTION = 'function',
}

/**
 * Chat message interface
 */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

/**
 * Chat session interface
 */
export interface ChatSession {
  id: string;
  userId?: string;
  title?: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, any>;
}

/**
 * Chat request payload
 */
export interface ChatRequest {
  message: string;
  sessionId?: string;
  options?: AgentConfig;
}

/**
 * Chat response payload
 */
export interface ChatResponse {
  message: ChatMessage;
  sessionId: string;
  metadata?: {
    model: string;
    tokensUsed?: number;
    processingTime?: number;
  };
}

// ============================================================================
// User Types
// ============================================================================

/**
 * User role enumeration
 */
export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  GUEST = 'guest',
}

/**
 * User interface
 */
export interface User {
  id: string;
  email: string;
  username: string;
  role: UserRole;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, any>;
}

/**
 * User authentication credentials
 */
export interface AuthCredentials {
  email: string;
  password: string;
}

/**
 * JWT payload interface
 */
export interface JwtPayload {
  userId: string;
  email: string;
  role: UserRole;
  iat?: number;
  exp?: number;
}

/**
 * Authentication response
 */
export interface AuthResponse {
  user: Omit<User, 'password'>;
  token: string;
  refreshToken?: string;
  expiresIn: number;
}

// ============================================================================
// Tool Types
// ============================================================================

/**
 * Tool execution result
 */
export interface ToolResult {
  success: boolean;
  data?: any;
  error?: string;
  metadata?: Record<string, any>;
}

/**
 * Tool definition for LangChain
 */
export interface ToolDefinition {
  name: string;
  description: string;
  schema: Record<string, any>;
}

// ============================================================================
// Database Types
// ============================================================================

/**
 * Base model interface with common fields
 */
export interface BaseModel {
  id: string;
  createdAt: string;
  updatedAt: string;
  deletedAt?: string;
}

/**
 * Query filter options
 */
export interface QueryFilter {
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'nin' | 'contains';
  value: any;
}

/**
 * Query options
 */
export interface QueryOptions {
  filters?: QueryFilter[];
  sort?: { field: string; order: 'asc' | 'desc' }[];
  pagination?: PaginationParams;
  select?: string[];
}

// ============================================================================
// Event Types
// ============================================================================

/**
 * Event types for system events
 */
export enum EventType {
  AGENT_START = 'agent.start',
  AGENT_COMPLETE = 'agent.complete',
  AGENT_ERROR = 'agent.error',
  MESSAGE_RECEIVED = 'message.received',
  MESSAGE_SENT = 'message.sent',
  USER_LOGIN = 'user.login',
  USER_LOGOUT = 'user.logout',
}

/**
 * System event interface
 */
export interface SystemEvent {
  type: EventType;
  timestamp: string;
  data: any;
  metadata?: Record<string, any>;
}

// ============================================================================
// Streaming Types
// ============================================================================

/**
 * Streaming chunk for SSE
 */
export interface StreamChunk<T = any> {
  type: 'data' | 'error' | 'complete';
  data?: T;
  error?: string;
  metadata?: Record<string, any>;
}

/**
 * Stream options
 */
export interface StreamOptions {
  bufferSize?: number;
  timeout?: number;
  onChunk?: (chunk: StreamChunk) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * Environment type
 */
export type Environment = 'development' | 'production' | 'test';

/**
 * Log level type
 */
export type LogLevel = 'error' | 'warn' | 'info' | 'http' | 'verbose' | 'debug' | 'silly';

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Make all properties optional recursively
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/**
 * Make all properties required recursively
 */
export type DeepRequired<T> = {
  [P in keyof T]-?: T[P] extends object ? DeepRequired<T[P]> : T[P];
};

/**
 * Extract keys of type T that have value type V
 */
export type KeysOfType<T, V> = {
  [K in keyof T]: T[K] extends V ? K : never;
}[keyof T];

/**
 * Promise or value type
 */
export type MaybePromise<T> = T | Promise<T>;

/**
 * Async function type
 */
export type AsyncFunction<TArgs extends any[] = any[], TReturn = any> = (
  ...args: TArgs
) => Promise<TReturn>;

// ============================================================================
// Validation Types
// ============================================================================

/**
 * Validation error
 */
export interface ValidationError {
  field: string;
  message: string;
  value?: any;
}

/**
 * Validation result
 */
export interface ValidationResult {
  valid: boolean;
  errors?: ValidationError[];
}

// ============================================================================
// Export all types
// ============================================================================

export type {
  BaseMessage,
};

/**
 * Common utility types shared across all domains.
 */

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
  timestamp?: string;
}

export interface ResponseMetadata {
  timestamp: string;
  requestId?: string;
  duration?: number;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ApiError;
  metadata?: ResponseMetadata;
}

export interface PaginationParams {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

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
// Streaming Types
// ============================================================================

export interface StreamChunk<T = unknown> {
  type: "data" | "error" | "complete";
  data?: T;
  error?: string;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Utility Types
// ============================================================================

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type DeepRequired<T> = {
  [P in keyof T]-?: T[P] extends object ? DeepRequired<T[P]> : T[P];
};

export type MaybePromise<T> = T | Promise<T>;

export type AsyncFunction<TArgs extends unknown[] = unknown[], TReturn = unknown> = (
  ...args: TArgs
) => Promise<TReturn>;

export type Environment = "development" | "production" | "test";

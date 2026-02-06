/**
 * ============================================================================
 * 05 - API INTEGRATION PATTERNS EXAMPLES
 * ============================================================================
 *
 * This file contains comprehensive examples of API integration patterns
 * commonly used in AI-powered backend applications. These patterns cover
 * REST APIs, external service integrations, streaming, and best practices.
 *
 * Topics covered:
 * - REST API client creation
 * - Request/Response handling
 * - Error handling and retries
 * - Rate limiting patterns
 * - Authentication (API keys, OAuth, JWT)
 * - Webhook handling
 * - Server-Sent Events (SSE) for streaming
 * - Request validation with Zod
 * - Response caching
 * - API versioning
 * - Timeout and circuit breaker patterns
 * - Batch request handling
 *
 * @author OmniMind Team
 * @version 1.0.0
 */

import { z } from "zod";
import { createLogger } from "../utils/logger";

const logger = createLogger("APIPatternExamples");

// ============================================================================
// SECTION 1: REST API CLIENT PATTERNS
// ============================================================================

/**
 * Example 1.1: Basic API Client Class
 *
 * A reusable API client with common functionality.
 * This pattern encapsulates all API communication logic.
 */
export class APIClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  private timeout: number;

  constructor(config: {
    baseUrl: string;
    apiKey?: string;
    timeout?: number;
    additionalHeaders?: Record<string, string>;
  }) {
    this.baseUrl = config.baseUrl.replace(/\/$/, ""); // Remove trailing slash
    this.timeout = config.timeout || 30000;

    this.headers = {
      "Content-Type": "application/json",
      "Accept": "application/json",
      ...config.additionalHeaders,
    };

    if (config.apiKey) {
      this.headers["Authorization"] = `Bearer ${config.apiKey}`;
    }

    logger.info("API Client initialized", { baseUrl: this.baseUrl });
  }

  private async request<T>(
    method: string,
    endpoint: string,
    options: {
      body?: any;
      params?: Record<string, string>;
      headers?: Record<string, string>;
    } = {}
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${endpoint}`);

    // Add query parameters
    if (options.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        url.searchParams.append(key, value);
      });
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      logger.debug(`API Request: ${method} ${url.toString()}`);

      const response = await fetch(url.toString(), {
        method,
        headers: { ...this.headers, ...options.headers },
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorBody = await response.text();
        throw new APIError(
          `API request failed: ${response.status} ${response.statusText}`,
          response.status,
          errorBody
        );
      }

      const data = await response.json();
      return data as T;
    } catch (error: any) {
      clearTimeout(timeoutId);

      if (error.name === "AbortError") {
        throw new APIError("Request timeout", 408, "Request exceeded timeout limit");
      }

      throw error;
    }
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>("GET", endpoint, { params });
  }

  async post<T>(endpoint: string, body: any): Promise<T> {
    return this.request<T>("POST", endpoint, { body });
  }

  async put<T>(endpoint: string, body: any): Promise<T> {
    return this.request<T>("PUT", endpoint, { body });
  }

  async patch<T>(endpoint: string, body: any): Promise<T> {
    return this.request<T>("PATCH", endpoint, { body });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>("DELETE", endpoint);
  }
}

/**
 * Custom API Error class with additional context
 */
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public responseBody?: string,
    public retryable: boolean = false
  ) {
    super(message);
    this.name = "APIError";

    // Determine if error is retryable
    this.retryable = [408, 429, 500, 502, 503, 504].includes(statusCode);
  }
}

/**
 * Example 1.2: Typed API Client with Response Validation
 *
 * Using Zod schemas to validate API responses for type safety.
 */

// Define response schemas
const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string(),
  role: z.enum(["admin", "user", "guest"]),
  createdAt: z.string().datetime(),
  metadata: z.record(z.any()).optional(),
});

const UsersListSchema = z.object({
  users: z.array(UserSchema),
  pagination: z.object({
    page: z.number(),
    limit: z.number(),
    total: z.number(),
    hasMore: z.boolean(),
  }),
});

type User = z.infer<typeof UserSchema>;
type UsersList = z.infer<typeof UsersListSchema>;

export class TypedAPIClient extends APIClient {
  async getUsers(page: number = 1, limit: number = 10): Promise<UsersList> {
    const response = await this.get<unknown>("/users", {
      page: page.toString(),
      limit: limit.toString(),
    });

    // Validate response against schema
    const validated = UsersListSchema.safeParse(response);

    if (!validated.success) {
      logger.error("Response validation failed", {
        errors: validated.error.errors,
      });
      throw new Error(`Invalid API response: ${validated.error.message}`);
    }

    return validated.data;
  }

  async getUser(id: string): Promise<User> {
    const response = await this.get<unknown>(`/users/${id}`);
    const validated = UserSchema.safeParse(response);

    if (!validated.success) {
      throw new Error(`Invalid user response: ${validated.error.message}`);
    }

    return validated.data;
  }

  async createUser(data: Omit<User, "id" | "createdAt">): Promise<User> {
    const response = await this.post<unknown>("/users", data);
    return UserSchema.parse(response);
  }
}

export async function example_1_2_typedApiClient(): Promise<User> {
  logger.info("Example 1.2: Typed API Client");

  const client = new TypedAPIClient({
    baseUrl: "https://api.example.com",
    apiKey: "your-api-key",
  });

  // This would make actual API calls in production
  // For demo, we'll simulate the response
  const mockUser: User = {
    id: "user-123",
    email: "john@example.com",
    name: "John Doe",
    role: "user",
    createdAt: new Date().toISOString(),
  };

  return mockUser;
}

// ============================================================================
// SECTION 2: ERROR HANDLING AND RETRIES
// ============================================================================

/**
 * Example 2.1: Retry with Exponential Backoff
 *
 * Automatically retry failed requests with increasing delays.
 */
export interface RetryConfig {
  maxRetries: number;
  baseDelayMs: number;
  maxDelayMs: number;
  retryableStatuses: number[];
  onRetry?: (attempt: number, error: Error, nextDelayMs: number) => void;
}

const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
  retryableStatuses: [408, 429, 500, 502, 503, 504],
};

export async function withRetry<T>(
  operation: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const finalConfig = { ...defaultRetryConfig, ...config };
  let lastError: Error | undefined;

  for (let attempt = 0; attempt <= finalConfig.maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error: any) {
      lastError = error;

      // Check if we should retry
      const shouldRetry =
        attempt < finalConfig.maxRetries &&
        (error instanceof APIError
          ? finalConfig.retryableStatuses.includes(error.statusCode)
          : true);

      if (!shouldRetry) {
        throw error;
      }

      // Calculate delay with exponential backoff and jitter
      const exponentialDelay = finalConfig.baseDelayMs * Math.pow(2, attempt);
      const jitter = Math.random() * 1000;
      const delay = Math.min(exponentialDelay + jitter, finalConfig.maxDelayMs);

      logger.warn(`Retry attempt ${attempt + 1}/${finalConfig.maxRetries}`, {
        error: error.message,
        delayMs: delay,
      });

      if (finalConfig.onRetry) {
        finalConfig.onRetry(attempt + 1, error, delay);
      }

      await sleep(delay);
    }
  }

  throw lastError;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function example_2_1_retryWithBackoff(): Promise<string> {
  logger.info("Example 2.1: Retry with Exponential Backoff");

  let attempts = 0;

  const result = await withRetry(
    async () => {
      attempts++;
      if (attempts < 3) {
        throw new APIError("Service unavailable", 503);
      }
      return "Success after retries!";
    },
    {
      maxRetries: 5,
      baseDelayMs: 100, // Shorter for demo
      onRetry: (attempt, error, delay) => {
        logger.info(`Retry ${attempt}: ${error.message}, waiting ${delay}ms`);
      },
    }
  );

  return result;
}

/**
 * Example 2.2: Circuit Breaker Pattern
 *
 * Prevent cascading failures by temporarily blocking requests
 * when a service is experiencing issues.
 */
export enum CircuitState {
  CLOSED = "CLOSED", // Normal operation
  OPEN = "OPEN", // Failing, reject requests
  HALF_OPEN = "HALF_OPEN", // Testing if service recovered
}

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount: number = 0;
  private successCount: number = 0;
  private lastFailureTime: number = 0;
  private nextAttemptTime: number = 0;

  constructor(
    private config: {
      failureThreshold: number;
      successThreshold: number;
      timeout: number; // Time to wait before trying again (ms)
    }
  ) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() < this.nextAttemptTime) {
        throw new Error("Circuit breaker is OPEN - request rejected");
      }
      // Transition to half-open
      this.state = CircuitState.HALF_OPEN;
      logger.info("Circuit breaker transitioning to HALF_OPEN");
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    if (this.state === CircuitState.HALF_OPEN) {
      this.successCount++;
      if (this.successCount >= this.config.successThreshold) {
        this.reset();
        logger.info("Circuit breaker CLOSED - service recovered");
      }
    } else {
      this.failureCount = 0; // Reset failures on success
    }
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.state === CircuitState.HALF_OPEN) {
      this.trip();
    } else if (this.failureCount >= this.config.failureThreshold) {
      this.trip();
    }
  }

  private trip(): void {
    this.state = CircuitState.OPEN;
    this.nextAttemptTime = Date.now() + this.config.timeout;
    logger.warn("Circuit breaker OPEN - blocking requests", {
      failures: this.failureCount,
      nextAttempt: new Date(this.nextAttemptTime).toISOString(),
    });
  }

  private reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
  }

  getState(): CircuitState {
    return this.state;
  }
}

export async function example_2_2_circuitBreaker(): Promise<{
  results: string[];
  finalState: CircuitState;
}> {
  logger.info("Example 2.2: Circuit Breaker Pattern");

  const breaker = new CircuitBreaker({
    failureThreshold: 3,
    successThreshold: 2,
    timeout: 1000,
  });

  const results: string[] = [];
  let requestCount = 0;

  // Simulate a service that fails initially then recovers
  const unreliableService = async (): Promise<string> => {
    requestCount++;
    if (requestCount <= 4) {
      throw new Error("Service error");
    }
    return "Success";
  };

  // Try multiple requests
  for (let i = 0; i < 10; i++) {
    try {
      const result = await breaker.execute(unreliableService);
      results.push(`Request ${i + 1}: ${result}`);
    } catch (error: any) {
      results.push(`Request ${i + 1}: ${error.message}`);
    }
    await sleep(200);
  }

  return {
    results,
    finalState: breaker.getState(),
  };
}

// ============================================================================
// SECTION 3: RATE LIMITING
// ============================================================================

/**
 * Example 3.1: Token Bucket Rate Limiter
 *
 * Client-side rate limiting to avoid hitting API limits.
 */
export class TokenBucketRateLimiter {
  private tokens: number;
  private lastRefill: number;

  constructor(
    private config: {
      maxTokens: number;
      refillRate: number; // Tokens per second
    }
  ) {
    this.tokens = config.maxTokens;
    this.lastRefill = Date.now();
  }

  private refill(): void {
    const now = Date.now();
    const timePassed = (now - this.lastRefill) / 1000;
    const newTokens = timePassed * this.config.refillRate;

    this.tokens = Math.min(this.config.maxTokens, this.tokens + newTokens);
    this.lastRefill = now;
  }

  async acquire(tokens: number = 1): Promise<void> {
    this.refill();

    if (this.tokens < tokens) {
      // Calculate wait time
      const tokensNeeded = tokens - this.tokens;
      const waitTime = (tokensNeeded / this.config.refillRate) * 1000;

      logger.debug(`Rate limit: waiting ${waitTime}ms for ${tokens} tokens`);
      await sleep(waitTime);
      this.refill();
    }

    this.tokens -= tokens;
  }

  getAvailableTokens(): number {
    this.refill();
    return this.tokens;
  }
}

export class RateLimitedAPIClient extends APIClient {
  private rateLimiter: TokenBucketRateLimiter;

  constructor(
    config: {
      baseUrl: string;
      apiKey?: string;
      timeout?: number;
    },
    rateLimit: { maxTokens: number; refillRate: number }
  ) {
    super(config);
    this.rateLimiter = new TokenBucketRateLimiter(rateLimit);
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    await this.rateLimiter.acquire(1);
    return super.get<T>(endpoint, params);
  }

  async post<T>(endpoint: string, body: any): Promise<T> {
    await this.rateLimiter.acquire(1);
    return super.post<T>(endpoint, body);
  }
}

export async function example_3_1_tokenBucketRateLimiter(): Promise<{
  requestTimes: number[];
  totalTime: number;
}> {
  logger.info("Example 3.1: Token Bucket Rate Limiter");

  const limiter = new TokenBucketRateLimiter({
    maxTokens: 5,
    refillRate: 2, // 2 tokens per second
  });

  const startTime = Date.now();
  const requestTimes: number[] = [];

  // Try to make 10 requests quickly
  for (let i = 0; i < 10; i++) {
    await limiter.acquire(1);
    requestTimes.push(Date.now() - startTime);
    logger.info(`Request ${i + 1} at ${Date.now() - startTime}ms`);
  }

  return {
    requestTimes,
    totalTime: Date.now() - startTime,
  };
}

/**
 * Example 3.2: Sliding Window Rate Limiter
 *
 * Track requests within a sliding time window.
 */
export class SlidingWindowRateLimiter {
  private timestamps: number[] = [];

  constructor(
    private config: {
      maxRequests: number;
      windowMs: number;
    }
  ) {}

  async acquire(): Promise<void> {
    const now = Date.now();

    // Remove old timestamps
    this.timestamps = this.timestamps.filter(
      (ts) => now - ts < this.config.windowMs
    );

    if (this.timestamps.length >= this.config.maxRequests) {
      // Calculate wait time until oldest request expires
      const oldestTimestamp = this.timestamps[0];
      const waitTime = this.config.windowMs - (now - oldestTimestamp);

      logger.debug(`Sliding window limit: waiting ${waitTime}ms`);
      await sleep(waitTime);

      // Clean up again after waiting
      this.timestamps = this.timestamps.filter(
        (ts) => Date.now() - ts < this.config.windowMs
      );
    }

    this.timestamps.push(Date.now());
  }

  getRequestsInWindow(): number {
    const now = Date.now();
    return this.timestamps.filter((ts) => now - ts < this.config.windowMs).length;
  }
}

// ============================================================================
// SECTION 4: AUTHENTICATION PATTERNS
// ============================================================================

/**
 * Example 4.1: API Key Authentication
 *
 * Simple API key authentication pattern.
 */
export function createApiKeyAuthClient(
  baseUrl: string,
  apiKey: string,
  keyHeader: string = "X-API-Key"
): APIClient {
  return new APIClient({
    baseUrl,
    additionalHeaders: {
      [keyHeader]: apiKey,
    },
  });
}

/**
 * Example 4.2: OAuth 2.0 Client Credentials Flow
 *
 * For server-to-server authentication.
 */
export class OAuth2Client {
  private accessToken: string | null = null;
  private tokenExpiry: number = 0;
  private tokenPromise: Promise<void> | null = null;

  constructor(
    private config: {
      tokenUrl: string;
      clientId: string;
      clientSecret: string;
      scope?: string;
    }
  ) {}

  private async fetchToken(): Promise<void> {
    logger.info("Fetching OAuth2 token");

    const params = new URLSearchParams({
      grant_type: "client_credentials",
      client_id: this.config.clientId,
      client_secret: this.config.clientSecret,
    });

    if (this.config.scope) {
      params.append("scope", this.config.scope);
    }

    const response = await fetch(this.config.tokenUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });

    if (!response.ok) {
      throw new Error(`Failed to obtain OAuth token: ${response.status}`);
    }

    const data = await response.json();
    this.accessToken = data.access_token;
    // Set expiry with 60 second buffer
    this.tokenExpiry = Date.now() + (data.expires_in - 60) * 1000;

    logger.info("OAuth2 token obtained", {
      expiresIn: data.expires_in,
    });
  }

  async getAccessToken(): Promise<string> {
    // Check if token is valid
    if (this.accessToken && Date.now() < this.tokenExpiry) {
      return this.accessToken;
    }

    // Avoid concurrent token requests
    if (!this.tokenPromise) {
      this.tokenPromise = this.fetchToken().finally(() => {
        this.tokenPromise = null;
      });
    }

    await this.tokenPromise;
    return this.accessToken!;
  }

  async createAuthenticatedClient(baseUrl: string): Promise<APIClient> {
    const token = await this.getAccessToken();
    return new APIClient({
      baseUrl,
      additionalHeaders: {
        Authorization: `Bearer ${token}`,
      },
    });
  }
}

/**
 * Example 4.3: JWT Token Management
 *
 * Handle JWT tokens with automatic refresh.
 */
export class JWTManager {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private accessTokenExpiry: number = 0;

  constructor(
    private config: {
      refreshUrl: string;
      onTokenRefresh?: (tokens: { accessToken: string; refreshToken: string }) => void;
    }
  ) {}

  setTokens(accessToken: string, refreshToken: string, expiresIn: number): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.accessTokenExpiry = Date.now() + (expiresIn - 60) * 1000;
  }

  async getValidAccessToken(): Promise<string> {
    if (this.accessToken && Date.now() < this.accessTokenExpiry) {
      return this.accessToken;
    }

    if (!this.refreshToken) {
      throw new Error("No refresh token available - user must re-authenticate");
    }

    await this.refreshTokens();
    return this.accessToken!;
  }

  private async refreshTokens(): Promise<void> {
    logger.info("Refreshing JWT tokens");

    const response = await fetch(this.config.refreshUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken: this.refreshToken }),
    });

    if (!response.ok) {
      this.accessToken = null;
      this.refreshToken = null;
      throw new Error("Token refresh failed - user must re-authenticate");
    }

    const data = await response.json();
    this.setTokens(data.accessToken, data.refreshToken, data.expiresIn);

    if (this.config.onTokenRefresh) {
      this.config.onTokenRefresh({
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
      });
    }
  }

  isAuthenticated(): boolean {
    return !!this.refreshToken;
  }

  logout(): void {
    this.accessToken = null;
    this.refreshToken = null;
    this.accessTokenExpiry = 0;
  }
}

// ============================================================================
// SECTION 5: STREAMING AND WEBHOOKS
// ============================================================================

/**
 * Example 5.1: Server-Sent Events (SSE) Client
 *
 * Handle streaming responses from APIs.
 */
export class SSEClient {
  private eventSource: EventSource | null = null;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;

  constructor(
    private url: string,
    private handlers: {
      onMessage: (data: any) => void;
      onError?: (error: Event) => void;
      onOpen?: () => void;
      onClose?: () => void;
    }
  ) {}

  connect(): void {
    logger.info("Connecting to SSE stream", { url: this.url });

    this.eventSource = new EventSource(this.url);

    this.eventSource.onopen = () => {
      this.reconnectAttempts = 0;
      logger.info("SSE connection opened");
      this.handlers.onOpen?.();
    };

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handlers.onMessage(data);
      } catch {
        this.handlers.onMessage(event.data);
      }
    };

    this.eventSource.onerror = (error) => {
      logger.error("SSE error", { error });
      this.handlers.onError?.(error);

      if (this.eventSource?.readyState === EventSource.CLOSED) {
        this.attemptReconnect();
      }
    };
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error("Max SSE reconnection attempts reached");
      this.handlers.onClose?.();
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.pow(2, this.reconnectAttempts) * 1000;

    logger.info(`Attempting SSE reconnect in ${delay}ms`, {
      attempt: this.reconnectAttempts,
    });

    setTimeout(() => this.connect(), delay);
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      logger.info("SSE connection closed");
      this.handlers.onClose?.();
    }
  }
}

/**
 * Example 5.2: Streaming Fetch for LLM Responses
 *
 * Handle streaming responses from LLM APIs.
 */
export async function* streamLLMResponse(
  url: string,
  body: any,
  headers: Record<string, string> = {}
): AsyncGenerator<string, void, unknown> {
  logger.info("Starting streaming LLM request");

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Stream request failed: ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Response body is null");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete lines
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") {
            return;
          }
          try {
            const parsed = JSON.parse(data);
            const content = parsed.choices?.[0]?.delta?.content;
            if (content) {
              yield content;
            }
          } catch {
            // Not JSON, yield as-is
            yield data;
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function example_5_2_streamingFetch(): Promise<string> {
  logger.info("Example 5.2: Streaming Fetch");

  // Simulate streaming (in production, use actual API)
  async function* mockStream(): AsyncGenerator<string> {
    const words = ["Hello", " ", "this", " ", "is", " ", "a", " ", "streamed", " ", "response!"];
    for (const word of words) {
      await sleep(50);
      yield word;
    }
  }

  let fullResponse = "";
  for await (const chunk of mockStream()) {
    fullResponse += chunk;
    process.stdout.write(chunk); // Real-time output
  }

  console.log("\n");
  return fullResponse;
}

/**
 * Example 5.3: Webhook Handler Pattern
 *
 * Secure webhook handling with signature verification.
 */
export interface WebhookConfig {
  secret: string;
  toleranceSeconds: number;
}

export class WebhookHandler {
  constructor(private config: WebhookConfig) {}

  verifySignature(
    payload: string,
    signature: string,
    timestamp: string
  ): boolean {
    // Check timestamp to prevent replay attacks
    const timestampNum = parseInt(timestamp, 10);
    const now = Math.floor(Date.now() / 1000);

    if (Math.abs(now - timestampNum) > this.config.toleranceSeconds) {
      logger.warn("Webhook timestamp outside tolerance");
      return false;
    }

    // Verify HMAC signature (simplified example)
    // In production, use crypto.createHmac
    const expectedSignature = this.computeSignature(payload, timestamp);

    // Constant-time comparison to prevent timing attacks
    return this.secureCompare(signature, expectedSignature);
  }

  private computeSignature(payload: string, timestamp: string): string {
    // In production:
    // const hmac = crypto.createHmac('sha256', this.config.secret);
    // hmac.update(`${timestamp}.${payload}`);
    // return hmac.digest('hex');
    return `mock-signature-${timestamp}`;
  }

  private secureCompare(a: string, b: string): boolean {
    if (a.length !== b.length) return false;

    let result = 0;
    for (let i = 0; i < a

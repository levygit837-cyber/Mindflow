/**
 * ============================================================================
 * 07 - TYPESCRIPT PATTERNS AND BEST PRACTICES EXAMPLES
 * ============================================================================
 *
 * This file contains comprehensive examples of TypeScript patterns and best
 * practices for building robust, type-safe applications. These patterns are
 * essential for any professional TypeScript developer.
 *
 * Topics covered:
 * - Type inference and explicit types
 * - Generics and generic constraints
 * - Utility types (Partial, Pick, Omit, etc.)
 * - Discriminated unions
 * - Type guards and narrowing
 * - Mapped types
 * - Conditional types
 * - Template literal types
 * - Function overloads
 * - Class patterns
 * - Error handling patterns
 * - Builder pattern
 * - Factory pattern
 * - Repository pattern
 * - Dependency injection
 * - Async patterns
 *
 * @author OmniMind Team
 * @version 1.0.0
 */

import { createLogger } from "../utils/logger";

const logger = createLogger("TypeScriptPatternsExamples");

// ============================================================================
// SECTION 1: GENERICS
// ============================================================================

/**
 * Example 1.1: Basic Generics
 *
 * Generics allow you to write flexible, reusable functions and classes
 * that work with multiple types while maintaining type safety.
 */

// Generic function - works with any type
export function identity<T>(value: T): T {
  return value;
}

// Usage examples:
// const num = identity(42);        // T is inferred as number
// const str = identity("hello");   // T is inferred as string

// Generic function with multiple type parameters
export function pair<T, U>(first: T, second: U): [T, U] {
  return [first, second];
}

// Generic function with array
export function firstElement<T>(arr: T[]): T | undefined {
  return arr[0];
}

// Generic function that filters array
export function filterByType<T, U extends T>(
  arr: T[],
  predicate: (item: T) => item is U
): U[] {
  return arr.filter(predicate);
}

/**
 * Example 1.2: Generic Constraints
 *
 * Constraints limit what types can be used with a generic.
 */

// Constraint: T must have a 'length' property
interface HasLength {
  length: number;
}

export function logLength<T extends HasLength>(item: T): number {
  console.log(`Length: ${item.length}`);
  return item.length;
}

// Constraint: Key must be a key of T
export function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// Constraint with default type
export function createArray<T = string>(length: number, value: T): T[] {
  return Array(length).fill(value);
}

// Multiple constraints using intersection
interface Identifiable {
  id: string;
}

interface Timestamped {
  createdAt: Date;
  updatedAt: Date;
}

export function updateEntity<T extends Identifiable & Timestamped>(
  entity: T,
  updates: Partial<Omit<T, "id" | "createdAt">>
): T {
  return {
    ...entity,
    ...updates,
    updatedAt: new Date(),
  };
}

/**
 * Example 1.3: Generic Classes
 *
 * Classes can also be generic, allowing type-safe data structures.
 */

export class Stack<T> {
  private items: T[] = [];

  push(item: T): void {
    this.items.push(item);
  }

  pop(): T | undefined {
    return this.items.pop();
  }

  peek(): T | undefined {
    return this.items[this.items.length - 1];
  }

  isEmpty(): boolean {
    return this.items.length === 0;
  }

  size(): number {
    return this.items.length;
  }
}

// Generic class with constraint
export class KeyValueStore<K extends string | number, V> {
  private store = new Map<K, V>();

  set(key: K, value: V): void {
    this.store.set(key, value);
  }

  get(key: K): V | undefined {
    return this.store.get(key);
  }

  has(key: K): boolean {
    return this.store.has(key);
  }

  delete(key: K): boolean {
    return this.store.delete(key);
  }

  keys(): K[] {
    return Array.from(this.store.keys());
  }

  values(): V[] {
    return Array.from(this.store.values());
  }
}

// ============================================================================
// SECTION 2: UTILITY TYPES
// ============================================================================

/**
 * Example 2.1: Built-in Utility Types
 *
 * TypeScript provides many utility types for common transformations.
 */

// Base interface for examples
interface User {
  id: string;
  email: string;
  name: string;
  age: number;
  role: "admin" | "user" | "guest";
  createdAt: Date;
  metadata?: Record<string, unknown>;
}

// Partial<T> - All properties optional
type PartialUser = Partial<User>;
// { id?: string; email?: string; name?: string; ... }

// Required<T> - All properties required
type RequiredUser = Required<User>;
// All properties including metadata are required

// Readonly<T> - All properties readonly
type ReadonlyUser = Readonly<User>;
// { readonly id: string; readonly email: string; ... }

// Pick<T, K> - Select specific properties
type UserCredentials = Pick<User, "email" | "id">;
// { email: string; id: string; }

// Omit<T, K> - Exclude specific properties
type UserWithoutMetadata = Omit<User, "metadata" | "createdAt">;
// { id: string; email: string; name: string; age: number; role: ... }

// Record<K, T> - Object with keys K and values T
type UserRoles = Record<string, "admin" | "user" | "guest">;
// { [key: string]: "admin" | "user" | "guest" }

// Extract<T, U> - Extract types from T that are assignable to U
type StringOrNumber = string | number | boolean;
type OnlyStringOrNumber = Extract<StringOrNumber, string | number>;
// string | number

// Exclude<T, U> - Exclude types from T that are assignable to U
type NotBoolean = Exclude<StringOrNumber, boolean>;
// string | number

// NonNullable<T> - Remove null and undefined
type MaybeString = string | null | undefined;
type DefinitelyString = NonNullable<MaybeString>;
// string

// ReturnType<T> - Get return type of function
function createUser(name: string, email: string): User {
  return {
    id: crypto.randomUUID(),
    name,
    email,
    age: 0,
    role: "user",
    createdAt: new Date(),
  };
}
type CreateUserReturn = ReturnType<typeof createUser>;
// User

// Parameters<T> - Get parameter types as tuple
type CreateUserParams = Parameters<typeof createUser>;
// [name: string, email: string]

/**
 * Example 2.2: Custom Utility Types
 *
 * You can create your own utility types for specific needs.
 */

// Make specific properties optional
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

// Usage:
type UserOptionalAge = PartialBy<User, "age" | "metadata">;

// Make specific properties required
export type RequiredBy<T, K extends keyof T> = T & Required<Pick<T, K>>;

// Deep partial (recursive)
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

// Deep readonly (recursive)
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};

// Make all properties mutable (remove readonly)
export type Mutable<T> = {
  -readonly [P in keyof T]: T[P];
};

// Get only required keys
export type RequiredKeys<T> = {
  [K in keyof T]-?: {} extends Pick<T, K> ? never : K;
}[keyof T];

// Get only optional keys
export type OptionalKeys<T> = {
  [K in keyof T]-?: {} extends Pick<T, K> ? K : never;
}[keyof T];

// Nullable - allow null for all properties
export type Nullable<T> = {
  [P in keyof T]: T[P] | null;
};

// ============================================================================
// SECTION 3: DISCRIMINATED UNIONS
// ============================================================================

/**
 * Example 3.1: Basic Discriminated Unions
 *
 * Discriminated unions use a common property to differentiate between types.
 * This enables TypeScript to narrow types automatically.
 */

// API Response pattern - very common in real applications
export type ApiResponse<T> =
  | { status: "success"; data: T; timestamp: Date }
  | { status: "error"; error: { code: string; message: string }; timestamp: Date }
  | { status: "loading"; progress?: number };

// Usage function
export function handleApiResponse<T>(response: ApiResponse<T>): T | null {
  switch (response.status) {
    case "success":
      // TypeScript knows response.data exists here
      return response.data;
    case "error":
      // TypeScript knows response.error exists here
      logger.error("API Error", {
        code: response.error.code,
        message: response.error.message,
      });
      return null;
    case "loading":
      // TypeScript knows response.progress might exist here
      logger.info("Loading...", { progress: response.progress });
      return null;
  }
}

/**
 * Example 3.2: State Machine with Discriminated Unions
 *
 * Perfect for modeling state transitions.
 */

export type AuthState =
  | { status: "unauthenticated" }
  | { status: "authenticating"; email: string }
  | { status: "authenticated"; user: User; token: string }
  | { status: "error"; error: string; lastAttempt: Date };

export class AuthStateMachine {
  private state: AuthState = { status: "unauthenticated" };

  getState(): AuthState {
    return this.state;
  }

  startLogin(email: string): void {
    if (this.state.status !== "unauthenticated" && this.state.status !== "error") {
      throw new Error("Cannot start login from current state");
    }
    this.state = { status: "authenticating", email };
  }

  loginSuccess(user: User, token: string): void {
    if (this.state.status !== "authenticating") {
      throw new Error("Cannot complete login - not authenticating");
    }
    this.state = { status: "authenticated", user, token };
  }

  loginFailure(error: string): void {
    if (this.state.status !== "authenticating") {
      throw new Error("Cannot fail login - not authenticating");
    }
    this.state = { status: "error", error, lastAttempt: new Date() };
  }

  logout(): void {
    this.state = { status: "unauthenticated" };
  }

  // Type-safe access to user
  getUser(): User | null {
    return this.state.status === "authenticated" ? this.state.user : null;
  }
}

/**
 * Example 3.3: Event System with Discriminated Unions
 *
 * Type-safe event handling.
 */

export type AppEvent =
  | { type: "USER_CREATED"; payload: { user: User } }
  | { type: "USER_UPDATED"; payload: { userId: string; changes: Partial<User> } }
  | { type: "USER_DELETED"; payload: { userId: string } }
  | { type: "SESSION_STARTED"; payload: { userId: string; sessionId: string } }
  | { type: "SESSION_ENDED"; payload: { sessionId: string; reason: string } };

// Extract event types
export type EventType = AppEvent["type"];

// Extract payload for a specific event type
export type EventPayload<T extends EventType> = Extract<AppEvent, { type: T }>["payload"];

// Type-safe event handler
export type EventHandler<T extends EventType> = (payload: EventPayload<T>) => void;

export class EventBus {
  private handlers = new Map<EventType, Set<EventHandler<any>>>();

  on<T extends EventType>(type: T, handler: EventHandler<T>): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.get(type)?.delete(handler);
    };
  }

  emit<T extends EventType>(type: T, payload: EventPayload<T>): void {
    const handlers = this.handlers.get(type);
    if (handlers) {
      handlers.forEach((handler) => handler(payload));
    }
  }
}

// ============================================================================
// SECTION 4: TYPE GUARDS AND NARROWING
// ============================================================================

/**
 * Example 4.1: Type Guard Functions
 *
 * Type guards allow runtime type checking that TypeScript understands.
 */

// Basic type guard with 'is' keyword
export function isString(value: unknown): value is string {
  return typeof value === "string";
}

export function isNumber(value: unknown): value is number {
  return typeof value === "number" && !isNaN(value);
}

export function isNonNull<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}

// Type guard for arrays
export function isArray<T>(value: unknown, itemGuard?: (item: unknown) => item is T): value is T[] {
  if (!Array.isArray(value)) return false;
  if (itemGuard) {
    return value.every(itemGuard);
  }
  return true;
}

// Type guard for objects
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// Type guard for specific object shape
export function isUser(value: unknown): value is User {
  return (
    isObject(value) &&
    isString(value.id) &&
    isString(value.email) &&
    isString(value.name) &&
    isNumber(value.age) &&
    ["admin", "user", "guest"].includes(value.role as string)
  );
}

/**
 * Example 4.2: Assertion Functions
 *
 * Functions that throw if a condition isn't met, narrowing the type afterward.
 */

export function assertDefined<T>(
  value: T | null | undefined,
  message?: string
): asserts value is T {
  if (value === null || value === undefined) {
    throw new Error(message ?? "Value must be defined");
  }
}

export function assertString(value: unknown, message?: string): asserts value is string {
  if (typeof value !== "string") {
    throw new Error(message ?? `Expected string, got ${typeof value}`);
  }
}

export function assertNever(value: never, message?: string): never {
  throw new Error(message ?? `Unexpected value: ${JSON.stringify(value)}`);
}

// Usage in exhaustive switch statements
export function handleRole(role: User["role"]): string {
  switch (role) {
    case "admin":
      return "Full access";
    case "user":
      return "Standard access";
    case "guest":
      return "Limited access";
    default:
      // This ensures all cases are handled
      return assertNever(role);
  }
}

/**
 * Example 4.3: Discriminated Union Guards
 *
 * Type guards for discriminated unions.
 */

export function isSuccessResponse<T>(
  response: ApiResponse<T>
): response is Extract<ApiResponse<T>, { status: "success" }> {
  return response.status === "success";
}

export function isErrorResponse<T>(
  response: ApiResponse<T>
): response is Extract<ApiResponse<T>, { status: "error" }> {
  return response.status === "error";
}

// ============================================================================
// SECTION 5: MAPPED AND CONDITIONAL TYPES
// ============================================================================

/**
 * Example 5.1: Mapped Types
 *
 * Transform types by mapping over their properties.
 */

// Add prefix to all keys
export type Prefixed<T, P extends string> = {
  [K in keyof T as `${P}${Capitalize<string & K>}`]: T[K];
};

// Example: Prefixed<{ name: string }, "user"> = { userName: string }

// Add suffix to all keys
export type Suffixed<T, S extends string> = {
  [K in keyof T as `${string & K}${S}`]: T[K];
};

// Remove keys that match a pattern
export type OmitByValue<T, V> = {
  [K in keyof T as T[K] extends V ? never : K]: T[K];
};

// Keep only keys of a certain value type
export type PickByValue<T, V> = {
  [K in keyof T as T[K] extends V ? K : never]: T[K];
};

// Make methods readonly (useful for immutable patterns)
export type ReadonlyMethods<T> = {
  readonly [K in keyof T]: T[K] extends (...args: any[]) => any
    ? T[K]
    : T[K];
};

// Convert all functions to async
export type AsyncMethods<T> = {
  [K in keyof T]: T[K] extends (...args: infer A) => infer R
    ? (...args: A) => Promise<Awaited<R>>
    : T[K];
};

/**
 * Example 5.2: Conditional Types
 *
 * Types that depend on conditions.
 */

// Unwrap promise type
export type Awaited<T> = T extends Promise<infer U> ? Awaited<U> : T;

// Unwrap array type
export type UnwrapArray<T> = T extends (infer U)[] ? U : T;

// Get function return type (if function)
export type MaybeReturnType<T> = T extends (...args: any[]) => infer R ? R : never;

// Check if type is a function
export type IsFunction<T> = T extends (...args: any[]) => any ? true : false;

// Flatten nested types
export type Flatten<T> = T extends Record<string, any>
  ? { [K in keyof T]: T[K] }
  : T;

// Infer array element type or keep original
export type ElementOf<T> = T extends readonly (infer E)[] ? E : T;

// ============================================================================
// SECTION 6: DESIGN PATTERNS
// ============================================================================

/**
 * Example 6.1: Builder Pattern
 *
 * Fluent interface for building complex objects.
 */

export interface EmailConfig {
  to: string[];
  cc?: string[];
  bcc?: string[];
  subject: string;
  body: string;
  isHtml?: boolean;
  attachments?: Array<{ name: string; content: Buffer }>;
  priority?: "low" | "normal" | "high";
}

export class EmailBuilder {
  private config: Partial<EmailConfig> = {};

  to(...recipients: string[]): this {
    this.config.to = recipients;
    return this;
  }

  cc(...recipients: string[]): this {
    this.config.cc = recipients;
    return this;
  }

  bcc(...recipients: string[]): this {
    this.config.bcc = recipients;
    return this;
  }

  subject(subject: string): this {
    this.config.subject = subject;
    return this;
  }

  body(content: string, isHtml: boolean = false): this {
    this.config.body = content;
    this.config.isHtml = isHtml;
    return this;
  }

  attach(name: string, content: Buffer): this {
    if (!this.config.attachments) {
      this.config.attachments = [];
    }
    this.config.attachments.push({ name, content });
    return this;
  }

  priority(level: "low" | "normal" | "high"): this {
    this.config.priority = level;
    return this;
  }

  build(): EmailConfig {
    if (!this.config.to || this.config.to.length === 0) {
      throw new Error("Email must have at least one recipient");
    }
    if (!this.config.subject) {
      throw new Error("Email must have a subject");
    }
    if (!this.config.body) {
      throw new Error("Email must have a body");
    }

    return {
      to: this.config.to,
      cc: this.config.cc,
      bcc: this.config.bcc,
      subject: this.config.subject,
      body: this.config.body,
      isHtml: this.config.isHtml ?? false,
      attachments: this.config.attachments,
      priority: this.config.priority ?? "normal",
    };
  }
}

// Usage:
// const email = new EmailBuilder()
//   .to("user@example.com")
//   .subject("Hello")
//   .body("<h1>Welcome!</h1>", true)
//   .priority("high")
//   .build();

/**
 * Example 6.2: Factory Pattern
 *
 * Create objects without specifying exact classes.
 */

// Product interface
export interface Logger {
  log(message: string, context?: Record<string, unknown>): void;
  error(message: string, error?: Error): void;
  warn(message: string): void;
}

// Concrete implementations
export class ConsoleLogger implements Logger {
  constructor(private prefix: string) {}

  log(message: string, context?: Record<string, unknown>): void {
    console.log(`[${this.prefix}] ${message}`, context ?? "");
  }

  error(message: string, error?: Error): void {
    console.error(`[${this.prefix}] ERROR: ${message}`, error);
  }

  warn(message: string): void {
    console.warn(`[${this.prefix}] WARN: ${message}`);
  }
}

export class JsonLogger implements Logger {
  constructor(private service: string) {}

  private formatLog(level: string, message: string, extra?: Record<string, unknown>): string {
    return JSON.stringify({
      timestamp: new Date().toISOString(),
      level,
      service: this.service,
      message,
      ...extra,
    });
  }

  log(message: string, context?: Record<string, unknown>): void {
    console.log(this.formatLog("INFO", message, { context }));
  }

  error(message: string, error?: Error): void {
    console.error(this.formatLog("ERROR", message, {
      error: error?.message,
      stack: error?.stack,
    }));
  }

  warn(message: string): void {
    console.warn(this.formatLog("WARN", message));
  }
}

// Factory
export type LoggerType = "console" | "json";

export class LoggerFactory {
  static create(type: LoggerType, identifier: string): Logger {
    switch (type) {
      case "console":
        return new ConsoleLogger(identifier);
      case "json":
        return new JsonLogger(identifier);
      default:
        throw new Error(`Unknown logger type: ${type}`);
    }
  }
}

/**
 * Example 6.3: Repository Pattern
 *
 * Abstract data access behind a consistent interface.
 */

export interface Entity {
  id: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface Repository<T extends Entity> {
  findById(id: string): Promise<T | null>;
  findAll(options?: { limit?: number; offset?: number }): Promise<T[]>;
  findBy(criteria: Partial<T>): Promise<T[]>;
  create(data: Omit<T, "id" | "createdAt" | "updatedAt">): Promise<T>;
  update(id: string, data: Partial<Omit<T, "id" | "createdAt" | "updatedAt">>): Promise<T>;
  delete(id: string): Promise<boolean>;
  count(criteria?: Partial<T>): Promise<number>;
}

// In-memory implementation
export class InMemoryRepository<T extends Entity> implements Repository<T> {
  protected items: Map<string, T> = new Map();

  async findById(id: string): Promise<T | null> {
    return this.items.get(id) ?? null;
  }

  async findAll(options?: { limit?: number; offset?: number }): Promise<T[]> {
    const all = Array.from(this.items.values());
    const offset = options?.offset ?? 0;
    const limit = options?.limit ?? all.length;
    return all.slice(offset, offset + limit);
  }

  async findBy(criteria: Partial<T>): Promise<T[]> {
    return Array.from(this.items.values()).filter((item) =>
      Object.entries(criteria).every(
        ([key, value]) => item[key as keyof T] === value
      )
    );
  }

  async create(data: Omit<T, "id" | "createdAt" | "updatedAt">): Promise<T> {
    const now = new Date();
    const item = {
      ...data,
      id: crypto.randomUUID(),
      createdAt: now,
      updatedAt: now,
    } as T;
    this.items.set(item.id, item);
    return item;
  }

  async update(
    id: string,
    data: Partial<Omit<T, "id" | "createdAt" | "updatedAt">>
  ): Promise<T> {
    const existing = this.items.get(id);
    if (!existing) {
      throw new Error(`Entity with id ${id} not found`);
    }
    const updated = {
      ...existing,
      ...data,
      updatedAt: new Date(),
    };
    this.items.set(id, updated);
    return updated;
  }

  async delete(id: string): Promise<boolean> {
    return this.items.delete(id);
  }

  async count(criteria?: Partial<T>): Promise<number> {
    if (!criteria) {
      return this.items.size;
    }
    return (await this.findBy(criteria)).length;
  }
}

/**
 * Example 6.4: Dependency Injection Container
 *
 * Simple DI container for managing dependencies.
 */

type Constructor<T = any> = new (...args: any[]) => T;
type Factory<T = any> = () => T;

export class Container {
  private singletons = new Map<string, any>();
  private factories = new Map<string, Factory>();

  // Register a singleton instance
  registerSingleton<T>(key: string, instance: T): void {
    this.singletons.set(key, instance);
  }

  // Register a factory function
  registerFactory<T>(key: string, factory: Factory<T>): void {
    this.factories.set(key, factory);
  }

  // Register a class as singleton
  registerClass<T>(key: string, ctor: Constructor<T>, ...args: any[]): void {
    this.singletons.set(key, new ctor(...args));
  }

  // Get a dependency
  resolve<T>(key: string): T {
    // Check singletons first
    if (this.singletons.has(key)) {
      return this.singletons.get(key) as T;
    }

    // Check factories
    if (this.factories.has(key)) {
      return this.factories.get(key)!() as T;
    }

    throw new Error(`No registration found for key: ${key}`);
  }

  // Check if a dependency is registered
  has(key: string): boolean {
    return this.singletons.has(key) || this.factories.has(key);
  }
}

// ============================================================================
// SECTION 7: ERROR HANDLING PATTERNS
// ============================================================================

/**
 * Example 7.1: Custom Error Classes
 *
 * Create specific error types for different error cases.
 */

export class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500,
    public isOperational: boolean = true
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }

  toJSON(): Record<string, unknown> {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      statusCode: this.statusCode,
    };
  }
}

export class ValidationError extends AppError {
  constructor(
    message: string,
    public fields: Record<string, string[]>
  ) {
    super(message, "VALIDATION_ERROR", 400);
  }

  toJSON(): Record<string, unknown> {
    return {
      ...super.toJSON(),
      fields: this.fields,
    };
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super(`${resource} with id '${id}' not found`, "NOT_FOUND", 404);
  }
}

export class UnauthorizedError extends AppError {
  constructor(message: string = "Unauthorized") {
    super(message, "UNAUTHORIZED", 401);
  }
}

export class ForbiddenError extends AppError {
  constructor(message: string = "Forbidden") {
    super(message, "FORBIDDEN", 403);
  }
}

export class ConflictError extends AppError {
  constructor(message: string) {
    super(message, "CONFLICT", 409);
  }
}

/**
 * Example 7.2: Result Type (Either Pattern)
 *
 * Explicitly handle success and failure without exceptions.
 */

export type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

export const Result = {
  ok<T>(data: T): Result<T, never> {
    return { success: true, data };
  },

  err<E>(error: E): Result<never, E> {
    return { success: false, error };
  },

  isOk<T, E>(result: Result<T, E>): result is { success: true; data: T } {
    return result.success === true;
  },

  isErr<T, E>(result: Result<T, E>): result is { success: false; error: E } {
    return result.success === false;
  },

  map<T, U, E>(result: Result<T, E>, fn: (data: T) => U): Result<U, E> {
    if (result.success) {
      return Result.ok(fn(result.data));
    }
    return result;
  },

  flatMap<T, U, E>(result: Result<T, E>, fn: (data: T) => Result<U, E>): Result<U, E>

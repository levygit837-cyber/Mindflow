/**
 * StructuredIO - NDJSON Streaming Protocol for MindFlow CLI
 * Handles streaming input/output with structured messages
 */

import { createInterface, Interface } from 'readline';
import type { Message, ControlRequest, ControlResponse } from '../types/protocol.js';

// Maximum number of resolved tool use IDs to track
const MAX_RESOLVED_TOOL_USE_IDS = 1000;

// Stream class for outbound messages
export class MessageStream<T> {
  private queue: T[] = [];
  private resolvers: Array<(value: IteratorResult<T>) => void> = [];
  private doneFlag = false;
  // private waiters: Array<Promise<IteratorResult<T>>> = [];

  enqueue(message: T): void {
    if (this.doneFlag) return;
    
    if (this.resolvers.length > 0) {
      const resolver = this.resolvers.shift()!;
      resolver({ value: message, done: false });
    } else {
      this.queue.push(message);
    }
  }

  async *read(): AsyncGenerator<T> {
    while (true) {
      // Check if there are queued messages
      if (this.queue.length > 0) {
        yield this.queue.shift()!;
        continue;
      }

      // Check if we're done
      if (this.doneFlag) {
        return;
      }

      // Wait for next message
      const promise = new Promise<IteratorResult<T>>((resolve) => {
        this.resolvers.push(resolve);
      });
      
      const result = await promise;
      if (result.done) {
        return;
      }
      yield result.value;
    }
  }

  done(): void {
    this.doneFlag = true;
    // Resolve any pending waiters
    while (this.resolvers.length > 0) {
      const resolver = this.resolvers.shift()!;
      resolver({ value: undefined as unknown as T, done: true });
    }
  }

  get isDone(): boolean {
    return this.doneFlag;
  }

  get pendingCount(): number {
    return this.queue.length;
  }
}

export interface StructuredIOOptions {
  input?: NodeJS.ReadStream;
  output?: NodeJS.WriteStream;
  replayUserMessages?: boolean;
}

export class StructuredIO {
  private input: NodeJS.ReadStream;
  private output: NodeJS.WriteStream;
  private rl: Interface | null = null;
  private inputClosed = false;
  private prependedLines: string[] = [];
  
  // Track resolved tool use IDs to prevent duplicate handling
  private resolvedToolUseIds = new Set<string>();
  
  // Outbound message stream
  readonly outbound = new MessageStream<Message>();
  
  // Pending control requests
  private pendingRequests = new Map<string, {
    request: ControlRequest;
    resolve: (response: ControlResponse) => void;
    reject: (error: Error) => void;
  }>();

  constructor(options: StructuredIOOptions = {}) {
    this.input = options.input ?? process.stdin;
    this.output = options.output ?? process.stdout;
    this.setupReadline();
  }

  private setupReadline(): void {
    this.rl = createInterface({
      input: this.input,
      crlfDelay: Infinity,
    });

    this.rl.on('line', (line) => {
      this.processLine(line).catch((err) => {
        console.error('Error processing line:', err);
      });
    });

    this.rl.on('close', () => {
      this.inputClosed = true;
      this.cleanupPendingRequests();
      this.outbound.done();
    });
  }

  /**
   * Prepend a user message to be processed before next input
   */
  prependUserMessage(content: string): void {
    const message: Message = {
      type: 'user',
      content,
      timestamp: Date.now(),
      uuid: crypto.randomUUID(),
      parent_tool_use_id: null,
      session_id: '',
    };
    this.prependedLines.push(JSON.stringify(message));
  }

  /**
   * Process a single NDJSON line
   */
  private async processLine(line: string): Promise<void> {
    // Check prepended lines first
    if (this.prependedLines.length > 0) {
      const prepended = this.prependedLines.shift()!;
      await this.processLine(prepended);
    }

    const trimmed = line.trim();
    if (!trimmed) return;

    try {
      const message = JSON.parse(trimmed) as Message;
      
      // Validate message structure
      if (!message.type || !message.uuid) {
        console.error('Invalid message format:', line);
        return;
      }

      // Handle control requests specially
      if (message.type === 'control_request') {
        this.handleControlRequest(message as ControlRequest);
        return;
      }

      // Handle control responses
      if (message.type === 'control_response') {
        this.handleControlResponse(message as ControlResponse);
        return;
      }

      // Track resolved tool use IDs
      if (message.type === 'tool_result') {
        const resultMsg = message as { tool_use_id: string };
        this.trackResolvedToolUseId(resultMsg.tool_use_id);
      }

      // Enqueue to outbound stream
      this.outbound.enqueue(message);
    } catch (error) {
      console.error('Error parsing message:', line, error);
    }
  }

  /**
   * Track resolved tool use ID
   */
  private trackResolvedToolUseId(toolUseId: string): void {
    this.resolvedToolUseIds.add(toolUseId);
    if (this.resolvedToolUseIds.size > MAX_RESOLVED_TOOL_USE_IDS) {
      // Evict oldest entry
      const first = this.resolvedToolUseIds.values().next().value;
      if (first !== undefined) {
        this.resolvedToolUseIds.delete(first);
      }
    }
  }

  /**
   * Handle incoming control request
   */
  private handleControlRequest(request: ControlRequest): void {
    // Store pending request - Promise created for future resolution
    new Promise<ControlResponse>((resolve, reject) => {
      this.pendingRequests.set(request.uuid, {
        request,
        resolve,
        reject,
      });
    });

    // Enqueue the request message
    this.outbound.enqueue(request);

    // Return the promise for resolution
    return;
  }

  /**
   * Handle control response
   */
  private handleControlResponse(response: ControlResponse): void {
    const pending = this.pendingRequests.get(response.request_id);
    if (pending) {
      pending.resolve(response);
      this.pendingRequests.delete(response.request_id);
    }
  }

  /**
   * Cleanup pending requests on close
   */
  private cleanupPendingRequests(): void {
    for (const [_id, pending] of this.pendingRequests) {
      pending.reject(new Error('Input stream closed before response'));
    }
    this.pendingRequests.clear();
  }

  /**
   * Write message to output (NDJSON format)
   */
  async write(message: Message): Promise<void> {
    const line = JSON.stringify(message) + '\n';
    return new Promise((resolve, reject) => {
      this.output.write(line, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  /**
   * Send control response for permission request
   */
  async sendControlResponse(requestId: string, decision: 'allow' | 'deny' | 'ask', message?: string): Promise<void> {
    const response: ControlResponse = {
      type: 'control_response',
      request_id: requestId,
      uuid: crypto.randomUUID(),
      timestamp: Date.now(),
      response: {
        decision,
        message,
      },
    };
    await this.write(response);
  }

  /**
   * Get async iterable of incoming messages
   */
  async *read(): AsyncGenerator<Message> {
    yield* this.outbound.read();
  }

  /**
   * Check if a tool use ID has been resolved
   */
  isToolUseResolved(toolUseId: string): boolean {
    return this.resolvedToolUseIds.has(toolUseId);
  }

  /**
   * Get pending permission requests
   */
  getPendingPermissionRequests(): ControlRequest[] {
    return Array.from(this.pendingRequests.values())
      .filter(p => p.request.request.subtype === 'can_use_tool')
      .map(p => p.request);
  }

  /**
   * Close the IO stream
   */
  close(): void {
    this.rl?.close();
    this.outbound.done();
  }

  /**
   * Check if input is closed
   */
  get isInputClosed(): boolean {
    return this.inputClosed;
  }

  /**
   * Get count of pending outbound messages
   */
  get pendingOutboundCount(): number {
    return this.outbound.pendingCount;
  }
}

// Factory function for easier creation
export function createStructuredIO(options?: StructuredIOOptions): StructuredIO {
  return new StructuredIO(options);
}

/**
 * In-memory task registry for active swarm sessions.
 *
 * Stores running tasks with their NotifierService instances, current status,
 * and a snapshot of the latest state. The API routes use this module to look
 * up tasks for status queries and SSE streaming.
 */

import type { NotifierService } from "./notifier";
import type { TaskStatus } from "@shared/types/swarm";
import { createLogger } from "@backend/utils/logger";

const logger = createLogger("swarm:registry");

export interface SwarmTaskSession {
  taskId: string;
  notifier: NotifierService;
  status: TaskStatus;
  /** Lightweight snapshot — updated after graph execution completes */
  stateSnapshot: {
    coder_plan: string | null;
    analyst_state: string;
    sandbox_display: string;
    reviewer_report_md: string;
  };
  startedAt: string;
}

/**
 * Module-level in-memory map of active swarm task sessions.
 */
const sessions = new Map<string, SwarmTaskSession>();

export function registerSession(session: SwarmTaskSession): void {
  sessions.set(session.taskId, session);
  logger.info("Session registered", { taskId: session.taskId });
}

export function getSession(taskId: string): SwarmTaskSession | undefined {
  return sessions.get(taskId);
}

export function updateSession(
  taskId: string,
  update: Partial<Omit<SwarmTaskSession, "taskId">>,
): void {
  const session = sessions.get(taskId);
  if (!session) return;
  Object.assign(session, update);
}

export function removeSession(taskId: string): boolean {
  const removed = sessions.delete(taskId);
  if (removed) {
    logger.info("Session removed", { taskId });
  }
  return removed;
}

export function listSessions(): SwarmTaskSession[] {
  return Array.from(sessions.values());
}

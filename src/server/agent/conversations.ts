import { v4 as uuidv4 } from "uuid";

/**
 * In-memory conversation store.
 * Will be migrated to PostgreSQL in a future iteration.
 */

interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

interface Message {
  id: string;
  conversationId: string;
  role: string;
  content: string;
  thoughts: string | null;
  toolCalls: string | null;
  createdAt: string;
}

const conversationStore = new Map<string, Conversation>();
const messageStore = new Map<string, Message[]>();

export function createConversation(title?: string): Conversation {
  const id = uuidv4();
  const now = new Date().toISOString();
  const conv: Conversation = {
    id,
    title: title || "New Conversation",
    createdAt: now,
    updatedAt: now,
  };
  conversationStore.set(id, conv);
  messageStore.set(id, []);
  return conv;
}

export function listConversations(): Conversation[] {
  return Array.from(conversationStore.values())
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export function getConversation(id: string): Conversation | undefined {
  return conversationStore.get(id);
}

export function updateConversationTitle(id: string, title: string): void {
  const conv = conversationStore.get(id);
  if (conv) {
    conv.title = title;
    conv.updatedAt = new Date().toISOString();
  }
}

export function deleteConversation(id: string): void {
  conversationStore.delete(id);
  messageStore.delete(id);
}

export function getMessages(conversationId: string): Message[] {
  return messageStore.get(conversationId) || [];
}

export function saveMessage(msg: {
  conversationId: string;
  role: string;
  content: string;
  thoughts?: string | null;
  toolCalls?: string | null;
}): string {
  const id = uuidv4();
  const now = new Date().toISOString();

  const message: Message = {
    id,
    conversationId: msg.conversationId,
    role: msg.role,
    content: msg.content,
    thoughts: msg.thoughts || null,
    toolCalls: msg.toolCalls || null,
    createdAt: now,
  };

  const messages = messageStore.get(msg.conversationId) || [];
  messages.push(message);
  messageStore.set(msg.conversationId, messages);

  const conv = conversationStore.get(msg.conversationId);
  if (conv) {
    conv.updatedAt = now;
  }

  return id;
}

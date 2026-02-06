import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";

export const notes = sqliteTable("notes", {
  id: text("id").primaryKey(),
  title: text("title").notNull().default("Untitled"),
  emoji: text("emoji").notNull().default("📝"),
  tags: text("tags").notNull().default("[]"), // JSON array
  starred: integer("starred", { mode: "boolean" }).notNull().default(false),
  color: text("color"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
  wordCount: integer("word_count").notNull().default(0),
  preview: text("preview").notNull().default(""),
});

export const noteLinks = sqliteTable("note_links", {
  id: text("id").primaryKey(),
  sourceId: text("source_id").notNull().references(() => notes.id, { onDelete: "cascade" }),
  targetId: text("target_id").notNull().references(() => notes.id, { onDelete: "cascade" }),
  label: text("label"),
});

export const conversations = sqliteTable("conversations", {
  id: text("id").primaryKey(),
  title: text("title").notNull().default("New Conversation"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const messages = sqliteTable("messages", {
  id: text("id").primaryKey(),
  conversationId: text("conversation_id").notNull().references(() => conversations.id, { onDelete: "cascade" }),
  role: text("role").notNull(), // "user" | "assistant"
  content: text("content").notNull(),
  thoughts: text("thoughts"),
  toolCalls: text("tool_calls"), // JSON
  createdAt: text("created_at").notNull(),
});

export const settings = sqliteTable("settings", {
  key: text("key").primaryKey(),
  value: text("value").notNull(),
});

import { sqlite } from "./index";

export function runMigrations() {
  // Create tables
  sqlite.exec(`
    CREATE TABLE IF NOT EXISTS notes (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL DEFAULT 'Untitled',
      emoji TEXT NOT NULL DEFAULT '📝',
      tags TEXT NOT NULL DEFAULT '[]',
      starred INTEGER NOT NULL DEFAULT 0,
      color TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      word_count INTEGER NOT NULL DEFAULT 0,
      preview TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS note_links (
      id TEXT PRIMARY KEY,
      source_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
      target_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
      label TEXT
    );

    CREATE TABLE IF NOT EXISTS conversations (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL DEFAULT 'New Conversation',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS messages (
      id TEXT PRIMARY KEY,
      conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      thoughts TEXT,
      tool_calls TEXT,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
  `);

  // Create FTS5 virtual table for full-text search
  sqlite.exec(`
    CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
      title,
      preview,
      content_text,
      tags,
      content='',
      contentless_delete=1
    );
  `);

  // Create indexes
  sqlite.exec(`
    CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at);
    CREATE INDEX IF NOT EXISTS idx_notes_starred ON notes(starred);
    CREATE INDEX IF NOT EXISTS idx_note_links_source ON note_links(source_id);
    CREATE INDEX IF NOT EXISTS idx_note_links_target ON note_links(target_id);
    CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
  `);
}

import { db } from "@/lib/db";
import { notes, noteLinks } from "@/lib/db/schema";
import { eq, desc, asc, inArray, and, like } from "drizzle-orm";
import { v4 as uuidv4 } from "uuid";
import { ensureDbInitialized } from "@/lib/db/init";
import { readNoteContent, writeNoteContent, deleteNoteContent, extractPlainText } from "./content";
import { indexNote, removeNoteFromIndex, searchNotes } from "./search";
import type { Note, CreateNoteInput, UpdateNoteInput, NoteSearchParams, BlockNoteDocument } from "@/types/note";

function rowToNote(row: typeof notes.$inferSelect): Note {
  return {
    id: row.id,
    title: row.title,
    emoji: row.emoji,
    tags: JSON.parse(row.tags),
    starred: row.starred,
    color: row.color,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
    wordCount: row.wordCount,
    preview: row.preview,
  };
}

export function listNotes(params: NoteSearchParams = {}): Note[] {
  ensureDbInitialized();

  const { query, tags, starred, sortBy = "updatedAt", sortOrder = "desc", limit = 100, offset = 0 } = params;

  // If there's a search query, use FTS
  if (query) {
    const matchingIds = searchNotes(query);
    if (matchingIds.length === 0) return [];
    const rows = db.select().from(notes).where(inArray(notes.id, matchingIds)).all();
    return rows.map(rowToNote);
  }

  const conditions = [];
  if (starred !== undefined) {
    conditions.push(eq(notes.starred, starred));
  }
  if (tags && tags.length > 0) {
    // Filter notes that contain any of the specified tags
    for (const tag of tags) {
      conditions.push(like(notes.tags, `%"${tag}"%`));
    }
  }

  const orderCol = sortBy === "title" ? notes.title : sortBy === "createdAt" ? notes.createdAt : notes.updatedAt;
  const orderFn = sortOrder === "asc" ? asc : desc;

  const where = conditions.length > 0 ? and(...conditions) : undefined;
  const rows = db.select().from(notes).where(where).orderBy(orderFn(orderCol)).limit(limit).offset(offset).all();
  return rows.map(rowToNote);
}

export function getNote(id: string): Note | null {
  ensureDbInitialized();
  const row = db.select().from(notes).where(eq(notes.id, id)).get();
  return row ? rowToNote(row) : null;
}

export function createNote(input: CreateNoteInput = {}): Note {
  ensureDbInitialized();
  const id = uuidv4();
  const now = new Date().toISOString();
  const newNote = {
    id,
    title: input.title || "Untitled",
    emoji: input.emoji || "📝",
    tags: JSON.stringify(input.tags || []),
    starred: false,
    color: input.color || null,
    createdAt: now,
    updatedAt: now,
    wordCount: 0,
    preview: "",
  };

  db.insert(notes).values(newNote).run();
  writeNoteContent(id, []);
  indexNote(id, newNote.title, "", "", newNote.tags);

  return rowToNote(newNote as typeof notes.$inferSelect);
}

export function updateNote(id: string, input: UpdateNoteInput): Note | null {
  ensureDbInitialized();
  const existing = db.select().from(notes).where(eq(notes.id, id)).get();
  if (!existing) return null;

  const updates: Partial<typeof notes.$inferInsert> = {
    updatedAt: new Date().toISOString(),
  };
  if (input.title !== undefined) updates.title = input.title;
  if (input.emoji !== undefined) updates.emoji = input.emoji;
  if (input.tags !== undefined) updates.tags = JSON.stringify(input.tags);
  if (input.starred !== undefined) updates.starred = input.starred;
  if (input.color !== undefined) updates.color = input.color;

  db.update(notes).set(updates).where(eq(notes.id, id)).run();

  const updated = db.select().from(notes).where(eq(notes.id, id)).get();
  if (!updated) return null;

  // Re-index if title or tags changed
  if (input.title !== undefined || input.tags !== undefined) {
    const content = readNoteContent(id);
    const contentText = extractPlainText(content);
    indexNote(id, updated.title, updated.preview, contentText, updated.tags);
  }

  return rowToNote(updated);
}

export function updateNoteContent(id: string, content: BlockNoteDocument): Note | null {
  ensureDbInitialized();
  const existing = db.select().from(notes).where(eq(notes.id, id)).get();
  if (!existing) return null;

  writeNoteContent(id, content);

  const plainText = extractPlainText(content);
  const wordCount = plainText.split(/\s+/).filter(Boolean).length;
  const preview = plainText.slice(0, 200);
  const now = new Date().toISOString();

  db.update(notes).set({ wordCount, preview, updatedAt: now }).where(eq(notes.id, id)).run();
  indexNote(id, existing.title, preview, plainText, existing.tags);

  const updated = db.select().from(notes).where(eq(notes.id, id)).get();
  return updated ? rowToNote(updated) : null;
}

export function deleteNote(id: string): boolean {
  ensureDbInitialized();
  removeNoteFromIndex(id);
  deleteNoteContent(id);
  const result = db.delete(notes).where(eq(notes.id, id)).run();
  return result.changes > 0;
}

export function getNoteContent(id: string): BlockNoteDocument {
  return readNoteContent(id);
}

// Note links for the graph
export function linkNotes(sourceId: string, targetId: string, label?: string): void {
  ensureDbInitialized();
  const id = uuidv4();
  db.insert(noteLinks).values({ id, sourceId, targetId, label: label || null }).run();
}

export function unlinkNotes(sourceId: string, targetId: string): void {
  ensureDbInitialized();
  db.delete(noteLinks).where(and(eq(noteLinks.sourceId, sourceId), eq(noteLinks.targetId, targetId))).run();
}

export function getNoteLinks() {
  ensureDbInitialized();
  return db.select().from(noteLinks).all();
}

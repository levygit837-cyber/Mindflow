import { sqlite } from "@/lib/db";

export function indexNote(noteId: string, title: string, preview: string, contentText: string, tags: string) {
  // Delete existing entry and re-insert
  sqlite.prepare("DELETE FROM notes_fts WHERE rowid = (SELECT rowid FROM notes_fts WHERE rowid IN (SELECT rowid FROM notes WHERE id = ?))").run(noteId);

  // Use a subquery approach - insert with explicit rowid
  const row = sqlite.prepare("SELECT rowid FROM notes WHERE id = ?").get(noteId) as { rowid: number } | undefined;
  if (row) {
    sqlite.prepare("INSERT INTO notes_fts(rowid, title, preview, content_text, tags) VALUES (?, ?, ?, ?, ?)").run(
      row.rowid,
      title,
      preview,
      contentText,
      tags
    );
  }
}

export function removeNoteFromIndex(noteId: string) {
  const row = sqlite.prepare("SELECT rowid FROM notes WHERE id = ?").get(noteId) as { rowid: number } | undefined;
  if (row) {
    sqlite.prepare("DELETE FROM notes_fts WHERE rowid = ?").run(row.rowid);
  }
}

export function searchNotes(query: string): string[] {
  const rows = sqlite.prepare(
    "SELECT rowid FROM notes_fts WHERE notes_fts MATCH ? ORDER BY rank LIMIT 50"
  ).all(query) as { rowid: number }[];

  const noteIds: string[] = [];
  for (const row of rows) {
    const note = sqlite.prepare("SELECT id FROM notes WHERE rowid = ?").get(row.rowid) as { id: string } | undefined;
    if (note) noteIds.push(note.id);
  }
  return noteIds;
}

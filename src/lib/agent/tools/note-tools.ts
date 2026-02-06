import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getNote, getNoteContent, listNotes, updateNoteContent, linkNotes } from "@/lib/notes/service";
import { searchNotes } from "@/lib/notes/search";
import { readNoteContent, extractPlainText } from "@/lib/notes/content";

export const readNoteTool = tool(
  async ({ noteId }) => {
    const note = getNote(noteId);
    if (!note) return `Note not found: ${noteId}`;
    const content = getNoteContent(noteId);
    const text = extractPlainText(content);
    return JSON.stringify({
      id: note.id,
      title: note.title,
      emoji: note.emoji,
      tags: note.tags,
      content: text,
      wordCount: note.wordCount,
      updatedAt: note.updatedAt,
    });
  },
  {
    name: "read_note",
    description: "Read a note's metadata and full text content by its ID",
    schema: z.object({
      noteId: z.string().describe("The UUID of the note to read"),
    }),
  }
);

export const searchNotesTool = tool(
  async ({ query }) => {
    const noteIds = searchNotes(query);
    if (noteIds.length === 0) return "No notes found matching the query.";
    const notes = noteIds.map((id) => {
      const note = getNote(id);
      return note ? { id: note.id, title: note.title, emoji: note.emoji, preview: note.preview } : null;
    }).filter(Boolean);
    return JSON.stringify(notes);
  },
  {
    name: "search_notes",
    description: "Search notes using full-text search. Returns matching note metadata.",
    schema: z.object({
      query: z.string().describe("The search query"),
    }),
  }
);

export const getNotesContextTool = tool(
  async ({ noteIds }) => {
    const results = [];
    for (const id of noteIds) {
      const note = getNote(id);
      if (!note) continue;
      const content = readNoteContent(id);
      const text = extractPlainText(content);
      results.push({
        id: note.id,
        title: note.title,
        emoji: note.emoji,
        tags: note.tags,
        content: text,
      });
    }
    return JSON.stringify(results);
  },
  {
    name: "get_notes_context",
    description: "Get the full content of multiple notes at once. Useful when you need context from several notes.",
    schema: z.object({
      noteIds: z.array(z.string()).describe("Array of note UUIDs to read"),
    }),
  }
);

export const listNotesTool = tool(
  async ({}) => {
    const notes = listNotes({ limit: 50 });
    return JSON.stringify(
      notes.map((n) => ({
        id: n.id,
        title: n.title,
        emoji: n.emoji,
        tags: n.tags,
        preview: n.preview.slice(0, 100),
      }))
    );
  },
  {
    name: "list_notes",
    description: "List all notes with their metadata. Returns up to 50 notes.",
    schema: z.object({}),
  }
);

export const linkNotesTool = tool(
  async ({ sourceId, targetId, label }) => {
    linkNotes(sourceId, targetId, label);
    return `Successfully linked note ${sourceId} to ${targetId}`;
  },
  {
    name: "link_notes",
    description: "Create a link between two notes in the knowledge graph",
    schema: z.object({
      sourceId: z.string().describe("Source note UUID"),
      targetId: z.string().describe("Target note UUID"),
      label: z.string().optional().describe("Optional label for the link"),
    }),
  }
);

export const noteTools = [
  readNoteTool,
  searchNotesTool,
  getNotesContextTool,
  listNotesTool,
  linkNotesTool,
];

import fs from "fs";
import path from "path";
import { NOTES_DIR } from "@/lib/db";
import type { BlockNoteDocument } from "@/types/note";

export function readNoteContent(noteId: string): BlockNoteDocument {
  const filePath = path.join(NOTES_DIR, `${noteId}.json`);
  if (!fs.existsSync(filePath)) {
    return [];
  }
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw);
}

export function writeNoteContent(noteId: string, content: BlockNoteDocument): void {
  const filePath = path.join(NOTES_DIR, `${noteId}.json`);
  fs.writeFileSync(filePath, JSON.stringify(content, null, 2), "utf-8");
}

export function deleteNoteContent(noteId: string): void {
  const filePath = path.join(NOTES_DIR, `${noteId}.json`);
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
  }
}

export function extractPlainText(content: BlockNoteDocument): string {
  const texts: string[] = [];

  function walk(blocks: Record<string, unknown>[]) {
    for (const block of blocks) {
      if (block.content && Array.isArray(block.content)) {
        for (const inline of block.content) {
          if (typeof inline === "object" && inline !== null && "text" in inline) {
            texts.push((inline as { text: string }).text);
          }
        }
      }
      if (block.children && Array.isArray(block.children)) {
        walk(block.children as Record<string, unknown>[]);
      }
    }
  }

  walk(content);
  return texts.join(" ");
}

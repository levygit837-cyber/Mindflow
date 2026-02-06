"use client";

import { useCallback, useRef } from "react";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/shadcn";
import "@blocknote/shadcn/style.css";
import type { BlockNoteDocument } from "@/types/note";

interface NoteEditorProps {
  initialContent: BlockNoteDocument;
  onSave: (content: BlockNoteDocument) => void;
}

export function NoteEditor({ initialContent, onSave }: NoteEditorProps) {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const editor = useCreateBlockNote({
    initialContent: initialContent.length > 0 ? initialContent as Parameters<typeof useCreateBlockNote>[0] extends { initialContent: infer T } ? T : never : undefined,
  });

  const handleChange = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const doc = editor.document as unknown as BlockNoteDocument;
      onSave(doc);
    }, 2000);
  }, [editor, onSave]);

  return (
    <div className="min-h-[500px]" data-theming-css-variables-demo>
      <BlockNoteView
        editor={editor}
        onChange={handleChange}
        theme="dark"
      />
    </div>
  );
}

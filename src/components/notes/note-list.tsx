"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NoteCard } from "./note-card";
import { useNotes } from "@/hooks/use-notes";

export function NoteList() {
  const [query, setQuery] = useState("");
  const { notes, loading, createNote, deleteNote } = useNotes({ query: query || undefined });
  const router = useRouter();

  const handleCreate = async () => {
    const note = await createNote();
    router.push(`/notes/${note.id}`);
  };

  const handleToggleStar = async (id: string, starred: boolean) => {
    await fetch(`/api/notes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ starred }),
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search notes..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button onClick={handleCreate}>
          <Plus className="h-4 w-4 mr-1" />
          New Note
        </Button>
      </div>

      {loading ? (
        <div className="text-center text-muted-foreground py-12">Loading...</div>
      ) : notes.length === 0 ? (
        <div className="text-center text-muted-foreground py-12">
          {query ? "No notes found" : "No notes yet. Create your first note!"}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {notes.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              onDelete={deleteNote}
              onToggleStar={handleToggleStar}
            />
          ))}
        </div>
      )}
    </div>
  );
}

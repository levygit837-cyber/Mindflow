"use client";

import { useState, useEffect, useCallback } from "react";
import type { Note, BlockNoteDocument, NoteSearchParams } from "@/types/note";

export function useNotes(params: NoteSearchParams = {}) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotes = useCallback(async () => {
    setLoading(true);
    const searchParams = new URLSearchParams();
    if (params.query) searchParams.set("q", params.query);
    if (params.tags?.length) searchParams.set("tags", params.tags.join(","));
    if (params.starred) searchParams.set("starred", "true");
    if (params.sortBy) searchParams.set("sortBy", params.sortBy);
    if (params.sortOrder) searchParams.set("sortOrder", params.sortOrder);

    const res = await fetch(`/api/notes?${searchParams}`);
    const data = await res.json();
    setNotes(data);
    setLoading(false);
  }, [params.query, params.tags, params.starred, params.sortBy, params.sortOrder]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const createNote = async (input: { title?: string; emoji?: string } = {}) => {
    const res = await fetch("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    const note = await res.json();
    await fetchNotes();
    return note as Note;
  };

  const deleteNote = async (id: string) => {
    await fetch(`/api/notes/${id}`, { method: "DELETE" });
    await fetchNotes();
  };

  return { notes, loading, createNote, deleteNote, refetch: fetchNotes };
}

export function useNote(id: string) {
  const [note, setNote] = useState<Note | null>(null);
  const [content, setContent] = useState<BlockNoteDocument>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const [noteRes, contentRes] = await Promise.all([
        fetch(`/api/notes/${id}`),
        fetch(`/api/notes/${id}/content`),
      ]);
      if (noteRes.ok) {
        setNote(await noteRes.json());
        setContent(await contentRes.json());
      }
      setLoading(false);
    }
    load();
  }, [id]);

  const updateNote = async (input: Partial<Note>) => {
    const res = await fetch(`/api/notes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    if (res.ok) setNote(await res.json());
  };

  const saveContent = async (newContent: BlockNoteDocument) => {
    const res = await fetch(`/api/notes/${id}/content`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newContent),
    });
    if (res.ok) setNote(await res.json());
  };

  return { note, content, loading, updateNote, saveContent };
}

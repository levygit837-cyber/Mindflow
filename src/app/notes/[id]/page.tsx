"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Star, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { NoteEditor } from "@/components/notes/note-editor";
import { useNote } from "@/hooks/use-notes";
import { cn } from "@/lib/utils";

export default function NoteEditorPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { note, content, loading, updateNote, saveContent } = useNote(id);
  const router = useRouter();
  const [tagInput, setTagInput] = useState("");

  if (loading) {
    return <div className="flex items-center justify-center h-full text-muted-foreground">Loading...</div>;
  }

  if (!note) {
    return <div className="flex items-center justify-center h-full text-muted-foreground">Note not found</div>;
  }

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !note.tags.includes(tag)) {
      updateNote({ tags: [...note.tags, tag] });
      setTagInput("");
    }
  };

  const handleRemoveTag = (tag: string) => {
    updateNote({ tags: note.tags.filter((t) => t !== tag) });
  };

  const handleDelete = async () => {
    await fetch(`/api/notes/${id}`, { method: "DELETE" });
    router.push("/notes");
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2 border-b">
        <Button variant="ghost" size="icon" onClick={() => router.push("/notes")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <span className="text-xl cursor-pointer">{note.emoji}</span>
        <Input
          value={note.title}
          onChange={(e) => updateNote({ title: e.target.value })}
          className="border-none text-lg font-semibold bg-transparent shadow-none focus-visible:ring-0 px-1 flex-1"
          placeholder="Untitled"
        />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => updateNote({ starred: !note.starred })}
        >
          <Star className={cn("h-4 w-4", note.starred && "fill-yellow-500 text-yellow-500")} />
        </Button>
        <Button variant="ghost" size="icon" className="text-destructive" onClick={handleDelete}>
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex items-center gap-2 px-4 py-1.5 border-b">
        {note.tags.map((tag) => (
          <Badge
            key={tag}
            variant="secondary"
            className="cursor-pointer"
            onClick={() => handleRemoveTag(tag)}
          >
            {tag} &times;
          </Badge>
        ))}
        <Input
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAddTag()}
          placeholder="Add tag..."
          className="border-none bg-transparent shadow-none focus-visible:ring-0 h-7 w-32 text-xs px-1"
        />
      </div>

      <div className="flex-1 overflow-auto px-4 py-4">
        <NoteEditor initialContent={content} onSave={saveContent} />
      </div>
    </div>
  );
}

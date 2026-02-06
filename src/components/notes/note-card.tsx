"use client";

import Link from "next/link";
import { Star, Trash2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Note } from "@/types/note";

interface NoteCardProps {
  note: Note;
  onDelete: (id: string) => void;
  onToggleStar?: (id: string, starred: boolean) => void;
}

export function NoteCard({ note, onDelete, onToggleStar }: NoteCardProps) {
  return (
    <Card className="group relative hover:bg-accent/30 transition-colors">
      <Link href={`/notes/${note.id}`} className="absolute inset-0 z-0" />
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <span>{note.emoji}</span>
            <span className="line-clamp-1">{note.title}</span>
          </CardTitle>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={(e) => {
                e.preventDefault();
                onToggleStar?.(note.id, !note.starred);
              }}
            >
              <Star className={cn("h-4 w-4", note.starred && "fill-yellow-500 text-yellow-500")} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive"
              onClick={(e) => {
                e.preventDefault();
                onDelete(note.id);
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-2 text-xs mb-2">
          {note.preview || "Empty note"}
        </CardDescription>
        <div className="flex flex-wrap gap-1">
          {note.tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0">
              {tag}
            </Badge>
          ))}
        </div>
        <p className="text-[10px] text-muted-foreground mt-2">
          {new Date(note.updatedAt).toLocaleDateString()}
        </p>
      </CardContent>
    </Card>
  );
}

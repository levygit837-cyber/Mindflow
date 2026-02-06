"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Globe, Bot, Plus } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { Note } from "@/types/note";

export default function DashboardPage() {
  const [recentNotes, setRecentNotes] = useState<Note[]>([]);
  const [noteCount, setNoteCount] = useState(0);

  useEffect(() => {
    fetch("/api/notes?sortBy=updatedAt&sortOrder=desc")
      .then((r) => r.json())
      .then((notes: Note[]) => {
        setNoteCount(notes.length);
        setRecentNotes(notes.slice(0, 5));
      })
      .catch(() => {});
  }, []);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Welcome to OmniMind</h2>
        <p className="text-muted-foreground mt-1">
          Your personal AI agent with notes and knowledge graph
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/notes">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">Notes</CardTitle>
                  <CardDescription>{noteCount} notes</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/graph">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10 text-purple-500">
                  <Globe className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">Knowledge Graph</CardTitle>
                  <CardDescription>Explore in 3D</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/agent">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10 text-green-500">
                  <Bot className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">AI Agent</CardTitle>
                  <CardDescription>Chat with OmniMind</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        </Link>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Recent Notes</h3>
          <Link href="/notes">
            <Button variant="ghost" size="sm">View all</Button>
          </Link>
        </div>
        {recentNotes.length === 0 ? (
          <Card className="p-8 text-center text-muted-foreground">
            <p>No notes yet.</p>
            <Link href="/notes">
              <Button variant="outline" className="mt-3">
                <Plus className="h-4 w-4 mr-1" />
                Create your first note
              </Button>
            </Link>
          </Card>
        ) : (
          <div className="space-y-2">
            {recentNotes.map((note) => (
              <Link key={note.id} href={`/notes/${note.id}`}>
                <Card className="p-3 hover:bg-accent/30 transition-colors cursor-pointer">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{note.emoji}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{note.title}</p>
                      <p className="text-xs text-muted-foreground truncate">{note.preview || "Empty"}</p>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {new Date(note.updatedAt).toLocaleDateString()}
                    </span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

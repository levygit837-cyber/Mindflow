import { NextRequest, NextResponse } from "next/server";
import { listNotes, createNote } from "@/lib/notes/service";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("q") || undefined;
  const tags = searchParams.get("tags")?.split(",").filter(Boolean) || undefined;
  const starred = searchParams.get("starred") === "true" ? true : undefined;
  const sortBy = (searchParams.get("sortBy") as "updatedAt" | "createdAt" | "title") || undefined;
  const sortOrder = (searchParams.get("sortOrder") as "asc" | "desc") || undefined;

  const notes = listNotes({ query, tags, starred, sortBy, sortOrder });
  return NextResponse.json(notes);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const note = createNote(body);
  return NextResponse.json(note, { status: 201 });
}

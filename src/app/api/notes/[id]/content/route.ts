import { NextRequest, NextResponse } from "next/server";
import { getNoteContent, updateNoteContent, getNote } from "@/lib/notes/service";

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const note = getNote(id);
  if (!note) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const content = getNoteContent(id);
  return NextResponse.json(content);
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const content = await request.json();
  const note = updateNoteContent(id, content);
  if (!note) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(note);
}

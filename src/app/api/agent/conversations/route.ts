import { NextRequest, NextResponse } from "next/server";
import {
  listConversations,
  createConversation,
  deleteConversation,
} from "@backend/agent/conversations";

export async function GET() {
  const convs = listConversations();
  return NextResponse.json(convs);
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const title = (body as { title?: string }).title;
  const conv = createConversation(title);
  return NextResponse.json(conv);
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");
  if (!id) {
    return NextResponse.json({ error: "Missing id" }, { status: 400 });
  }
  deleteConversation(id);
  return NextResponse.json({ ok: true });
}

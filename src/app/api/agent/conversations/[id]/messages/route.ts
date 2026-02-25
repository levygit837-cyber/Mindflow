import { NextRequest, NextResponse } from "next/server";
import { getMessages } from "@backend/agent/conversations";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const msgs = getMessages(id);

  const parsed = msgs.map((m) => ({
    ...m,
    toolCalls: m.toolCalls ? JSON.parse(m.toolCalls) : null,
  }));

  return NextResponse.json(parsed);
}

import { NextResponse } from "next/server";
import { buildGraphData } from "@/lib/graph/service";

export async function GET() {
  const data = buildGraphData();
  return NextResponse.json(data);
}

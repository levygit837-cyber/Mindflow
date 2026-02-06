import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { settings } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { ensureDbInitialized } from "@/lib/db/init";
import { DEFAULT_SETTINGS, type AppSettings } from "@/types/settings";

export async function GET() {
  ensureDbInitialized();
  const rows = db.select().from(settings).all();
  const result: Record<string, string> = {};
  for (const row of rows) {
    result[row.key] = row.value;
  }

  const appSettings: AppSettings = {
    ...DEFAULT_SETTINGS,
    ...Object.fromEntries(
      Object.entries(result).filter(([key]) => key in DEFAULT_SETTINGS)
    ),
  } as AppSettings;

  return NextResponse.json(appSettings);
}

export async function PUT(request: NextRequest) {
  ensureDbInitialized();
  const body = await request.json();

  for (const [key, value] of Object.entries(body)) {
    if (typeof value === "string") {
      const existing = db.select().from(settings).where(eq(settings.key, key)).get();
      if (existing) {
        db.update(settings).set({ value }).where(eq(settings.key, key)).run();
      } else {
        db.insert(settings).values({ key, value }).run();
      }
    }
  }

  return NextResponse.json({ success: true });
}

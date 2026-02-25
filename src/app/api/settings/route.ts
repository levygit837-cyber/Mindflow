import { NextRequest, NextResponse } from "next/server";
import { DEFAULT_SETTINGS, type AppSettings } from "@shared/types/settings";
import { settingsUpdateSchema } from "@backend/schemas/settings.schema";

/**
 * In-memory settings store.
 * Returns DEFAULT_SETTINGS merged with any saved overrides.
 */
const settingsStore = new Map<string, string>();

export async function GET() {
  const overrides: Record<string, string> = {};
  for (const [key, value] of settingsStore) {
    overrides[key] = value;
  }

  const appSettings: AppSettings = {
    ...DEFAULT_SETTINGS,
    ...Object.fromEntries(
      Object.entries(overrides).filter(([key]) => key in DEFAULT_SETTINGS)
    ),
  } as AppSettings;

  return NextResponse.json(appSettings);
}

export async function PUT(request: NextRequest) {
  const body = await request.json();

  const parsed = settingsUpdateSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "Invalid settings", details: parsed.error.flatten().fieldErrors },
      { status: 400 }
    );
  }

  for (const [key, value] of Object.entries(parsed.data)) {
    if (value !== undefined) {
      settingsStore.set(key, String(value));
    }
  }

  return NextResponse.json({ success: true });
}

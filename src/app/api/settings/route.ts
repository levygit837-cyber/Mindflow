import { NextRequest, NextResponse } from "next/server";
import { DEFAULT_SETTINGS, type AppSettings } from "@/types/settings";

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

  for (const [key, value] of Object.entries(body)) {
    if (typeof value === "string") {
      settingsStore.set(key, value);
    }
  }

  return NextResponse.json({ success: true });
}

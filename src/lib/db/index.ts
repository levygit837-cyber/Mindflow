import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import * as schema from "./schema";
import path from "path";
import fs from "fs";

const DATA_DIR = path.join(process.cwd(), "data");
const NOTES_DIR = path.join(DATA_DIR, "notes");
const DB_PATH = path.join(DATA_DIR, "omnimind.db");

// Ensure directories exist
fs.mkdirSync(NOTES_DIR, { recursive: true });

const sqlite = new Database(DB_PATH);

// Enable WAL mode for better concurrent performance
sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

export const db = drizzle(sqlite, { schema });
export { sqlite };
export { DATA_DIR, NOTES_DIR, DB_PATH };

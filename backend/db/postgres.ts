import "server-only";
import pg from "pg";
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";

const { Pool } = pg;

let pool: pg.Pool | null = null;
let checkpointer: PostgresSaver | null = null;
let initialized = false;

function getPool(): pg.Pool {
  if (!pool) {
    const connectionString = process.env.DATABASE_URL;
    if (!connectionString) {
      throw new Error("DATABASE_URL environment variable is required");
    }
    pool = new Pool({
      connectionString,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
  }
  return pool;
}

export function getCheckpointer(): PostgresSaver {
  if (!checkpointer) {
    checkpointer = new PostgresSaver(getPool());
  }
  return checkpointer;
}

export async function ensureDbInitialized(): Promise<void> {
  if (initialized) return;
  const cp = getCheckpointer();
  await cp.setup();
  initialized = true;
}

export { getPool };

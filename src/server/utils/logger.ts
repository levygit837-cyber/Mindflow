type LogLevel = "error" | "warn" | "info" | "http" | "debug";

const LOG_LEVELS: Record<LogLevel, number> = {
  error: 0,
  warn: 1,
  info: 2,
  http: 3,
  debug: 4,
};

function getCurrentLevel(): number {
  const env = process.env.NODE_ENV || "development";
  if (env === "development") return LOG_LEVELS.debug;
  const configLevel = (process.env.LOG_LEVEL || "info") as LogLevel;
  return LOG_LEVELS[configLevel] ?? LOG_LEVELS.info;
}

function timestamp(): string {
  return new Date().toISOString();
}

function formatMeta(metadata?: Record<string, unknown>): string {
  if (!metadata || Object.keys(metadata).length === 0) return "";
  return " " + JSON.stringify(metadata);
}

function log(level: LogLevel, context: string, message: string, metadata?: Record<string, unknown>): void {
  if (LOG_LEVELS[level] > getCurrentLevel()) return;

  const prefix = `${timestamp()} [${level.toUpperCase()}] [${context}]`;
  const meta = formatMeta(metadata);

  switch (level) {
    case "error":
      console.error(`${prefix} ${message}${meta}`);
      break;
    case "warn":
      console.warn(`${prefix} ${message}${meta}`);
      break;
    case "debug":
      console.debug(`${prefix} ${message}${meta}`);
      break;
    default:
      console.log(`${prefix} ${message}${meta}`);
  }
}

export function createLogger(context: string) {
  return {
    error: (message: string, metadata?: Record<string, unknown>) =>
      log("error", context, message, metadata),
    warn: (message: string, metadata?: Record<string, unknown>) =>
      log("warn", context, message, metadata),
    info: (message: string, metadata?: Record<string, unknown>) =>
      log("info", context, message, metadata),
    http: (message: string, metadata?: Record<string, unknown>) =>
      log("http", context, message, metadata),
    debug: (message: string, metadata?: Record<string, unknown>) =>
      log("debug", context, message, metadata),
  };
}

export default createLogger("app");

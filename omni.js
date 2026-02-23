#!/usr/bin/env node
// omni.js — CLI do OmniMind
// Uso: node omni.js [--logs]

const { spawn } = require("child_process");
const http = require("http");

const args = process.argv.slice(2);
const showLogs = args.includes("--logs");

// Cores ANSI
const C = {
  reset: "\x1b[0m",
  dim: "\x1b[2m",
  bold: "\x1b[1m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
  magenta: "\x1b[35m",
  red: "\x1b[31m",
  white: "\x1b[37m",
  gray: "\x1b[90m",
};

const TYPE_COLOR = {
  thought: C.magenta,
  tool_call: C.yellow,
  tool_result: C.green,
  response: C.white,
  agent_step: C.blue,
  done: C.cyan,
  error: C.red,
  step: C.gray,
  notifier: C.gray,
};

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toTimeString().slice(0, 8) + "." + String(d.getMilliseconds()).padStart(3, "0");
  } catch {
    return "";
  }
}

function summarize(type, data) {
  if (!data) return "";
  if (type === "tool_call" || type === "tool_result") {
    try {
      const p = JSON.parse(data);
      if (p.name) {
        const extra = p.result
          ? ` → ${p.result.slice(0, 80)}`
          : p.args
          ? `(${JSON.stringify(p.args).slice(0, 80)})`
          : "";
        return `${p.name}${extra}`;
      }
    } catch {}
  }
  const str = typeof data === "string" ? data : JSON.stringify(data);
  return str.replace(/\n/g, " ").slice(0, 100);
}

function printLog(entry) {
  const color = TYPE_COLOR[entry.type] || C.gray;
  const time = C.gray + formatTime(entry.wallTime || entry.meta?.timestamp || new Date().toISOString()) + C.reset;
  const tag = color + C.bold + `[${(entry.type || "?").toUpperCase().slice(0, 8).padEnd(8)}]` + C.reset;
  const content = C.dim + summarize(entry.type, entry.data) + C.reset;
  const session = entry.sessionId ? C.gray + ` (${entry.sessionId.slice(0, 12)})` + C.reset : "";
  process.stdout.write(`${time} ${tag} ${content}${session}\n`);
}

function connectLogs(retries = 0) {
  const MAX_RETRIES = 30;
  const req = http.get("http://localhost:3000/api/agent/logs/stream", (res) => {
    process.stdout.write(`${C.green}${C.bold}● Logs conectados${C.reset}\n`);
    let buffer = "";
    res.on("data", (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const entry = JSON.parse(line.slice(6));
          if (entry.type === "connected") continue;
          printLog(entry);
        } catch {}
      }
    });
    res.on("end", () => {
      process.stdout.write(`${C.yellow}Logs desconectados. Reconectando...${C.reset}\n`);
      setTimeout(() => connectLogs(0), 2000);
    });
  });

  req.on("error", () => {
    if (retries < MAX_RETRIES) {
      setTimeout(() => connectLogs(retries + 1), 1000);
    } else {
      process.stdout.write(`${C.red}Não foi possível conectar ao stream de logs.${C.reset}\n`);
    }
  });
}

// Iniciar o servidor Next.js
process.stdout.write(`${C.bold}${C.cyan}🧠 OmniMind${C.reset}\n`);
if (showLogs) {
  process.stdout.write(`${C.gray}Modo: servidor + logs em tempo real${C.reset}\n\n`);
} else {
  process.stdout.write(`${C.gray}Modo: servidor${C.reset}\n\n`);
}

const server = spawn("pnpm", ["dev"], {
  cwd: __dirname,
  stdio: "inherit",
  shell: true,
});

if (showLogs) {
  // Aguardar o servidor subir antes de conectar aos logs
  process.stdout.write(`${C.gray}Aguardando servidor iniciar...${C.reset}\n`);
  setTimeout(() => connectLogs(), 4000);
}

server.on("close", (code) => {
  process.exit(code ?? 0);
});

process.on("SIGINT", () => {
  server.kill("SIGINT");
  process.exit(0);
});

process.on("SIGTERM", () => {
  server.kill("SIGTERM");
  process.exit(0);
});

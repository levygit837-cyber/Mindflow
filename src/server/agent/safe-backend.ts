/**
 * SafeBackend wraps any BackendProtocol and intercepts execute() calls
 * to block dangerous shell commands before they reach the shell.
 *
 * This is ENFORCEMENT, not advisory — even if the LLM ignores system
 * prompt instructions, these commands will never execute.
 */

// Patterns that ALWAYS block the command (case-insensitive, checked against normalized command)
const BLOCKED_PATTERNS: RegExp[] = [
  // File/directory deletion
  /\brm\s/i,
  /\brmdir\s/i,
  /\bdel\s/i,
  /\bfind\b.*-delete/i,
  /\bxargs\b.*\brm\b/i,

  // Disk/partition operations
  /\bmkfs\b/i,
  /\bfdisk\b/i,
  /\bdd\s/i,

  // Permission/ownership changes
  /\bchmod\s/i,
  /\bchown\s/i,

  // Process control
  /\bkill\b/i,
  /\bkillall\b/i,
  /\bpkill\b/i,

  // System control
  /\bshutdown\b/i,
  /\breboot\b/i,
  /\bhalt\b/i,
  /\bpoweroff\b/i,

  // Firewall
  /\biptables\b/i,
  /\bufw\b/i,
  /\bfirewall-cmd\b/i,

  // User management
  /\buseradd\b/i,
  /\buserdel\b/i,
  /\bpasswd\b/i,
  /\busermod\b/i,

  // Mount operations
  /\bmount\b/i,
  /\bumount\b/i,

  // Service control
  /\bsystemctl\b/i,
  /\bservice\s/i,

  // Cron modification
  /\bcrontab\s+-[re]/i,

  // Privilege escalation
  /\bsudo\b/i,
  /\bsu\s/i,
  /\bdoas\b/i,

  // Remote access
  /\bssh\b/i,
  /\bscp\b/i,
  /\brsync\b.*@/i,

  // Mutating HTTP
  /\bcurl\b.*-X\s*(POST|PUT|DELETE|PATCH)/i,
  /\bwget\b.*--post/i,

  // Pipe to shell (code execution)
  /\|\s*(bash|sh|zsh|fish)\b/i,
  /\beval\b/i,

  // Destructive git
  /\bgit\s+push\s+--force\b/i,
  /\bgit\s+reset\s+--hard\b/i,
  /\bgit\s+clean\s+-f/i,

  // Container deletion
  /\bdocker\s+(rm|rmi)\b/i,

  // Destructive SQL (in case of shell-piped SQL)
  /\bDROP\s+TABLE\b/i,
  /\bDELETE\s+FROM\b/i,
  /\bTRUNCATE\b/i,

  // Background processes
  /\bnohup\b/i,
  /\bdisown\b/i,

  // Fork bombs
  /:\(\)\s*\{/i,
];

interface ExecuteResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

/**
 * SafeBackend proxies all methods to the inner backend, but intercepts
 * execute() to check commands against the blocklist.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export class SafeBackend {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private inner: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(innerBackend: any) {
    this.inner = innerBackend;

    // Proxy all methods from inner backend
    return new Proxy(this, {
      get(target, prop, receiver) {
        // Use SafeBackend's own execute
        if (prop === "execute") {
          return target.execute.bind(target);
        }

        // For everything else, delegate to inner backend
        const innerValue = target.inner[prop];
        if (typeof innerValue === "function") {
          return innerValue.bind(target.inner);
        }
        return innerValue;
      },
    });
  }

  async execute(command: string): Promise<ExecuteResult> {
    const normalized = command.trim();

    for (const pattern of BLOCKED_PATTERNS) {
      if (pattern.test(normalized)) {
        const matchedRule = pattern.source;
        console.warn(
          `[SafeBackend] BLOCKED dangerous command: "${normalized}" (matched: ${matchedRule})`
        );
        return {
          stdout: "",
          stderr: `BLOCKED: This command matches a security rule and cannot be executed. Matched pattern: ${matchedRule}. If you need to perform this operation, ask the user to do it manually.`,
          exitCode: 1,
        };
      }
    }

    // Command is safe — delegate to inner backend
    return this.inner.execute(command);
  }
}

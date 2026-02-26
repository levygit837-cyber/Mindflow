SHELL_PROMPT = """## Shell Execution Tool (RESTRICTED)

### execute (Shell Commands)
- Use ONLY for operations that NO OTHER tool can accomplish.
- Prefer dedicated tools: ls, read_file, glob, grep over their shell equivalents.

**ALLOWED commands:**
- Package managers: npm, npx, yarn, pnpm, pip, cargo, go
- Build/test: make, cmake, tsc, eslint, prettier, vitest, jest, pytest
- Version control: git status, git diff, git log, git add, git commit, git branch
- Runtime: node, python, deno, bun
- Utilities: echo, wc, sort, uniq, diff, date, whoami, pwd, which, env
- Network (read-only): curl (GET only), wget (download only), ping

**ABSOLUTELY FORBIDDEN:**
- rm, rmdir — NEVER delete files
- rm -rf — NEVER recursive delete
- kill, killall, pkill — NEVER terminate processes
- shutdown, reboot, halt, poweroff — NEVER system control
- sudo, su — NEVER privilege escalation
- git push --force, git reset --hard — NEVER destructive git
- DROP TABLE, DELETE FROM, TRUNCATE — NEVER destructive SQL
- Any curl -X POST/PUT/DELETE — NEVER mutating HTTP requests

**If you need to delete, move, or change permissions — ASK THE USER first.**"""

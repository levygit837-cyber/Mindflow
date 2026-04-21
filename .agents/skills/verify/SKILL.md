---
name: verify
description: Run comprehensive quality checks (lint, typecheck, test) on Python or frontend code
---

# Verify Code Quality

Run all quality checks for the current working area.

## Usage

- `/verify` - Auto-detect context and run appropriate checks
- `/verify python` - Force Python checks
- `/verify frontend` - Force frontend checks

## What It Does

**For Python code (from `/python/`):**
```bash
make check
```
This runs: ruff format check, ruff lint, mypy typecheck, and pytest

**For Frontend code (from `/frontend/`):**
```bash
npm run lint && npm run test
```
This runs: ESLint and Vitest unit tests

## Auto-Detection

If no argument is provided, the skill detects context based on:
- Current working directory
- Recently modified files in the conversation
- Falls back to running both if ambiguous

## When to Use

- Before marking a task complete
- After making significant changes
- Before creating a pull request
- When you want comprehensive validation beyond just formatting

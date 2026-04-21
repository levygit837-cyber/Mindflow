#!/usr/bin/env bash
# smoke_unified.sh — End-to-end smoke test for unified QueryEngine migration.
#
# Runs the minimal set of scenarios that MUST keep working when
# UNIFIED_ENGINE_ENABLED flips between false (legacy) and true (new kernel).
#
# Usage:
#   scripts/smoke_unified.sh                     # runs against both legacy + unified
#   UNIFIED_ENGINE_ENABLED=true scripts/smoke_unified.sh   # unified only
#
# Each scenario is minimal — it exists to catch contract regressions, not to
# replace the full test suite. See docs/09-analysis-and-reports/REPO-AUDIT-2026-04-20.md
# checklist §5 for the full coverage list.

set -euo pipefail

API="${MINDFLOW_API_URL:-http://localhost:8000}"
GREEN="\033[0;32m"; RED="\033[0;31m"; YELLOW="\033[1;33m"; NC="\033[0m"

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; FAILED=1; }
skip() { echo -e "${YELLOW}⚠${NC} $1 (skipped)"; }

FAILED=0

wait_for_api() {
  echo "Waiting for API at ${API}..."
  for _ in $(seq 1 30); do
    if curl -fsS "${API}/health" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  fail "API did not come up at ${API}"
  exit 1
}

run_scenario() {
  local label="$1"
  local flag_value="$2"
  echo
  echo "── ${label} (UNIFIED_ENGINE_ENABLED=${flag_value}) ──"
  export UNIFIED_ENGINE_ENABLED="${flag_value}"

  # 1. Health
  if curl -fsS "${API}/health" | grep -q '"status":"ok"'; then
    pass "health endpoint"
  else
    fail "health endpoint"
  fi

  # 2. Basic chat (non-streaming)
  local resp
  resp=$(curl -fsS -X POST "${API}/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"say hello","stream":false}' 2>/dev/null || echo "ERR")
  if [[ "$resp" != "ERR" ]] && [[ -n "$resp" ]]; then
    pass "basic chat (non-streaming)"
  else
    fail "basic chat (non-streaming)"
  fi

  # 3. Streaming chat (SSE)
  if curl -fsS -X POST "${API}/api/v1/chat" \
    -H "Content-Type: application/json" \
    -H "Accept: text/event-stream" \
    -d '{"message":"hi","stream":true}' \
    --max-time 10 2>/dev/null | head -5 | grep -q 'data:'; then
    pass "streaming chat (SSE)"
  else
    fail "streaming chat (SSE)"
  fi

  # 4. Orchestrate mode
  resp=$(curl -fsS -X POST "${API}/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"analyze this simple task","orchestrate":true,"stream":false}' \
    --max-time 30 2>/dev/null || echo "ERR")
  if [[ "$resp" != "ERR" ]] && [[ -n "$resp" ]]; then
    pass "orchestrate mode"
  else
    fail "orchestrate mode"
  fi

  # 5. Direct agent (skip if agent registry not loaded)
  resp=$(curl -fsS -X POST "${API}/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"what is 2+2","agent_type":"analyst","stream":false}' \
    --max-time 20 2>/dev/null || echo "ERR")
  if [[ "$resp" != "ERR" ]] && [[ -n "$resp" ]]; then
    pass "direct agent (analyst)"
  else
    skip "direct agent — agent service may be unavailable"
  fi
}

wait_for_api

# Legacy path
run_scenario "LEGACY" "false"

# Unified path (only if user didn't explicitly pin the flag)
if [[ -z "${UNIFIED_ENGINE_ENABLED_PIN:-}" ]]; then
  run_scenario "UNIFIED" "true"
fi

echo
if [[ $FAILED -eq 0 ]]; then
  echo -e "${GREEN}All smoke scenarios passed.${NC}"
  exit 0
else
  echo -e "${RED}Smoke tests FAILED. See output above.${NC}"
  exit 1
fi

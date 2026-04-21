#!/usr/bin/env bash
set -euo pipefail

SERVER_NAME="aidesigner"
REMOVE_SERVER=0

usage() {
  cat <<'EOF'
Usage:
  bash .agents/skills/aidesigner-remove-auth/scripts/remove_aidesigner_auth.sh [--remove-server] [--server NAME]

Options:
  --remove-server   Also remove the MCP server entry from Codex config
  --server NAME     Override the MCP server name (default: aidesigner)
  -h, --help        Show this help
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remove-server)
      REMOVE_SERVER=1
      shift
      ;;
    --server)
      SERVER_NAME="${2:-}"
      if [[ -z "$SERVER_NAME" ]]; then
        echo "--server requires a value" >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_cmd codex

echo "Inspecting MCP server '$SERVER_NAME'..."
if server_info="$(codex mcp get "$SERVER_NAME" 2>/dev/null)"; then
  printf '%s\n' "$server_info"
else
  echo "Server '$SERVER_NAME' is not currently configured."
fi

echo
echo "Removing OAuth credentials for '$SERVER_NAME'..."
codex mcp logout "$SERVER_NAME"

if [[ "$REMOVE_SERVER" -eq 1 ]]; then
  echo
  echo "Removing MCP server configuration for '$SERVER_NAME'..."
  codex mcp remove "$SERVER_NAME"
fi

echo
echo "Verifying current MCP status..."
list_output="$(codex mcp list)"
printf '%s\n' "$list_output"

if [[ "$REMOVE_SERVER" -eq 1 ]]; then
  if codex mcp get "$SERVER_NAME" >/dev/null 2>&1; then
    echo "Server '$SERVER_NAME' is still configured." >&2
    exit 1
  fi
  echo
  echo "Done: OAuth removed and MCP server entry deleted."
  exit 0
fi

if printf '%s\n' "$list_output" | grep -E "^${SERVER_NAME}[[:space:]]" | grep -F "Not logged in" >/dev/null 2>&1; then
  echo
  echo "Done: OAuth removed and server remains configured as 'Not logged in'."
  exit 0
fi

echo "Unable to confirm logout state for '$SERVER_NAME'." >&2
exit 1

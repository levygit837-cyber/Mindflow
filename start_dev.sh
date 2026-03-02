#!/bin/bash

# OmniMind Development Stack Starter
# Starts: gRPC Server, FastAPI Backend, Vite Frontend

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting OmniMind Dev Stack...${NC}"

# Get absolute path to project root
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Fix Python Path for imports and generated gRPC files
export PYTHONPATH="$ROOT_DIR/python:$ROOT_DIR/python/omnimind_backend/grpc/generated:$PYTHONPATH"

# Ensure Database is correctly mapped
if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="postgresql+psycopg://omnimind_app:omnimind_dev_local_2026@localhost:5433/omnimind_v1"
fi

echo -e "Project Root: $ROOT_DIR"

# 1. Start gRPC Server
echo -e "${PURPLE}[1/3] Starting gRPC Server...${NC}"
cd "$ROOT_DIR/python" && uv run python -m omnimind_backend.grpc.server > "$ROOT_DIR/grpc.log" 2>&1 &
GRPC_PID=$!

# 2. Start FastAPI Backend
sleep 2
echo -e "${PURPLE}[2/3] Starting FastAPI Backend...${NC}"
cd "$ROOT_DIR/python" && uv run python -m omnimind_backend.main > "$ROOT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

# 3. Start Vite Frontend
sleep 2
echo -e "${PURPLE}[3/3] Starting Vite Frontend...${NC}"
cd "$ROOT_DIR/frontend" && npm run dev > "$ROOT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

echo -e "${GREEN}Stack is up and running!${NC}"
echo -e "Backend:  http://localhost:8000 (Logs: backend.log)"
echo -e "Frontend: http://localhost:5173 (Logs: frontend.log)"
echo -e "gRPC:     localhost:50051 (Logs: grpc.log)"
echo ""
echo -e "Press Ctrl+C to stop all services."

# Trap SIGINT to kill background processes
trap "echo -e '\n${BLUE}Stopping services...${NC}'; kill $GRPC_PID $BACKEND_PID $FRONTEND_PID; exit" SIGINT

# Wait for background processes
wait

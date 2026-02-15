#!/bin/bash

echo "🚀 Iniciando OmniMind..."
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

cleanup() {
    echo ""
    echo "👋 Encerrando processos..."
    if [ -n "$APP_PID" ]; then
        kill $APP_PID 2>/dev/null
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}✅ Iniciando OmniMind...${NC}"
pnpm dev &
APP_PID=$!

echo ""
echo -e "${BLUE}App: http://localhost:3000${NC}"
echo -e "${YELLOW}Pressione Ctrl+C para encerrar${NC}"

wait

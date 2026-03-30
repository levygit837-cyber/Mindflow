#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Stopping MindFlow Development Stack..."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_COMPOSE_FILE="python/docker-compose.backend.yml"

print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

stop_pid_file() {
    local label=$1
    local pid_file=$2

    if [ ! -f "${pid_file}" ]; then
        print_status "${label} PID file not found"
        return
    fi

    local pid
    pid=$(cat "${pid_file}")

    if kill -0 "${pid}" 2>/dev/null; then
        kill "${pid}"
        print_success "${label} stopped"
    else
        print_status "${label} was not running"
    fi

    rm -f "${pid_file}"
}

stop_services() {
    print_status "Stopping MindFlow services..."
    stop_pid_file "Backend API" "logs/api.pid"
    stop_pid_file "Frontend" "logs/frontend.pid"
    stop_pid_file "Background Worker" "logs/worker.pid"
}

cleanup_processes() {
    print_status "Cleaning up any remaining MindFlow processes..."
    pkill -f "mindflow-api" 2>/dev/null || true
    pkill -f "mindflow-worker" 2>/dev/null || true
    pkill -f "vite.*${FRONTEND_PORT:-5173}" 2>/dev/null || true
    print_success "Process cleanup completed"
}

stop_docker_services() {
    if ! command -v docker >/dev/null 2>&1; then
        print_status "Docker is not installed"
        return
    fi

    if [ ! -f "${BACKEND_COMPOSE_FILE}" ]; then
        print_status "Compose file not found: ${BACKEND_COMPOSE_FILE}"
        return
    fi

    read -r -p "Stop Docker services too? (y/N): " reply
    if [[ "${reply}" =~ ^[Yy]$ ]]; then
        docker compose -f "${BACKEND_COMPOSE_FILE}" down
        print_success "Docker services stopped"
    fi
}

main() {
    stop_services
    cleanup_processes
    stop_docker_services
    print_success "MindFlow Development Stack stopped successfully!"
}

main "$@"

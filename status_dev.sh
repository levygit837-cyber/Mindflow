#!/usr/bin/env bash
set -euo pipefail

echo "📊 MindFlow Development Stack Status"
echo "=================================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_COMPOSE_FILE="python/docker-compose.backend.yml"
APP_PORT="${APP_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[RUNNING]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[STOPPED]${NC} $1"
}

check_service() {
    local service_name=$1
    local pid_file=$2
    local url=$3

    if [ -f "${pid_file}" ]; then
        local pid
        pid=$(cat "${pid_file}")
        if kill -0 "${pid}" 2>/dev/null; then
            if [ -n "${url}" ] && curl -fsS "${url}" >/dev/null 2>&1; then
                print_success "${service_name} (PID: ${pid}) - ${url}"
            elif [ -n "${url}" ]; then
                print_warning "${service_name} (PID: ${pid}) - running but not responding yet"
            else
                print_success "${service_name} (PID: ${pid})"
            fi
            return
        fi

        print_warning "${service_name} PID file exists but process is not running"
        return
    fi

    if [ -n "${url}" ] && curl -fsS "${url}" >/dev/null 2>&1; then
        print_warning "${service_name} is responding but was not started by this script"
        return
    fi

    print_error "${service_name} is not running"
}

check_port() {
    local port=$1
    local service=$2

    if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
        print_success "${service} is using port ${port}"
    else
        print_error "${service} is not using port ${port}"
    fi
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        print_warning "Docker not installed"
        return
    fi

    if [ ! -f "${BACKEND_COMPOSE_FILE}" ]; then
        print_warning "Compose file not found: ${BACKEND_COMPOSE_FILE}"
        return
    fi

    print_status "Docker Services:"
    docker compose -f "${BACKEND_COMPOSE_FILE}" ps
}

check_logs() {
    print_status "Recent log entries (last 5 lines):"

    for log_file in logs/api.log logs/frontend.log logs/worker.log; do
        if [ -f "${log_file}" ]; then
            echo ""
            echo "$(basename "${log_file}" .log | tr '[:lower:]' '[:upper:]') LOG:"
            tail -5 "${log_file}" | sed 's/^/  /'
        fi
    done
}

echo ""
echo "🔍 Service Status:"
check_service "Backend API" "logs/api.pid" "http://127.0.0.1:${APP_PORT}/health"
check_service "Frontend" "logs/frontend.pid" "http://127.0.0.1:${FRONTEND_PORT}"
check_service "Background Worker" "logs/worker.pid" ""

echo ""
echo "🌐 Port Status:"
check_port "${APP_PORT}" "Backend API"
check_port "${FRONTEND_PORT}" "Frontend"

echo ""
check_docker

echo ""
check_logs

echo ""
echo "📝 Quick Actions:"
echo "   • Start all:  ./start_dev.sh"
echo "   • Stop all:   ./stop_dev.sh"
echo "   • View logs: tail -f logs/api.log logs/frontend.log logs/worker.log"

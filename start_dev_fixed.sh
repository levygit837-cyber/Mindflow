#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting MindFlow Development Stack..."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_COMPOSE_FILE="python/docker-compose.backend.yml"
APP_PORT="${APP_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
API_HEALTH_URL="http://127.0.0.1:${APP_PORT}/health"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"
POSTGRES_CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-mindflow-postgres-v1}"

API_STARTED=0
FRONTEND_STARTED=0
WORKER_STARTED=0
STARTUP_COMPLETE=0

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

run_compose() {
    docker compose -f "${BACKEND_COMPOSE_FILE}" "$@"
}

start_detached() {
    local log_path=$1
    shift

    if command -v setsid >/dev/null 2>&1; then
        setsid "$@" >"${log_path}" 2>&1 < /dev/null &
    else
        nohup "$@" >"${log_path}" 2>&1 < /dev/null &
    fi

    echo $!
}

port_listener_details() {
    local port=$1

    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"${port}" -sTCP:LISTEN || true
        return
    fi

    ss -ltnp "( sport = :${port} )" || true
}

is_port_listening() {
    local port=$1

    if command -v lsof >/dev/null 2>&1; then
        lsof -tiTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
        return
    fi

    ss -ltn "( sport = :${port} )" | grep -q ":${port}"
}

wait_for_http() {
    local url=$1
    local service_name=$2
    local attempts=${3:-30}
    local sleep_seconds=${4:-1}

    for _ in $(seq 1 "${attempts}"); do
        if curl -fsS "${url}" >/dev/null 2>&1; then
            print_success "${service_name} is running at ${url}"
            return 0
        fi

        sleep "${sleep_seconds}"
    done

    return 1
}

wait_for_container_health() {
    local container_name=$1
    local display_name=$2
    local attempts=${3:-30}

    for _ in $(seq 1 "${attempts}"); do
        local status
        status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_name}" 2>/dev/null || true)

        if [ "${status}" = "healthy" ] || [ "${status}" = "running" ]; then
            print_success "${display_name} is ${status}"
            return 0
        fi

        sleep 2
    done

    return 1
}

cleanup() {
    if [ "${STARTUP_COMPLETE}" -eq 1 ]; then
        return
    fi

    print_status "Cleaning up incomplete startup..."

    if [ "${API_STARTED}" -eq 1 ] && [ -f "logs/api.pid" ]; then
        kill "$(cat logs/api.pid)" 2>/dev/null || true
        rm -f logs/api.pid
    fi

    if [ "${FRONTEND_STARTED}" -eq 1 ] && [ -f "logs/frontend.pid" ]; then
        kill "$(cat logs/frontend.pid)" 2>/dev/null || true
        rm -f logs/frontend.pid
    fi

    if [ "${WORKER_STARTED}" -eq 1 ] && [ -f "logs/worker.pid" ]; then
        kill "$(cat logs/worker.pid)" 2>/dev/null || true
        rm -f logs/worker.pid
    fi

    print_success "Cleanup completed"
}

trap cleanup EXIT INT TERM

if [ ! -f "README.md" ] || [ ! -d "python" ] || [ ! -d "frontend" ]; then
    print_error "Please run this script from the MindFlow project root directory"
    exit 1
fi

check_dependencies() {
    print_status "Checking dependencies..."

    if ! command -v uv >/dev/null 2>&1; then
        print_error "uv is not installed. Please install uv first."
        exit 1
    fi

    if ! command -v npm >/dev/null 2>&1; then
        print_error "npm is not installed. Please install Node.js and npm first."
        exit 1
    fi

    if ! command -v docker >/dev/null 2>&1; then
        print_error "Docker is required to start the backend infrastructure."
        exit 1
    fi

    print_success "Dependencies check completed"
}

setup_environment() {
    print_status "Setting up environment..."

    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
            print_warning "Review .env before using external integrations."
        else
            print_error ".env.example not found"
            exit 1
        fi
    fi

    cd python
    print_status "Syncing Python dependencies..."
    uv sync
    cd ..

    cd frontend
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm install
    else
        print_status "Frontend dependencies already installed"
    fi
    cd ..

    print_success "Environment setup completed"
}

start_infrastructure() {
    print_status "Starting backend infrastructure..."

    if [ ! -f "${BACKEND_COMPOSE_FILE}" ]; then
        print_error "Compose file not found: ${BACKEND_COMPOSE_FILE}"
        exit 1
    fi

    run_compose up -d
    print_success "Docker services started"

    print_status "Waiting for PostgreSQL to be ready..."
    if ! wait_for_container_health "${POSTGRES_CONTAINER_NAME}" "PostgreSQL"; then
        print_error "PostgreSQL did not become ready in time"
        run_compose ps
        exit 1
    fi

    print_status "Running database migrations..."
    cd python
    uv run alembic upgrade head
    cd ..

    print_success "Database migrations completed"
}

start_backend() {
    print_status "Starting Backend API..."

    if curl -fsS "${API_HEALTH_URL}" >/dev/null 2>&1; then
        print_success "Backend API already running at ${API_HEALTH_URL}"
        return
    fi

    if is_port_listening "${APP_PORT}"; then
        print_error "Port ${APP_PORT} is already in use by another process."
        port_listener_details "${APP_PORT}"
        print_warning "Stop the conflicting process or set APP_PORT to another value before retrying."
        exit 1
    fi

    cd python
    local api_pid
    api_pid=$(start_detached ../logs/api.log env APP_PORT="${APP_PORT}" uv run mindflow-api)
    cd ..

    echo "${api_pid}" > logs/api.pid
    API_STARTED=1

    if ! wait_for_http "${API_HEALTH_URL}" "Backend API"; then
        print_error "Backend API failed to start"
        tail -20 logs/api.log || true
        exit 1
    fi
}

start_frontend() {
    print_status "Starting Frontend..."

    if is_port_listening "${FRONTEND_PORT}"; then
        print_error "Port ${FRONTEND_PORT} is already in use."
        port_listener_details "${FRONTEND_PORT}"
        print_warning "Stop the conflicting process or set FRONTEND_PORT to another value before retrying."
        exit 1
    fi

    cd frontend
    local frontend_pid
    frontend_pid=$(start_detached ../logs/frontend.log env FRONTEND_PORT="${FRONTEND_PORT}" npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}")
    cd ..

    echo "${frontend_pid}" > logs/frontend.pid
    FRONTEND_STARTED=1

    if ! wait_for_http "${FRONTEND_URL}" "Frontend" 30 1; then
        print_error "Frontend failed to start"
        tail -20 logs/frontend.log || true
        exit 1
    fi
}

start_worker() {
    print_status "Starting Background Worker..."

    if pgrep -f "mindflow-worker" >/dev/null 2>&1; then
        print_warning "Background worker already running; skipping duplicate start"
        return
    fi

    cd python
    local worker_pid
    worker_pid=$(start_detached ../logs/worker.log uv run mindflow-worker)
    cd ..

    echo "${worker_pid}" > logs/worker.pid
    WORKER_STARTED=1

    sleep 2
    if ! kill -0 "${worker_pid}" 2>/dev/null; then
        print_error "Background worker failed to start"
        tail -20 logs/worker.log || true
        exit 1
    fi

    print_success "Background worker started"
}

start_services() {
    print_status "Starting MindFlow services..."
    mkdir -p logs

    start_backend
    start_frontend
    start_worker
}

show_status() {
    echo ""
    echo "🎉 MindFlow Development Stack is running!"
    echo ""
    echo "📊 Services Status:"
    echo "   • Frontend:          ${FRONTEND_URL}"
    echo "   • Backend API:       http://127.0.0.1:${APP_PORT}"
    echo "   • API Docs:          http://127.0.0.1:${APP_PORT}/docs"
    echo "   • Background Worker: Running"
    echo ""
    echo "📝 Logs:"
    echo "   • API:      logs/api.log"
    echo "   • Frontend: logs/frontend.log"
    echo "   • Worker:   logs/worker.log"
    echo ""
    echo "🛑 To stop all services:"
    echo "   ./stop_dev.sh"
    echo ""
    echo "🔍 To check service status:"
    echo "   ./status_dev.sh"
    echo ""
}

main() {
    echo "MindFlow Development Stack Starter"
    echo "================================="
    echo ""

    check_dependencies
    setup_environment
    start_infrastructure
    start_services
    show_status
    STARTUP_COMPLETE=1
}

main "$@"

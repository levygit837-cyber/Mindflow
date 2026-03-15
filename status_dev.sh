#!/usr/bin/env bash
set -euo pipefail

echo "📊 MindFlow Development Stack Status"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check service status
check_service() {
    local service_name=$1
    local pid_file=$2
    local url=$3
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            if [ -n "$url" ]; then
                if curl -s "$url" > /dev/null 2>&1; then
                    print_success "$service_name (PID: $pid) - $url"
                else
                    print_warning "$service_name (PID: $pid) - Starting up or not responding"
                fi
            else
                print_success "$service_name (PID: $pid)"
            fi
        else
            print_error "$service_name (PID file exists but process not running)"
        fi
    else
        print_error "$service_name (Not started)"
    fi
}

# Check ports
check_port() {
    local port=$1
    local service=$2
    
    if lsof -i :$port > /dev/null 2>&1; then
        print_success "$service is using port $port"
    else
        print_error "$service is not using port $port"
    fi
}

# Check Docker services
check_docker() {
    if command -v docker &> /dev/null; then
        print_status "Docker Services:"
        if [ -f "docker-compose.yml" ]; then
            docker-compose ps
        else
            print_warning "docker-compose.yml not found"
        fi
    else
        print_warning "Docker not installed"
    fi
}

# Check logs for errors
check_logs() {
    print_status "Recent Log Entries (last 5 lines):"
    
    for log_file in logs/api.log logs/frontend.log logs/worker.log; do
        if [ -f "$log_file" ]; then
            echo ""
            echo "$(basename "$log_file" .log | tr '[:lower:]' '[:upper:]') LOG:"
            tail -5 "$log_file" | sed 's/^/  /'
        fi
    done
}

# Main checks
echo ""
echo "🔍 Service Status:"
check_service "Backend API" "logs/api.pid" "http://localhost:8000/health"
check_service "Frontend" "logs/frontend.pid" "http://localhost:5173"
check_service "Background Worker" "logs/worker.pid" ""

echo ""
echo "🌐 Port Status:"
check_port 8000 "Backend API"
check_port 5173 "Frontend"
check_port 5433 "PostgreSQL"
check_port 6380 "Redis"

echo ""
check_docker

echo ""
check_logs

echo ""
echo "📝 Quick Actions:"
echo "   • Start all:  ./start_dev.sh"
echo "   • Stop all:   ./stop_dev.sh"
echo "   • View logs: tail -f logs/api.log logs/frontend.log logs/worker.log"

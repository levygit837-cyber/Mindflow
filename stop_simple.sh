#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Stopping MindFlow Services..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Stop services
stop_services() {
    print_status "Stopping MindFlow services..."
    
    # Stop API
    if [ -f "logs/api.pid" ]; then
        API_PID=$(cat logs/api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            kill $API_PID
            print_success "Backend API stopped"
        else
            print_status "Backend API was not running"
        fi
        rm logs/api.pid
    else
        print_status "API PID file not found"
    fi
    
    # Stop Frontend
    if [ -f "logs/frontend.pid" ]; then
        FRONTEND_PID=$(cat logs/frontend.pid)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            kill $FRONTEND_PID
            print_success "Frontend stopped"
        else
            print_status "Frontend was not running"
        fi
        rm logs/frontend.pid
    else
        print_status "Frontend PID file not found"
    fi
    
    # Clean up any remaining processes
    cleanup_processes
}

# Clean up any remaining processes
cleanup_processes() {
    print_status "Cleaning up any remaining processes..."
    
    # Kill any remaining mindflow processes
    pkill -f "mindflow-api" 2>/dev/null || true
    pkill -f "vite.*5173" 2>/dev/null || true
    
    print_success "Cleanup completed"
}

print_success "MindFlow services stopped successfully!"

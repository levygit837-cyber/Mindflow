#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting MindFlow (Simple Mode - No Docker)"

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
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "python" ] || [ ! -d "frontend" ]; then
    print_error "Please run this script from the MindFlow project root directory"
    exit 1
fi

# Setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Copy .env if it doesn't exist
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
            print_warning "Please edit .env file with your API keys"
        else
            print_error ".env.example not found"
            exit 1
        fi
    fi
    
    # Setup Python environment
    cd python
    print_status "Setting up Python environment..."
    uv sync
    cd ..
    
    # Setup frontend
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

# Start services without database
start_services() {
    print_status "Starting MindFlow services..."
    
    # Create logs directory
    mkdir -p logs
    
    # Start backend API
    print_status "Starting Backend API..."
    cd python
    uv run mindflow-api > ../logs/api.log 2>&1 &
    API_PID=$!
    cd ..
    echo $API_PID > logs/api.pid
    
    # Wait a bit for API to start
    sleep 5
    
    # Check if API is running
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend API is running on http://localhost:8000"
    else
        print_warning "Backend API might not be fully started yet"
        print_status "Check logs: tail -f logs/api.log"
    fi
    
    # Start frontend
    print_status "Starting Frontend..."
    cd frontend
    npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    echo $FRONTEND_PID > logs/frontend.pid
    
    # Wait a bit for frontend to start
    sleep 3
    
    print_success "Frontend is running on http://localhost:5173"
}

# Show status
show_status() {
    echo ""
    echo "🎉 MindFlow Development Stack is running!"
    echo ""
    echo "📊 Services Status:"
    echo "   • Frontend:     http://localhost:5173"
    echo "   • Backend API:  http://localhost:8000"
    echo "   • API Docs:     http://localhost:8000/docs"
    echo ""
    echo "📝 Logs:"
    echo "   • API:     logs/api.log"
    echo "   • Frontend: logs/frontend.log"
    echo ""
    echo "🛑 To stop all services:"
    echo "   ./stop_simple.sh"
    echo ""
    echo "⚠️  Note: Running without PostgreSQL/Redis - some features may be limited"
    echo ""
}

# Main execution
main() {
    echo "MindFlow Simple Starter (No Database)"
    echo "====================================="
    echo ""
    
    setup_environment
    start_services
    show_status
}

# Trap to handle cleanup
cleanup() {
    print_status "Cleaning up..."
    # Kill any background processes
    if [ -f "logs/api.pid" ]; then
        kill $(cat logs/api.pid) 2>/dev/null || true
        rm logs/api.pid
    fi
    if [ -f "logs/frontend.pid" ]; then
        kill $(cat logs/frontend.pid) 2>/dev/null || true
        rm logs/frontend.pid
    fi
    print_success "Cleanup completed"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Run main function
main "$@"

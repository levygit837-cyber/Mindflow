#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting MindFlow Development Stack..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check for required dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install uv first."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install Node.js and npm first."
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        print_warning "Docker is not installed. You'll need to start PostgreSQL and Redis manually."
    fi
    
    print_success "Dependencies check completed"
}

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
    if [ ! -d ".venv" ]; then
        print_status "Creating Python virtual environment..."
        uv sync
    else
        print_status "Updating Python dependencies..."
        uv sync
    fi
    
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

# Start infrastructure
start_infrastructure() {
    print_status "Starting infrastructure services..."
    
    if command -v docker &> /dev/null; then
        # Start Docker services
        if [ -f "docker-compose.yml" ]; then
            docker compose up -d
            print_success "Docker services started"
            
            # Wait for PostgreSQL
            print_status "Waiting for PostgreSQL to be ready..."
            sleep 5
            
            # Run database migrations
            cd python
            uv run alembic upgrade head
            cd ..
            
            print_success "Database migrations completed"
        else
            print_warning "docker-compose.yml not found. Please start PostgreSQL and Redis manually."
        fi
    else
        print_warning "Docker not available. Please start PostgreSQL and Redis manually."
    fi
}

# Start services
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
    sleep 3
    
    # Check if API is running
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend API is running on http://localhost:8000"
    else
        print_warning "Backend API might not be fully started yet"
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
    
    # Start worker (optional)
    print_status "Starting Background Worker..."
    cd python
    uv run mindflow-worker > ../logs/worker.log 2>&1 &
    WORKER_PID=$!
    cd ..
    echo $WORKER_PID > logs/worker.pid
    
    print_success "Background worker started"
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
    echo "   • Background Worker: Running"
    echo ""
    echo "📝 Logs:"
    echo "   • API:     logs/api.log"
    echo "   • Frontend: logs/frontend.log"
    echo "   • Worker:  logs/worker.log"
    echo ""
    echo "🛑 To stop all services:"
    echo "   ./stop_dev.sh"
    echo ""
    echo "🔍 To check service status:"
    echo "   ./status_dev.sh"
    echo ""
}

# Main execution
main() {
    echo "MindFlow Development Stack Starter"
    echo "================================="
    echo ""
    
    check_dependencies
    setup_environment
    start_infrastructure
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
    if [ -f "logs/worker.pid" ]; then
        kill $(cat logs/worker.pid) 2>/dev/null || true
        rm logs/worker.pid
    fi
    print_success "Cleanup completed"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Run main function
main "$@"

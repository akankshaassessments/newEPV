#!/bin/bash

# EPV Development Helper Script
# Choose between local development or Docker development

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Local development (your current setup)
run_local() {
    print_header "Starting Local Development Environment"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_warning "Virtual environment not found. Creating one..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    # Install/update dependencies
    print_status "Installing dependencies..."
    pip install -r requirements.txt
    
    # Start the application
    print_status "Starting EPV application..."
    print_status "Access your application at: http://127.0.0.1:5000"
    python app.py
}

# Docker development
run_docker_dev() {
    print_header "Starting Docker Development Environment"
    
    # Stop any existing containers
    print_status "Stopping existing containers..."
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    
    # Start development containers
    print_status "Starting development containers..."
    docker-compose -f docker-compose.dev.yml up --build
}

# Docker production (for testing production setup locally)
run_docker_prod() {
    print_header "Starting Docker Production Environment (Local Testing)"
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from example..."
        cp .env.example .env
        print_warning "Please edit .env file with your configuration"
        return 1
    fi
    
    # Stop any existing containers
    print_status "Stopping existing containers..."
    docker-compose down 2>/dev/null || true
    
    # Start production containers
    print_status "Starting production containers..."
    docker-compose up --build
}

# Show status of all environments
show_status() {
    print_header "Environment Status"
    
    echo ""
    echo "Local Development:"
    if pgrep -f "python app.py" > /dev/null; then
        print_status "Local Flask app is running"
    else
        echo "  Local Flask app is not running"
    fi
    
    echo ""
    echo "Docker Development:"
    if docker ps | grep epv-app-dev > /dev/null; then
        print_status "Docker development containers are running"
        docker-compose -f docker-compose.dev.yml ps
    else
        echo "  Docker development containers are not running"
    fi
    
    echo ""
    echo "Docker Production:"
    if docker ps | grep epv-app > /dev/null; then
        print_status "Docker production containers are running"
        docker-compose ps
    else
        echo "  Docker production containers are not running"
    fi
}

# Stop all environments
stop_all() {
    print_header "Stopping All Environments"
    
    # Stop local Flask app
    print_status "Stopping local Flask app..."
    pkill -f "python app.py" 2>/dev/null || true
    
    # Stop Docker development
    print_status "Stopping Docker development..."
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    
    # Stop Docker production
    print_status "Stopping Docker production..."
    docker-compose down 2>/dev/null || true
    
    print_status "All environments stopped"
}

# Show help
show_help() {
    echo "EPV Development Helper"
    echo "====================="
    echo ""
    echo "Usage: $0 {local|docker-dev|docker-prod|status|stop|help}"
    echo ""
    echo "Commands:"
    echo "  local       - Run local development (your current setup)"
    echo "  docker-dev  - Run Docker development environment"
    echo "  docker-prod - Run Docker production environment (for testing)"
    echo "  status      - Show status of all environments"
    echo "  stop        - Stop all running environments"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 local       # Start local development as you do now"
    echo "  $0 docker-dev  # Test Docker development setup"
    echo "  $0 status      # Check what's running"
    echo "  $0 stop        # Stop everything"
}

# Handle script arguments
case "${1:-help}" in
    "local")
        run_local
        ;;
    "docker-dev")
        run_docker_dev
        ;;
    "docker-prod")
        run_docker_prod
        ;;
    "status")
        show_status
        ;;
    "stop")
        stop_all
        ;;
    "help"|*)
        show_help
        ;;
esac

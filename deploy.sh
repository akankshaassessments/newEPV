#!/bin/bash

# EPV Application Deployment Script
# This script helps deploy the EPV application using Docker

set -e

echo "🚀 EPV Application Deployment Script"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    print_header "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed."
}

# Check if .env file exists
check_env_file() {
    print_header "Checking environment configuration..."
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Please edit .env file with your actual configuration before proceeding."
            print_warning "Press Enter to continue after editing .env file..."
            read
        else
            print_error ".env.example file not found. Please create .env file manually."
            exit 1
        fi
    else
        print_status ".env file found."
    fi
}

# Create necessary directories
create_directories() {
    print_header "Creating necessary directories..."
    mkdir -p logs uploads temp ssl
    chmod 755 logs uploads temp
    print_status "Directories created successfully."
}

# Build and start services
deploy_application() {
    print_header "Building and starting EPV application..."
    
    # Stop existing containers
    print_status "Stopping existing containers..."
    docker-compose down
    
    # Build images
    print_status "Building Docker images..."
    docker-compose build --no-cache
    
    # Start services
    print_status "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    print_status "Checking service health..."
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        print_status "Application is healthy and running!"
    else
        print_warning "Application health check failed. Checking logs..."
        docker-compose logs web
    fi
}

# Show deployment information
show_deployment_info() {
    print_header "Deployment Information"
    echo ""
    echo "🌐 Application URL: http://localhost:5000"
    echo "🗄️  Database: MySQL on localhost:3306"
    echo "📊 Redis: localhost:6379"
    echo "🔧 Nginx: localhost:80 (if enabled)"
    echo ""
    echo "📋 Useful Commands:"
    echo "  View logs:           docker-compose logs -f"
    echo "  Stop application:    docker-compose down"
    echo "  Restart application: docker-compose restart"
    echo "  Update application:  ./deploy.sh"
    echo ""
    echo "📁 Important Directories:"
    echo "  Logs:    ./logs/"
    echo "  Uploads: ./uploads/"
    echo "  Temp:    ./temp/"
    echo ""
}

# Main deployment process
main() {
    echo ""
    print_status "Starting EPV Application deployment..."
    echo ""
    
    check_docker
    check_env_file
    create_directories
    deploy_application
    show_deployment_info
    
    print_status "Deployment completed successfully! 🎉"
    echo ""
    print_status "You can now access your EPV application at: http://localhost:5000"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        print_header "Stopping EPV application..."
        docker-compose down
        print_status "Application stopped."
        ;;
    "restart")
        print_header "Restarting EPV application..."
        docker-compose restart
        print_status "Application restarted."
        ;;
    "logs")
        print_header "Showing application logs..."
        docker-compose logs -f
        ;;
    "status")
        print_header "Checking application status..."
        docker-compose ps
        ;;
    "clean")
        print_header "Cleaning up Docker resources..."
        docker-compose down -v
        docker system prune -f
        print_status "Cleanup completed."
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status|clean}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy the application (default)"
        echo "  stop    - Stop the application"
        echo "  restart - Restart the application"
        echo "  logs    - Show application logs"
        echo "  status  - Show container status"
        echo "  clean   - Clean up Docker resources"
        exit 1
        ;;
esac

#!/bin/bash

# BaseChat System Startup Script
# This script starts all system services and application services
# Usage: ./start-system.sh [llm_type]
#   llm_type: openai (default) or vllm

set -e

# Parse command line arguments
LLM_TYPE=${1:-openai}  # Default to openai if no argument provided

echo "🚀 Starting BaseChat System with LLM type: $LLM_TYPE"

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

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists in backend
if [ ! -f "backend/.env" ]; then
    print_warning "backend/.env file not found. Creating from example..."
    cp backend/env.example backend/.env
    print_warning "Please update backend/.env with your OpenAI API key and other settings."
fi

# Check if .env file exists in system-docker
if [ ! -f "system-docker/.env" ]; then
    print_warning "system-docker/.env file not found. Creating from example..."
    cp system-docker/env.example system-docker/.env
    print_success "system-docker/.env created with default settings."
fi

# Function to wait for service health
wait_for_service() {
    local service_name=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps $service_name | grep -q "healthy"; then
            print_success "$service_name is healthy!"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts: $service_name is not ready yet..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to become healthy after $max_attempts attempts"
    return 1
}

# Start system services first
print_status "Starting system services (PostgreSQL, Redis, Nginx)..."
cd system-docker
docker-compose up -d

# Wait for PostgreSQL to be ready
if wait_for_service "postgres"; then
    print_success "PostgreSQL is ready!"
else
    print_error "PostgreSQL failed to start properly"
    exit 1
fi

# Wait for Redis to be ready
if wait_for_service "redis"; then
    print_success "Redis is ready!"
else
    print_error "Redis failed to start properly"
    exit 1
fi

cd ..

# Start application services
print_status "Starting application services (Backend, Frontend)..."
cd backend

# Start services based on LLM type
if [ "$LLM_TYPE" = "vllm" ]; then
    print_status "Starting with vLLM profile..."
    docker-compose --profile vllm up -d --build
else
    print_status "Starting with OpenAI profile..."
    docker-compose --profile openai up -d --build
fi

cd ..

# Wait for all services to be ready
print_status "Waiting for all services to be ready..."

# Wait for main-backend
sleep 30
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Main Backend is ready!"
else
    print_warning "Main Backend might still be starting..."
fi

# Wait for frontend
sleep 10
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    print_success "Frontend is ready!"
else
    print_warning "Frontend might still be starting..."
fi

# Final status check
print_status "Checking service status..."
echo ""
echo "📊 Service Status:"
echo "=================="

# System services
cd system-docker
docker-compose ps
cd ..

echo ""
# Application services
cd backend
docker-compose ps
cd ..

echo ""
print_success "🎉 BaseChat system is starting up!"
echo ""
echo "🤖 LLM Configuration:"
echo "   Type:         $LLM_TYPE"
echo "   Service:      $(if [ "$LLM_TYPE" = "vllm" ]; then echo "vLLM (local)"; else echo "OpenAI (cloud)"; fi)"
echo ""
echo "🌐 Access URLs:"
echo "   Frontend:     http://localhost:3000"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   LLM Agent:    http://localhost:8001"
echo "   MCP Server:   http://localhost:8002"
echo "   Nginx:        http://localhost:80"
echo ""
echo "🗄️  Database:"
echo "   PostgreSQL:   localhost:15432"
echo "   Redis:        localhost:6379"
echo ""
echo "📝 Useful commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop system:  ./stop-system.sh"
echo "   Restart:      ./restart-system.sh"
echo "" 
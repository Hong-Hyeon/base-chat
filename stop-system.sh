#!/bin/bash

# BaseChat System Stop Script
# This script stops all system services and application services

set -e

echo "🛑 Stopping BaseChat System..."

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

# Stop application services first
print_status "Stopping application services (Backend, Frontend)..."
cd backend
docker-compose --profile openai --profile vllm down
cd ..

# Stop system services
print_status "Stopping system services (PostgreSQL, Redis, Nginx)..."
cd system-docker
docker-compose down
cd ..

print_success "🎉 All BaseChat services have been stopped!"
echo ""
echo "📝 To start the system again, run: ./start-system.sh"
echo "" 
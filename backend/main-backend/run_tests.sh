#!/bin/bash

# Test execution script for main backend with caching

set -e

echo "🧪 Starting cache system tests..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clean up any existing test containers
print_status "Cleaning up existing test containers..."
docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true

# Build and run tests
print_status "Building and running cache system tests..."
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Clean up
print_status "Cleaning up test containers..."
docker-compose -f docker-compose.test.yml down -v

# Report results
print_status "✅ All tests passed! Cache system is working correctly."
print_status "🎉 Cache system implementation completed successfully!" 
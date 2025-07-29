#!/bin/bash

# BaseChat System Restart Script
# This script restarts all system services and application services

set -e

echo "🔄 Restarting BaseChat System..."

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

# Stop all services first
print_status "Stopping all services..."
./stop-system.sh

# Wait a moment for services to fully stop
sleep 5

# Start all services
print_status "Starting all services..."
./start-system.sh

print_success "🎉 BaseChat system has been restarted!"
echo "" 
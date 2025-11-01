#!/bin/bash

# EDIH ADRIA Analytics Dashboard - Deployment Script
# Usage: ./deploy.sh [environment]
# Environment: dev, staging, production (default: dev)

set -e

ENVIRONMENT=${1:-dev}
echo "🚀 Deploying EDIH Analytics Dashboard - Environment: $ENVIRONMENT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
    exit 1
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if .env file exists
if [ ! -f .env ]; then
    warning ".env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    warning "Please edit .env file with your configuration before continuing"
    exit 1
fi

success ".env file found"

# Check Docker installation
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
fi

success "Docker is installed"

# Check Docker Compose installation
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed. Please install Docker Compose first."
fi

success "Docker Compose is installed"

# Validate Python dependencies
echo "📦 Checking Python dependencies..."
if [ ! -f requirements.txt ]; then
    error "requirements.txt not found"
fi

success "requirements.txt found"

# Build Docker image
echo "🔨 Building Docker image..."
docker-compose build || error "Failed to build Docker image"

success "Docker image built successfully"

# Start services
echo "🚀 Starting services..."
docker-compose up -d || error "Failed to start services"

success "Services started successfully"

# Wait for service to be healthy
echo "⏳ Waiting for service to be healthy..."
sleep 10

# Check if service is running
if docker-compose ps | grep -q "Up"; then
    success "Service is running"
    echo ""
    echo "🎉 Deployment complete!"
    echo ""
    echo "📊 Dashboard URL: http://localhost:8501"
    echo ""
    echo "Useful commands:"
    echo "  • View logs:        docker-compose logs -f"
    echo "  • Stop services:    docker-compose down"
    echo "  • Restart services: docker-compose restart"
    echo "  • Check status:     docker-compose ps"
    echo ""
else
    error "Service failed to start. Check logs with: docker-compose logs"
fi

# Save deployment info
echo "$(date)" > .last_deployment
echo "$ENVIRONMENT" >> .last_deployment

success "Deployment information saved to .last_deployment"

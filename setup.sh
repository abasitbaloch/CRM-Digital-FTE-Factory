#!/bin/bash

# Customer Success Platform - Setup Script
# This script helps you get started quickly

set -e

echo "=========================================="
echo "Customer Success Platform - Setup"
echo "=========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi
echo "✅ Python 3 found: $(python3 --version)"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi
echo "✅ Docker found: $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi
echo "✅ Docker Compose found: $(docker-compose --version)"

echo ""
echo "All prerequisites met!"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "⚠️  Please edit .env and add your API keys"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r production/requirements.txt
echo "✅ Dependencies installed"
echo ""

# Start Docker services
echo "Starting Docker services..."
docker-compose up -d
echo "✅ Services started"
echo ""

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 15

# Check if services are healthy
echo "Checking service health..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API is healthy"
else
    echo "⚠️  API is not responding yet, may need more time"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - PostgreSQL: localhost:5432"
echo "  - Kafka: localhost:9092"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Visit http://localhost:8000/docs to explore the API"
echo "  3. Run tests: make test"
echo ""
echo "To stop services: docker-compose down"
echo "To view logs: docker-compose logs -f"
echo ""

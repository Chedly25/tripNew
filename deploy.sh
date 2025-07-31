#!/bin/bash
# Production deployment script for European Travel Planner

set -e

echo "======================================"
echo "European Travel Planner - Production Deployment"
echo "======================================"

# Check if required tools are installed
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "Git is required but not installed. Aborting." >&2; exit 1; }

# Build Docker image
echo "Building production Docker image..."
docker build -t european-travel-planner:production .

# Test the image locally
echo "Testing Docker image..."
docker run --rm -p 8000:8000 --env-file .env european-travel-planner:production &
CONTAINER_PID=$!

# Wait for container to start
sleep 10

# Health check
echo "Performing health check..."
if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    kill $CONTAINER_PID
    exit 1
fi

# Stop test container
kill $CONTAINER_PID

echo "✅ Docker image built and tested successfully"
echo ""
echo "🚀 Ready for deployment to:"
echo "   • Railway: https://railway.app"
echo "   • Render: https://render.com"
echo "   • Heroku: https://heroku.com"
echo "   • Google Cloud Run"
echo "   • AWS ECS"
echo ""
echo "📋 Manual steps:"
echo "1. Push code to GitHub repository"
echo "2. Connect repository to deployment platform"
echo "3. Set environment variables:"
echo "   - FLASK_ENV=production"
echo "   - SECRET_KEY=(generate secure key)"
echo "   - ANTHROPIC_API_KEY=(your Claude API key)"
echo "   - OPENWEATHER_API_KEY=(optional)"
echo "   - GOOGLE_MAPS_API_KEY=(optional)"
echo "   - OPENROUTE_API_KEY=(optional)"
echo "4. Deploy!"
echo "======================================"
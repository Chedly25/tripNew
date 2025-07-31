#!/bin/bash
# One-click deployment to Railway.app

set -e

echo "🚀 Deploying European Travel Planner to Railway.app"
echo "=================================================="

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "Installing Railway CLI..."
    curl -fsSL https://railway.app/install.sh | sh
    echo "✅ Railway CLI installed"
fi

# Login to Railway
echo "🔑 Please login to Railway..."
railway login

# Create new Railway project
echo "📋 Creating new Railway project..."
railway init

# Set environment variables
echo "⚙️  Setting environment variables..."
railway variables set FLASK_ENV=production
railway variables set SECRET_KEY=$(openssl rand -hex 32)
railway variables set ANTHROPIC_API_KEY=your-claude-api-key-here

echo "📝 Optional: Set additional API keys for full functionality"
echo "   OpenWeather: railway variables set OPENWEATHER_API_KEY=your-key"
echo "   Google Maps: railway variables set GOOGLE_MAPS_API_KEY=your-key"
echo "   OpenRoute: railway variables set OPENROUTE_API_KEY=your-key"

# Deploy application
echo "🚀 Deploying application..."
railway up

echo ""
echo "✅ Deployment complete!"
echo "🌐 Your application will be available at:"
railway domain

echo ""
echo "📊 Check deployment status:"
echo "   railway status"
echo ""
echo "📝 View logs:"
echo "   railway logs"
echo ""
echo "🎯 Your European Travel Planner is now live and accessible to anyone!"
echo "=================================================="
#!/bin/bash

# Setup script for Heroku environment variables
# Run this script to configure your Heroku app with necessary environment variables

echo "🚀 Setting up Heroku environment variables for Travel Planner..."

# Check if heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI is not installed. Please install it first:"
    echo "   https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Get app name
echo "📱 Please enter your Heroku app name:"
read -p "App name: " APP_NAME

if [ -z "$APP_NAME" ]; then
    echo "❌ App name is required"
    exit 1
fi

echo "🔐 Setting up API keys..."

# Set Anthropic API Key
echo "🤖 Please enter your Anthropic API Key (starts with sk-ant-):"
read -s -p "Anthropic API Key: " ANTHROPIC_KEY
echo ""

if [ ! -z "$ANTHROPIC_KEY" ]; then
    heroku config:set ANTHROPIC_API_KEY="$ANTHROPIC_KEY" --app $APP_NAME
    echo "✅ Anthropic API Key configured"
else
    echo "⚠️  Anthropic API Key skipped (AI features will be limited)"
fi

# Set Google OAuth credentials
echo "🔐 Please enter your Google OAuth Client ID:"
read -p "Google Client ID: " GOOGLE_CLIENT_ID

echo "🔐 Please enter your Google OAuth Client Secret:"
read -s -p "Google Client Secret: " GOOGLE_CLIENT_SECRET
echo ""

if [ ! -z "$GOOGLE_CLIENT_ID" ] && [ ! -z "$GOOGLE_CLIENT_SECRET" ]; then
    heroku config:set GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" --app $APP_NAME
    heroku config:set GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" --app $APP_NAME
    echo "✅ Google OAuth credentials configured"
else
    echo "⚠️  Google OAuth credentials skipped (Google Sign-In will not work)"
fi

# Optional: Set other API keys
echo ""
echo "🌐 Optional: Set additional API keys for enhanced features"

echo "Would you like to set OpenWeather API key? (y/n)"
read -p "OpenWeather: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "OpenWeather API Key: " WEATHER_KEY
    if [ ! -z "$WEATHER_KEY" ]; then
        heroku config:set OPENWEATHER_API_KEY="$WEATHER_KEY" --app $APP_NAME
        echo "✅ OpenWeather API Key configured"
    fi
fi

echo "Would you like to set Google Maps API key? (y/n)"
read -p "Google Maps: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Google Maps API Key: " MAPS_KEY
    if [ ! -z "$MAPS_KEY" ]; then
        heroku config:set GOOGLE_MAPS_API_KEY="$MAPS_KEY" --app $APP_NAME
        echo "✅ Google Maps API Key configured"
    fi
fi

echo ""
echo "🎉 Environment variables setup complete!"
echo ""
echo "📋 Current configuration:"
heroku config --app $APP_NAME

echo ""
echo "🚀 Your app should now have:"
echo "   ✅ Anthropic API for AI features"
echo "   ✅ Google OAuth for social login"
echo "   ✅ Enhanced travel planning capabilities"
echo ""
echo "🌐 Deploy your changes:"
echo "   git push heroku master"
echo ""
echo "📖 For more details, see GOOGLE_OAUTH_SETUP.md"
# 🚀 Production Deployment Guide

## European Travel Planner - Live Website Deployment

This guide shows how to deploy the production-ready European Travel Planner to a live website that anyone can access.

## 🌐 Deployment Options

### Option 1: Railway (Recommended - Free & Fast)

1. **Create GitHub Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial production deployment"
   git branch -M main
   git remote add origin https://github.com/yourusername/european-travel-planner.git
   git push -u origin main
   ```

2. **Deploy to Railway**
   - Visit [railway.app](https://railway.app)
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect the Dockerfile and deploy

3. **Set Environment Variables in Railway Dashboard**
   ```
   FLASK_ENV=production
   SECRET_KEY=your-secret-key-here
   ANTHROPIC_API_KEY=your-claude-api-key-here
   OPENWEATHER_API_KEY=your-openweather-key
   GOOGLE_MAPS_API_KEY=your-google-maps-key
   OPENROUTE_API_KEY=your-openroute-key
   ```

4. **Custom Domain (Optional)**
   - Railway provides free subdomain: `yourapp.railway.app`
   - Add custom domain in Railway dashboard

### Option 2: Render.com (Free Tier Available)

1. **Push to GitHub** (same as Railway step 1)

2. **Deploy to Render**
   - Visit [render.com](https://render.com)
   - Connect GitHub account
   - Create "New Web Service"
   - Select repository
   - Render will use the `render.yaml` configuration

3. **Environment Variables**
   - Set in Render dashboard (same variables as Railway)

### Option 3: Heroku (Requires Credit Card)

1. **Install Heroku CLI**
   ```bash
   # Install Heroku CLI
   npm install -g heroku
   
   # Login
   heroku login
   
   # Create app
   heroku create european-travel-planner
   
   # Set environment variables
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set ANTHROPIC_API_KEY=your-claude-key
   
   # Deploy
   git push heroku main
   ```

### Option 4: Google Cloud Run

1. **Enable Cloud Run API**
2. **Build and push image**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT-ID/travel-planner
   gcloud run deploy --image gcr.io/PROJECT-ID/travel-planner --platform managed
   ```

## 🔧 Production Configuration

### Required Environment Variables

```bash
# Core Application
FLASK_ENV=production
SECRET_KEY=<generate-secure-32-char-key>
PORT=8000

# API Keys (Claude is required, others optional)
ANTHROPIC_API_KEY=sk-ant-api03-...  # Your Claude API key
OPENWEATHER_API_KEY=your-key        # Free at openweathermap.org
GOOGLE_MAPS_API_KEY=your-key        # $200/month free credit
OPENROUTE_API_KEY=your-key          # 2000 requests/day free

# Database (automatically provided by platform)
DATABASE_URL=postgresql://...        # Provided by Railway/Render
REDIS_URL=redis://...               # Provided by Railway/Render
```

### Free API Keys Setup

1. **OpenWeather** (1000 calls/day free)
   - Sign up at https://openweathermap.org/api
   - Get API key from dashboard

2. **OpenRouteService** (2000 requests/day free)
   - Sign up at https://openrouteservice.org/
   - Create API key

3. **Google Places** ($200/month free credit)
   - Go to https://console.cloud.google.com/
   - Enable Places API
   - Create credentials

## 🏗️ Production Features Enabled

✅ **Real External APIs**
- OpenRouteService for routing
- OpenWeatherMap for weather
- Google Places for hotels/restaurants
- Claude AI for travel insights

✅ **Production Infrastructure**
- Docker containerization
- Gunicorn WSGI server (4 workers)
- PostgreSQL database
- Redis caching
- Health checks
- Auto-scaling

✅ **Security & Performance**
- Security headers (CSP, HSTS, etc.)
- Input validation and sanitization  
- Rate limiting
- Error handling and logging
- Production-optimized settings

✅ **Monitoring & Reliability**
- Health check endpoint: `/api/health`
- Structured logging
- Error tracking
- Performance monitoring ready

## 🌍 Live Website Result

After deployment, your website will be accessible at:
- **Railway**: `https://yourapp.railway.app`
- **Render**: `https://yourapp.onrender.com`
- **Heroku**: `https://yourapp.herokuapp.com`
- **Custom domain**: `https://yourdomain.com`

## 🧪 Testing Production Deployment

```bash
# Health check
curl https://yourapp.railway.app/api/health

# Get available cities
curl https://yourapp.railway.app/api/cities

# Test complete travel planning (requires form data)
curl -X POST https://yourapp.railway.app/api/plan-complete \
  -d "start_city=Paris&end_city=Rome&travel_days=5&season=summer"
```

## 📊 Expected Performance

- **Cold start**: < 3 seconds
- **Response time**: < 500ms (cached)
- **Concurrent users**: 100+ (with scaling)
- **Uptime**: 99.9% (platform SLA)

## 🔄 Continuous Deployment

The GitHub Actions workflow automatically:
1. Tests the application
2. Builds Docker image
3. Pushes to container registry
4. Triggers deployment

Every push to `main` branch deploys to production.

## 🎯 What Users Will Experience

1. **Visit your live website**
2. **Professional travel planning interface**
3. **Real AI-powered route generation**
4. **Interactive maps with live data**
5. **Weather forecasts and recommendations**
6. **Hotel and restaurant suggestions**
7. **Complete trip cost calculations**

## 💰 Cost Breakdown

**Free Tier Deployment:**
- Railway: Free for 512MB RAM, $5/month for more
- Render: Free with limitations, $7/month for production
- API calls: All within free tiers initially

**Production Scale:**
- ~$20-50/month for serious traffic
- Scales automatically based on usage

## 🚀 Ready to Deploy?

1. Copy your files to GitHub repository
2. Choose deployment platform (Railway recommended)
3. Set environment variables
4. Deploy and share your live website!

Your European Travel Planner will be live and accessible to anyone worldwide. 🌍
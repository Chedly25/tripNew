# 🏗️ Clean Codebase Structure

## 📂 Project Overview
Production-ready European Travel Planner with clean architecture, real APIs, and proper separation of concerns.

## 🚀 Entry Points
- **`production_app.py`** - Main Flask application (production-ready)
- **`wsgi.py`** - WSGI entry point for deployment

## 📁 Directory Structure

```
├── production_app.py          # Main Flask app with security headers
├── wsgi.py                    # WSGI deployment entry
├── requirements.txt           # Python dependencies
├── src/                       # Clean architecture source code
│   ├── core/                  # Domain models and interfaces
│   │   ├── models.py          # Data models (TripRequest, City, etc.)
│   │   ├── interfaces.py      # Service interfaces
│   │   └── exceptions.py      # Custom exceptions
│   ├── infrastructure/        # Infrastructure layer
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database connections
│   │   ├── cache.py           # Redis caching
│   │   └── logging.py         # Structured logging
│   ├── services/              # Business logic services
│   │   ├── real_places_service.py     # Google Places API integration
│   │   ├── production_travel_service.py # Route planning
│   │   ├── travel_amenities_service.py  # Hotels/restaurants
│   │   ├── city_service.py            # City data management
│   │   ├── validation_service.py      # Input validation
│   │   └── ...
│   ├── templates/             # Jinja2 templates
│   │   ├── travel_planner_main.html   # Main planning page
│   │   └── travel_results.html        # Results page
│   └── web/                   # Web layer (alternative Flask app)
├── tests/                     # Unit and integration tests
├── migrations/                # Database migrations
└── docs/                      # Documentation
    ├── REAL_DATA_SETUP.md     # API setup guide
    └── CLAUDE.md              # Development guidelines
```

## 🛠️ Key Features

### ✅ Production-Ready Features
- **Real Data Integration**: Google Places API for authentic hotels/restaurants
- **Security Headers**: CSP, XSS protection, HSTS
- **Clean Architecture**: Separated concerns with dependency injection
- **Structured Logging**: Production-grade logging with structlog
- **Input Validation**: Comprehensive request validation
- **Error Handling**: Proper exception handling and user feedback
- **Caching**: Redis integration for performance
- **Testing**: Unit and integration test suite

### 🎯 Removed Redundancies
**Before cleanup: 50+ files including:**
- 14 redundant Python app files
- 8 duplicate template files  
- 6 redundant documentation files
- Multiple unused service implementations
- Test/debug files
- Screenshots and binary files

**After cleanup: ~25 essential files**
- 1 main Flask app (`production_app.py`)
- Clean src/ architecture
- 2 production templates
- Essential deployment files only

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export GOOGLE_PLACES_API_KEY=your_api_key_here
   export SECRET_KEY=your_secret_key
   ```

3. **Run Development Server**
   ```bash
   python production_app.py
   ```

4. **Deploy to Production**
   ```bash
   gunicorn wsgi:application
   ```

## 📋 Configuration

### Required Environment Variables
- `GOOGLE_PLACES_API_KEY` - For real hotel/restaurant data
- `SECRET_KEY` - Flask security key

### Optional Environment Variables  
- `REDIS_URL` - Redis caching (falls back to in-memory)
- `LOG_LEVEL` - Logging level (default: INFO)
- `FLASK_ENV` - Environment (development/production)

## 🧪 Testing
```bash
python -m pytest tests/
```

## 📚 Documentation
- `REAL_DATA_SETUP.md` - How to configure Google Places API
- `CLAUDE.md` - Development guidelines and best practices

## ⚡ Performance
- Google Places API for real data
- Redis caching for route calculations
- Optimized algorithms (O(n log n) route optimization)
- CDN resources with fallbacks
- Production security headers

This clean structure provides a maintainable, scalable, and production-ready travel planning application.
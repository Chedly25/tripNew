# Configuration for Real-World European Roadtrip Planner
import os
from datetime import datetime, timedelta

class Config:
    # API Keys (set as environment variables or replace with actual keys)
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', 'your_google_maps_api_key_here')
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', 'your_openweather_api_key_here')
    TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY', 'your_ticketmaster_api_key_here')
    BOOKING_COM_API_KEY = os.getenv('BOOKING_COM_API_KEY', 'your_booking_api_key_here')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
    
    # API Endpoints
    GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
    GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5"
    TICKETMASTER_URL = "https://app.ticketmaster.com/discovery/v2"
    
    # OpenRoute Service (Free alternative to Google)
    OPENROUTE_API_KEY = os.getenv('OPENROUTE_API_KEY', 'your_openroute_api_key_here')
    OPENROUTE_URL = "https://api.openrouteservice.org/v2"
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///roadtrip_planner.db')
    
    # Caching
    CACHE_DURATION_HOURS = 6  # Cache API responses for 6 hours
    
    # Route Optimization Parameters
    MAX_DRIVING_HOURS_PER_DAY = 8
    PREFERRED_ARRIVAL_TIME = "18:00"  # 6 PM
    TRAFFIC_WEIGHT = 0.3
    EVENT_WEIGHT = 0.4
    WEATHER_WEIGHT = 0.2
    COST_WEIGHT = 0.1
    
    # Event Categories to Consider
    EVENT_CATEGORIES = [
        'music', 'arts', 'sports', 'family', 'food', 'cultural',
        'festivals', 'exhibitions', 'theater', 'comedy'
    ]
    
    # Countries and regions
    SUPPORTED_COUNTRIES = [
        'france', 'italy', 'spain', 'germany', 'austria', 'switzerland',
        'netherlands', 'belgium', 'portugal', 'croatia', 'slovenia',
        'czech_republic', 'hungary', 'poland'
    ]
    
    # Currency rates (update periodically)
    CURRENCY_RATES = {
        'EUR': 1.0,
        'USD': 1.1,
        'GBP': 0.86
    }
    
    # Fuel prices per country (EUR per liter, updated weekly)
    FUEL_PRICES = {
        'france': 1.65,
        'italy': 1.70,
        'spain': 1.45,
        'germany': 1.55,
        'austria': 1.52,
        'switzerland': 1.75,
        'netherlands': 1.85,
        'belgium': 1.60,
        'portugal': 1.50,
        'croatia': 1.35,
        'slovenia': 1.45
    }
    
    # Toll costs estimation (EUR per 100km)
    TOLL_COSTS = {
        'france': 9.50,
        'italy': 7.20,
        'spain': 8.10,
        'germany': 0.00,  # No tolls for cars
        'austria': 8.60,
        'switzerland': 40.00,  # Vignette system
        'netherlands': 0.00,
        'belgium': 0.00,
        'portugal': 6.50,
        'croatia': 5.80,
        'slovenia': 15.00  # Vignette
    }

# Weather condition scoring (0-1, where 1 is perfect)
WEATHER_SCORES = {
    'clear': 1.0,
    'few_clouds': 0.9,
    'scattered_clouds': 0.8,
    'broken_clouds': 0.7,
    'shower_rain': 0.4,
    'rain': 0.3,
    'thunderstorm': 0.1,
    'snow': 0.2,
    'mist': 0.6
}

# Event impact on route attractiveness (multiplier)
EVENT_IMPACT = {
    'major_festival': 2.0,
    'concert': 1.5,
    'sports_event': 1.4,
    'cultural_event': 1.3,
    'food_festival': 1.6,
    'art_exhibition': 1.2,
    'local_event': 1.1
}
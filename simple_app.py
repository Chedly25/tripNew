#!/usr/bin/env python3
"""
Simple demo version of the production travel planner.
"""
import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from typing import Dict, List, Any
import json

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

try:
    from src.services.validation_service import ValidationService
    from src.services.city_service import CityService
    from src.services.route_service import ProductionRouteService
    from src.services.travel_planner import TravelPlannerServiceImpl
    from src.infrastructure.config import SecureConfigurationService
    from src.core.models import TripRequest, Season, City, Coordinates
    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Services not available: {e}")
    SERVICES_AVAILABLE = False

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'demo-key'

# Simplified city data for demo
DEMO_CITIES = {
    "aix-en-provence": {"name": "Aix-en-Provence", "lat": 43.5297, "lon": 5.4474, "country": "France"},
    "venice": {"name": "Venice", "lat": 45.4408, "lon": 12.3155, "country": "Italy"},
    "lyon": {"name": "Lyon", "lat": 45.7640, "lon": 4.8357, "country": "France"},
    "milan": {"name": "Milan", "lat": 45.4642, "lon": 9.1900, "country": "Italy"},
    "nice": {"name": "Nice", "lat": 43.7102, "lon": 7.2620, "country": "France"},
}

def calculate_distance(lat1, lon1, lat2, lon2):
    """Simple distance calculation."""
    from geopy.distance import geodesic
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

def generate_demo_routes(start_city: str, end_city: str, travel_days: int, season: str) -> List[Dict]:
    """Generate demo routes with proper data."""
    start_data = DEMO_CITIES.get(start_city.lower().replace(" ", "-").replace("'", "-"))
    end_data = DEMO_CITIES.get(end_city.lower().replace(" ", "-").replace("'", "-"))
    
    if not start_data or not end_data:
        return []
    
    distance = calculate_distance(
        start_data["lat"], start_data["lon"],
        end_data["lat"], end_data["lon"]
    )
    
    driving_time = distance / 70.0  # Average speed with stops
    
    routes = [
        {
            "name": "Fastest Direct Route",
            "description": "Optimize for minimal driving time and maximum time at destinations",
            "route_type": "fastest",
            "total_distance_km": round(distance, 1),
            "total_duration_hours": round(driving_time, 1),
            "estimated_driving_time": f"{driving_time:.1f} hours",
            "intermediate_cities": [],
            "start_city": {"name": start_data["name"], "coordinates": [start_data["lat"], start_data["lon"]]},
            "end_city": {"name": end_data["name"], "coordinates": [end_data["lat"], end_data["lon"]]},
            "estimated_cost": {
                "fuel_estimate": round(distance * 0.08, 2),
                "accommodation_estimate": travel_days * 80,
                "total_estimate": round(distance * 0.08 + travel_days * 80, 2)
            },
            "season_tips": get_season_tips(season)
        },
        {
            "name": "Scenic Route",
            "description": "Beautiful landscapes and scenic viewpoints along the way",
            "route_type": "scenic", 
            "total_distance_km": round(distance * 1.2, 1),
            "total_duration_hours": round(driving_time * 1.3, 1),
            "estimated_driving_time": f"{driving_time * 1.3:.1f} hours",
            "intermediate_cities": [{"name": "Nice", "coordinates": [43.7102, 7.2620], "types": ["coastal", "scenic"]}],
            "start_city": {"name": start_data["name"], "coordinates": [start_data["lat"], start_data["lon"]]},
            "end_city": {"name": end_data["name"], "coordinates": [end_data["lat"], end_data["lon"]]},
            "estimated_cost": {
                "fuel_estimate": round(distance * 1.2 * 0.08, 2),
                "accommodation_estimate": travel_days * 90,
                "total_estimate": round(distance * 1.2 * 0.08 + travel_days * 90, 2)
            },
            "season_tips": get_season_tips(season)
        },
        {
            "name": "Cultural Route",
            "description": "Visit UNESCO World Heritage sites and cultural landmarks",
            "route_type": "cultural",
            "total_distance_km": round(distance * 1.15, 1),
            "total_duration_hours": round(driving_time * 1.25, 1),
            "estimated_driving_time": f"{driving_time * 1.25:.1f} hours",
            "intermediate_cities": [{"name": "Lyon", "coordinates": [45.7640, 4.8357], "types": ["cultural", "culinary"]}],
            "start_city": {"name": start_data["name"], "coordinates": [start_data["lat"], start_data["lon"]]},
            "end_city": {"name": end_data["name"], "coordinates": [end_data["lat"], end_data["lon"]]},
            "estimated_cost": {
                "fuel_estimate": round(distance * 1.15 * 0.08, 2),
                "accommodation_estimate": travel_days * 85,
                "total_estimate": round(distance * 1.15 * 0.08 + travel_days * 85, 2)
            },
            "season_tips": get_season_tips(season)
        }
    ]
    
    return routes

def get_season_tips(season: str) -> List[str]:
    """Get season-specific tips."""
    tips = {
        'winter': [
            "Check weather conditions and carry winter equipment",
            "Some mountain passes may be closed",
            "Book accommodations early due to ski season"
        ],
        'summer': [
            "Book accommodations early due to high season",
            "Consider early morning starts to avoid traffic",
            "Pack sun protection and stay hydrated"
        ],
        'spring': [
            "Perfect weather for sightseeing",
            "Flowers blooming make scenic routes extra beautiful",
            "Mild temperatures ideal for walking tours"
        ],
        'autumn': [
            "Beautiful fall colors on scenic routes",
            "Harvest season - great for food and wine experiences", 
            "Pack layers as temperatures can vary"
        ]
    }
    return tips.get(season, ["Enjoy your journey!"])

@app.route('/')
def index():
    """Landing page."""
    return render_template('professional_dynamic.html')

@app.route('/plan', methods=['POST'])
def plan_trip():
    """Main trip planning endpoint."""
    try:
        # Get form data
        start_city = request.form.get('start_city', '').strip()
        end_city = request.form.get('end_city', '').strip()
        travel_days = int(request.form.get('travel_days', 5))
        season = request.form.get('season', 'summer')
        claude_api_key = request.form.get('claude_api_key', '').strip()
        
        # Basic validation
        if not start_city or not end_city:
            return jsonify({'error': 'Start and end cities are required'}), 400
            
        if travel_days < 1 or travel_days > 30:
            return jsonify({'error': 'Travel days must be between 1 and 30'}), 400
        
        # Generate routes
        routes = generate_demo_routes(start_city, end_city, travel_days, season)
        
        if not routes:
            return jsonify({'error': 'Could not generate routes for these cities'}), 400
        
        # Add AI insights if Claude API key provided
        if claude_api_key and claude_api_key.startswith('sk-ant-'):
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=claude_api_key)
                
                # Get AI insights for the first route
                prompt = f"Provide 3 brief travel tips for a {season} trip from {start_city} to {end_city}. Keep each tip under 50 words."
                
                message = client.messages.create(
                    model="claude-3-sonnet-20241022",
                    max_tokens=200,
                    messages=[{
                        "role": "user", 
                        "content": prompt
                    }]
                )
                
                ai_tips = message.content[0].text.split('\n')
                ai_tips = [tip.strip('- ').strip() for tip in ai_tips if tip.strip()]
                
                # Add AI tips to first route
                if ai_tips and routes:
                    routes[0]['ai_insights'] = ai_tips[:3]
                    
            except Exception as e:
                print(f"Claude API error: {e}")
                # Continue without AI insights
        
        return jsonify({
            'success': True,
            'data': {
                'routes': routes,
                'start_city': start_city,
                'end_city': end_city,
                'travel_days': travel_days,
                'season': season
            }
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'healthy': True,
        'version': '2.0.0-demo',
        'services_available': SERVICES_AVAILABLE,
        'cities_loaded': len(DEMO_CITIES)
    })

if __name__ == '__main__':
    print("Starting Production-Ready Travel Planner Demo")
    print("Available cities:", ", ".join([city["name"] for city in DEMO_CITIES.values()]))
    print("Server will be available at: http://localhost:5004")
    app.run(host='0.0.0.0', port=5004, debug=True)
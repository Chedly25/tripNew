#!/usr/bin/env python3
"""
Debug the full pipeline from request to frontend display.
"""
import asyncio
import sys
import os
import json

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.travel_planner import TravelPlannerServiceImpl
from src.services.google_places_city_service import GooglePlacesCityService
from src.services.route_service import ProductionRouteService
from src.services.validation_service import ValidationService
from src.infrastructure.config import SecureConfigurationService
from src.core.models import TripRequest

async def test_full_pipeline():
    """Test the complete pipeline."""
    print("DEBUG: Testing full travel planning pipeline...")
    
    # Initialize services
    config_service = SecureConfigurationService()
    city_service = GooglePlacesCityService()
    route_service = ProductionRouteService(config_service)
    validation_service = ValidationService()
    
    travel_planner = TravelPlannerServiceImpl(
        city_service, route_service, validation_service
    )
    
    # Create test request
    request = TripRequest(
        start_city="Aix-en-Provence",
        end_city="Venice",
        travel_days=5,
        nights_at_destination=2,
        season="summer"
    )
    
    print(f"Request: {request.start_city} -> {request.end_city}")
    
    # Generate routes
    result = travel_planner.generate_routes(request)
    
    if result.success:
        print(f"SUCCESS: Generated {len(result.data.get('routes', []))} routes")
        
        for i, route in enumerate(result.data.get('routes', [])):
            print(f"\nRoute {i+1}: {route.get('name', 'Unknown')}")
            print(f"  Type: {route.get('route_type', 'Unknown')}")
            print(f"  Distance: {route.get('total_distance_km', 0)} km")
            print(f"  Duration: {route.get('total_duration_hours', 0)} hours")
            
            intermediate = route.get('intermediate_cities', [])
            print(f"  Intermediate cities ({len(intermediate)}):")
            for city in intermediate:
                if hasattr(city, 'name'):
                    print(f"    - {city.name} ({getattr(city, 'country', 'Unknown')})")
                else:
                    print(f"    - {city}")
        
        # Test JSON serialization (what frontend receives)
        print("\n=== JSON OUTPUT FOR FRONTEND ===")
        try:
            json_output = json.dumps(result.data, default=str, indent=2)
            print("JSON serialization: OK")
            # Show first 500 chars
            print(json_output[:500] + "..." if len(json_output) > 500 else json_output)
        except Exception as e:
            print(f"JSON serialization ERROR: {e}")
    else:
        print(f"FAILED: {result.error_message}")
    
    await city_service.close()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
#!/usr/bin/env python3
"""
Debug intermediate cities issue - test the actual city discovery.
"""
import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.google_places_city_service import GooglePlacesCityService
from src.core.models import Coordinates

async def test_intermediate_cities():
    """Test intermediate city discovery."""
    print("DEBUG: Testing intermediate cities discovery...")
    
    # Initialize service
    service = GooglePlacesCityService()
    
    # Test cities
    start = Coordinates(latitude=43.5297, longitude=5.4474)  # Aix-en-Provence
    end = Coordinates(latitude=45.4408, longitude=12.3155)   # Venice
    
    print(f"Start: Aix-en-Provence {start.latitude}, {start.longitude}")
    print(f"End: Venice {end.latitude}, {end.longitude}")
    print(f"Google API Key available: {bool(service.google_api_key)}")
    
    # Test different route types
    route_types = ['scenic', 'cultural', 'adventure', 'culinary', 'romantic']
    
    for route_type in route_types:
        print(f"\n>>> Testing {route_type} route...")
        
        try:
            cities = await service.find_cities_near_route(
                start, end, max_deviation_km=120, route_type=route_type
            )
            
            print(f"Found {len(cities)} cities:")
            for city in cities:
                print(f"  - {city.name} ({city.country}) - Types: {city.types}")
                
        except Exception as e:
            print(f"ERROR for {route_type}: {e}")
    
    # Test fallback method directly
    print(f"\n>>> Testing fallback method directly...")
    fallback_cities = service._get_fallback_route_cities(start, end, 120, 'scenic')
    print(f"Fallback cities: {len(fallback_cities)}")
    for city in fallback_cities:
        print(f"  - {city.name} ({city.country}) - Types: {city.types}")
    
    await service.close()

if __name__ == "__main__":
    asyncio.run(test_intermediate_cities())
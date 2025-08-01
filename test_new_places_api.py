#!/usr/bin/env python3
"""
Test the updated Google Places service with the new API.
"""
import sys
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.google_places_city_service import GooglePlacesCityService
from src.core.models import Coordinates

async def test_new_places_api():
    """Test the updated Google Places API integration."""
    print("=== TESTING NEW PLACES API ===")
    
    # Check API key
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("ERROR: GOOGLE_PLACES_API_KEY not found in environment")
        return
    else:
        print(f"SUCCESS: Google Places API Key configured")
    
    # Initialize the service
    city_service = GooglePlacesCityService()
    
    try:
        # Test 1: Simple city search
        print("\n1. Testing get_city_by_name for 'Paris'...")
        paris_city = await city_service.get_city_by_name("Paris")
        if paris_city:
            print(f"SUCCESS: Found city: {paris_city.name} at {paris_city.coordinates.latitude}, {paris_city.coordinates.longitude}")
            print(f"Country: {paris_city.country}, Types: {paris_city.types}")
        else:
            print("FAIL: Failed to find Paris")
        
        # Test 2: Another city search
        print("\n2. Testing get_city_by_name for 'Nice'...")
        nice_city = await city_service.get_city_by_name("Nice")
        if nice_city:
            print(f"SUCCESS: Found city: {nice_city.name} at {nice_city.coordinates.latitude}, {nice_city.coordinates.longitude}")
            print(f"Country: {nice_city.country}, Types: {nice_city.types}")
        else:
            print("FAIL: Failed to find Nice")
        
        # Test 3: Route search if we have both cities
        if paris_city and nice_city:
            print(f"\n3. Testing find_cities_near_route from {paris_city.name} to {nice_city.name}...")
            intermediate_cities = await city_service.find_cities_near_route(
                start=paris_city.coordinates,
                end=nice_city.coordinates,
                max_deviation_km=100
            )
            
            print(f"Found {len(intermediate_cities)} intermediate cities:")
            for i, city in enumerate(intermediate_cities, 1):
                print(f"  {i}. {city.name} ({city.country}) - Types: {city.types} - Rating: {city.rating}")
        
        # Test 4: Original Aix to Venice route
        print(f"\n4. Testing original Aix-en-Provence to Venice route...")
        aix_city = await city_service.get_city_by_name("Aix-en-Provence")
        venice_city = await city_service.get_city_by_name("Venice")
        
        if aix_city and venice_city:
            print(f"Found both cities: {aix_city.name} -> {venice_city.name}")
            intermediate_cities = await city_service.find_cities_near_route(
                start=aix_city.coordinates,
                end=venice_city.coordinates,
                max_deviation_km=100
            )
            
            print(f"Found {len(intermediate_cities)} intermediate cities for Aix->Venice:")
            for i, city in enumerate(intermediate_cities, 1):
                print(f"  {i}. {city.name} ({city.country}) - Types: {city.types} - Rating: {city.rating}")
            
            if len(intermediate_cities) > 0:
                print("SUCCESS: New API returned intermediate cities for Aix->Venice!")
            else:
                print("WARNING: Still no intermediate cities found - may need to adjust search parameters")
        else:
            print("FAIL: Could not find Aix-en-Provence or Venice")
        
    except Exception as e:
        print(f"API Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await city_service.close()
    
    print(f"\n=== NEW PLACES API TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_new_places_api())
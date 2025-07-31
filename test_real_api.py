#!/usr/bin/env python3
"""
Test real API integration to verify intermediate cities work with actual API calls.
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

async def test_real_api_integration():
    """Test the Google Places API integration for intermediate cities."""
    print("=== TESTING REAL API INTEGRATION ===")
    
    # Check API key
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("ERROR: GOOGLE_PLACES_API_KEY not found in environment")
        return
    else:
        print(f"SUCCESS: Google Places API Key: {api_key[:10]}...")
    
    # Initialize the service
    city_service = GooglePlacesCityService()
    
    try:
        # Test 1: Get city by name (Aix-en-Provence)
        print("\n1. Testing get_city_by_name for 'Aix-en-Provence'...")
        aix_city = await city_service.get_city_by_name("Aix-en-Provence")
        if aix_city:
            print(f"SUCCESS: Found city: {aix_city.name} at {aix_city.coordinates.latitude}, {aix_city.coordinates.longitude}")
        else:
            print("ERROR: Failed to find Aix-en-Provence")
            return
        
        # Test 2: Get city by name (Venice)
        print("\n2. Testing get_city_by_name for 'Venice'...")
        venice_city = await city_service.get_city_by_name("Venice")
        if venice_city:
            print(f"SUCCESS: Found city: {venice_city.name} at {venice_city.coordinates.latitude}, {venice_city.coordinates.longitude}")
        else:
            print("ERROR: Failed to find Venice")
            return
        
        # Test 3: Find intermediate cities using real API
        print(f"\n3. Testing find_cities_near_route from {aix_city.name} to {venice_city.name}...")
        intermediate_cities = await city_service.find_cities_near_route(
            start=aix_city.coordinates,
            end=venice_city.coordinates,
            max_deviation_km=100
        )
        
        print(f"Found {len(intermediate_cities)} intermediate cities:")
        for i, city in enumerate(intermediate_cities, 1):
            print(f"  {i}. {city.name} ({city.country}) - Types: {city.types}")
        
        if len(intermediate_cities) > 0:
            print("SUCCESS: Real API returned intermediate cities!")
        else:
            print("FAIL: No intermediate cities found")
        
        # Test 4: Test route type filtering
        print(f"\n4. Testing route type filtering (scenic route)...")
        scenic_cities = await city_service.find_cities_near_route(
            start=aix_city.coordinates,
            end=venice_city.coordinates,
            max_deviation_km=100,
            route_type='scenic'
        )
        
        print(f"Found {len(scenic_cities)} scenic intermediate cities:")
        for i, city in enumerate(scenic_cities, 1):
            print(f"  {i}. {city.name} ({city.country}) - Types: {city.types}")
        
    except Exception as e:
        print(f"API Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await city_service.close()
    
    print(f"\n=== REAL API TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_real_api_integration())
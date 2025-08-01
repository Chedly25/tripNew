"""
Simple test script for OpenTripMap API integration without Unicode issues.
"""
import os
import asyncio
import json
from datetime import datetime

# Set the API key for testing
os.environ['OPENTRIPMAP_API_KEY'] = '5ae2e3f221c38a28845f05b695632f298c9cd7dcec52ac9251a5f7fd'

from src.services.opentripmap_service import OpenTripMapService
from src.core.models import Coordinates


async def test_basic_functionality():
    """Test basic OpenTripMap API functionality."""
    print("Testing OpenTripMap API Integration")
    print("=" * 40)
    
    service = OpenTripMapService()
    
    async with service:
        # Test 1: Get city information for Paris
        print("\nTest 1: Getting Paris city information...")
        paris_info = await service.get_city_info("Paris", "FR")
        print(f"Paris info: {paris_info}")
        
        # Test 2: Get attractions for Paris
        print("\nTest 2: Getting Paris attractions...")
        paris_coords = Coordinates(latitude=48.8566, longitude=2.3522)
        attractions = await service.get_city_attractions(paris_coords, radius_km=5, limit=10)
        print(f"Found {len(attractions)} attractions in Paris")
        
        # Show first 3 attractions
        for i, attraction in enumerate(attractions[:3]):
            print(f"  {i+1}. {attraction.get('name', 'Unknown')} (Rating: {attraction.get('rating', 'N/A')})")
        
        # Test 3: Get some cities in France
        print("\nTest 3: Getting French cities...")
        french_cities = await service.get_cities_in_country('france', limit=20)
        print(f"Found {len(french_cities)} cities in France")
        
        # Show first 5 cities
        for i, city in enumerate(french_cities[:5]):
            print(f"  {i+1}. {city.get('name', 'Unknown')}")
        
        print("\nAPI test completed successfully!")
        
        return {
            'paris_info': paris_info,
            'attractions_count': len(attractions),
            'cities_count': len(french_cities),
            'sample_attractions': attractions[:3],
            'sample_cities': french_cities[:5]
        }


if __name__ == "__main__":
    results = asyncio.run(test_basic_functionality())
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'opentripmap_test_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\nResults saved to: {filename}")
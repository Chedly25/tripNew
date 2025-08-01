"""
Test Foursquare API specifically for Venice restaurants.
"""
import os
import asyncio
import json
from datetime import datetime

# Set credentials for testing
os.environ['FOURSQUARE_API_KEY'] = 'VLWY02FCX44U25TLQB243URQIIZX1Q0USJ521ZZ0SLQXG4R3'

from src.services.foursquare_service import FoursquareService
from src.core.models import Coordinates


async def test_foursquare_venice():
    """Test Foursquare API for Venice restaurants."""
    print("Testing Foursquare API for Venice Restaurants")
    print("=" * 45)
    
    service = FoursquareService()
    
    # Venice coordinates: 45.4408° N, 12.3155° E
    venice_coords = Coordinates(latitude=45.4408, longitude=12.3155)
    
    print(f"Foursquare API Key: {service.api_key[:20]}..." if service.api_key else "No API key found")
    print(f"Venice coordinates: {venice_coords.latitude}, {venice_coords.longitude}")
    
    try:
        print("\n1. Testing restaurant search (async)...")
        restaurants = await service.find_restaurants(venice_coords, "Venice", limit=10)
        
        print(f"Found {len(restaurants)} restaurants:")
        for i, restaurant in enumerate(restaurants[:5], 1):
            print(f"  {i}. {restaurant.get('name', 'Unknown')}")
            print(f"     Rating: {restaurant.get('rating', 'N/A')}")
            print(f"     Cuisine: {restaurant.get('cuisine', 'N/A')}")
            print(f"     Address: {restaurant.get('address', 'N/A')}")
            print(f"     Source: {restaurant.get('source', 'unknown')}")
            
            # Check if it's real Foursquare data or fallback
            if restaurant.get('source') == 'foursquare':
                print("     [SUCCESS] REAL FOURSQUARE DATA!")
            else:
                print("     [FALLBACK] Fallback data")
        
        print("\n2. Testing activities search...")
        activities = await service.find_activities(venice_coords, "Venice", limit=5)
        
        print(f"Found {len(activities)} activities:")
        for i, activity in enumerate(activities[:3], 1):
            print(f"  {i}. {activity.get('name', 'Unknown')}")
            print(f"     Category: {activity.get('category', 'N/A')}")
            print(f"     Address: {activity.get('address', 'N/A')}")
            print(f"     Source: {activity.get('source', 'unknown')}")
        
        print("\n3. Testing fallback data...")
        fallback_restaurants = service._get_fallback_restaurants("Venice", 3)
        print(f"Fallback restaurants for Venice:")
        for restaurant in fallback_restaurants:
            print(f"  - {restaurant['name']}: {restaurant.get('cuisine', 'N/A')} cuisine")
        
        # Save results
        results = {
            'restaurants': restaurants,
            'activities': activities,
            'fallback_restaurants': fallback_restaurants,
            'test_timestamp': datetime.now().isoformat()
        }
        
        with open('foursquare_venice_test.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to foursquare_venice_test.json")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nFoursquare Venice Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_foursquare_venice())
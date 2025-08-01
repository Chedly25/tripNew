#!/usr/bin/env python3
"""
Test API data to find examples of hotels/restaurants with URLs.
"""
import sys
import os
import asyncio

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.booking_service import BookingService
from src.services.foursquare_service import FoursquareService
from src.core.models import Coordinates

async def test_api_urls():
    """Test API services to find real URL examples."""
    print("=== TESTING API SERVICES FOR URLs ===")
    
    # Test coordinates for Venice (popular tourist destination)
    venice_coords = Coordinates(latitude=45.4408, longitude=12.3155)
    
    # Test Booking service
    print("\n1. Testing Booking Service...")
    booking = BookingService()
    try:
        hotels = await booking.find_hotels(venice_coords, "Venice", limit=3)
        print(f"Found {len(hotels)} hotels")
        
        for i, hotel in enumerate(hotels, 1):
            print(f"\nHotel {i}: {hotel.get('name', 'Unknown')}")
            print(f"  Website: {hotel.get('website', 'None')}")
            print(f"  URL: {hotel.get('url', 'None')}")
            if hotel.get('website') or hotel.get('url'):
                print(f"  ✓ HAS URL!")
            else:
                print(f"  ✗ No URL")
                
    except Exception as e:
        print(f"Booking service error: {e}")
    finally:
        await booking.close()
    
    # Test Foursquare service
    print(f"\n2. Testing Foursquare Service...")
    foursquare = FoursquareService()
    try:
        restaurants = await foursquare.find_restaurants(venice_coords, "Venice", limit=3)
        print(f"Found {len(restaurants)} restaurants")
        
        for i, restaurant in enumerate(restaurants, 1):
            print(f"\nRestaurant {i}: {restaurant.get('name', 'Unknown')}")
            print(f"  Website: {restaurant.get('website', 'None')}")
            print(f"  URL: {restaurant.get('url', 'None')}")
            if restaurant.get('website') or restaurant.get('url'):
                print(f"  ✓ HAS URL!")
            else:
                print(f"  ✗ No URL")
                
    except Exception as e:
        print(f"Foursquare service error: {e}")
    finally:
        await foursquare.close()
    
    print(f"\n=== URL TESTING COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_api_urls())
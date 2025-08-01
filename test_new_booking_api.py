#!/usr/bin/env python3
"""
Test the updated Booking.com API with the correct endpoint and format.
"""
import sys
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.booking_service import BookingService
from src.core.models import Coordinates

async def test_new_booking_api():
    """Test the updated Booking.com API integration."""
    print("=== TESTING NEW BOOKING.COM API ===")
    
    # Check API key
    api_key = os.getenv('RAPIDAPI_KEY')
    if not api_key:
        print("ERROR: RAPIDAPI_KEY not found in environment")
        return
    else:
        print(f"SUCCESS: RapidAPI Key configured")
    
    # Initialize the service
    booking_service = BookingService()
    
    try:
        # Test with Nice, France
        print("\n1. Testing hotel search for Nice, France...")
        nice_coords = Coordinates(latitude=43.7102, longitude=7.2620)
        
        hotels = await booking_service.find_hotels(nice_coords, "Nice", limit=3)
        
        print(f"Found {len(hotels)} hotels:")
        for i, hotel in enumerate(hotels, 1):
            print(f"\n  Hotel {i}: {hotel.get('name', 'Unknown')}")
            print(f"    Rating: {hotel.get('rating', 'N/A')}/5")
            print(f"    Price: {hotel.get('price_per_night', 'N/A')} {hotel.get('currency', 'EUR')}")
            print(f"    Address: {hotel.get('address', 'N/A')}")
            print(f"    URL: {hotel.get('url', 'N/A')}")
            print(f"    Amenities: {hotel.get('amenities', [])}")
            
            # Check if this is real API data or fallback
            if 'Grand Hotel Nice' in hotel.get('name', ''):
                print("    STATUS: This appears to be fallback data")
            else:
                print("    STATUS: This appears to be REAL API data!")
        
        # Test with Venice
        print("\n2. Testing hotel search for Venice, Italy...")
        venice_coords = Coordinates(latitude=45.4408, longitude=12.3155)
        
        hotels = await booking_service.find_hotels(venice_coords, "Venice", limit=2)
        
        print(f"Found {len(hotels)} hotels:")
        for i, hotel in enumerate(hotels, 1):
            print(f"\n  Hotel {i}: {hotel.get('name', 'Unknown')}")
            print(f"    Rating: {hotel.get('rating', 'N/A')}/5")
            print(f"    Price: {hotel.get('price_per_night', 'N/A')} {hotel.get('currency', 'EUR')}")
            print(f"    URL: {hotel.get('url', 'N/A')}")
            
            # Check if this is real API data or fallback
            if 'Grand Hotel Venice' in hotel.get('name', ''):
                print("    STATUS: This appears to be fallback data")
            else:
                print("    STATUS: This appears to be REAL API data!")
        
        if len(hotels) > 0:
            print("\n✅ SUCCESS: Booking API is working!")
        else:
            print("\n❌ FAIL: No hotels returned from API")
        
    except Exception as e:
        print(f"API Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await booking_service.close()
    
    print(f"\n=== NEW BOOKING API TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_new_booking_api())
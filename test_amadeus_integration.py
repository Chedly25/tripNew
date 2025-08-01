"""
Test Amadeus service integration with the Flask application.
"""
import os
import asyncio
import json
from datetime import datetime

# Set credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'

from src.services.amadeus_service import AmadeusHotelService
from src.core.models import Coordinates


async def test_amadeus_service_integration():
    """Test the Amadeus service integration."""
    print("Testing Amadeus Service Integration")
    print("=" * 40)
    
    service = AmadeusHotelService()
    
    async with service:
        # Test 1: Find hotels using the main method (compatible interface)
        print("\nTest 1: Find hotels in Paris (main interface)...")
        paris_coords = Coordinates(latitude=48.8566, longitude=2.3522)
        hotels = await service.find_hotels(paris_coords, "Paris", limit=3)
        
        print(f"Found {len(hotels)} hotels:")
        for i, hotel in enumerate(hotels, 1):
            print(f"  {i}. {hotel['name']}")
            print(f"     Price: {hotel['price_per_night']} {hotel['currency']}")
            print(f"     Rating: {hotel['rating']} stars")
            print(f"     Source: {hotel['source']}")
        
        # Test 2: Test city code guessing
        print(f"\nTest 2: Testing city code detection...")
        city_codes = {
            'Paris': service._guess_city_code_from_name('Paris'),
            'Rome': service._guess_city_code_from_name('Rome'),
            'Barcelona': service._guess_city_code_from_name('Barcelona')
        }
        
        for city, code in city_codes.items():
            print(f"  {city} -> {code}")
        
        # Test 3: Test hotels by city code
        print(f"\nTest 3: Get hotels by city code (Rome)...")
        rome_hotels = await service.get_hotels_by_city('ROM', radius=5)
        print(f"Found {len(rome_hotels)} hotels in Rome")
        
        if rome_hotels:
            # Test offers for first 2 hotels
            hotel_ids = [h['hotel_id'] for h in rome_hotels[:2] if h.get('hotel_id')]
            if hotel_ids:
                print(f"Testing offers for {len(hotel_ids)} hotels...")
                
                check_in = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                check_out = (datetime.now() + timedelta(days=31)).strftime('%Y-%m-%d')
                
                offers = await service.search_hotel_offers(
                    hotel_ids, check_in, check_out, adults=2
                )
                
                print(f"Found {len(offers)} offers:")
                for offer in offers:
                    price = offer.get('offer', {}).get('price', {})
                    print(f"  - {offer['name']}: {price.get('total')} {price.get('currency')}")
        
        # Test 4: Test fallback data
        print(f"\nTest 4: Testing fallback data...")
        fallback_hotels = service._get_fallback_hotels("Milan", 3)
        print(f"Fallback hotels for Milan:")
        for hotel in fallback_hotels:
            print(f"  - {hotel['name']}: {hotel['price_per_night']} {hotel['currency']}")
    
    print(f"\nAmadeus Service Integration Test Complete!")


async def test_flask_compatibility():
    """Test compatibility with Flask app structure."""
    print("\n" + "=" * 40)
    print("Testing Flask App Compatibility")
    print("=" * 40)
    
    # Test the async call pattern used in Flask
    service = AmadeusHotelService()
    
    print("Testing async call pattern...")
    
    try:
        # Simulate Flask route pattern
        async def simulate_flask_call():
            coords = Coordinates(latitude=48.8566, longitude=2.3522)
            async with service:
                return await service.find_hotels(coords, "Paris", limit=2)
        
        # This is what Flask will do
        hotels = asyncio.run(simulate_flask_call())
        
        print("SUCCESS: Flask compatibility test passed!")
        print(f"Retrieved {len(hotels)} hotels:")
        for hotel in hotels:
            print(f"  - {hotel['name']}: {hotel['price_per_night']} {hotel['currency']}")
        
    except Exception as e:
        print(f"FAILED: Flask compatibility error - {e}")


async def test_error_handling():
    """Test error handling and fallback scenarios."""
    print("\n" + "=" * 40) 
    print("Testing Error Handling")
    print("=" * 40)
    
    # Test with invalid credentials
    original_client_id = os.environ.get('AMADEUS_CLIENT_ID')
    os.environ['AMADEUS_CLIENT_ID'] = 'invalid_key'
    
    service = AmadeusHotelService()
    
    print("Testing with invalid credentials (should use fallback)...")
    async with service:
        coords = Coordinates(latitude=48.8566, longitude=2.3522)
        hotels = await service.find_hotels(coords, "Paris", limit=2)
        
        print(f"With invalid creds: {len(hotels)} hotels (source: {hotels[0]['source'] if hotels else 'none'})")
    
    # Restore credentials
    if original_client_id:
        os.environ['AMADEUS_CLIENT_ID'] = original_client_id
    
    print("Error handling test complete!")


if __name__ == "__main__":
    from datetime import timedelta
    
    print("Amadeus Service - Comprehensive Integration Test")
    print("=" * 60)
    
    # Run all tests
    asyncio.run(test_amadeus_service_integration())
    asyncio.run(test_flask_compatibility())
    asyncio.run(test_error_handling())
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED!")
    print("Ready for deployment with Amadeus credentials!")
    print("=" * 60)
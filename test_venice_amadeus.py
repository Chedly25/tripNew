"""
Test Amadeus API specifically for Venice hotels.
"""
import os
import asyncio
import json
from datetime import datetime, timedelta

# Set credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'

from src.services.amadeus_service import AmadeusHotelService
from src.core.models import Coordinates


async def test_venice_hotels():
    """Test Venice hotel search comprehensively."""
    print("Testing Amadeus API for Venice Hotels")
    print("=" * 40)
    
    service = AmadeusHotelService()
    
    # Venice coordinates: 45.4408° N, 12.3155° E
    venice_coords = Coordinates(latitude=45.4408, longitude=12.3155)
    
    async with service:
        print("\n1. Testing Venice city code detection...")
        city_code = service._guess_city_code_from_name('Venice')
        print(f"Venice city code: {city_code}")
        
        print("\n2. Getting hotels by city code (VCE)...")
        try:
            hotels_by_city = await service.get_hotels_by_city('VCE', radius=10)
            print(f"Found {len(hotels_by_city)} hotels by city code")
            
            # Show first 5 hotels
            for i, hotel in enumerate(hotels_by_city[:5], 1):
                print(f"  {i}. {hotel['name']}")
                print(f"     ID: {hotel['hotel_id']}")
                print(f"     Address: {service._format_address(hotel['address'])}")
                print(f"     Distance: {hotel.get('distance')} {hotel.get('distance_unit', 'km')}")
        except Exception as e:
            print(f"City code search failed: {e}")
            hotels_by_city = []
        
        print("\n3. Getting hotels by coordinates...")
        try:
            hotels_by_coords = await service.get_hotels_by_coordinates(venice_coords, radius=10)
            print(f"Found {len(hotels_by_coords)} hotels by coordinates")
            
            # Show first 5 hotels
            for i, hotel in enumerate(hotels_by_coords[:5], 1):
                print(f"  {i}. {hotel['name']}")
                print(f"     ID: {hotel['hotel_id']}")
                print(f"     Distance: {hotel.get('distance')} {hotel.get('distance_unit', 'km')}")
        except Exception as e:
            print(f"Coordinates search failed: {e}")
            hotels_by_coords = []
        
        print("\n4. Testing hotel offers search...")
        hotels_to_test = hotels_by_city[:3] if hotels_by_city else hotels_by_coords[:3]
        
        if hotels_to_test:
            hotel_ids = [h['hotel_id'] for h in hotels_to_test if h.get('hotel_id')]
            print(f"Testing offers for {len(hotel_ids)} hotels: {hotel_ids}")
            
            check_in = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            check_out = (datetime.now() + timedelta(days=31)).strftime('%Y-%m-%d')
            
            try:
                offers = await service.search_hotel_offers(
                    hotel_ids, check_in, check_out, adults=2, room_quantity=1
                )
                
                print(f"Found {len(offers)} offers:")
                for offer in offers:
                    price = offer.get('offer', {}).get('price', {})
                    room = offer.get('offer', {}).get('room', {})
                    
                    print(f"  - {offer['name']}")
                    print(f"    Price: {price.get('total')} {price.get('currency')}")
                    print(f"    Room: {room.get('type')}")
                    
                    # Show amenities if available
                    amenities = offer.get('amenities', [])
                    if amenities:
                        amenity_names = [a.get('name', '') for a in amenities[:3]]
                        print(f"    Amenities: {', '.join(amenity_names)}")
                
            except Exception as e:
                print(f"Offers search failed: {e}")
        else:
            print("No hotels found to test offers")
        
        print("\n5. Testing main interface (find_hotels)...")
        try:
            venice_hotels = await service.find_hotels(
                venice_coords, "Venice", 
                check_in_date=None, check_out_date=None, 
                limit=5
            )
            
            print(f"Main interface found {len(venice_hotels)} hotels:")
            for i, hotel in enumerate(venice_hotels, 1):
                print(f"  {i}. {hotel['name']}")
                print(f"     Price: {hotel['price_per_night']} {hotel['currency']}")
                print(f"     Rating: {hotel['rating']} stars")
                print(f"     Source: {hotel['source']}")
                print(f"     Amadeus ID: {hotel.get('amadeus_hotel_id', 'N/A')}")
            
            # Save detailed results
            with open('venice_hotels_test.json', 'w') as f:
                json.dump(venice_hotels, f, indent=2, default=str)
            print(f"\nDetailed results saved to venice_hotels_test.json")
            
        except Exception as e:
            print(f"Main interface failed: {e}")
        
        print("\n6. Testing fallback data...")
        fallback_hotels = service._get_fallback_hotels("Venice", 3)
        print(f"Fallback hotels for Venice:")
        for hotel in fallback_hotels:
            print(f"  - {hotel['name']}: {hotel['price_per_night']} {hotel['currency']}")
    
    print(f"\nVenice Hotels Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_venice_hotels())
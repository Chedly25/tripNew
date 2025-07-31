#!/usr/bin/env python3
"""
Test the specific "Get Search Hotels" endpoint that's working on RapidAPI website.
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_booking_search_hotels():
    """Test the Get Search Hotels endpoint that's confirmed working."""
    print("=== TESTING BOOKING.COM 'GET SEARCH HOTELS' ENDPOINT ===")
    
    api_key = os.getenv('RAPIDAPI_KEY')
    if not api_key:
        print("ERROR: No RapidAPI key found")
        return
    
    print(f"RapidAPI Key: {api_key[:10]}...")
    
    # Test the specific endpoint that's working on RapidAPI website
    base_url = "https://booking-com.p.rapidapi.com/v1/hotels/search"
    
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'booking-com.p.rapidapi.com'
    }
    
    # Try different parameter combinations based on what might work
    test_params = [
        {
            'query': 'Nice France hotels',
            'locale': 'en-gb',
            'adults_number': 2,
            'room_number': 1,
            'checkin_date': '2025-08-15',
            'checkout_date': '2025-08-16'
        },
        {
            'location': 'Nice, France',
            'adults_number': 2,
            'room_number': 1,
            'checkin_date': '2025-08-15',
            'checkout_date': '2025-08-16'
        },
        {
            'city': 'Nice',
            'country': 'France',
            'adults_number': 2,
            'checkin_date': '2025-08-15',
            'checkout_date': '2025-08-16'
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, params in enumerate(test_params, 1):
            print(f"\n{i}. Testing parameter set {i}:")
            print(f"   Params: {params}")
            
            try:
                async with session.get(base_url, params=params, headers=headers) as response:
                    print(f"   Status: {response.status}")
                    response_text = await response.text()
                    print(f"   Response length: {len(response_text)} characters")
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            print(f"   SUCCESS: Got JSON response")
                            
                            # Check what's in the response
                            if 'result' in data:
                                hotels = data['result']
                                print(f"   Found {len(hotels)} hotels")
                                
                                # Show first hotel details
                                if hotels:
                                    first_hotel = hotels[0]
                                    print(f"   First hotel: {first_hotel.get('hotel_name', 'Unknown')}")
                                    print(f"   Price: {first_hotel.get('min_total_price', 'N/A')} {first_hotel.get('currencycode', 'EUR')}")
                                    print(f"   Rating: {first_hotel.get('review_score', 'N/A')}/10")
                                    print(f"   URL: {first_hotel.get('url', 'N/A')}")
                                    
                                    print("   🎉 REAL BOOKING.COM DATA FOUND!")
                                    return True
                            else:
                                print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                                
                        except Exception as e:
                            print(f"   JSON parsing error: {e}")
                            print(f"   Raw response: {response_text[:500]}")
                    else:
                        print(f"   Error response: {response_text[:500]}")
                        
            except Exception as e:
                print(f"   Request error: {e}")
    
    print(f"\n=== BOOKING SEARCH HOTELS TEST COMPLETE ===")
    return False

if __name__ == "__main__":
    asyncio.run(test_booking_search_hotels())
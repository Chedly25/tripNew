#!/usr/bin/env python3
"""
Test the exact Booking.com API format from the curl example.
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_exact_booking_api():
    """Test the exact API format from the curl example."""
    print("=== TESTING EXACT BOOKING.COM API FORMAT ===")
    
    api_key = os.getenv('RAPIDAPI_KEY')
    if not api_key:
        print("ERROR: No RapidAPI key found")
        return
    
    print(f"RapidAPI Key: {api_key[:10]}...")
    
    # Use the exact format from your curl example
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
    
    headers = {
        'x-rapidapi-host': 'booking-com15.p.rapidapi.com',
        'x-rapidapi-key': api_key
    }
    
    # Test with the exact parameters from your example, but for Nice
    params = {
        'dest_id': '-1456928',  # This might need to be the correct dest_id for Nice
        'search_type': 'CITY',
        'arrival_date': '2025-08-14',
        'departure_date': '2025-08-21',
        'adults': '1',
        'children_age': '',
        'room_qty': '1',
        'page_number': '1',
        'units': 'metric',
        'temperature_unit': 'c',
        'languagecode': 'en-us',
        'currency_code': 'EUR',
        'location': 'FR'  # France
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            print(f"Making request to: {url}")
            print(f"Parameters: {params}")
            
            async with session.get(url, params=params, headers=headers) as response:
                print(f"Status: {response.status}")
                response_text = await response.text()
                print(f"Response length: {len(response_text)} characters")
                
                if len(response_text) < 1000:
                    print(f"Full response: {response_text}")
                else:
                    print(f"Response preview: {response_text[:1000]}...")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        print(f"SUCCESS: Got JSON response")
                        
                        # Explore the response structure
                        if isinstance(data, dict):
                            print(f"Response keys: {list(data.keys())}")
                            
                            # Look for hotels in different possible locations
                            if 'result' in data:
                                result = data['result']
                                if isinstance(result, dict):
                                    print(f"Result keys: {list(result.keys())}")
                                    
                                    if 'hotels' in result:
                                        hotels = result['hotels']
                                        print(f"FOUND {len(hotels)} HOTELS!")
                                        
                                        # Show first hotel
                                        if hotels and len(hotels) > 0:
                                            first_hotel = hotels[0]
                                            print(f"First hotel keys: {list(first_hotel.keys()) if isinstance(first_hotel, dict) else 'Not a dict'}")
                                            if isinstance(first_hotel, dict):
                                                print(f"Hotel name: {first_hotel.get('hotel_name', 'No name')}")
                                                print(f"Hotel rating: {first_hotel.get('review_score', 'No rating')}")
                                                print(f"THIS IS REAL BOOKING.COM DATA!")
                                                return True
                        
                    except Exception as e:
                        print(f"JSON parsing error: {e}")
                else:
                    print(f"HTTP Error: {response.status}")
                    
        except Exception as e:
            print(f"Request error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== EXACT BOOKING API TEST COMPLETE ===")
    return False

if __name__ == "__main__":
    asyncio.run(test_exact_booking_api())
#!/usr/bin/env python3
"""
Test the Booking.com API directly to see if it's working.
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_booking_api_direct():
    """Test the Booking.com API directly."""
    print("=== TESTING BOOKING.COM API DIRECTLY ===")
    
    api_key = os.getenv('RAPIDAPI_KEY')
    if not api_key:
        print("ERROR: No RapidAPI key found")
        return
    
    print(f"RapidAPI Key: {api_key}")
    
    # Test the API endpoints directly
    base_url = "https://booking-com.p.rapidapi.com/v1"
    
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'booking-com.p.rapidapi.com'
    }
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Get destination ID for Nice
        print("\n1. Testing destination lookup for Nice...")
        
        url = f"{base_url}/hotels/locations"
        params = {
            'name': 'Nice',
            'locale': 'en-gb'
        }
        
        try:
            async with session.get(url, params=params, headers=headers) as response:
                print(f"Status: {response.status}")
                response_text = await response.text()
                print(f"Response: {response_text[:1000]}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"JSON data: {data}")
                    
                    results = data.get('result', [])
                    if results:
                        dest_id = results[0].get('dest_id')
                        print(f"Found destination ID: {dest_id}")
                        
                        # Test 2: Search for hotels using the destination ID
                        print(f"\n2. Testing hotel search with dest_id {dest_id}...")
                        
                        search_url = f"{base_url}/hotels/search"
                        search_params = {
                            'dest_id': dest_id,
                            'order_by': 'review_score',
                            'adults_number': 2,
                            'checkin_date': '2025-08-15',
                            'checkout_date': '2025-08-16',
                            'filter_by_currency': 'EUR',
                            'locale': 'en-gb',
                            'room_number': 1,
                            'units': 'metric'
                        }
                        
                        async with session.get(search_url, params=search_params, headers=headers) as search_response:
                            print(f"Hotel search status: {search_response.status}")
                            search_text = await search_response.text()
                            print(f"Hotel search response: {search_text[:2000]}")
                    else:
                        print("No destination results found")
                else:
                    print(f"API Error: {response.status}")
                    
        except Exception as e:
            print(f"Request error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== DIRECT API TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_booking_api_direct())
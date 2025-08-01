#!/usr/bin/env python3
"""
Test the corrected Booking.com API with the right endpoint.
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_correct_booking_api():
    """Test the correct booking-com15.p.rapidapi.com endpoint."""
    print("=== TESTING CORRECT BOOKING.COM API (booking-com15) ===")
    
    api_key = os.getenv('RAPIDAPI_KEY')
    if not api_key:
        print("ERROR: No RapidAPI key found")
        return
    
    print(f"RapidAPI Key: {api_key[:10]}...")
    
    # Test the correct endpoint
    base_url = "https://booking-com15.p.rapidapi.com/v1"
    
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'booking-com15.p.rapidapi.com'
    }
    
    async with aiohttp.ClientSession() as session:
        # Test destination lookup first
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
                    results = data.get('result', [])
                    if results:
                        dest_id = results[0].get('dest_id')
                        print(f"SUCCESS: Found destination ID: {dest_id}")
                        
                        # Test hotel search
                        print(f"\n2. Testing hotel search...")
                        search_url = f"{base_url}/hotels/search"
                        search_params = {
                            'dest_id': dest_id,
                            'order_by': 'review_score',
                            'adults_number': 2,
                            'checkin_date': '2025-08-15',
                            'checkout_date': '2025-08-16',
                            'locale': 'en-gb',
                            'room_number': 1
                        }
                        
                        async with session.get(search_url, params=search_params, headers=headers) as search_response:
                            print(f"Hotel search status: {search_response.status}")
                            search_text = await search_response.text()
                            
                            if search_response.status == 200:
                                search_data = await search_response.json()
                                hotels = search_data.get('result', [])
                                print(f"SUCCESS: Found {len(hotels)} real hotels!")
                                
                                # Show first few hotels
                                for i, hotel in enumerate(hotels[:3], 1):
                                    name = hotel.get('hotel_name', 'Unknown')
                                    rating = hotel.get('review_score', 'N/A')
                                    price = hotel.get('min_total_price', 'N/A')
                                    print(f"  {i}. {name} - Rating: {rating}/10 - Price: {price} EUR")
                                
                                return True
                            else:
                                print(f"Hotel search error: {search_text[:500]}")
                    else:
                        print("No destination results found")
                else:
                    print(f"Destination lookup failed")
                    
        except Exception as e:
            print(f"Request error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== CORRECT BOOKING API TEST COMPLETE ===")
    return False

if __name__ == "__main__":
    asyncio.run(test_correct_booking_api())
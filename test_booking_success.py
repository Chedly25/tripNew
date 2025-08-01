#!/usr/bin/env python3
"""
Test successful Booking.com API and parse the response.
"""
import asyncio
import aiohttp
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def test_booking_success():
    """Test and parse the successful Booking.com API response."""
    print("=== TESTING SUCCESSFUL BOOKING.COM API ===")
    
    api_key = os.getenv('RAPIDAPI_KEY')
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
    
    headers = {
        'x-rapidapi-host': 'booking-com15.p.rapidapi.com',
        'x-rapidapi-key': api_key
    }
    
    params = {
        'dest_id': '-1456928',
        'search_type': 'CITY',
        'arrival_date': '2025-08-14',
        'departure_date': '2025-08-21',
        'adults': '1',
        'room_qty': '1',
        'page_number': '1',
        'units': 'metric',
        'temperature_unit': 'c',
        'languagecode': 'en-us',
        'currency_code': 'EUR',
        'location': 'FR'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print("SUCCESS: Booking.com API is working!")
                    print(f"Response type: {type(data)}")
                    
                    if isinstance(data, dict):
                        print(f"Top-level keys: {list(data.keys())}")
                        
                        # Navigate to hotels
                        if 'result' in data:
                            result = data['result']
                            if isinstance(result, dict) and 'hotels' in result:
                                hotels = result['hotels']
                                print(f"FOUND {len(hotels)} REAL HOTELS!")
                                
                                # Show first 3 hotels
                                for i, hotel in enumerate(hotels[:3], 1):
                                    if isinstance(hotel, dict):
                                        name = hotel.get('hotel_name', 'Unknown')
                                        rating = hotel.get('review_score', 'N/A')
                                        address = hotel.get('address', 'N/A')
                                        print(f"  {i}. {name}")
                                        print(f"     Rating: {rating}/10")
                                        print(f"     Address: {address}")
                                        
                                        # Check for price information
                                        if 'price_breakdown' in hotel:
                                            price_info = hotel['price_breakdown']
                                            if 'gross_price' in price_info:
                                                price = price_info['gross_price'].get('value', 'N/A')
                                                currency = price_info.get('currency', 'EUR')
                                                print(f"     Price: {price} {currency}")
                                
                                print("\nSUCCESS: Real Booking.com hotel data retrieved!")
                                return True
                            else:
                                print("Hotels not found in expected location")
                                print(f"Result structure: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                    
                else:
                    print(f"HTTP Error: {response.status}")
                    
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    return False

if __name__ == "__main__":
    asyncio.run(test_booking_success())
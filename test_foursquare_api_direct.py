#!/usr/bin/env python3
"""
Test the Foursquare API directly to see if it's working.
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_foursquare_api_direct():
    """Test the Foursquare API directly."""
    print("=== TESTING FOURSQUARE API DIRECTLY ===")
    
    api_key = os.getenv('FOURSQUARE_API_KEY')
    if not api_key:
        print("ERROR: No Foursquare API key found")
        return
    
    print(f"Foursquare API Key: {api_key[:10]}...")
    
    # Test the Foursquare Places API
    base_url = "https://api.foursquare.com/v3/places"
    
    headers = {
        'Authorization': api_key,
        'Accept': 'application/json'
    }
    
    async with aiohttp.ClientSession() as session:
        # Test: Search for restaurants in Nice
        print("\n1. Testing restaurant search in Nice...")
        
        url = f"{base_url}/search"
        params = {
            'll': '43.7102,7.2620',  # Nice coordinates
            'categories': '13000',  # Food & Drink category
            'limit': 5,
            'sort': 'RATING',
            'fields': 'name,rating,price,location,categories,photos,hours,website'
        }
        
        try:
            async with session.get(url, params=params, headers=headers) as response:
                print(f"Status: {response.status}")
                response_text = await response.text()
                print(f"Response length: {len(response_text)} characters")
                print(f"First 1000 chars: {response_text[:1000]}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        results = data.get('results', [])
                        print(f"\nFound {len(results)} restaurants:")
                        
                        for i, place in enumerate(results[:3], 1):
                            name = place.get('name', 'Unknown')
                            rating = place.get('rating', 'N/A')
                            website = place.get('website', 'N/A')
                            location = place.get('location', {})
                            address = location.get('formatted_address', 'N/A')
                            
                            print(f"  {i}. {name}")
                            print(f"     Rating: {rating}")
                            print(f"     Address: {address}")
                            print(f"     Website: {website}")
                            
                        if len(results) > 0:
                            print("\nSUCCESS: Foursquare API is working!")
                        else:
                            print("\nWARNING: No results returned")
                            
                    except Exception as e:
                        print(f"JSON parsing error: {e}")
                else:
                    print(f"API Error: {response.status}")
                    
        except Exception as e:
            print(f"Request error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== FOURSQUARE API TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_foursquare_api_direct())
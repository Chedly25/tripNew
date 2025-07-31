#!/usr/bin/env python3
"""
Test basic Google Places API functionality to check for quota/authentication issues.
"""
import sys
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_simple_places_api():
    """Test basic Google Places API calls."""
    print("=== TESTING BASIC GOOGLE PLACES API ===")
    
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("ERROR: No API key found")
        return
    
    print(f"API Key: {api_key[:10]}...")
    
    base_url = "https://maps.googleapis.com/maps/api/place"
    
    # Test 1: Simple text search for a known city
    print("\n1. Testing text search for 'Nice France'...")
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{base_url}/textsearch/json"
            params = {
                'query': 'Nice France',
                'key': api_key
            }
            
            async with session.get(url, params=params) as response:
                print(f"Status: {response.status}")
                data = await response.json()
                
                if response.status == 200:
                    results = data.get('results', [])
                    print(f"Found {len(results)} results")
                    
                    if results:
                        first = results[0]
                        name = first.get('name', 'Unknown')
                        location = first.get('geometry', {}).get('location', {})
                        print(f"First result: {name} at {location}")
                    else:
                        print("No results found")
                else:
                    print(f"API Error: {data}")
                    
        except Exception as e:
            print(f"Request error: {e}")
    
    # Test 2: Nearby search around a known location (Nice, France)
    print("\n2. Testing nearby search around Nice, France...")
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{base_url}/nearbysearch/json"
            params = {
                'location': '43.7102,7.2620',  # Nice coordinates
                'radius': 50000,  # 50km
                'type': 'locality',
                'key': api_key
            }
            
            async with session.get(url, params=params) as response:
                print(f"Status: {response.status}")
                data = await response.json()
                
                if response.status == 200:
                    results = data.get('results', [])
                    print(f"Found {len(results)} nearby places")
                    
                    for i, place in enumerate(results[:5]):
                        name = place.get('name', 'Unknown')
                        location = place.get('geometry', {}).get('location', {})
                        types = place.get('types', [])
                        print(f"  {i+1}. {name} at {location} - Types: {types[:3]}")
                        
                else:
                    print(f"API Error: {data}")
                    
        except Exception as e:
            print(f"Request error: {e}")
    
    # Test 3: Check API quotas (if available in response)
    print("\n3. Testing with different search parameters...")
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{base_url}/nearbysearch/json"
            params = {
                'location': '44.4853,8.8815',  # Midpoint between Aix and Venice
                'radius': 30000,  # 30km
                'type': 'tourist_attraction',
                'key': api_key
            }
            
            async with session.get(url, params=params) as response:
                print(f"Status: {response.status}")
                data = await response.json()
                
                if response.status == 200:
                    results = data.get('results', [])
                    print(f"Found {len(results)} tourist attractions")
                    
                    for i, place in enumerate(results[:3]):
                        name = place.get('name', 'Unknown')
                        location = place.get('geometry', {}).get('location', {})
                        rating = place.get('rating', 'N/A')
                        print(f"  {i+1}. {name} at {location} - Rating: {rating}")
                        
                else:
                    print(f"API Error: {data}")
                    if 'error_message' in data:
                        print(f"Error message: {data['error_message']}")
                    
        except Exception as e:
            print(f"Request error: {e}")
    
    print("\n=== BASIC API TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_simple_places_api())
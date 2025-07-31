#!/usr/bin/env python3
"""
Detailed Google Places API test with full error reporting.
"""
import sys
import os
import asyncio
import aiohttp
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_api_detailed():
    """Test Google Places API with detailed error reporting."""
    print("=== DETAILED GOOGLE PLACES API TEST ===")
    
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("ERROR: No API key found")
        return
    
    print(f"API Key: {api_key}")  # Show full key for debugging
    
    base_url = "https://maps.googleapis.com/maps/api/place"
    
    # Test with the simplest possible request
    print("\n1. Testing simplest text search...")
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{base_url}/textsearch/json"
            params = {
                'query': 'Paris',
                'key': api_key
            }
            
            print(f"Request URL: {url}")
            print(f"Request params: {params}")
            
            async with session.get(url, params=params) as response:
                print(f"Response status: {response.status}")
                print(f"Response headers: {dict(response.headers)}")
                
                # Get response text for debugging
                response_text = await response.text()
                print(f"Response body: {response_text}")
                
                try:
                    data = json.loads(response_text)
                    print(f"Parsed JSON: {json.dumps(data, indent=2)}")
                    
                    # Check for specific error fields
                    if 'status' in data:
                        print(f"API Status: {data['status']}")
                    if 'error_message' in data:
                        print(f"Error Message: {data['error_message']}")
                    if 'results' in data:
                        print(f"Results count: {len(data['results'])}")
                        
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    
        except Exception as e:
            print(f"Request error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n=== DETAILED API TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_api_detailed())
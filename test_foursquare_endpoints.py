"""
Test different Foursquare API endpoints to find the correct one
"""
import asyncio
import aiohttp
import os

os.environ['FOURSQUARE_API_KEY'] = 'VLWY02FCX44U25TLQB243URQIIZX1Q0USJ521ZZ0SLQXG4R3'

async def test_foursquare_endpoints():
    """Test different Foursquare API endpoints."""
    print("Testing Foursquare API Endpoints")
    print("=" * 40)
    
    api_key = os.getenv('FOURSQUARE_API_KEY')
    print(f"API Key: {api_key[:20]}...")
    
    # Test different endpoints
    endpoints = [
        {
            'name': 'Original v3 endpoint',
            'url': 'https://api.foursquare.com/v3/places/search',
            'headers': {
                'Authorization': api_key,
                'Accept': 'application/json'
            }
        },
        {
            'name': 'Original v3 with Bearer',
            'url': 'https://api.foursquare.com/v3/places/search',
            'headers': {
                'Authorization': f'Bearer {api_key}',
                'Accept': 'application/json'
            }
        },
        {
            'name': 'Migration guide endpoint',
            'url': 'https://places-api.foursquare.com/places/search',
            'headers': {
                'Authorization': f'Bearer {api_key}',
                'Accept': 'application/json',
                'X-Places-Api-Version': '2025-06-17'
            }
        }
    ]
    
    params = {
        'll': '45.4408,12.3155',  # Venice coordinates
        'categories': '13000',    # Food & Drink
        'limit': 5
    }
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            print(f"\n--- Testing {endpoint['name']} ---")
            print(f"URL: {endpoint['url']}")
            print(f"Headers: {endpoint['headers']}")
            
            try:
                async with session.get(endpoint['url'], headers=endpoint['headers'], params=params) as response:
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        print(f"SUCCESS! Found {len(results)} places")
                        
                        if results:
                            place = results[0]
                            print(f"First result: {place.get('name', 'Unknown')}")
                            print(f"Categories: {[cat.get('name') for cat in place.get('categories', [])]}")
                        
                    else:
                        error_text = await response.text()
                        print(f"ERROR: {error_text}")
                        
            except Exception as e:
                print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    asyncio.run(test_foursquare_endpoints())
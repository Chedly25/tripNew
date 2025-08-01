"""
Test Amadeus API credentials directly to debug authentication issue
"""
import asyncio
import aiohttp
import os

# Set credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'

async def test_amadeus_auth():
    """Test Amadeus API authentication directly."""
    print("Testing Amadeus API Authentication")
    print("=" * 40)
    
    client_id = os.getenv('AMADEUS_CLIENT_ID')
    client_secret = os.getenv('AMADEUS_CLIENT_SECRET')
    
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret[:10]}...")
    
    auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    async with aiohttp.ClientSession() as session:
        print(f"\nSending auth request to: {auth_url}")
        print(f"Data: {data}")
        
        async with session.post(auth_url, data=data, headers=headers) as response:
            print(f"\nResponse Status: {response.status}")
            
            if response.status == 200:
                result = await response.json()
                print("SUCCESS! Authentication successful")
                print(f"Access Token: {result.get('access_token', '')[:20]}...")
                print(f"Token Type: {result.get('token_type')}")
                print(f"Expires In: {result.get('expires_in')} seconds")
                return result.get('access_token')
            else:
                error_result = await response.json()
                print("FAILED! Authentication error:")
                print(f"Error: {error_result}")
                return None

async def test_amadeus_hotels_with_token(token):
    """Test hotel search with valid token."""
    if not token:
        print("No token available, skipping hotel test")
        return
    
    print("\n" + "=" * 40)
    print("Testing Hotel Search with Token")
    print("=" * 40)
    
    # Venice coordinates
    base_url = "https://test.api.amadeus.com"
    url = f"{base_url}/v1/reference-data/locations/hotels/by-geocode"
    
    params = {
        'latitude': 45.4408,
        'longitude': 12.3155,
        'radius': 5,
        'radiusUnit': 'KM',
        'hotelSource': 'ALL'
    }
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    async with aiohttp.ClientSession() as session:
        print(f"Sending hotel search request to: {url}")
        print(f"Params: {params}")
        
        async with session.get(url, headers=headers, params=params) as response:
            print(f"\nResponse Status: {response.status}")
            
            if response.status == 200:
                result = await response.json()
                hotels_data = result.get('data', [])
                print(f"SUCCESS! Found {len(hotels_data)} hotels")
                
                for i, hotel in enumerate(hotels_data[:3], 1):
                    print(f"{i}. {hotel.get('name', 'Unknown')}")
                    print(f"   Hotel ID: {hotel.get('hotelId')}")
                    print(f"   Address: {hotel.get('address', {}).get('lines', [])}")
                
            else:
                error_result = await response.json()
                print("FAILED! Hotel search error:")
                print(f"Error: {error_result}")

async def main():
    """Main test function."""
    token = await test_amadeus_auth()
    await test_amadeus_hotels_with_token(token)

if __name__ == "__main__":
    asyncio.run(main())
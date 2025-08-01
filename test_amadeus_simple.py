"""
Simple Amadeus Hotel Search API test without Unicode issues.
"""
import os
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

# Set credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'


async def test_amadeus_api():
    """Test Amadeus API with complete credentials."""
    client_id = os.getenv('AMADEUS_CLIENT_ID')
    client_secret = os.getenv('AMADEUS_CLIENT_SECRET')
    
    print("Amadeus Hotel Search API Test")
    print("=" * 40)
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret[:8]}...")
    
    session = aiohttp.ClientSession()
    
    try:
        # Step 1: Get access token
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        auth_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        print("\nStep 1: Getting access token...")
        async with session.post(auth_url, data=auth_data, headers=auth_headers) as response:
            auth_result = await response.json()
            print(f"Auth status: {response.status}")
            
            if response.status == 200 and 'access_token' in auth_result:
                access_token = auth_result['access_token']
                expires_in = auth_result.get('expires_in', 1800)
                print(f"SUCCESS: Got access token!")
                print(f"Token: {access_token[:20]}...")
                print(f"Expires in: {expires_in} seconds")
            else:
                print(f"FAILED: Auth error - {auth_result}")
                return
        
        # Step 2: Search hotels in Paris
        print("\nStep 2: Searching hotels in Paris...")
        search_url = "https://test.api.amadeus.com/v3/shopping/hotel-offers"
        search_headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        check_in = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        check_out = (datetime.now() + timedelta(days=31)).strftime('%Y-%m-%d')
        
        search_params = {
            'cityCode': 'PAR',
            'checkInDate': check_in,
            'checkOutDate': check_out,
            'adults': 2,
            'max': 5
        }
        
        print(f"Searching: {check_in} to {check_out}, 2 adults")
        
        async with session.get(search_url, headers=search_headers, params=search_params) as response:
            search_result = await response.json()
            print(f"Search status: {response.status}")
            
            if response.status == 200:
                hotels = search_result.get('data', [])
                print(f"SUCCESS: Found {len(hotels)} hotels!")
                
                for i, hotel in enumerate(hotels[:3], 1):  # Show first 3
                    hotel_info = hotel.get('hotel', {})
                    offers = hotel.get('offers', [])
                    
                    name = hotel_info.get('name', 'Unknown Hotel')
                    hotel_id = hotel_info.get('hotelId', 'N/A')
                    
                    if offers:
                        price = offers[0].get('price', {})
                        total = price.get('total', 'N/A')
                        currency = price.get('currency', 'EUR')
                        print(f"  {i}. {name}")
                        print(f"     ID: {hotel_id}")
                        print(f"     Price: {total} {currency}")
                    else:
                        print(f"  {i}. {name} - No offers")
                
                # Save sample result
                with open('amadeus_test_result.json', 'w') as f:
                    json.dump(search_result, f, indent=2)
                print("\nSample result saved to amadeus_test_result.json")
                
            else:
                print(f"FAILED: Search error - {search_result}")
        
        # Step 3: Test other cities
        print("\nStep 3: Testing other cities...")
        test_cities = ['ROM', 'MAD', 'BCN']  # Rome, Madrid, Barcelona
        
        for city in test_cities:
            search_params['cityCode'] = city
            search_params['max'] = 2  # Fewer results
            
            async with session.get(search_url, headers=search_headers, params=search_params) as response:
                if response.status == 200:
                    result = await response.json()
                    hotel_count = len(result.get('data', []))
                    print(f"  {city}: {hotel_count} hotels found")
                else:
                    print(f"  {city}: Search failed ({response.status})")
                
                await asyncio.sleep(0.5)  # Rate limiting
        
        print("\nALL TESTS COMPLETED!")
        
    except Exception as e:
        print(f"ERROR: {e}")
    
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(test_amadeus_api())
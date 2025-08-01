"""
Test Amadeus Hotel Search API with complete credentials.
"""
import os
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

# Set credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'


class AmadeusAPITester:
    """Test Amadeus API with complete credentials."""
    
    def __init__(self):
        self.client_id = os.getenv('AMADEUS_CLIENT_ID')
        self.client_secret = os.getenv('AMADEUS_CLIENT_SECRET')
        
        # Amadeus API endpoints
        self.auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        self.base_url = "https://test.api.amadeus.com"
        
        self.access_token = None
        self.token_expires_at = None
        self.session = None
    
    async def get_access_token(self):
        """Get access token using client credentials."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            print(f"Requesting access token...")
            print(f"Client ID: {self.client_id}")
            print(f"Client Secret: {self.client_secret[:8]}...")
            
            async with self.session.post(self.auth_url, data=data, headers=headers) as response:
                result = await response.json()
                print(f"Auth response: Status {response.status}")
                
                if response.status == 200 and 'access_token' in result:
                    self.access_token = result['access_token']
                    expires_in = result.get('expires_in', 1800)  # Default 30 minutes
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    print(f"✅ Authentication successful!")
                    print(f"Access token: {self.access_token[:20]}...")
                    print(f"Expires in: {expires_in} seconds")
                    return True
                else:
                    print(f"❌ Authentication failed: {result}")
                    return False
                
        except Exception as e:
            print(f"❌ Auth error: {e}")
            return False
    
    async def search_hotels_by_city(self, city_code='PAR', adults=2, max_results=5):
        """Search hotels by city code."""
        if not self.access_token:
            print("No access token - cannot search hotels")
            return None
        
        try:
            endpoint = f"{self.base_url}/v3/shopping/hotel-offers"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
            
            # Calculate dates (30 days from now for 1 night)
            check_in = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            check_out = (datetime.now() + timedelta(days=31)).strftime('%Y-%m-%d')
            
            params = {
                'cityCode': city_code,
                'checkInDate': check_in,
                'checkOutDate': check_out,
                'adults': adults,
                'max': max_results
            }
            
            print(f"\n🏨 Searching hotels in {city_code}...")
            print(f"Check-in: {check_in}, Check-out: {check_out}")
            print(f"Adults: {adults}, Max results: {max_results}")
            
            async with self.session.get(endpoint, headers=headers, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Hotel search successful!")
                    
                    # Parse and display results
                    hotels = result.get('data', [])
                    print(f"Found {len(hotels)} hotels:")
                    
                    for i, hotel in enumerate(hotels, 1):
                        hotel_info = hotel.get('hotel', {})
                        offers = hotel.get('offers', [])
                        
                        name = hotel_info.get('name', 'Unknown Hotel')
                        hotel_id = hotel_info.get('hotelId', 'N/A')
                        
                        if offers:
                            price = offers[0].get('price', {})
                            total = price.get('total', 'N/A')
                            currency = price.get('currency', 'EUR')
                            
                            print(f"  {i}. {name} (ID: {hotel_id})")
                            print(f"     Price: {total} {currency} per night")
                        else:
                            print(f"  {i}. {name} (ID: {hotel_id}) - No offers available")
                    
                    return result
                else:
                    error_result = await response.json()
                    print(f"❌ Hotel search failed: Status {response.status}")
                    print(f"Error: {error_result}")
                    return None
                
        except Exception as e:
            print(f"❌ Hotel search error: {e}")
            return None
    
    async def get_hotel_details(self, hotel_id):
        """Get detailed information about a specific hotel."""
        if not self.access_token:
            print("No access token - cannot get hotel details")
            return None
        
        try:
            endpoint = f"{self.base_url}/v3/shopping/hotel-offers/by-hotel"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
            
            check_in = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            check_out = (datetime.now() + timedelta(days=31)).strftime('%Y-%m-%d')
            
            params = {
                'hotelId': hotel_id,
                'checkInDate': check_in,
                'checkOutDate': check_out,
                'adults': 2
            }
            
            print(f"\n🔍 Getting details for hotel {hotel_id}...")
            
            async with self.session.get(endpoint, headers=headers, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Hotel details retrieved!")
                    
                    hotel_data = result.get('data', {})
                    hotel_info = hotel_data.get('hotel', {})
                    
                    print(f"Hotel: {hotel_info.get('name', 'Unknown')}")
                    print(f"Address: {hotel_info.get('address', {})}")
                    print(f"Contact: {hotel_info.get('contact', {})}")
                    print(f"Amenities: {hotel_info.get('amenities', [])}")
                    
                    return result
                else:
                    error_result = await response.json()
                    print(f"❌ Hotel details failed: Status {response.status}")
                    print(f"Error: {error_result}")
                    return None
                
        except Exception as e:
            print(f"❌ Hotel details error: {e}")
            return None
    
    async def run_comprehensive_test(self):
        """Run comprehensive Amadeus API tests."""
        print("🏨 Amadeus Hotel Search API - Comprehensive Test")
        print("=" * 50)
        
        # Step 1: Authentication
        auth_success = await self.get_access_token()
        if not auth_success:
            print("❌ Cannot proceed without authentication")
            return
        
        # Step 2: Search hotels in Paris
        paris_hotels = await self.search_hotels_by_city('PAR', adults=2, max_results=3)
        
        # Step 3: Search hotels in Rome  
        rome_hotels = await self.search_hotels_by_city('ROM', adults=2, max_results=3)
        
        # Step 4: Get details for first Paris hotel if available
        if paris_hotels and paris_hotels.get('data'):
            first_hotel = paris_hotels['data'][0]
            hotel_id = first_hotel.get('hotel', {}).get('hotelId')
            if hotel_id:
                await self.get_hotel_details(hotel_id)
        
        # Step 5: Test different city codes
        test_cities = ['MAD', 'BCN', 'MIL', 'FLR']  # Madrid, Barcelona, Milan, Florence
        for city in test_cities:
            await self.search_hotels_by_city(city, adults=1, max_results=2)
            await asyncio.sleep(0.5)  # Rate limiting
        
        print("\n🎉 Comprehensive test completed!")
        
        # Cleanup
        if self.session:
            await self.session.close()


async def main():
    """Run Amadeus API comprehensive test."""
    tester = AmadeusAPITester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
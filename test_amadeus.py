"""
Test script for Amadeus Hotel Search API integration.
"""
import os
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta


class AmadeusAPITester:
    """Test Amadeus API functionality."""
    
    def __init__(self):
        # The provided key - need to determine if it's client_id or client_secret
        self.provided_key = "SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ"
        
        # Amadeus API endpoints
        self.auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        self.base_url = "https://test.api.amadeus.com"
        
        self.access_token = None
        self.session = None
    
    async def get_access_token_attempt1(self):
        """Try to get access token assuming provided key is client_id."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Try with provided key as client_id (need client_secret)
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.provided_key,
                'client_secret': 'unknown'  # This will likely fail
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            async with self.session.post(self.auth_url, data=data, headers=headers) as response:
                result = await response.json()
                print(f"Attempt 1 (key as client_id): Status {response.status}")
                print(f"Response: {result}")
                
                if response.status == 200 and 'access_token' in result:
                    self.access_token = result['access_token']
                    return True
                return False
                
        except Exception as e:
            print(f"Auth attempt 1 error: {e}")
            return False
    
    async def get_access_token_attempt2(self):
        """Try to get access token assuming provided key is client_secret."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Try with provided key as client_secret (need client_id)
            data = {
                'grant_type': 'client_credentials',
                'client_id': 'unknown',  # This will likely fail
                'client_secret': self.provided_key
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            async with self.session.post(self.auth_url, data=data, headers=headers) as response:
                result = await response.json()
                print(f"Attempt 2 (key as client_secret): Status {response.status}")
                print(f"Response: {result}")
                
                if response.status == 200 and 'access_token' in result:
                    self.access_token = result['access_token']
                    return True
                return False
                
        except Exception as e:
            print(f"Auth attempt 2 error: {e}")
            return False
    
    async def test_hotel_search(self):
        """Test hotel search functionality if we have access token."""
        if not self.access_token:
            print("No access token available - cannot test hotel search")
            return False
        
        try:
            # Test hotel search endpoint
            endpoint = f"{self.base_url}/v3/shopping/hotel-offers"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Search for hotels in Paris
            params = {
                'cityCode': 'PAR',
                'checkInDate': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'checkOutDate': (datetime.now() + timedelta(days=31)).strftime('%Y-%m-%d'),
                'adults': 2,
                'max': 5  # Limit results for testing
            }
            
            async with self.session.get(endpoint, headers=headers, params=params) as response:
                result = await response.json()
                print(f"Hotel search: Status {response.status}")
                print(f"Response: {json.dumps(result, indent=2)[:500]}...")
                
                return response.status == 200
                
        except Exception as e:
            print(f"Hotel search error: {e}")
            return False
    
    async def run_tests(self):
        """Run all API tests."""
        print("Testing Amadeus Hotel Search API")
        print("=" * 40)
        print(f"Provided key: {self.provided_key}")
        print()
        
        # Test authentication approaches
        print("Testing authentication...")
        auth1 = await self.get_access_token_attempt1()
        if not auth1:
            auth2 = await self.get_access_token_attempt2()
        
        # Test hotel search if authenticated
        if self.access_token:
            print(f"Successfully authenticated! Access token: {self.access_token[:20]}...")
            await self.test_hotel_search()
        else:
            print("Authentication failed. Need both client_id and client_secret.")
            print("The provided key might be only part of the credentials.")
        
        # Cleanup
        if self.session:
            await self.session.close()


async def main():
    """Run Amadeus API tests."""
    tester = AmadeusAPITester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())
"""
Amadeus Hotel Search API test with correct v3 workflow.
"""
import os
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

# Set credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'


async def test_amadeus_correct_workflow():
    """Test Amadeus API with correct v3 workflow."""
    client_id = os.getenv('AMADEUS_CLIENT_ID')
    client_secret = os.getenv('AMADEUS_CLIENT_SECRET')
    
    print("Amadeus Hotel Search API - Correct v3 Workflow")
    print("=" * 45)
    
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
        
        print("Step 1: Getting access token...")
        async with session.post(auth_url, data=auth_data, headers=auth_headers) as response:
            auth_result = await response.json()
            
            if response.status == 200 and 'access_token' in auth_result:
                access_token = auth_result['access_token']
                print(f"SUCCESS: Access token obtained!")
                print(f"Token expires in: {auth_result.get('expires_in', 1800)} seconds")
            else:
                print(f"FAILED: {auth_result}")
                return
        
        # Step 2: Get hotel IDs from city code using Hotel List API
        print("\nStep 2: Getting hotel IDs for Paris...")
        hotel_list_url = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
        api_headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        # Get hotels in Paris
        hotel_list_params = {
            'cityCode': 'PAR',
            'radius': 5,  # 5km radius
            'radiusUnit': 'KM',
            'hotelSource': 'ALL'
        }
        
        async with session.get(hotel_list_url, headers=api_headers, params=hotel_list_params) as response:
            hotel_list_result = await response.json()
            print(f"Hotel list status: {response.status}")
            
            if response.status == 200:
                hotels_data = hotel_list_result.get('data', [])
                print(f"SUCCESS: Found {len(hotels_data)} hotels in Paris!")
                
                # Get first 5 hotel IDs
                hotel_ids = []
                for hotel in hotels_data[:5]:
                    hotel_id = hotel.get('hotelId')
                    name = hotel.get('name', 'Unknown')
                    if hotel_id:
                        hotel_ids.append(hotel_id)
                        print(f"  - {name} (ID: {hotel_id})")
                
                if not hotel_ids:
                    print("No hotel IDs found!")
                    return
                
            else:
                print(f"FAILED: Hotel list error - {hotel_list_result}")
                return
        
        # Step 3: Search for offers using hotel IDs
        print(f"\nStep 3: Searching offers for {len(hotel_ids)} hotels...")
        offers_url = "https://test.api.amadeus.com/v3/shopping/hotel-offers"
        
        check_in = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        check_out = (datetime.now() + timedelta(days=31)).strftime('%Y-%m-%d')
        
        # Search for first 3 hotels
        offers_params = {
            'hotelIds': ','.join(hotel_ids[:3]),  # First 3 hotels
            'checkInDate': check_in,
            'checkOutDate': check_out,
            'adults': 2,
            'roomQuantity': 1
        }
        
        print(f"Dates: {check_in} to {check_out}")
        print(f"Hotel IDs: {offers_params['hotelIds']}")
        
        async with session.get(offers_url, headers=api_headers, params=offers_params) as response:
            offers_result = await response.json()
            print(f"Offers search status: {response.status}")
            
            if response.status == 200:
                offers_data = offers_result.get('data', [])
                print(f"SUCCESS: Found {len(offers_data)} hotel offers!")
                
                for i, offer in enumerate(offers_data, 1):
                    hotel_info = offer.get('hotel', {})
                    offers_list = offer.get('offers', [])
                    
                    name = hotel_info.get('name', 'Unknown Hotel')
                    hotel_id = hotel_info.get('hotelId', 'N/A')
                    
                    print(f"\n  {i}. {name} (ID: {hotel_id})")
                    
                    if offers_list:
                        best_offer = offers_list[0]  # First offer is usually best
                        price = best_offer.get('price', {})
                        room = best_offer.get('room', {})
                        
                        total = price.get('total', 'N/A')
                        currency = price.get('currency', 'EUR')
                        room_type = room.get('type', 'Standard')
                        
                        print(f"     Price: {total} {currency}")
                        print(f"     Room: {room_type}")
                        
                        # Show amenities if available
                        amenities = hotel_info.get('amenities', [])
                        if amenities:
                            amenity_names = [a.get('name', '') for a in amenities[:3]]
                            print(f"     Amenities: {', '.join(amenity_names)}")
                    else:
                        print(f"     No offers available")
                
                # Save detailed result
                with open('amadeus_hotels_result.json', 'w') as f:
                    json.dump(offers_result, f, indent=2)
                print(f"\nDetailed results saved to amadeus_hotels_result.json")
                
            else:
                print(f"FAILED: Offers search error - {offers_result}")
        
        # Step 4: Test other cities
        print("\nStep 4: Testing other cities...")
        test_cities = [('ROM', 'Rome'), ('MAD', 'Madrid'), ('BCN', 'Barcelona')]
        
        for city_code, city_name in test_cities:
            print(f"\nTesting {city_name} ({city_code})...")
            
            # Get hotel IDs for this city
            hotel_list_params['cityCode'] = city_code
            async with session.get(hotel_list_url, headers=api_headers, params=hotel_list_params) as response:
                if response.status == 200:
                    city_result = await response.json()
                    city_hotels = city_result.get('data', [])
                    if city_hotels:
                        city_hotel_ids = [h.get('hotelId') for h in city_hotels[:2] if h.get('hotelId')]
                        print(f"  Found {len(city_hotels)} hotels, testing {len(city_hotel_ids)} offers...")
                        
                        # Quick offers check
                        if city_hotel_ids:
                            offers_params['hotelIds'] = ','.join(city_hotel_ids)
                            async with session.get(offers_url, headers=api_headers, params=offers_params) as offer_response:
                                if offer_response.status == 200:
                                    city_offers = await offer_response.json()
                                    offers_count = len(city_offers.get('data', []))
                                    print(f"  SUCCESS: {offers_count} offers found")
                                else:
                                    print(f"  FAILED: Offers search failed ({offer_response.status})")
                    else:
                        print(f"  No hotels found in {city_name}")
                else:
                    print(f"  FAILED: Hotel list failed ({response.status})")
                
                await asyncio.sleep(0.5)  # Rate limiting
        
        print("\n" + "=" * 45)
        print("AMADEUS API TEST COMPLETED SUCCESSFULLY!")
        print("=" * 45)
        
    except Exception as e:
        print(f"ERROR: {e}")
    
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(test_amadeus_correct_workflow())
"""
Test the Flask /api/trip-data endpoint with Amadeus integration.
"""
import os
import requests
import json

# Set credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'

def test_trip_data_endpoint():
    """Test the /api/trip-data endpoint with real data."""
    print("Testing Flask /api/trip-data endpoint")
    print("=" * 40)
    
    # Test data - Venice coordinates
    test_data = {
        "cities": [
            {
                "name": "Venice", 
                "coordinates": [45.4408, 12.3155]
            }
        ]
    }
    
    # Start Flask app in test mode
    from src.web.app import create_app
    app = create_app()
    
    with app.test_client() as client:
        print("Sending POST request to /api/trip-data...")
        print(f"Request data: {json.dumps(test_data, indent=2)}")
        
        response = client.post(
            '/api/trip-data',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.get_json()
            print("SUCCESS! API Response:")
            print(f"Success: {result.get('success')}")
            
            hotels = result.get('data', {}).get('hotels', {})
            venice_hotels = hotels.get('Venice', [])
            
            print(f"\nVenice Hotels Found: {len(venice_hotels)}")
            
            for i, hotel in enumerate(venice_hotels[:3], 1):  # Show first 3
                print(f"\n{i}. {hotel.get('name', 'Unknown')}")
                print(f"   Price: {hotel.get('price_per_night')} {hotel.get('currency', 'EUR')}")
                print(f"   Rating: {hotel.get('rating')} stars")
                print(f"   Source: {hotel.get('source', 'unknown')}")
                
                # Check if it's real Amadeus data
                if hotel.get('amadeus_hotel_id'):
                    print(f"   Amadeus ID: {hotel.get('amadeus_hotel_id')}")
                    print("   ✅ REAL AMADEUS DATA!")
                elif hotel.get('source') == 'amadeus':
                    print("   ✅ AMADEUS SERVICE DATA!")
                else:
                    print("   ⚠️  Fallback data")
            
            # Save full response for inspection
            with open('flask_endpoint_test.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nFull response saved to flask_endpoint_test.json")
            
        else:
            print("FAILED! Error response:")
            print(response.get_data(as_text=True))


if __name__ == "__main__":
    test_trip_data_endpoint()
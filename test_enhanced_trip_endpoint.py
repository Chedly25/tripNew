"""
Test the enhanced /api/trip-data endpoint with OpenTripMap integration
"""
import os
import json

# Set all API credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'
os.environ['FOURSQUARE_API_KEY'] = 'VLWY02FCX44U25TLQB243URQIIZX1Q0USJ521ZZ0SLQXG4R3'
os.environ['OPENTRIPMAP_API_KEY'] = '5ae2e3f221c38a28845f05b695632f298c9cd7dcec52ac9251a5f7fd'

def test_enhanced_trip_endpoint():
    """Test the enhanced /api/trip-data endpoint with real OpenTripMap attractions."""
    print("Testing Enhanced /api/trip-data Endpoint with OpenTripMap")
    print("=" * 60)
    
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
            print("SUCCESS! Enhanced API Response:")
            print(f"Success: {result.get('success')}")
            
            data = result.get('data', {})
            hotels = data.get('hotels', {})
            restaurants = data.get('restaurants', {})
            activities = data.get('activities', {})
            
            print(f"\n=== HOTELS ===")
            venice_hotels = hotels.get('Venice', [])
            print(f"Hotels found: {len(venice_hotels)}")
            for i, hotel in enumerate(venice_hotels[:2], 1):
                print(f"{i}. {hotel.get('name', 'Unknown')}")
                print(f"   Source: {hotel.get('source', 'unknown')}")
                print(f"   Price: {hotel.get('price_per_night')} {hotel.get('currency', 'EUR')}")
            
            print(f"\n=== RESTAURANTS ===")
            venice_restaurants = restaurants.get('Venice', [])
            print(f"Restaurants found: {len(venice_restaurants)}")
            for i, restaurant in enumerate(venice_restaurants[:2], 1):
                print(f"{i}. {restaurant.get('name', 'Unknown')}")
                print(f"   Source: {restaurant.get('source', 'unknown')}")
                print(f"   Cuisine: {restaurant.get('cuisine', 'N/A')}")
                
                if restaurant.get('source') == 'foursquare':
                    print("   [SUCCESS] REAL FOURSQUARE DATA!")
                else:
                    print("   [FALLBACK] Sample/fallback data")
            
            print(f"\n=== ACTIVITIES/ATTRACTIONS ===")
            venice_activities = activities.get('Venice', [])
            print(f"Activities found: {len(venice_activities)}")
            for i, activity in enumerate(venice_activities[:3], 1):
                print(f"{i}. {activity.get('name', 'Unknown')}")
                print(f"   Source: {activity.get('source', 'unknown')}")
                print(f"   Category: {activity.get('category', 'N/A')}")
                print(f"   Rating: {activity.get('rating', 'N/A')}")
                
                if activity.get('source') == 'opentripmap':
                    print("   [SUCCESS] REAL OPENTRIPMAP ATTRACTION!")
                elif activity.get('source') == 'foursquare':
                    print("   [SUCCESS] REAL FOURSQUARE ACTIVITY!")
                else:
                    print("   [FALLBACK] Sample/fallback data")
                    
            # Save detailed response for inspection
            with open('enhanced_trip_data_test.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nFull response saved to enhanced_trip_data_test.json")
            
            # Check overall success rate
            real_hotels = sum(1 for h in venice_hotels if h.get('source') in ['amadeus'])
            real_restaurants = sum(1 for r in venice_restaurants if r.get('source') == 'foursquare')
            real_activities = sum(1 for a in venice_activities if a.get('source') in ['opentripmap', 'foursquare'])
            
            print(f"\n=== SUMMARY ===")
            print(f"Real Hotels: {real_hotels}/{len(venice_hotels)}")
            print(f"Real Restaurants: {real_restaurants}/{len(venice_restaurants)}")
            print(f"Real Activities: {real_activities}/{len(venice_activities)}")
            
        else:
            print("FAILED! Error response:")
            print(response.get_data(as_text=True))

if __name__ == "__main__":
    test_enhanced_trip_endpoint()
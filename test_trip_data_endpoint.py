"""
Test the /api/trip-data endpoint to debug restaurant/activity data
"""
import os
import requests
import json

# Set credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkysSqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'
os.environ['FOURSQUARE_API_KEY'] = 'VLWY02FCX44U25TLQB243URQIIZX1Q0USJ521ZZ0SLQXG4R3'

def test_trip_data_endpoint():
    """Test the /api/trip-data endpoint specifically for restaurant/activity data."""
    print("Testing /api/trip-data endpoint for restaurant/activity data")
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
            print("SUCCESS! API Response Structure:")
            print(f"Success: {result.get('success')}")
            
            data = result.get('data', {})
            hotels = data.get('hotels', {})
            restaurants = data.get('restaurants', {})
            activities = data.get('activities', {})
            
            print(f"\n=== HOTELS ===")
            venice_hotels = hotels.get('Venice', [])
            print(f"Hotels found: {len(venice_hotels)}")
            for i, hotel in enumerate(venice_hotels[:2], 1):  # Show first 2
                print(f"{i}. {hotel.get('name', 'Unknown')}")
                print(f"   Source: {hotel.get('source', 'unknown')}")
                print(f"   Price: {hotel.get('price_per_night')} {hotel.get('currency', 'EUR')}")
            
            print(f"\n=== RESTAURANTS ===")
            venice_restaurants = restaurants.get('Venice', [])
            print(f"Restaurants found: {len(venice_restaurants)}")
            for i, restaurant in enumerate(venice_restaurants[:2], 1):  # Show first 2
                print(f"{i}. {restaurant.get('name', 'Unknown')}")
                print(f"   Source: {restaurant.get('source', 'unknown')}")
                print(f"   Cuisine: {restaurant.get('cuisine', 'N/A')}")
                print(f"   Rating: {restaurant.get('rating', 'N/A')}")
                
                # Check if it's real data
                if restaurant.get('source') == 'foursquare':
                    print("   [SUCCESS] REAL FOURSQUARE DATA!")
                else:
                    print("   [FALLBACK] Sample/fallback data")
            
            print(f"\n=== ACTIVITIES ===")
            venice_activities = activities.get('Venice', [])
            print(f"Activities found: {len(venice_activities)}")
            for i, activity in enumerate(venice_activities[:2], 1):  # Show first 2
                print(f"{i}. {activity.get('name', 'Unknown')}")
                print(f"   Source: {activity.get('source', 'unknown')}")
                print(f"   Category: {activity.get('category', 'N/A')}")
                print(f"   Rating: {activity.get('rating', 'N/A')}")
                
                # Check if it's real data
                if activity.get('source') == 'foursquare':
                    print("   [SUCCESS] REAL FOURSQUARE DATA!")
                else:
                    print("   [FALLBACK] Sample/fallback data")
                    
            # Save detailed response for inspection
            with open('trip_data_test_detailed.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nFull response saved to trip_data_test_detailed.json")
            
        else:
            print("FAILED! Error response:")
            print(response.get_data(as_text=True))


if __name__ == "__main__":
    test_trip_data_endpoint()
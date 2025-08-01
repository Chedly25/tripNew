#!/usr/bin/env python3
"""
Test the complete integration: Eventbrite + OpenTripMap images + enhanced frontend
"""
import os
import json
import requests
import time

# Set all API credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'
os.environ['FOURSQUARE_API_KEY'] = 'VLWY02FCX44U25TLQB243URQIIZX1Q0USJ521ZZ0SLQXG4R3'
os.environ['OPENTRIPMAP_API_KEY'] = '5ae2e3f221c38a28845f05b695632f298c9cd7dcec52ac9251a5f7fd'
os.environ['EVENTBRITE_API_KEY'] = 'JSX3J2PNVFPHALLHFTHM'

def test_complete_integration():
    """Test the complete integration with all services."""
    print("Testing Complete API Integration")
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
            print("SUCCESS! Complete Integration Response:")
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
                print(f"   Photo: {'Available' if hotel.get('photo') else 'No photo'}")
            
            print(f"\n=== RESTAURANTS ===")
            venice_restaurants = restaurants.get('Venice', [])
            print(f"Restaurants found: {len(venice_restaurants)}")
            for i, restaurant in enumerate(venice_restaurants[:2], 1):
                print(f"{i}. {restaurant.get('name', 'Unknown')}")
                print(f"   Source: {restaurant.get('source', 'unknown')}")
                print(f"   Cuisine: {restaurant.get('cuisine', 'N/A')}")
                print(f"   Photo: {'Available' if restaurant.get('photo') else 'No photo'}")
                
                if restaurant.get('source') == 'foursquare':
                    print("   [SUCCESS] REAL FOURSQUARE DATA!")
                else:
                    print("   [FALLBACK] Sample/fallback data")
            
            print(f"\n=== ACTIVITIES/ATTRACTIONS ===")
            venice_activities = activities.get('Venice', [])
            print(f"Activities found: {len(venice_activities)}")
            
            # Count by source
            opentripmap_count = sum(1 for a in venice_activities if a.get('source') == 'opentripmap')
            eventbrite_count = sum(1 for a in venice_activities if a.get('source') == 'eventbrite')
            foursquare_count = sum(1 for a in venice_activities if a.get('source') == 'foursquare')  
            fallback_count = sum(1 for a in venice_activities if a.get('source') == 'fallback')
            
            print(f"Activity Sources:")
            print(f"   OpenTripMap: {opentripmap_count}")
            print(f"   Eventbrite: {eventbrite_count}")  
            print(f"   Foursquare: {foursquare_count}")
            print(f"   Fallback: {fallback_count}")
            
            # Show detailed info for first few activities
            for i, activity in enumerate(venice_activities[:5], 1):
                print(f"\n{i}. {activity.get('name', 'Unknown')}")
                print(f"   Source: {activity.get('source', 'unknown')}")
                print(f"   Category: {activity.get('category', 'N/A')}")
                print(f"   Rating: {activity.get('rating', 'N/A')}")
                print(f"   Photo: {'Available' if activity.get('photo') else 'No photo'}")
                print(f"   Description: {'Available' if activity.get('description') else 'No description'}")
                
                if activity.get('source') == 'opentripmap':
                    print("   [SUCCESS] REAL OPENTRIPMAP ATTRACTION WITH IMAGES!")
                elif activity.get('source') == 'eventbrite':
                    print("   [SUCCESS] EVENTBRITE EVENT INTEGRATED!")
                elif activity.get('source') == 'foursquare':
                    print("   [SUCCESS] REAL FOURSQUARE ACTIVITY!")
                else:
                    print("   [FALLBACK] Sample/fallback data")
                    
            # Save detailed response for inspection
            with open('complete_integration_test.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nFull response saved to complete_integration_test.json")
            
            # Check image availability
            images_available = sum(1 for a in venice_activities if a.get('photo'))
            print(f"\n=== IMAGE ANALYSIS ===")  
            print(f"Activities with images: {images_available}/{len(venice_activities)}")
            print(f"Image success rate: {(images_available/len(venice_activities)*100):.1f}%" if venice_activities else "0%")
            
            # Test Eventbrite integration specifically
            eventbrite_events = [a for a in venice_activities if a.get('source') == 'eventbrite']
            if eventbrite_events:
                print(f"\n=== EVENTBRITE EVENTS ===")
                for event in eventbrite_events:
                    print(f"- {event.get('name')}")
                    print(f"   Category: {event.get('category')}")
                    print(f"   Address: {event.get('address')}")
                    print(f"   URL: {event.get('url', 'N/A')}")
            
            print(f"\n=== FINAL SUMMARY ===")
            real_hotels = sum(1 for h in venice_hotels if h.get('source') in ['amadeus'])
            real_restaurants = sum(1 for r in venice_restaurants if r.get('source') == 'foursquare')
            real_activities = sum(1 for a in venice_activities if a.get('source') in ['opentripmap', 'foursquare', 'eventbrite'])
            
            print(f"Real Hotels: {real_hotels}/{len(venice_hotels)}")
            print(f"Real Restaurants: {real_restaurants}/{len(venice_restaurants)}")  
            print(f"Real Activities: {real_activities}/{len(venice_activities)}")
            print(f"Activities with Images: {images_available}/{len(venice_activities)}")
            print(f"Eventbrite Events: {eventbrite_count}")
            
            overall_success = (real_hotels + real_activities) / (len(venice_hotels) + len(venice_activities)) * 100
            print(f"\nOverall API Success Rate: {overall_success:.1f}%")
            
        else:
            print("FAILED! Error response:")
            print(response.get_data(as_text=True))

if __name__ == "__main__":
    test_complete_integration()
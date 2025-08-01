#!/usr/bin/env python3
"""
Test what might be happening on Heroku with the Google Places API.
"""
import requests
import json

def test_heroku_api_behavior():
    """Test the production behavior on Heroku."""
    print("=== TESTING HEROKU API BEHAVIOR ===")
    
    # Test locally first to establish baseline
    heroku_url = "http://127.0.0.1:5004"
    
    print(f"Testing: {heroku_url}")
    
    # Test the travel planning endpoint
    form_data = {
        'start_city': 'Aix-en-Provence',
        'end_city': 'Venice',
        'travel_days': '5',
        'nights_at_destination': '2',
        'season': 'summer',
        'trip_type': 'home'
    }
    
    try:
        print("\n1. Testing /plan endpoint...")
        response = requests.post(f"{heroku_url}/plan", data=form_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                routes = result.get('data', {}).get('routes', [])
                print(f"✅ Success: {len(routes)} routes generated")
                
                # Check intermediate cities for each route
                total_intermediates = 0
                for i, route in enumerate(routes, 1):
                    intermediates = route.get('intermediate_cities', [])
                    total_intermediates += len(intermediates)
                    print(f"   Route {i}: {route.get('name', 'Unknown')} - {len(intermediates)} intermediate cities")
                    
                    # Show first intermediate city if exists
                    if intermediates:
                        first_city = intermediates[0]
                        if isinstance(first_city, dict):
                            print(f"      First: {first_city.get('name', 'Unknown')} at {first_city.get('coordinates', 'No coords')}")
                        else:
                            print(f"      First: {first_city} (string format)")
                
                if total_intermediates == 0:
                    print("❌ PROBLEM: No intermediate cities found on Heroku!")
                    print("   This explains why you see straight lines in the frontend")
                else:
                    print(f"✅ SUCCESS: Found {total_intermediates} total intermediate cities")
                    
            else:
                print(f"❌ API Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - Heroku app might be slow to start")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n=== HEROKU TEST COMPLETE ===")

if __name__ == "__main__":
    test_heroku_api_behavior()
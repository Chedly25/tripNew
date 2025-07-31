#!/usr/bin/env python3
"""
Final comprehensive test of all fixes.
"""
import requests
import json

def test_all_fixes():
    """Test all the fixes comprehensively."""
    base_url = "http://127.0.0.1:5004"
    
    print("=== FINAL COMPREHENSIVE TEST ===")
    
    # Test 1: Aix-en-Provence to Venice (original issue)
    print("\n1. Testing Aix-en-Provence -> Venice...")
    form_data = {
        'start_city': 'Aix-en-Provence',
        'end_city': 'Venice',
        'travel_days': '5',
        'nights_at_destination': '2',
        'season': 'summer',
        'trip_type': 'home'
    }
    
    try:
        response = requests.post(base_url + "/plan", data=form_data)
        if response.status_code == 200:
            result = response.json()
            routes = result.get('data', {}).get('routes', [])
            print(f"Generated {len(routes)} routes")
            
            # Check each route has intermediate cities
            all_have_intermediate = True
            for i, route in enumerate(routes):
                intermediate = route.get('intermediate_cities', [])
                print(f"Route {i+1} ({route.get('name', 'Unknown')}): {len(intermediate)} intermediate cities")
                if len(intermediate) == 0:
                    all_have_intermediate = False
            
            if all_have_intermediate:
                print("SUCCESS: All routes have intermediate cities!")
            else:
                print("FAIL: Some routes missing intermediate cities")
        else:
            print(f"FAIL: HTTP {response.status_code}")
    except Exception as e:
        print(f"FAIL: {e}")
    
    # Test 2: Different cities (Paris to Rome)
    print(f"\n2. Testing Paris -> Rome...")
    form_data = {
        'start_city': 'Paris',
        'end_city': 'Rome',
        'travel_days': '5',
        'nights_at_destination': '2',
        'season': 'summer',
        'trip_type': 'home'
    }
    
    try:
        response = requests.post(base_url + "/plan", data=form_data)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                routes = result.get('data', {}).get('routes', [])
                print(f"SUCCESS: Paris -> Rome generated {len(routes)} routes")
            else:
                print(f"FAIL: {result.get('error')}")
        else:
            print(f"FAIL: HTTP {response.status_code}")
    except Exception as e:
        print(f"FAIL: {e}")
    
    # Test 3: Trip details API (start city exclusion)
    print(f"\n3. Testing trip details API (start city exclusion)...")
    cities_data = [
        {"name": "Cannes", "coordinates": [43.5528, 7.0174]},
        {"name": "Monaco", "coordinates": [43.7384, 7.4246]},
        {"name": "Venice", "coordinates": [45.4408, 12.3155]}
    ]
    
    try:
        response = requests.post(base_url + "/api/trip-data", 
                               json={"cities": cities_data},
                               headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                hotels = result.get('data', {}).get('hotels', {})
                print(f"SUCCESS: Got hotel data for {len(hotels)} cities")
                
                # Check for URLs in fallback data
                for city, city_hotels in hotels.items():
                    if city_hotels and len(city_hotels) > 0:
                        first_hotel = city_hotels[0]
                        if first_hotel.get('url') or first_hotel.get('website'):
                            print(f"SUCCESS: Hotel in {city} has URL: {first_hotel.get('url', first_hotel.get('website'))}")
                            break
            else:
                print(f"FAIL: {result.get('error')}")
        else:
            print(f"FAIL: HTTP {response.status_code}")
    except Exception as e:
        print(f"FAIL: {e}")
    
    print(f"\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    test_all_fixes()
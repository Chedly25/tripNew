#!/usr/bin/env python3
"""
Test the real frontend flow exactly as user experiences it.
"""
import requests
import json
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_frontend_flow():
    """Test the exact flow a user would experience."""
    base_url = "http://127.0.0.1:5004"
    
    print("=== TESTING REAL FRONTEND FLOW ===")
    
    # Test 1: Homepage loads
    print("\n1. Testing homepage...")
    try:
        response = requests.get(base_url + "/")
        print(f"Homepage status: {response.status_code}")
        if response.status_code != 200:
            print(f"ERROR: Homepage failed to load")
            return
    except Exception as e:
        print(f"ERROR: Cannot connect to app: {e}")
        return
    
    # Test 2: Submit form data exactly like frontend
    print("\n2. Testing form submission (Aix-en-Provence -> Venice)...")
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
        print(f"Form submission status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response success: {result.get('success', False)}")
            
            if result.get('success'):
                routes = result.get('data', {}).get('routes', [])
                print(f"Number of routes generated: {len(routes)}")
                
                for i, route in enumerate(routes, 1):
                    print(f"\n--- Route {i}: {route.get('name', 'Unknown')} ---")
                    print(f"Type: {route.get('route_type')}")
                    print(f"Distance: {route.get('total_distance_km')} km")
                    
                    intermediate = route.get('intermediate_cities', [])
                    print(f"Intermediate cities: {len(intermediate)}")
                    
                    if intermediate:
                        for city in intermediate:
                            if isinstance(city, dict):
                                print(f"  - {city.get('name', 'Unknown')} ({city.get('coordinates', 'No coords')})")
                            else:
                                print(f"  - {city}")
                    else:
                        print("  ❌ NO INTERMEDIATE CITIES!")
                        
            else:
                print(f"❌ Route generation failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Test 3: Try different cities
    print(f"\n3. Testing different cities (Paris -> Rome)...")
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
        print(f"Paris->Rome status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Paris->Rome success: {result.get('success', False)}")
            if not result.get('success'):
                print(f"❌ Error: {result.get('error', 'Unknown')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_frontend_flow()
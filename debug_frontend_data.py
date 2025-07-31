#!/usr/bin/env python3
"""
Test what exactly the frontend receives and processes.
"""
import requests
import json
from pprint import pprint

def test_frontend_data():
    """Test the exact data that goes to the frontend."""
    base_url = "http://127.0.0.1:5004"
    
    print("=== TESTING FRONTEND DATA FLOW ===")
    
    # Submit form and get the exact JSON response
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
            
            print(f"Success: {result.get('success')}")
            
            if result.get('success'):
                # This is exactly what gets stored in sessionStorage
                print("\n=== DATA STORED IN SESSIONSTORAGE ===")
                print("Structure:")
                print(f"- success: {result.get('success')}")
                print(f"- data: {type(result.get('data'))}")
                print(f"- data.routes: {type(result.get('data', {}).get('routes'))}")
                print(f"- Number of routes: {len(result.get('data', {}).get('routes', []))}")
                
                routes = result.get('data', {}).get('routes', [])
                
                print(f"\n=== ROUTE ANALYSIS ===")
                for i, route in enumerate(routes, 1):
                    print(f"\nRoute {i}:")
                    print(f"  - name: {route.get('name')}")
                    print(f"  - route_type: {route.get('route_type')}")
                    print(f"  - intermediate_cities type: {type(route.get('intermediate_cities'))}")
                    print(f"  - intermediate_cities count: {len(route.get('intermediate_cities', []))}")
                    
                    # Check the structure of intermediate cities
                    intermediate = route.get('intermediate_cities', [])
                    if intermediate:
                        print(f"  - First intermediate city type: {type(intermediate[0])}")
                        if isinstance(intermediate[0], dict):
                            print(f"  - First intermediate city keys: {list(intermediate[0].keys())}")
                            print(f"  - First intermediate city: {intermediate[0]}")
                        else:
                            print(f"  - First intermediate city value: {intermediate[0]}")
                    else:
                        print(f"  - NO INTERMEDIATE CITIES FOUND!")
                
                # Save to file for inspection
                with open("frontend_data.json", "w") as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"\n✅ Full data saved to 'frontend_data.json'")
                
        else:
            print(f"HTTP Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_frontend_data()
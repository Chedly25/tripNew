#!/usr/bin/env python3
"""
Debug frontend data storage to see what's being stored in sessionStorage.
"""
import requests
import json

def test_frontend_data_storage():
    """Test what data is being stored and retrieved in the frontend."""
    print("=== DEBUGGING FRONTEND DATA STORAGE ===")
    
    base_url = "http://127.0.0.1:5004"
    
    # Test the API endpoint directly
    print("\n1. Testing API endpoint directly...")
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
            print(f"SUCCESS API Response: {result.get('success')}")
            
            if result.get('success') and 'data' in result:
                routes = result['data'].get('routes', [])
                print(f"FOUND {len(routes)} routes")
                
                for i, route in enumerate(routes):
                    intermediate_cities = route.get('intermediate_cities', [])
                    print(f"   Route {i+1}: {route.get('name', 'Unknown')} - {len(intermediate_cities)} intermediate cities")
                    
                    # Show the structure of intermediate cities
                    if intermediate_cities:
                        first_city = intermediate_cities[0]
                        print(f"     First city structure: {type(first_city)} - {first_city}")
                        
                        # Check coordinates format
                        if hasattr(first_city, 'get') and 'coordinates' in first_city:
                            coords = first_city['coordinates']
                            print(f"     Coordinates type: {type(coords)} - {coords}")
                
                # Show what would be stored in sessionStorage
                print(f"\n📦 Data structure that would be stored in sessionStorage:")
                print(f"   - result.success: {result.get('success')}")
                print(f"   - result.data exists: {'data' in result}")
                print(f"   - result.data.routes exists: {'routes' in result.get('data', {})}")
                print(f"   - Total JSON size: {len(json.dumps(result))} bytes")
                
            else:
                print(f"ERROR API returned success=False or no data: {result}")
        else:
            print(f"ERROR HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"ERROR Request failed: {e}")
    
    print(f"\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    test_frontend_data_storage()
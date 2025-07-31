#!/usr/bin/env python3
"""
Simulate the exact user workflow to identify where the issue occurs.
"""
import requests
import json
import time

def simulate_user_workflow():
    """Simulate exactly what a user does."""
    base_url = "http://127.0.0.1:5004"
    session = requests.Session()
    
    print("=== SIMULATING USER WORKFLOW ===")
    
    # Step 1: User visits homepage
    print("\n1. User visits homepage...")
    try:
        response = session.get(base_url + "/")
        print(f"✓ Homepage loaded: {response.status_code}")
    except Exception as e:
        print(f"✗ Homepage failed: {e}")
        return
    
    # Step 2: User fills form and submits
    print("\n2. User submits form (Aix-en-Provence → Venice)...")
    form_data = {
        'start_city': 'Aix-en-Provence',
        'end_city': 'Venice',
        'travel_days': '5',
        'nights_at_destination': '2',
        'season': 'summer',
        'trip_type': 'home'
    }
    
    try:
        response = session.post(base_url + "/plan", data=form_data)
        print(f"Form submission status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                routes = result.get('data', {}).get('routes', [])
                print(f"✓ Generated {len(routes)} routes")
                
                # Check if routes have intermediate cities
                has_intermediate = False
                for i, route in enumerate(routes):
                    intermediate = route.get('intermediate_cities', [])
                    if intermediate:
                        has_intermediate = True
                        print(f"✓ Route {i+1} ({route.get('name', 'Unknown')}) has {len(intermediate)} intermediate cities")
                        for city in intermediate[:2]:  # Show first 2
                            city_name = city.get('name') if isinstance(city, dict) else str(city)
                            print(f"    - {city_name}")
                    else:
                        print(f"✗ Route {i+1} ({route.get('name', 'Unknown')}) has NO intermediate cities")
                
                if not has_intermediate:
                    print("✗ CRITICAL: NO ROUTES HAVE INTERMEDIATE CITIES!")
                else:
                    print("✓ All routes have intermediate cities")
                    
                # Save what would be stored in sessionStorage
                session_data = json.dumps(result)
                print(f"✓ SessionStorage data size: {len(session_data)} characters")
                
            else:
                print(f"✗ Route generation failed: {result.get('error')}")
        else:
            print(f"✗ HTTP Error: {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"✗ Form submission failed: {e}")
        return
    
    # Step 3: User would be redirected to /results
    print("\n3. User visits results page...")
    try:
        response = session.get(base_url + "/results")
        print(f"✓ Results page loaded: {response.status_code}")
        
        # Check if results page contains expected elements
        html_content = response.text
        if 'itineraries-container' in html_content:
            print("✓ Results page has itineraries container")
        else:
            print("✗ Results page missing itineraries container")
            
        if 'loadItineraries' in html_content:
            print("✓ Results page has loadItineraries function")
        else:
            print("✗ Results page missing loadItineraries function")
            
    except Exception as e:
        print(f"✗ Results page failed: {e}")
        return
    
    # Step 4: Test different cities (user's other complaint)
    print("\n4. Testing different cities (Paris → Rome)...")
    form_data = {
        'start_city': 'Paris',
        'end_city': 'Rome',
        'travel_days': '5',
        'nights_at_destination': '2',
        'season': 'summer',
        'trip_type': 'home'
    }
    
    try:
        response = session.post(base_url + "/plan", data=form_data)
        print(f"Paris → Rome status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                routes = result.get('data', {}).get('routes', [])
                print(f"✓ Paris → Rome generated {len(routes)} routes")
            else:
                print(f"✗ Paris → Rome failed: {result.get('error')}")
        else:
            print(f"✗ Paris → Rome HTTP Error: {response.status_code}")
            if response.status_code == 500:
                print("This matches user's complaint about other cities not working!")
                
    except Exception as e:
        print(f"✗ Paris → Rome request failed: {e}")

if __name__ == "__main__":
    simulate_user_workflow()
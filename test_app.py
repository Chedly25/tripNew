#!/usr/bin/env python3
"""
Quick test script to verify the road trip app is working correctly.
"""
import requests
import json
import time

def test_app():
    base_url = "http://127.0.0.1:5004"
    
    print("Testing European Road Trip Planner")
    print("="*50)
    
    # Test 1: Check if homepage loads
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            print("SUCCESS: Homepage loads successfully")
        else:
            print(f"ERROR: Homepage failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Homepage test failed: {e}")
        return False
    
    # Test 2: Check if results page loads
    try:
        response = requests.get(f"{base_url}/results", timeout=10)
        if response.status_code == 200:
            print("SUCCESS: Results page loads successfully")
        else:
            print(f"ERROR: Results page failed with status {response.status_code}")
    except Exception as e:
        print(f"ERROR: Results page test failed: {e}")
    
    # Test 3: Test route planning endpoint
    try:
        form_data = {
            'start_city': 'Aix-en-Provence',
            'end_city': 'Venice',
            'travel_days': '5',
            'nights_at_destination': '2',
            'season': 'summer',
            'trip_type': 'home'
        }
        
        print("Testing route planning: Aix-en-Provence -> Venice")
        response = requests.post(f"{base_url}/plan", data=form_data, timeout=30)
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    routes = result.get('data', {}).get('routes', [])
                    print(f"SUCCESS: Route planning successful! Generated {len(routes)} routes")
                    
                    # Display route summary
                    for i, route in enumerate(routes, 1):
                        print(f"   Route {i}: {route.get('name', 'Unknown')} ({route.get('total_distance_km', 0)}km)")
                else:
                    print(f"ERROR: Route planning failed: {result.get('error', 'Unknown error')}")
            except json.JSONDecodeError:
                print("ERROR: Route planning returned invalid JSON")
        else:
            print(f"ERROR: Route planning failed with status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"ERROR: Route planning test failed: {e}")
    
    # Test 4: Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"SUCCESS: Health check passed - App version: {health_data.get('version')}")
        else:
            print(f"ERROR: Health check failed with status {response.status_code}")
    except Exception as e:
        print(f"ERROR: Health check failed: {e}")
    
    print("\nTesting completed!")
    print("\nTo use the app:")
    print(f"   1. Open http://127.0.0.1:5004 in your browser")
    print(f"   2. Enter your trip details (e.g., Aix-en-Provence to Venice)")
    print(f"   3. Click 'Create My Perfect Journey'")
    print(f"   4. View 5 different route options with interactive maps!")
    
    return True

if __name__ == "__main__":
    print("Waiting for server to be ready...")
    time.sleep(2)  # Give server time to start
    test_app()
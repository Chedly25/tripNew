#!/usr/bin/env python3
"""
Test the complete browser flow to simulate what happens when a user submits the form.
"""
import requests
import time

def test_browser_flow():
    """Simulate the complete browser flow."""
    print("=== TESTING COMPLETE BROWSER FLOW ===")
    
    base_url = "http://127.0.0.1:5004"
    
    # Step 1: Access the main page
    print("\n1. Accessing main page...")
    try:
        response = requests.get(base_url)
        print(f"Main page status: {response.status_code}")
    except Exception as e:
        print(f"ERROR accessing main page: {e}")
        return
    
    # Step 2: Submit the form (simulating what the browser does)
    print("\n2. Submitting travel planning form...")
    form_data = {
        'start_city': 'Aix-en-Provence',
        'end_city': 'Venice',
        'travel_days': '5',
        'nights_at_destination': '2',
        'season': 'summer',
        'trip_type': 'home'
    }
    
    try:
        # Use a session to maintain cookies like a browser
        session = requests.Session()
        response = session.post(base_url + "/plan", data=form_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Form submission success: {result.get('success')}")
            
            if result.get('success'):
                # Step 3: Access the results page (what browser would do after redirect)
                print("\n3. Accessing results page after form submission...")
                results_response = session.get(base_url + "/results")
                print(f"Results page status: {results_response.status_code}")
                
                # Check if the results page contains the expected JavaScript data structure
                results_content = results_response.text
                if "intermediate_cities" in results_content:
                    print("SUCCESS: Results page contains intermediate_cities references")
                else:
                    print("WARNING: Results page does not contain intermediate_cities references")
                
                # Check if the sample data is being used instead
                if "sampleItineraries" in results_content:
                    print("INFO: Results page contains sample data fallback")
                
                # Check for console.log statements that would help debug
                if "console.log" in results_content:
                    print("INFO: Results page contains debug console.log statements")
                
                # Show a snippet of what's in the results page
                print(f"\nSample of results page content (first 1000 chars):")
                print(results_content[:1000])
                
            else:
                print(f"Form submission failed: {result}")
        else:
            print(f"HTTP Error submitting form: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"ERROR in browser flow: {e}")
    
    print(f"\n=== BROWSER FLOW TEST COMPLETE ===")

if __name__ == "__main__":
    test_browser_flow()
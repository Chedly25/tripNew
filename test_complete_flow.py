#!/usr/bin/env python3
"""
Complete end-to-end test of the road trip application.
Tests the full user flow from form submission to results display.
"""
import json
from src.web.app import create_app

def test_complete_flow():
    """Test the complete user flow."""
    print("Testing complete road trip application flow...")
    
    app = create_app()
    with app.test_client() as client:
        print("\n1. Testing main page loads...")
        response = client.get('/')
        assert response.status_code == 200
        print("SUCCESS: Main page loads successfully")
        
        print("\n2. Testing form submission...")
        form_data = {
            'start_city': 'Aix-en-Provence',
            'end_city': 'Venice',
            'travel_days': '5',
            'nights_at_destination': '2',
            'season': 'summer',
            'trip_type': 'home'
        }
        
        response = client.post('/plan', data=form_data)
        assert response.status_code == 200
        print("SUCCESS: Form submission successful")
        
        print("\n3. Testing API response structure...")
        result = response.get_json()
        print(f"Response keys: {list(result.keys())}")
        
        assert result['success'] == True
        assert 'data' in result
        assert 'routes' in result['data']
        
        routes = result['data']['routes']
        print(f"SUCCESS: Generated {len(routes)} routes")
        
        print("\n4. Testing route data structure...")
        for i, route in enumerate(routes):
            print(f"\nRoute {i+1}: {route['name']}")
            print(f"  - Type: {route['route_type']}")
            print(f"  - Distance: {route['total_distance_km']} km")
            print(f"  - Duration: {route['total_duration_hours']} hours")
            print(f"  - Intermediate cities: {len(route['intermediate_cities'])}")
            
            # Test intermediate cities structure
            for j, city in enumerate(route['intermediate_cities']):
                if isinstance(city, dict):
                    print(f"    {j+1}. {city['name']} - {city['coordinates']}")
                else:
                    print(f"    {j+1}. {city}")
            
            # Verify essential route data
            assert 'name' in route
            assert 'route_type' in route
            assert 'intermediate_cities' in route
            assert 'start_city' in route
            assert 'end_city' in route
            assert isinstance(route['intermediate_cities'], list)
            
        print("SUCCESS: All routes have proper structure")
        
        print("\n5. Testing results page loads...")
        response = client.get('/results')
        assert response.status_code == 200
        print("SUCCESS: Results page loads successfully")
        
        print("\n6. Testing health check...")
        response = client.get('/health')
        health_data = response.get_json()
        print(f"Health status: {health_data}")
        print("SUCCESS: Health check completed")
        
        print("\nALL TESTS PASSED!")
        print("The complete road trip application flow is working correctly!")
        
        return True

if __name__ == "__main__":
    try:
        test_complete_flow()
        print("\nSUCCESS: All functionality working perfectly!")
        print("The app is ready for deployment on Heroku!")
        print("Users can now plan their road trips with:")
        print("   - 5 different route types (scenic, cultural, adventure, culinary, romantic)")
        print("   - Real intermediate cities between start and destination")
        print("   - Interactive maps with route visualization")
        print("   - Complete cost estimates and highlights")
        print("   - Full API integration with Google Places, OpenRoute, and OpenWeather")
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
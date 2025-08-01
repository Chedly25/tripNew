#!/usr/bin/env python3
"""
Test script to verify the route calculation fix
"""
import json
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_route_calculations():
    """Test the enhanced route calculation function"""
    try:
        from web.app import enhance_route_with_calculations
        
        print("Testing Route Calculations")
        print("=" * 50)
        
        # Test case 1: Empty route
        print("\n1. Testing empty route (Aix-en-Provence → Venice)")
        route = {}
        result = enhance_route_with_calculations(route, 'Aix-en-Provence', 'Venice')
        
        print(f"   Distance: {result['total_distance']} km")
        print(f"   Duration: {result['total_duration']} minutes ({result['total_duration']//60}h {result['total_duration']%60}m)")
        print(f"   Fuel Cost: €{result['estimated_fuel_cost']}")
        print(f"   Coordinates: {len(result.get('coordinates', []))} waypoints")
        
        # Test case 2: Route with some missing data
        print("\n2. Testing route with partial data (Paris → Rome)")
        route = {'total_distance': None, 'coordinates': []}
        result = enhance_route_with_calculations(route, 'Paris', 'Rome')
        
        print(f"   Distance: {result['total_distance']} km")
        print(f"   Duration: {result['total_duration']} minutes ({result['total_duration']//60}h {result['total_duration']%60}m)")
        print(f"   Fuel Cost: €{result['estimated_fuel_cost']}")
        print(f"   Coordinates: {len(result.get('coordinates', []))} waypoints")
        
        # Test case 3: Unknown route
        print("\n3. Testing unknown route (Berlin → Madrid)")
        route = {}
        result = enhance_route_with_calculations(route, 'Berlin', 'Madrid')
        
        print(f"   Distance: {result['total_distance']} km")
        print(f"   Duration: {result['total_duration']} minutes ({result['total_duration']//60}h {result['total_duration']%60}m)")
        print(f"   Fuel Cost: €{result['estimated_fuel_cost']}")
        
        # Verify no NaN values
        print("\nVerification:")
        for key, value in result.items():
            if isinstance(value, (int, float)):
                if str(value).lower() in ['nan', 'inf', '-inf'] or value != value:  # NaN check
                    print(f"   ERROR {key}: Invalid value ({value})")
                    return False
                else:
                    print(f"   SUCCESS {key}: Valid value ({value})")
        
        print("\nAll tests passed! Route calculations are working correctly.")
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mock_api_response():
    """Test creating a complete API response with route calculations"""
    print("\nTesting Complete API Response")
    print("=" * 50)
    
    try:
        from web.app import enhance_route_with_calculations
        
        # Simulate the route data that would come from the route service
        mock_route_data = {
            'routes': [
                {
                    'route_type': 'scenic',
                    'start_city': {'name': 'Aix-en-Provence', 'country': 'France'},
                    'end_city': {'name': 'Venice', 'country': 'Italy'},
                    'waypoints': [
                        {'name': 'Nice', 'country': 'France'},
                        {'name': 'Genoa', 'country': 'Italy'},
                        {'name': 'Bologna', 'country': 'Italy'}
                    ]
                }
            ]
        }
        
        # Enhance each route
        enhanced_routes = []
        for route in mock_route_data['routes']:
            enhanced_route = enhance_route_with_calculations(
                route, 
                route['start_city']['name'], 
                route['end_city']['name']
            )
            enhanced_routes.append(enhanced_route)
        
        # Create complete response
        api_response = {
            'success': True,
            'data': {
                'routes': enhanced_routes,
                'trip_details': {
                    'duration_days': 8,
                    'season': 'summer',
                    'travel_style': 'scenic'
                }
            }
        }
        
        print("Complete API Response:")
        print(json.dumps(api_response, indent=2, default=str))
        
        # Verify no NaN values in the response
        route = api_response['data']['routes'][0]
        assert route['total_distance'] > 0, "Distance should be positive"
        assert route['total_duration'] > 0, "Duration should be positive" 
        assert route['estimated_fuel_cost'] > 0, "Fuel cost should be positive"
        assert len(route['coordinates']) > 0, "Should have coordinates"
        
        print("\nComplete API response test passed!")
        return True
        
    except Exception as e:
        print(f"API response test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("EuroRoam Route Calculation Tests")
    print("Testing the fix for NaN values in route calculations")
    print()
    
    success1 = test_route_calculations()
    success2 = test_mock_api_response()
    
    if success1 and success2:
        print("\nALL TESTS PASSED!")
        print("The route calculation fix is working correctly.")
        print("No more NaN values should appear in the frontend!")
    else:
        print("\nSOME TESTS FAILED")
        sys.exit(1)
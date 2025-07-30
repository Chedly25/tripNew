#!/usr/bin/env python3
"""
Test Geographic Routing - Verify routes are geographically logical
"""

from geographic_router import GeographicRouter

def test_geographic_routing():
    router = GeographicRouter()
    
    # Test different route combinations
    test_routes = [
        ("Paris", "Rome", "Different routes should be generated for different start/end combinations"),
        ("London", "Berlin", "London to Berlin should go through different cities than Paris to Rome"),
        ("Barcelona", "Vienna", "Long route should have logical intermediate cities"),
        ("Amsterdam", "Venice", "Northern to Southern Europe route"),
        ("Aix-en-Provence", "Venice", "Original route with new geographic logic")
    ]
    
    print("TESTING GEOGRAPHIC ROUTING SYSTEM")
    print("=" * 60)
    
    for start, end, description in test_routes:
        print(f"\nROUTE: {start} -> {end}")
        print(f"Description: {description}")
        print("-" * 40)
        
        # Test different focus types
        for focus in ['speed', 'scenery', 'culture', 'culinary']:
            cities = router.generate_route_cities(start, end, focus)
            print(f"\n{focus.upper()} FOCUS:")
            
            start_info = router.get_city_info(start)
            end_info = router.get_city_info(end)
            
            print(f"   Start: {start} ({start_info['lat']:.2f}, {start_info['lon']:.2f})")
            
            for i, city in enumerate(cities, 1):
                print(f"   Stop {i}: {city['name']}, {city['country']}")
                print(f"          Reason: {city['reason']}")
                print(f"          Distance from start: {city['distance_from_start']:.0f}km")
            
            print(f"   End: {end} ({end_info['lat']:.2f}, {end_info['lon']:.2f})")
            
            # Calculate total route distance
            total_distance = router.calculate_distance(
                start_info['lat'], start_info['lon'],
                end_info['lat'], end_info['lon']
            )
            print(f"   Direct distance: {total_distance:.0f}km")
    
    print("\n" + "=" * 60)
    print("GEOGRAPHIC ROUTING TEST COMPLETED")
    print("Each route should show different, logical intermediate cities")
    print("Cities should be geographically between start and end points")

if __name__ == "__main__":
    test_geographic_routing()
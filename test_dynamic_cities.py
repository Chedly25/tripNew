#!/usr/bin/env python3
"""
Test script to demonstrate dynamic city count calculation based on trip duration.
"""

# Simulate the calculation logic
def calculate_optimal_city_count(strategy_type: str, trip_days: int) -> int:
    """Calculate optimal number of intermediate cities based on trip duration and type."""
    
    # Base ratios: cities per day for different route types
    base_ratios = {
        'scenic': 0.4,      # Scenic routes: spend more time in fewer places to enjoy views
        'cultural': 0.6,    # Cultural routes: more cities to see different heritage sites
        'adventure': 0.3,   # Adventure routes: fewer cities, more time for activities
        'culinary': 0.5,    # Culinary routes: moderate pace to savor local cuisine
        'romantic': 0.3,    # Romantic routes: fewer cities, more time to relax
        'hidden_gems': 0.4  # Hidden gems: moderate pace to discover authentic places
    }
    
    ratio = base_ratios.get(strategy_type, 0.4)  # Default ratio
    
    # Calculate base city count
    base_count = max(1, int(trip_days * ratio))
    
    # Apply constraints based on trip duration
    if trip_days <= 3:
        # Short trips: 1-2 intermediate cities max
        return min(base_count, 2)
    elif trip_days <= 7:
        # Week-long trips: 2-4 intermediate cities
        return min(base_count, 4)
    elif trip_days <= 14:
        # Two-week trips: 3-8 intermediate cities
        return min(base_count, 8)
    else:
        # Long trips: 4-12 intermediate cities
        return min(max(base_count, 4), 12)

def calculate_ml_recommendation_count(duration_days: int) -> int:
    """Calculate optimal number of city recommendations based on trip duration."""
    if duration_days <= 3:
        return min(8, max(3, duration_days * 2))  # 3-6 recommendations for short trips
    elif duration_days <= 7:
        return min(12, max(5, int(duration_days * 1.2)))  # 5-8 recommendations for week trips
    elif duration_days <= 14:
        return min(15, max(8, int(duration_days * 0.8)))  # 8-11 recommendations for two weeks
    else:
        return min(20, max(10, int(duration_days * 0.6)))  # 10-20 recommendations for long trips

if __name__ == "__main__":
    print("DYNAMIC CITY COUNT CALCULATION TEST")
    print("=" * 50)
    
    # Test different trip durations and route types
    test_cases = [
        (3, "Weekend getaway"),
        (7, "Week vacation"), 
        (14, "Two-week trip"),
        (21, "Three-week adventure"),
        (30, "Month-long journey")
    ]
    
    route_types = ['scenic', 'cultural', 'adventure', 'culinary', 'romantic', 'hidden_gems']
    
    for days, description in test_cases:
        print(f"\n{description} ({days} days):")
        print("-" * 30)
        
        for route_type in route_types:
            intermediate_cities = calculate_optimal_city_count(route_type, days)
            ml_recommendations = calculate_ml_recommendation_count(days)
            
            print(f"  {route_type:12} -> {intermediate_cities:2d} intermediate cities, {ml_recommendations:2d} ML recommendations")
    
    print("\nKey Improvements:")
    print("  * No more hardcoded 2-3 city limits!")
    print("  * Scales intelligently with trip duration")
    print("  * Different ratios per route type (cultural > culinary > scenic > adventure/romantic)")
    print("  * ML system provides more candidates to choose from")
    print("  * Longer trips get substantially more intermediate stops")
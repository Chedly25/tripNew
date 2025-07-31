#!/usr/bin/env python3
"""
Debug the Google Places API route search to see why no intermediate cities are found.
"""
import sys
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.google_places_city_service import GooglePlacesCityService
from src.core.models import Coordinates
from geopy.distance import geodesic

async def debug_route_search():
    """Debug the route search logic."""
    print("=== DEBUGGING ROUTE SEARCH ===")
    
    # Test coordinates
    aix_coords = Coordinates(latitude=43.5297, longitude=5.4474)
    venice_coords = Coordinates(latitude=45.4408, longitude=12.3155)
    
    print(f"Route: Aix-en-Provence {aix_coords.latitude},{aix_coords.longitude}")
    print(f"    -> Venice {venice_coords.latitude},{venice_coords.longitude}")
    
    # Calculate route distance
    route_distance = geodesic(
        (aix_coords.latitude, aix_coords.longitude),
        (venice_coords.latitude, venice_coords.longitude)
    ).kilometers
    print(f"Route distance: {route_distance:.1f} km")
    
    # Calculate midpoint
    mid_lat = (aix_coords.latitude + venice_coords.latitude) / 2
    mid_lng = (aix_coords.longitude + venice_coords.longitude) / 2
    print(f"Route midpoint: {mid_lat:.4f}, {mid_lng:.4f}")
    
    city_service = GooglePlacesCityService()
    
    try:
        # Test with the actual Google Places search
        print(f"\n=== Testing Google Places nearby search ===")
        
        # Search for cities along the route - let's try a manual approach
        search_radius = min(100 * 1000, 50000)  # 50km max
        print(f"Search radius: {search_radius/1000:.1f} km")
        
        # Use the internal method to search for places
        places = await city_service._search_places_along_route(
            center_lat=mid_lat,
            center_lng=mid_lng,
            radius=search_radius,
            route_start=aix_coords,
            route_end=venice_coords,
            max_deviation_km=100
        )
        
        print(f"Found {len(places)} raw places from Google API")
        
        # Show first few places
        for i, place in enumerate(places[:10]):
            name = place.get('name', 'Unknown')
            location = place.get('geometry', {}).get('location', {})
            lat = location.get('lat', 0)
            lng = location.get('lng', 0)
            types = place.get('types', [])
            rating = place.get('rating', 0)
            
            print(f"  {i+1}. {name} at {lat:.4f},{lng:.4f} - Rating: {rating} - Types: {types[:3]}")
            
            # Check if this place passes the route filter (debugging)
            if lat and lng:
                place_coords = Coordinates(latitude=lat, longitude=lng)
                is_near = city_service._is_place_near_route(place, aix_coords, venice_coords, 100)
                
                # Calculate distances for manual check
                start_dist = geodesic((lat, lng), (aix_coords.latitude, aix_coords.longitude)).kilometers
                end_dist = geodesic((lat, lng), (venice_coords.latitude, venice_coords.longitude)).kilometers
                deviation = abs(start_dist + end_dist - route_distance)
                
                print(f"     -> Start dist: {start_dist:.1f}km, End dist: {end_dist:.1f}km, Deviation: {deviation:.1f}km, Near route: {is_near}")
        
        # Now test the full conversion to cities
        print(f"\n=== Testing city conversion ===")
        cities = []
        for place in places[:5]:  # Test first 5
            city = await city_service._create_city_from_place(place)
            if city:
                cities.append(city)
                print(f"Converted: {city.name} ({city.country}) - Types: {city.types}")
        
        print(f"\nSuccessfully converted {len(cities)} places to cities")
        
        # Test fallback method for comparison
        print(f"\n=== Testing fallback method ===")
        fallback_cities = city_service._get_fallback_route_cities(aix_coords, venice_coords, 100)
        print(f"Fallback method found {len(fallback_cities)} cities:")
        for city in fallback_cities[:5]:
            print(f"  - {city.name} ({city.country}) - Types: {city.types}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await city_service.close()
    
    print(f"\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(debug_route_search())
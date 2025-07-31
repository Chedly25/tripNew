"""
Real-world routing service using Google Maps and OpenRoute Service APIs
"""
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from geopy.distance import geodesic
from config import Config
import logging

logger = logging.getLogger(__name__)

class RoutingService:
    def __init__(self):
        self.google_api_key = Config.GOOGLE_MAPS_API_KEY
        self.openroute_api_key = Config.OPENROUTE_API_KEY
        self.use_google = bool(self.google_api_key and self.google_api_key != 'your_google_maps_api_key_here')
        self.use_openroute = bool(self.openroute_api_key and self.openroute_api_key != 'your_openroute_api_key_here')
        
    def geocode_city(self, city_name: str, country: str = None) -> Optional[Dict]:
        """Get latitude and longitude for a city"""
        if self.use_google:
            return self._geocode_google(city_name, country)
        elif self.use_openroute:
            return self._geocode_openroute(city_name, country)
        else:
            # Fallback to hardcoded coordinates
            return self._geocode_fallback(city_name)
    
    def _geocode_google(self, city_name: str, country: str = None) -> Optional[Dict]:
        """Geocode using Google Maps API"""
        try:
            query = city_name
            if country:
                query += f", {country}"
            
            params = {
                'address': query,
                'key': self.google_api_key
            }
            
            response = requests.get(Config.GOOGLE_GEOCODING_URL, params=params)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                return {
                    'lat': location['lat'],
                    'lon': location['lng'],
                    'formatted_address': data['results'][0]['formatted_address']
                }
        except Exception as e:
            logger.error(f"Google geocoding error for {city_name}: {e}")
            
        return None
    
    def _geocode_openroute(self, city_name: str, country: str = None) -> Optional[Dict]:
        """Geocode using OpenRoute Service"""
        try:
            query = city_name
            if country:
                query += f", {country}"
                
            headers = {'Authorization': self.openroute_api_key}
            params = {'text': query}
            
            response = requests.get(
                f"{Config.OPENROUTE_URL}/geocoding/search",
                headers=headers,
                params=params
            )
            data = response.json()
            
            if data.get('features'):
                coords = data['features'][0]['geometry']['coordinates']
                return {
                    'lat': coords[1],
                    'lon': coords[0],
                    'formatted_address': data['features'][0]['properties']['label']
                }
        except Exception as e:
            logger.error(f"OpenRoute geocoding error for {city_name}: {e}")
            
        return None
    
    def _geocode_fallback(self, city_name: str) -> Optional[Dict]:
        """Fallback geocoding using hardcoded coordinates"""
        coordinates = {
            'paris': {'lat': 48.8566, 'lon': 2.3522},
            'rome': {'lat': 41.9028, 'lon': 12.4964},
            'barcelona': {'lat': 41.3851, 'lon': 2.1734},
            'venice': {'lat': 45.4404, 'lon': 12.3160},
            'aix-en-provence': {'lat': 43.5297, 'lon': 5.4474},
            'milan': {'lat': 45.4642, 'lon': 9.1900},
            'florence': {'lat': 43.7696, 'lon': 11.2558},
            'nice': {'lat': 43.7102, 'lon': 7.2620},
            'madrid': {'lat': 40.4168, 'lon': -3.7038},
            'vienna': {'lat': 48.2082, 'lon': 16.3738}
        }
        
        city_key = city_name.lower().replace(' ', '-')
        if city_key in coordinates:
            coords = coordinates[city_key]
            return {
                'lat': coords['lat'],
                'lon': coords['lon'],
                'formatted_address': city_name
            }
        return None
    
    def get_route_with_traffic(self, start_coords: Tuple[float, float], 
                              end_coords: Tuple[float, float],
                              waypoints: List[Tuple[float, float]] = None,
                              departure_time: datetime = None) -> Optional[Dict]:
        """Get route with real-time traffic data"""
        if self.use_google:
            return self._get_route_google(start_coords, end_coords, waypoints, departure_time)
        elif self.use_openroute:
            return self._get_route_openroute(start_coords, end_coords, waypoints)
        else:
            return self._get_route_fallback(start_coords, end_coords, waypoints)
    
    def _get_route_google(self, start_coords: Tuple[float, float],
                         end_coords: Tuple[float, float],
                         waypoints: List[Tuple[float, float]] = None,
                         departure_time: datetime = None) -> Optional[Dict]:
        """Get route using Google Directions API"""
        try:
            params = {
                'origin': f"{start_coords[0]},{start_coords[1]}",
                'destination': f"{end_coords[0]},{end_coords[1]}",
                'key': self.google_api_key,
                'traffic_model': 'best_guess',
                'departure_time': 'now'
            }
            
            if departure_time:
                # Convert to Unix timestamp
                params['departure_time'] = int(departure_time.timestamp())
            
            if waypoints:
                waypoint_str = '|'.join([f"{wp[0]},{wp[1]}" for wp in waypoints])
                params['waypoints'] = waypoint_str
            
            response = requests.get(Config.GOOGLE_DIRECTIONS_URL, params=params)
            data = response.json()
            
            if data['status'] == 'OK' and data['routes']:
                route = data['routes'][0]
                leg = route['legs'][0]
                
                return {
                    'distance_km': leg['distance']['value'] / 1000,
                    'duration_hours': leg['duration']['value'] / 3600,
                    'duration_in_traffic_hours': leg.get('duration_in_traffic', {}).get('value', leg['duration']['value']) / 3600,
                    'polyline': route['overview_polyline']['points'],
                    'steps': [step['html_instructions'] for step in leg['steps']],
                    'traffic_delay_minutes': (leg.get('duration_in_traffic', {}).get('value', 0) - leg['duration']['value']) / 60,
                    'route_quality': 'excellent' if len(route['warnings']) == 0 else 'good'
                }
                
        except Exception as e:
            logger.error(f"Google routing error: {e}")
            
        return None
    
    def _get_route_openroute(self, start_coords: Tuple[float, float],
                            end_coords: Tuple[float, float],
                            waypoints: List[Tuple[float, float]] = None) -> Optional[Dict]:
        """Get route using OpenRoute Service"""
        try:
            headers = {
                'Authorization': self.openroute_api_key,
                'Content-Type': 'application/json'
            }
            
            coordinates = [[start_coords[1], start_coords[0]]]  # OpenRoute uses [lon, lat]
            
            if waypoints:
                for wp in waypoints:
                    coordinates.append([wp[1], wp[0]])
                    
            coordinates.append([end_coords[1], end_coords[0]])
            
            body = {
                'coordinates': coordinates,
                'format_out': 'geojson',
                'profile': 'driving-car',
                'geometry_format': 'polyline',
                'instructions': True
            }
            
            response = requests.post(
                f"{Config.OPENROUTE_URL}/directions/driving-car/geojson",
                headers=headers,
                json=body
            )
            data = response.json()
            
            if data.get('features'):
                feature = data['features'][0]
                props = feature['properties']
                
                return {
                    'distance_km': props['segments'][0]['distance'] / 1000,
                    'duration_hours': props['segments'][0]['duration'] / 3600,
                    'duration_in_traffic_hours': props['segments'][0]['duration'] / 3600,  # No traffic data
                    'polyline': feature['geometry'],
                    'steps': [step['instruction'] for step in props['segments'][0]['steps']],
                    'traffic_delay_minutes': 0,  # No traffic data available
                    'route_quality': 'good'
                }
                
        except Exception as e:
            logger.error(f"OpenRoute routing error: {e}")
            
        return None
    
    def _get_route_fallback(self, start_coords: Tuple[float, float],
                           end_coords: Tuple[float, float],
                           waypoints: List[Tuple[float, float]] = None) -> Optional[Dict]:
        """Fallback route calculation using simple distance"""
        try:
            # Calculate straight-line distance
            total_distance = geodesic(start_coords, end_coords).kilometers
            
            # Add waypoint distances
            if waypoints:
                prev_point = start_coords
                for wp in waypoints:
                    total_distance += geodesic(prev_point, wp).kilometers
                    prev_point = wp
                total_distance += geodesic(prev_point, end_coords).kilometers
            
            # Estimate driving time (assume 80 km/h average)
            duration_hours = total_distance / 80
            
            return {
                'distance_km': total_distance,
                'duration_hours': duration_hours,
                'duration_in_traffic_hours': duration_hours * 1.2,  # Add 20% for traffic
                'polyline': None,
                'steps': ['Drive from start to destination'],
                'traffic_delay_minutes': duration_hours * 0.2 * 60,
                'route_quality': 'estimated'
            }
            
        except Exception as e:
            logger.error(f"Fallback routing error: {e}")
            
        return None
    
    def get_alternative_routes(self, start_coords: Tuple[float, float],
                              end_coords: Tuple[float, float],
                              num_alternatives: int = 3) -> List[Dict]:
        """Get multiple route alternatives"""
        routes = []
        
        # Get main route
        main_route = self.get_route_with_traffic(start_coords, end_coords)
        if main_route:
            main_route['route_type'] = 'fastest'
            routes.append(main_route)
        
        # For now, create variations of the main route
        # In a real implementation, you'd request actual alternative routes
        if main_route:
            # Scenic route (longer but potentially more interesting)
            scenic_route = main_route.copy()
            scenic_route.update({
                'distance_km': main_route['distance_km'] * 1.15,
                'duration_hours': main_route['duration_hours'] * 1.1,
                'route_type': 'scenic',
                'route_quality': 'scenic'
            })
            routes.append(scenic_route)
            
            # Avoid highways route
            avoid_highways = main_route.copy()
            avoid_highways.update({
                'distance_km': main_route['distance_km'] * 1.08,
                'duration_hours': main_route['duration_hours'] * 1.25,
                'route_type': 'avoid_highways',
                'route_quality': 'local_roads'
            })
            routes.append(avoid_highways)
        
        return routes[:num_alternatives]
    
    def estimate_fuel_cost(self, distance_km: float, country: str, fuel_efficiency: float = 7.5) -> float:
        """Estimate fuel cost for a route"""
        fuel_price = Config.FUEL_PRICES.get(country.lower(), 1.60)  # Default price
        liters_needed = distance_km / 100 * fuel_efficiency
        return liters_needed * fuel_price
    
    def estimate_toll_cost(self, distance_km: float, country: str) -> float:
        """Estimate toll costs for a route"""
        toll_rate = Config.TOLL_COSTS.get(country.lower(), 0.0)
        return (distance_km / 100) * toll_rate
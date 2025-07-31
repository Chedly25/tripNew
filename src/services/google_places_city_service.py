"""
Dynamic City Service using Google Places API for real-time city discovery.
This replaces hardcoded city data with live Google Places searches.
"""
import os
import asyncio
import aiohttp
from typing import List, Optional, Dict, Any, Tuple
from geopy.distance import geodesic
import structlog
from ..core.models import City, Coordinates, ServiceResult
from ..core.exceptions import ExternalServiceError

logger = structlog.get_logger(__name__)


class GooglePlacesCityService:
    """Dynamic city service using Google Places API for real-time discovery."""
    
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.session = None
        self._city_cache: Dict[str, City] = {}
        
        if not self.google_api_key:
            logger.warning("Google Places API key not configured - using minimal fallback")
    
    async def get_city_by_name(self, name: str) -> Optional[City]:
        """Get city by name using Google Places API."""
        if not name or not name.strip():
            return None
        
        # Check cache first
        cache_key = name.lower().strip()
        if cache_key in self._city_cache:
            return self._city_cache[cache_key]
        
        if not self.google_api_key:
            return self._get_fallback_city(name)
        
        try:
            # Search for the city using Google Places API
            search_results = await self._search_cities(name)
            
            if search_results:
                # Take the first result as the most relevant
                place = search_results[0]
                city = await self._create_city_from_place(place)
                
                if city:
                    self._city_cache[cache_key] = city
                    return city
            
            return self._get_fallback_city(name)
            
        except Exception as e:
            logger.error(f"Failed to find city {name}: {e}")
            return self._get_fallback_city(name)
    
    async def find_cities_near_route(self, start: Coordinates, end: Coordinates, 
                                   max_deviation_km: float = 100) -> List[City]:
        """Find interesting cities near the route using Google Places API."""
        if not self.google_api_key:
            logger.warning("No Google API key - returning empty list for route cities")
            return []
        
        try:
            # Calculate midpoint and search radius
            mid_lat = (start.latitude + end.latitude) / 2
            mid_lng = (start.longitude + end.longitude) / 2
            
            # Calculate distance between start and end to determine search radius
            route_distance = geodesic(
                (start.latitude, start.longitude),
                (end.latitude, end.longitude)
            ).kilometers
            
            # Search radius should cover the route corridor
            search_radius = min(max_deviation_km * 1000, 50000)  # Max 50km radius
            
            # Search for tourist attractions and cities along the route
            places = await self._search_places_along_route(
                center_lat=mid_lat,
                center_lng=mid_lng,
                radius=search_radius,
                route_start=start,
                route_end=end,
                max_deviation_km=max_deviation_km
            )
            
            cities = []
            for place in places:
                city = await self._create_city_from_place(place)
                if city and city.name not in [c.name for c in cities]:
                    cities.append(city)
            
            return cities[:10]  # Return top 10 cities
            
        except Exception as e:
            logger.error(f"Failed to find cities near route: {e}")
            return []
    
    async def find_cities_by_type(self, city_type: str) -> List[City]:
        """Find cities by type using Google Places API."""
        if not self.google_api_key:
            return []
        
        try:
            # Map our types to Google Places types and keywords
            type_mapping = {
                'scenic': {'types': ['tourist_attraction'], 'keywords': ['scenic', 'mountains', 'lakes', 'national park']},
                'cultural': {'types': ['museum', 'tourist_attraction'], 'keywords': ['unesco', 'historic', 'cultural', 'heritage']},
                'adventure': {'types': ['tourist_attraction'], 'keywords': ['adventure', 'hiking', 'skiing', 'outdoor']},
                'culinary': {'types': ['restaurant'], 'keywords': ['food market', 'wine region', 'culinary']},
                'romantic': {'types': ['tourist_attraction'], 'keywords': ['romantic', 'couple', 'honeymoon']}
            }
            
            if city_type not in type_mapping:
                return []
            
            mapping = type_mapping[city_type]
            places = []
            
            # Search for places matching the type
            for place_type in mapping['types']:
                for keyword in mapping['keywords']:
                    search_results = await self._text_search(f"{keyword} Europe")
                    places.extend(search_results[:5])  # Limit results per search
            
            # Convert places to cities
            cities = []
            seen_names = set()
            
            for place in places:
                city = await self._create_city_from_place(place)
                if city and city.name not in seen_names:
                    cities.append(city)
                    seen_names.add(city.name)
            
            return cities[:15]  # Return top 15 cities
            
        except Exception as e:
            logger.error(f"Failed to find cities by type {city_type}: {e}")
            return []
    
    async def _search_cities(self, query: str) -> List[Dict]:
        """Search for cities using Google Places text search."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/textsearch/json"
            params = {
                'query': f"{query} city Europe",
                'type': 'locality',
                'key': self.google_api_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', [])
                else:
                    logger.error(f"Places API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"City search error: {e}")
            return []
    
    async def _text_search(self, query: str) -> List[Dict]:
        """General text search using Google Places API."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/textsearch/json"
            params = {
                'query': query,
                'key': self.google_api_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', [])
                else:
                    logger.error(f"Text search API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Text search error: {e}")
            return []
    
    async def _search_places_along_route(self, center_lat: float, center_lng: float,
                                       radius: int, route_start: Coordinates, 
                                       route_end: Coordinates, max_deviation_km: float) -> List[Dict]:
        """Search for interesting places along a route."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Search for different types of attractions
            search_types = [
                'tourist_attraction',
                'locality',
                'natural_feature',
                'point_of_interest'
            ]
            
            all_places = []
            
            for place_type in search_types:
                url = f"{self.base_url}/nearbysearch/json"
                params = {
                    'location': f"{center_lat},{center_lng}",
                    'radius': radius,
                    'type': place_type,
                    'key': self.google_api_key
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        places = data.get('results', [])
                        
                        # Filter places that are reasonably close to the route
                        for place in places:
                            if self._is_place_near_route(place, route_start, route_end, max_deviation_km):
                                all_places.append(place)
            
            return all_places[:20]  # Return top 20 places
            
        except Exception as e:
            logger.error(f"Route places search error: {e}")
            return []
    
    def _is_place_near_route(self, place: Dict, route_start: Coordinates, 
                           route_end: Coordinates, max_deviation_km: float) -> bool:
        """Check if a place is reasonably close to the route."""
        try:
            location = place.get('geometry', {}).get('location', {})
            place_lat = location.get('lat')
            place_lng = location.get('lng')
            
            if not place_lat or not place_lng:
                return False
            
            place_coords = Coordinates(latitude=place_lat, longitude=place_lng)
            
            # Calculate distance from place to route line (simplified)
            start_dist = geodesic(
                (place_lat, place_lng),
                (route_start.latitude, route_start.longitude)
            ).kilometers
            
            end_dist = geodesic(
                (place_lat, place_lng),
                (route_end.latitude, route_end.longitude)
            ).kilometers
            
            route_dist = geodesic(
                (route_start.latitude, route_start.longitude),
                (route_end.latitude, route_end.longitude)
            ).kilometers
            
            # If the place forms a reasonable triangle with start/end, it's likely on route
            deviation = abs(start_dist + end_dist - route_dist)
            return deviation <= max_deviation_km
            
        except Exception:
            return False
    
    async def _create_city_from_place(self, place: Dict) -> Optional[City]:
        """Create a City object from Google Places data."""
        try:
            name = place.get('name', '')
            if not name:
                return None
            
            # Extract coordinates
            location = place.get('geometry', {}).get('location', {})
            lat = location.get('lat')
            lng = location.get('lng')
            
            if not lat or not lng:
                return None
            
            coordinates = Coordinates(latitude=lat, longitude=lng)
            
            # Extract place types and map to our city types
            place_types = place.get('types', [])
            city_types = self._map_place_types_to_city_types(place_types)
            
            # Extract address components for country/region
            formatted_address = place.get('formatted_address', '')
            country = self._extract_country_from_address(formatted_address)
            region = self._extract_region_from_address(formatted_address)
            
            # Get rating if available (for popularity)
            rating = place.get('rating', 0)
            
            return City(
                name=name,
                coordinates=coordinates,
                country=country,
                region=region,
                types=city_types,
                population=None,  # Not available from Places API
                rating=rating
            )
            
        except Exception as e:
            logger.error(f"Error creating city from place: {e}")
            return None
    
    def _map_place_types_to_city_types(self, place_types: List[str]) -> List[str]:
        """Map Google Places types to our city types."""
        type_mapping = {
            'tourist_attraction': ['scenic', 'cultural'],
            'natural_feature': ['scenic', 'adventure'],
            'park': ['scenic', 'adventure'],
            'museum': ['cultural'],
            'church': ['historic', 'cultural'],
            'locality': ['major'],
            'sublocality': ['local'],
            'point_of_interest': ['interesting'],
            'establishment': ['commercial'],
            'food': ['culinary'],
            'lodging': ['accommodation'],
            'amusement_park': ['entertainment', 'adventure'],
            'zoo': ['family', 'entertainment'],
            'shopping_mall': ['shopping'],
            'university': ['cultural', 'educational']
        }
        
        city_types = []
        for place_type in place_types:
            if place_type in type_mapping:
                city_types.extend(type_mapping[place_type])
        
        # Add default types if none found
        if not city_types:
            city_types = ['interesting']
        
        return list(set(city_types))  # Remove duplicates
    
    def _extract_country_from_address(self, address: str) -> Optional[str]:
        """Extract country from formatted address."""
        if not address:
            return None
        
        # Simple extraction - look for known European countries at the end
        european_countries = [
            'France', 'Italy', 'Spain', 'Germany', 'Switzerland', 'Austria',
            'Netherlands', 'Belgium', 'Portugal', 'Greece', 'Croatia',
            'Slovenia', 'Czech Republic', 'Poland', 'Hungary', 'Slovakia'
        ]
        
        for country in european_countries:
            if country in address:
                return country
        
        # Try to get last part of address (usually country)
        parts = address.split(', ')
        if parts:
            return parts[-1]
        
        return None
    
    def _extract_region_from_address(self, address: str) -> Optional[str]:
        """Extract region from formatted address."""
        if not address:
            return None
        
        # Simple extraction - get second to last part (usually region/state)
        parts = address.split(', ')
        if len(parts) >= 2:
            return parts[-2]
        
        return None
    
    def _get_fallback_city(self, name: str) -> Optional[City]:
        """Create a minimal fallback city when API is unavailable."""
        # Only create fallback for well-known cities
        known_cities = {
            'aix-en-provence': {'lat': 43.5297, 'lon': 5.4474, 'country': 'France'},
            'venice': {'lat': 45.4408, 'lon': 12.3155, 'country': 'Italy'},
            'nice': {'lat': 43.7102, 'lon': 7.2620, 'country': 'France'},
            'milan': {'lat': 45.4642, 'lon': 9.1900, 'country': 'Italy'},
            'geneva': {'lat': 46.2044, 'lon': 6.1432, 'country': 'Switzerland'},
            'lyon': {'lat': 45.7640, 'lon': 4.8357, 'country': 'France'},
            'turin': {'lat': 45.0703, 'lon': 7.6869, 'country': 'Italy'},
            'monaco': {'lat': 43.7384, 'lon': 7.4246, 'country': 'Monaco'}
        }
        
        name_key = name.lower().strip().replace(' ', '-')
        if name_key in known_cities:
            data = known_cities[name_key]
            return City(
                name=name,
                coordinates=Coordinates(latitude=data['lat'], longitude=data['lon']),
                country=data['country'],
                types=['fallback']
            )
        
        return None
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
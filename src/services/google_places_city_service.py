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
            logger.warning("No Google API key - using fallback route cities")
            return self._get_fallback_route_cities(start, end, max_deviation_km)
        
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
        # Comprehensive fallback for European cities
        known_cities = {
            'aix-en-provence': {'lat': 43.5297, 'lon': 5.4474, 'country': 'France', 'types': ['cultural', 'culinary']},
            'venice': {'lat': 45.4408, 'lon': 12.3155, 'country': 'Italy', 'types': ['romantic', 'historic', 'unesco']},
            'nice': {'lat': 43.7102, 'lon': 7.2620, 'country': 'France', 'types': ['coastal', 'scenic']},
            'cannes': {'lat': 43.5528, 'lon': 7.0174, 'country': 'France', 'types': ['luxury', 'coastal']},
            'monaco': {'lat': 43.7384, 'lon': 7.4246, 'country': 'Monaco', 'types': ['luxury', 'coastal']},
            'milan': {'lat': 45.4642, 'lon': 9.1900, 'country': 'Italy', 'types': ['fashion', 'business', 'cultural']},
            'turin': {'lat': 45.0703, 'lon': 7.6869, 'country': 'Italy', 'types': ['cultural', 'historic']},
            'geneva': {'lat': 46.2044, 'lon': 6.1432, 'country': 'Switzerland', 'types': ['scenic', 'expensive']},
            'lyon': {'lat': 45.7640, 'lon': 4.8357, 'country': 'France', 'types': ['culinary', 'cultural']},
            'annecy': {'lat': 45.8992, 'lon': 6.1294, 'country': 'France', 'types': ['scenic', 'alpine', 'romantic']},
            'chamonix': {'lat': 45.9237, 'lon': 6.8694, 'country': 'France', 'types': ['alpine', 'adventure', 'skiing']},
            'grenoble': {'lat': 45.1885, 'lon': 5.7245, 'country': 'France', 'types': ['alpine', 'adventure']},
            'avignon': {'lat': 43.9493, 'lon': 4.8055, 'country': 'France', 'types': ['historic', 'unesco']},
            'marseille': {'lat': 43.2965, 'lon': 5.3698, 'country': 'France', 'types': ['coastal', 'culinary']},
            'florence': {'lat': 43.7696, 'lon': 11.2558, 'country': 'Italy', 'types': ['cultural', 'renaissance', 'artistic']},
            'pisa': {'lat': 43.7228, 'lon': 10.4017, 'country': 'Italy', 'types': ['historic', 'iconic']},
            'genoa': {'lat': 44.4056, 'lon': 8.9463, 'country': 'Italy', 'types': ['coastal', 'historic']},
            'bologna': {'lat': 44.4949, 'lon': 11.3426, 'country': 'Italy', 'types': ['culinary', 'cultural']},
            'verona': {'lat': 45.4384, 'lon': 10.9916, 'country': 'Italy', 'types': ['romantic', 'historic']},
            'vicenza': {'lat': 45.5455, 'lon': 11.5353, 'country': 'Italy', 'types': ['historic', 'architectural']},
            'padua': {'lat': 45.4064, 'lon': 11.8768, 'country': 'Italy', 'types': ['historic', 'university']},
            'como': {'lat': 45.8081, 'lon': 9.0852, 'country': 'Italy', 'types': ['scenic', 'lakes', 'romantic']},
            'bergamo': {'lat': 45.6983, 'lon': 9.6773, 'country': 'Italy', 'types': ['historic', 'medieval']},
            'brescia': {'lat': 45.5416, 'lon': 10.2118, 'country': 'Italy', 'types': ['historic', 'cultural']},
            'parma': {'lat': 44.8015, 'lon': 10.3279, 'country': 'Italy', 'types': ['culinary', 'cultural']},
            'modena': {'lat': 44.6471, 'lon': 10.9252, 'country': 'Italy', 'types': ['culinary', 'automotive']},
            'innsbruck': {'lat': 47.2692, 'lon': 11.4041, 'country': 'Austria', 'types': ['alpine', 'adventure']},
            'salzburg': {'lat': 47.8095, 'lon': 13.0550, 'country': 'Austria', 'types': ['cultural', 'music', 'historic']}
        }
        
        name_key = name.lower().strip().replace(' ', '-')
        if name_key in known_cities:
            data = known_cities[name_key]
            return City(
                name=name,
                coordinates=Coordinates(latitude=data['lat'], longitude=data['lon']),
                country=data['country'],
                types=data.get('types', ['fallback'])
            )
        
        return None
    
    def _get_fallback_route_cities(self, start: Coordinates, end: Coordinates, 
                                 max_deviation_km: float) -> List[City]:
        """Get fallback cities for route when API is unavailable."""
        # Use all known cities and filter by distance to route
        all_cities = []
        known_cities = {
            'annecy': {'lat': 45.8992, 'lon': 6.1294, 'country': 'France', 'types': ['scenic', 'alpine', 'romantic']},
            'chamonix': {'lat': 45.9237, 'lon': 6.8694, 'country': 'France', 'types': ['alpine', 'adventure', 'skiing']},
            'grenoble': {'lat': 45.1885, 'lon': 5.7245, 'country': 'France', 'types': ['alpine', 'adventure']},
            'avignon': {'lat': 43.9493, 'lon': 4.8055, 'country': 'France', 'types': ['historic', 'unesco']},
            'marseille': {'lat': 43.2965, 'lon': 5.3698, 'country': 'France', 'types': ['coastal', 'culinary']},
            'nice': {'lat': 43.7102, 'lon': 7.2620, 'country': 'France', 'types': ['coastal', 'scenic']},
            'cannes': {'lat': 43.5528, 'lon': 7.0174, 'country': 'France', 'types': ['luxury', 'coastal']},
            'monaco': {'lat': 43.7384, 'lon': 7.4246, 'country': 'Monaco', 'types': ['luxury', 'coastal']},
            'lyon': {'lat': 45.7640, 'lon': 4.8357, 'country': 'France', 'types': ['culinary', 'cultural']},
            'geneva': {'lat': 46.2044, 'lon': 6.1432, 'country': 'Switzerland', 'types': ['scenic', 'expensive']},
            'turin': {'lat': 45.0703, 'lon': 7.6869, 'country': 'Italy', 'types': ['cultural', 'historic']},
            'milan': {'lat': 45.4642, 'lon': 9.1900, 'country': 'Italy', 'types': ['fashion', 'business', 'cultural']},
            'como': {'lat': 45.8081, 'lon': 9.0852, 'country': 'Italy', 'types': ['scenic', 'lakes', 'romantic']},
            'bergamo': {'lat': 45.6983, 'lon': 9.6773, 'country': 'Italy', 'types': ['historic', 'medieval']},
            'brescia': {'lat': 45.5416, 'lon': 10.2118, 'country': 'Italy', 'types': ['historic', 'cultural']},
            'verona': {'lat': 45.4384, 'lon': 10.9916, 'country': 'Italy', 'types': ['romantic', 'historic']},
            'vicenza': {'lat': 45.5455, 'lon': 11.5353, 'country': 'Italy', 'types': ['historic', 'architectural']},
            'padua': {'lat': 45.4064, 'lon': 11.8768, 'country': 'Italy', 'types': ['historic', 'university']},
            'florence': {'lat': 43.7696, 'lon': 11.2558, 'country': 'Italy', 'types': ['cultural', 'renaissance', 'artistic']},
            'pisa': {'lat': 43.7228, 'lon': 10.4017, 'country': 'Italy', 'types': ['historic', 'iconic']},
            'genoa': {'lat': 44.4056, 'lon': 8.9463, 'country': 'Italy', 'types': ['coastal', 'historic']},
            'bologna': {'lat': 44.4949, 'lon': 11.3426, 'country': 'Italy', 'types': ['culinary', 'cultural']},
            'parma': {'lat': 44.8015, 'lon': 10.3279, 'country': 'Italy', 'types': ['culinary', 'cultural']},
            'modena': {'lat': 44.6471, 'lon': 10.9252, 'country': 'Italy', 'types': ['culinary', 'automotive']},
            'innsbruck': {'lat': 47.2692, 'lon': 11.4041, 'country': 'Austria', 'types': ['alpine', 'adventure']},
            'salzburg': {'lat': 47.8095, 'lon': 13.0550, 'country': 'Austria', 'types': ['cultural', 'music', 'historic']}
        }
        
        # Create city objects and filter by distance to route
        candidates = []
        for name, data in known_cities.items():
            city_coords = Coordinates(latitude=data['lat'], longitude=data['lon'])
            if self._is_city_near_route(city_coords, start, end, max_deviation_km):
                city = City(
                    name=name.replace('-', ' ').title(),
                    coordinates=city_coords,
                    country=data['country'],
                    types=data['types']
                )
                candidates.append(city)
        
        # Sort by distance from start point
        from geopy.distance import geodesic
        candidates.sort(key=lambda c: geodesic(
            (start.latitude, start.longitude),
            (c.coordinates.latitude, c.coordinates.longitude)
        ).kilometers)
        
        return candidates[:8]  # Return up to 8 candidates
    
    def _is_city_near_route(self, city_coords: Coordinates, start: Coordinates, 
                          end: Coordinates, max_deviation_km: float) -> bool:
        """Check if a city is near the route between start and end."""
        from geopy.distance import geodesic
        
        # Calculate distances
        start_dist = geodesic(
            (city_coords.latitude, city_coords.longitude),
            (start.latitude, start.longitude)
        ).kilometers
        
        end_dist = geodesic(
            (city_coords.latitude, city_coords.longitude),
            (end.latitude, end.longitude)
        ).kilometers
        
        route_dist = geodesic(
            (start.latitude, start.longitude),
            (end.latitude, end.longitude)
        ).kilometers
        
        # If the city creates a reasonable detour, it's on the route
        total_detour = start_dist + end_dist - route_dist
        return total_detour <= max_deviation_km
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
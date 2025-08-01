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
        # Use the new Places API endpoint
        self.base_url = "https://places.googleapis.com/v1/places"
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
                                   max_deviation_km: float = 100, route_type: str = None) -> List[City]:
        """Find interesting cities near the route using Google Places API."""
        if not self.google_api_key:
            logger.warning("No Google API key - using fallback route cities")
            return self._get_fallback_route_cities(start, end, max_deviation_km, route_type)
        
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
            
            # If Google API returned cities, use them
            if len(cities) > 0:
                return cities[:10]  # Return top 10 cities
            
            # If Google API returned no cities, fall back to our comprehensive system
            logger.warning("Google Places API returned no cities - using fallback system")
            return self._get_fallback_route_cities(start, end, max_deviation_km, route_type)
            
        except Exception as e:
            logger.error(f"Failed to find cities near route: {e}")
            # Always fall back to our comprehensive system instead of returning empty
            logger.warning("Google Places API failed - using fallback system")
            return self._get_fallback_route_cities(start, end, max_deviation_km, route_type)
    
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
        """Search for cities using Google Places API (New)."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Use the new Places API searchText endpoint
            url = f"{self.base_url}:searchText"
            
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': self.google_api_key,
                'X-Goog-FieldMask': 'places.displayName,places.location,places.types,places.formattedAddress,places.rating'
            }
            
            payload = {
                'textQuery': f"{query} city Europe",
                'includedType': 'locality',
                'maxResultCount': 10
            }
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('places', [])
                else:
                    response_text = await response.text()
                    logger.error(f"Places API error: {response.status} - {response_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"City search error: {e}")
            return []
    
    async def _text_search(self, query: str) -> List[Dict]:
        """General text search using Google Places API (New)."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}:searchText"
            
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': self.google_api_key,
                'X-Goog-FieldMask': 'places.displayName,places.location,places.types,places.formattedAddress,places.rating'
            }
            
            payload = {
                'textQuery': query,
                'maxResultCount': 20
            }
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('places', [])
                else:
                    response_text = await response.text()
                    logger.error(f"Text search API error: {response.status} - {response_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Text search error: {e}")
            return []
    
    async def _search_places_along_route(self, center_lat: float, center_lng: float,
                                       radius: int, route_start: Coordinates, 
                                       route_end: Coordinates, max_deviation_km: float) -> List[Dict]:
        """Search for interesting places along a route using Places API (New)."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Use searchNearby endpoint for the new API
            url = f"{self.base_url}:searchNearby"
            
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': self.google_api_key,
                'X-Goog-FieldMask': 'places.displayName,places.location,places.types,places.formattedAddress,places.rating'
            }
            
            # Search for different types of places along the route
            search_types = [
                'tourist_attraction',
                'locality',
                'natural_feature',
                'point_of_interest'
            ]
            
            all_places = []
            
            for place_type in search_types:
                payload = {
                    'includedTypes': [place_type],
                    'maxResultCount': 20,
                    'locationRestriction': {
                        'circle': {
                            'center': {
                                'latitude': center_lat,
                                'longitude': center_lng
                            },
                            'radius': radius
                        }
                    }
                }
                
                async with self.session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        places = data.get('places', [])
                        
                        # Filter places that are reasonably close to the route
                        for place in places:
                            if self._is_place_near_route_new_api(place, route_start, route_end, max_deviation_km):
                                all_places.append(place)
                    else:
                        response_text = await response.text()
                        logger.warning(f"Route search failed for {place_type}: {response.status} - {response_text}")
            
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
    
    def _is_place_near_route_new_api(self, place: Dict, route_start: Coordinates, 
                                   route_end: Coordinates, max_deviation_km: float) -> bool:
        """Check if a place is reasonably close to the route (for new API format)."""
        try:
            location = place.get('location', {})
            place_lat = location.get('latitude')
            place_lng = location.get('longitude')
            
            if not place_lat or not place_lng:
                return False
            
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
        """Create a City object from Google Places data (New API format)."""
        try:
            # New API uses displayName instead of name
            display_name = place.get('displayName', {})
            name = display_name.get('text', '') if isinstance(display_name, dict) else str(place.get('displayName', ''))
            
            if not name:
                return None
            
            # Extract coordinates (new API format)
            location = place.get('location', {})
            lat = location.get('latitude')
            lng = location.get('longitude')
            
            if not lat or not lng:
                return None
            
            coordinates = Coordinates(latitude=lat, longitude=lng)
            
            # Extract place types and map to our city types
            place_types = place.get('types', [])
            city_types = self._map_place_types_to_city_types(place_types)
            
            # Extract address components for country/region
            formatted_address = place.get('formattedAddress', '')
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
            'paris': {'lat': 48.8566, 'lon': 2.3522, 'country': 'France', 'types': ['cultural', 'romantic', 'historic', 'artistic']},
            'rome': {'lat': 41.9028, 'lon': 12.4964, 'country': 'Italy', 'types': ['cultural', 'historic', 'unesco', 'roman']},
            'barcelona': {'lat': 41.3851, 'lon': 2.1734, 'country': 'Spain', 'types': ['cultural', 'artistic', 'coastal', 'gaudi']},
            'madrid': {'lat': 40.4168, 'lon': -3.7038, 'country': 'Spain', 'types': ['cultural', 'artistic', 'historic', 'museums']},
            'london': {'lat': 51.5074, 'lon': -0.1278, 'country': 'United Kingdom', 'types': ['cultural', 'historic', 'royal', 'museums']},
            'amsterdam': {'lat': 52.3676, 'lon': 4.9041, 'country': 'Netherlands', 'types': ['cultural', 'canals', 'historic', 'artistic']},
            'brussels': {'lat': 50.8476, 'lon': 4.3572, 'country': 'Belgium', 'types': ['cultural', 'historic', 'culinary', 'european']},
            'berlin': {'lat': 52.5200, 'lon': 13.4050, 'country': 'Germany', 'types': ['cultural', 'historic', 'artistic', 'modern']},
            'munich': {'lat': 48.1351, 'lon': 11.5820, 'country': 'Germany', 'types': ['cultural', 'beer', 'bavarian', 'alpine']},
            'vienna': {'lat': 48.2082, 'lon': 16.3738, 'country': 'Austria', 'types': ['cultural', 'historic', 'imperial', 'music']},
            'zurich': {'lat': 47.3769, 'lon': 8.5417, 'country': 'Switzerland', 'types': ['scenic', 'lakes', 'alpine', 'luxury']},
            'florence': {'lat': 43.7696, 'lon': 11.2558, 'country': 'Italy', 'types': ['cultural', 'renaissance', 'artistic', 'unesco']},
            'naples': {'lat': 40.8518, 'lon': 14.2681, 'country': 'Italy', 'types': ['cultural', 'historic', 'culinary', 'coastal']},
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
                                 max_deviation_km: float, route_type: str = None) -> List[City]:
        """Get fallback cities for route when API is unavailable, filtered by route type."""
        # Comprehensive city database with detailed type information
        known_cities = {
            'annecy': {'lat': 45.8992, 'lon': 6.1294, 'country': 'France', 'types': ['scenic', 'alpine', 'romantic', 'lakes']},
            'chamonix': {'lat': 45.9237, 'lon': 6.8694, 'country': 'France', 'types': ['alpine', 'adventure', 'skiing', 'nature']},
            'grenoble': {'lat': 45.1885, 'lon': 5.7245, 'country': 'France', 'types': ['alpine', 'adventure', 'outdoor']},
            'avignon': {'lat': 43.9493, 'lon': 4.8055, 'country': 'France', 'types': ['historic', 'unesco', 'cultural', 'medieval']},
            'marseille': {'lat': 43.2965, 'lon': 5.3698, 'country': 'France', 'types': ['coastal', 'culinary', 'mediterranean']},
            'nice': {'lat': 43.7102, 'lon': 7.2620, 'country': 'France', 'types': ['coastal', 'scenic', 'luxury', 'resort']},
            'cannes': {'lat': 43.5528, 'lon': 7.0174, 'country': 'France', 'types': ['luxury', 'coastal', 'glamour', 'festivals']},
            'monaco': {'lat': 43.7384, 'lon': 7.4246, 'country': 'Monaco', 'types': ['luxury', 'coastal', 'casinos', 'glamour']},
            'lyon': {'lat': 45.7640, 'lon': 4.8357, 'country': 'France', 'types': ['culinary', 'cultural', 'gastronomy', 'unesco']},
            'geneva': {'lat': 46.2044, 'lon': 6.1432, 'country': 'Switzerland', 'types': ['scenic', 'lakes', 'diplomatic', 'luxury']},
            'turin': {'lat': 45.0703, 'lon': 7.6869, 'country': 'Italy', 'types': ['cultural', 'historic', 'royal', 'chocolate']},
            'milan': {'lat': 45.4642, 'lon': 9.1900, 'country': 'Italy', 'types': ['fashion', 'business', 'cultural', 'shopping']},
            'como': {'lat': 45.8081, 'lon': 9.0852, 'country': 'Italy', 'types': ['scenic', 'lakes', 'romantic', 'luxury']},
            'bergamo': {'lat': 45.6983, 'lon': 9.6773, 'country': 'Italy', 'types': ['historic', 'medieval', 'cultural']},
            'brescia': {'lat': 45.5416, 'lon': 10.2118, 'country': 'Italy', 'types': ['historic', 'cultural', 'roman']},
            'verona': {'lat': 45.4384, 'lon': 10.9916, 'country': 'Italy', 'types': ['romantic', 'historic', 'shakespeare', 'unesco']},
            'vicenza': {'lat': 45.5455, 'lon': 11.5353, 'country': 'Italy', 'types': ['historic', 'architectural', 'palladio', 'unesco']},
            'padua': {'lat': 45.4064, 'lon': 11.8768, 'country': 'Italy', 'types': ['historic', 'university', 'cultural', 'pilgrimage']},
            'florence': {'lat': 43.7696, 'lon': 11.2558, 'country': 'Italy', 'types': ['cultural', 'renaissance', 'artistic', 'unesco']},
            'pisa': {'lat': 43.7228, 'lon': 10.4017, 'country': 'Italy', 'types': ['historic', 'iconic', 'university', 'architectural']},
            'genoa': {'lat': 44.4056, 'lon': 8.9463, 'country': 'Italy', 'types': ['coastal', 'historic', 'maritime', 'cultural']},
            'bologna': {'lat': 44.4949, 'lon': 11.3426, 'country': 'Italy', 'types': ['culinary', 'cultural', 'university', 'gastronomy']},
            'parma': {'lat': 44.8015, 'lon': 10.3279, 'country': 'Italy', 'types': ['culinary', 'cultural', 'ham', 'cheese']},
            'modena': {'lat': 44.6471, 'lon': 10.9252, 'country': 'Italy', 'types': ['culinary', 'automotive', 'balsamic', 'ferrari']},
            'innsbruck': {'lat': 47.2692, 'lon': 11.4041, 'country': 'Austria', 'types': ['alpine', 'adventure', 'skiing', 'mountains']},
            'salzburg': {'lat': 47.8095, 'lon': 13.0550, 'country': 'Austria', 'types': ['cultural', 'music', 'historic', 'mozart']},
            'siena': {'lat': 43.3188, 'lon': 11.3307, 'country': 'Italy', 'types': ['historic', 'medieval', 'unesco', 'cultural']},
            'rimini': {'lat': 44.0678, 'lon': 12.5695, 'country': 'Italy', 'types': ['coastal', 'resort', 'beach', 'nightlife']},
            'ravenna': {'lat': 44.4184, 'lon': 12.2035, 'country': 'Italy', 'types': ['historic', 'byzantine', 'unesco', 'mosaics']},
            # Hidden gems - lesser-known authentic destinations
            'san_gimignano': {'lat': 43.4674, 'lon': 11.0431, 'country': 'Italy', 'types': ['hidden', 'medieval', 'village', 'towers', 'authentic']},
            'civita_di_bagnoregio': {'lat': 42.6274, 'lon': 12.0992, 'country': 'Italy', 'types': ['hidden', 'village', 'authentic', 'cliff', 'unique']},
            'colmar': {'lat': 48.0794, 'lon': 7.3581, 'country': 'France', 'types': ['hidden', 'village', 'authentic', 'fairytale', 'canals']},
            'riquewihr': {'lat': 48.1667, 'lon': 7.2989, 'country': 'France', 'types': ['hidden', 'village', 'wine', 'medieval', 'authentic']},
            'rothenburg': {'lat': 49.3779, 'lon': 10.1803, 'country': 'Germany', 'types': ['hidden', 'medieval', 'village', 'walls', 'authentic']},
            'cesky_krumlov': {'lat': 49.3174, 'lon': 14.3175, 'country': 'Czech Republic', 'types': ['hidden', 'medieval', 'unesco', 'village', 'authentic']},
            'bled': {'lat': 46.3683, 'lon': 14.1147, 'country': 'Slovenia', 'types': ['hidden', 'lakes', 'romantic', 'village', 'authentic']},
            'hallstatt': {'lat': 47.5622, 'lon': 13.6493, 'country': 'Austria', 'types': ['hidden', 'lakes', 'village', 'authentic', 'fairytale']},
            'giethoorn': {'lat': 52.7386, 'lon': 6.0809, 'country': 'Netherlands', 'types': ['hidden', 'village', 'canals', 'authentic', 'unique']},
            'sintra': {'lat': 38.7979, 'lon': -9.3902, 'country': 'Portugal', 'types': ['hidden', 'romantic', 'palaces', 'village', 'authentic']}
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
        
        # Filter by route type if specified
        if route_type:
            type_filters = {
                'scenic': ['scenic', 'alpine', 'lakes', 'romantic', 'resort', 'luxury'],
                'cultural': ['cultural', 'historic', 'unesco', 'artistic', 'renaissance', 'medieval', 'roman'],
                'adventure': ['adventure', 'alpine', 'skiing', 'nature', 'outdoor', 'mountains'],
                'culinary': ['culinary', 'gastronomy', 'wine', 'food', 'ham', 'cheese', 'balsamic'],
                'romantic': ['romantic', 'scenic', 'lakes', 'luxury', 'shakespeare', 'glamour'],
                'hidden_gems': ['hidden', 'village', 'authentic', 'medieval', 'unique', 'fairytale']
            }
            
            if route_type in type_filters:
                target_types = type_filters[route_type]
                # Prioritize cities that match the route type
                typed_candidates = [c for c in candidates if any(t in c.types for t in target_types)]
                if len(typed_candidates) >= 2:
                    candidates = typed_candidates
        
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
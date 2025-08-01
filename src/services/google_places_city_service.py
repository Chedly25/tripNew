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
            'sintra': {'lat': 38.7979, 'lon': -9.3902, 'country': 'Portugal', 'types': ['hidden', 'romantic', 'palaces', 'village', 'authentic']},
            
            # Additional French cities (Provence-Alpes-Côte d'Azur region)
            'toulon': {'lat': 43.1242, 'lon': 5.9280, 'country': 'France', 'types': ['coastal', 'naval', 'historic', 'mediterranean']},
            'antibes': {'lat': 43.5808, 'lon': 7.1239, 'country': 'France', 'types': ['coastal', 'resort', 'luxury', 'yachting']},
            'grasse': {'lat': 43.6591, 'lon': 6.9226, 'country': 'France', 'types': ['perfume', 'cultural', 'hilltop', 'artisan']},
            'saint_tropez': {'lat': 43.2677, 'lon': 6.6407, 'country': 'France', 'types': ['luxury', 'coastal', 'glamour', 'beach']},
            'menton': {'lat': 43.7765, 'lon': 7.5048, 'country': 'France', 'types': ['coastal', 'gardens', 'citrus', 'italian-influence']},
            'saint_paul_de_vence': {'lat': 43.6968, 'lon': 7.1227, 'country': 'France', 'types': ['artistic', 'medieval', 'hilltop', 'galleries']},
            'vence': {'lat': 43.7228, 'lon': 7.1139, 'country': 'France', 'types': ['artistic', 'chapel', 'matisse', 'medieval']},
            'eze': {'lat': 43.7286, 'lon': 7.3615, 'country': 'France', 'types': ['medieval', 'hilltop', 'gardens', 'panoramic']},
            'villefranche_sur_mer': {'lat': 43.7049, 'lon': 7.3089, 'country': 'France', 'types': ['coastal', 'colorful', 'harbor', 'authentic']},
            'cassis': {'lat': 43.2151, 'lon': 5.5378, 'country': 'France', 'types': ['coastal', 'calanques', 'wine', 'fishing']},
            'bandol': {'lat': 43.1366, 'lon': 5.7523, 'country': 'France', 'types': ['coastal', 'wine', 'resort', 'beaches']},
            'saint_remy_de_provence': {'lat': 43.7887, 'lon': 4.8312, 'country': 'France', 'types': ['van_gogh', 'roman', 'provencal', 'artistic']},
            'les_baux_de_provence': {'lat': 43.7444, 'lon': 4.7947, 'country': 'France', 'types': ['medieval', 'fortress', 'dramatic', 'artistic']},
            'gordes': {'lat': 43.9111, 'lon': 5.2003, 'country': 'France', 'types': ['hilltop', 'stone', 'lavender', 'scenic']},
            'roussillon': {'lat': 43.9022, 'lon': 5.2934, 'country': 'France', 'types': ['ochre', 'colorful', 'artistic', 'unique']},
            'lourmarin': {'lat': 43.7639, 'lon': 5.3628, 'country': 'France', 'types': ['literary', 'castle', 'markets', 'authentic']},
            'isle_sur_la_sorgue': {'lat': 43.9208, 'lon': 5.0515, 'country': 'France', 'types': ['antiques', 'canals', 'markets', 'watermill']},
            'fontaine_de_vaucluse': {'lat': 43.9214, 'lon': 5.1275, 'country': 'France', 'types': ['spring', 'natural', 'petrarch', 'dramatic']},
            'vaison_la_romaine': {'lat': 44.2410, 'lon': 5.0753, 'country': 'France', 'types': ['roman', 'archaeological', 'medieval', 'markets']},
            'carpentras': {'lat': 44.0550, 'lon': 5.0479, 'country': 'France', 'types': ['historic', 'truffle', 'jewish', 'markets']},
            'orange': {'lat': 44.1361, 'lon': 4.8080, 'country': 'France', 'types': ['roman', 'theater', 'unesco', 'historic']},
            'arles': {'lat': 43.6768, 'lon': 4.6304, 'country': 'France', 'types': ['roman', 'van_gogh', 'unesco', 'photography']},
            'nimes': {'lat': 43.8367, 'lon': 4.3601, 'country': 'France', 'types': ['roman', 'arena', 'historic', 'denim']},
            'uzès': {'lat': 44.0122, 'lon': 4.4195, 'country': 'France', 'types': ['medieval', 'duchy', 'markets', 'authentic']},
            'pont_du_gard': {'lat': 43.9475, 'lon': 4.5350, 'country': 'France', 'types': ['roman', 'aqueduct', 'unesco', 'engineering']},
            'aigues_mortes': {'lat': 43.5667, 'lon': 4.1917, 'country': 'France', 'types': ['medieval', 'walled', 'salt', 'crusades']},
            'saintes_maries_de_la_mer': {'lat': 43.4518, 'lon': 4.4282, 'country': 'France', 'types': ['pilgrimage', 'gypsy', 'camargue', 'coastal']},
            'gap': {'lat': 44.5590, 'lon': 6.0793, 'country': 'France', 'types': ['alpine', 'gateway', 'hiking', 'sports']},
            'briançon': {'lat': 44.8965, 'lon': 6.6358, 'country': 'France', 'types': ['fortified', 'alpine', 'vauban', 'skiing']},
            'embrun': {'lat': 44.5635, 'lon': 6.4961, 'country': 'France', 'types': ['alpine', 'lake', 'historic', 'water-sports']},
            'sisteron': {'lat': 44.1950, 'lon': 5.9438, 'country': 'France', 'types': ['citadel', 'gateway', 'dramatic', 'lavender']},
            'manosque': {'lat': 43.8317, 'lon': 5.7833, 'country': 'France', 'types': ['provencal', 'giono', 'olive', 'authentic']},
            'forcalquier': {'lat': 43.9597, 'lon': 5.7814, 'country': 'France', 'types': ['hilltop', 'observatory', 'lavender', 'markets']},
            'digne_les_bains': {'lat': 44.0919, 'lon': 6.2369, 'country': 'France', 'types': ['thermal', 'lavender', 'geological', 'alpine']},
            'barcelonnette': {'lat': 44.3867, 'lon': 6.6517, 'country': 'France', 'types': ['alpine', 'mexican', 'skiing', 'unique']},
            'moustiers_sainte_marie': {'lat': 43.8456, 'lon': 6.2214, 'country': 'France', 'types': ['pottery', 'gorge', 'star', 'picturesque']},
            'castellane': {'lat': 43.8472, 'lon': 6.5125, 'country': 'France', 'types': ['gateway', 'verdon', 'adventure', 'medieval']},
            'thorenc': {'lat': 43.7817, 'lon': 6.8075, 'country': 'France', 'types': ['mountain', 'quiet', 'nature', 'authentic']},
            'seillans': {'lat': 43.6319, 'lon': 6.6408, 'country': 'France', 'types': ['perched', 'artistic', 'peaceful', 'medieval']},
            'fayence': {'lat': 43.6244, 'lon': 6.6942, 'country': 'France', 'types': ['gliding', 'pottery', 'hilltop', 'markets']},
            'draguignan': {'lat': 43.5369, 'lon': 6.4647, 'country': 'France', 'types': ['provencal', 'military', 'markets', 'authentic']},
            'lorgues': {'lat': 43.4931, 'lon': 6.3622, 'country': 'France', 'types': ['wine', 'olive', 'markets', 'provencal']},
            'cotignac': {'lat': 43.5286, 'lon': 6.1494, 'country': 'France', 'types': ['cliff', 'caves', 'artistic', 'authentic']},
            'tourtour': {'lat': 43.5917, 'lon': 6.3028, 'country': 'France', 'types': ['village_in_sky', 'panoramic', 'artistic', 'peaceful']},
            'aups': {'lat': 43.6274, 'lon': 6.2235, 'country': 'France', 'types': ['truffle', 'markets', 'authentic', 'provencal']},
            'salernes': {'lat': 43.5633, 'lon': 6.2339, 'country': 'France', 'types': ['tiles', 'pottery', 'hexagonal', 'crafts']},
            'villecroze': {'lat': 43.5822, 'lon': 6.2756, 'country': 'France', 'types': ['caves', 'park', 'medieval', 'waterfall']},
            'brignoles': {'lat': 43.4060, 'lon': 6.0618, 'country': 'France', 'types': ['bauxite', 'medieval', 'wine', 'authentic']},
            'saint_maximin': {'lat': 43.4525, 'lon': 5.8619, 'country': 'France', 'types': ['basilica', 'gothic', 'mary_magdalene', 'pilgrimage']},
            'tourves': {'lat': 43.4078, 'lon': 5.9236, 'country': 'France', 'types': ['wine', 'countryside', 'quiet', 'authentic']},
            'barjols': {'lat': 43.5558, 'lon': 6.0086, 'country': 'France', 'types': ['fountains', 'leather', 'waterfalls', 'authentic']},
            'saint_martin_de_bromes': {'lat': 43.7756, 'lon': 5.9444, 'country': 'France', 'types': ['templar', 'quiet', 'rural', 'historic']},
            'riez': {'lat': 43.8183, 'lon': 6.0919, 'country': 'France', 'types': ['roman', 'lavender', 'baptistery', 'authentic']},
            'valensole': {'lat': 43.8378, 'lon': 5.9839, 'country': 'France', 'types': ['lavender', 'plateau', 'almond', 'photogenic']},
            'gréoux_les_bains': {'lat': 43.7578, 'lon': 5.8825, 'country': 'France', 'types': ['thermal', 'spa', 'verdon', 'relaxation']},
            'vinon_sur_verdon': {'lat': 43.7222, 'lon': 5.8089, 'country': 'France', 'types': ['aviation', 'riverside', 'gliding', 'peaceful']},
            'quinson': {'lat': 43.6967, 'lon': 6.0394, 'country': 'France', 'types': ['prehistory', 'museum', 'gorges', 'archaeology']},
            'montmeyan': {'lat': 43.6603, 'lon': 6.0906, 'country': 'France', 'types': ['castle', 'village', 'views', 'quiet']},
            'regusse': {'lat': 43.6519, 'lon': 6.1333, 'country': 'France', 'types': ['windmills', 'hilltop', 'views', 'authentic']},
            'moissac_bellevue': {'lat': 43.6036, 'lon': 6.1669, 'country': 'France', 'types': ['panoramic', 'quiet', 'rural', 'authentic']},
            'bauduen': {'lat': 43.7342, 'lon': 6.1833, 'country': 'France', 'types': ['lakeside', 'beach', 'water-sports', 'peaceful']},
            'les_salles_sur_verdon': {'lat': 43.7750, 'lon': 6.2042, 'country': 'France', 'types': ['reconstructed', 'lake', 'modern', 'water-sports']},
            'la_palud_sur_verdon': {'lat': 43.7811, 'lon': 6.3422, 'country': 'France', 'types': ['climbing', 'hiking', 'verdon', 'adventure']},
            'rougon': {'lat': 43.8025, 'lon': 6.4011, 'country': 'France', 'types': ['eagles', 'viewpoint', 'hiking', 'wildlife']},
            'trigance': {'lat': 43.7606, 'lon': 6.4464, 'country': 'France', 'types': ['castle', 'medieval', 'dramatic', 'gateway']},
            'comps_sur_artuby': {'lat': 43.7100, 'lon': 6.5111, 'country': 'France', 'types': ['chapel', 'truffle', 'quiet', 'authentic']},
            'bargeme': {'lat': 43.7286, 'lon': 6.5683, 'country': 'France', 'types': ['highest_village', 'castle', 'views', 'remote']},
            'la_bastide': {'lat': 43.7456, 'lon': 6.6236, 'country': 'France', 'types': ['fortified', 'quiet', 'hiking', 'authentic']},
            'le_bourguet': {'lat': 43.7619, 'lon': 6.6511, 'country': 'France', 'types': ['mountain', 'remote', 'hiking', 'peaceful']},
            'brenon': {'lat': 43.7661, 'lon': 6.5461, 'country': 'France', 'types': ['tiny', 'authentic', 'quiet', 'rural']},
            'chateauvieux': {'lat': 43.7772, 'lon': 6.5789, 'country': 'France', 'types': ['ruins', 'history', 'views', 'hiking']},
            'soleilhas': {'lat': 43.8500, 'lon': 6.6458, 'country': 'France', 'types': ['mountain', 'skiing', 'quiet', 'nature']},
            'demandolx': {'lat': 43.8256, 'lon': 6.6111, 'country': 'France', 'types': ['perched', 'quiet', 'rural', 'authentic']},
            'peyroules': {'lat': 43.8142, 'lon': 6.6622, 'country': 'France', 'types': ['mountain', 'chapel', 'hiking', 'remote']},
            'la_garde': {'lat': 43.8333, 'lon': 6.5667, 'country': 'France', 'types': ['railway', 'viaduct', 'hiking', 'history']},
            'le_mas': {'lat': 43.8417, 'lon': 6.7853, 'country': 'France', 'types': ['hamlet', 'stone', 'quiet', 'authentic']},
            'valderoure': {'lat': 43.7950, 'lon': 6.6972, 'country': 'France', 'types': ['mountain', 'skiing', 'hiking', 'nature']},
            'andon': {'lat': 43.7875, 'lon': 6.7444, 'country': 'France', 'types': ['plateau', 'nature', 'cross-country', 'peaceful']},
            'caille': {'lat': 43.7792, 'lon': 6.7428, 'country': 'France', 'types': ['plateau', 'observatory', 'nature', 'stargazing']},
            'escragnolles': {'lat': 43.7303, 'lon': 6.7744, 'country': 'France', 'types': ['napoleon', 'route', 'historic', 'mountain']},
            'saint_vallier_de_thiey': {'lat': 43.6989, 'lon': 6.8489, 'country': 'France', 'types': ['prehistoric', 'caves', 'plateau', 'hiking']},
            'saint_cezaire_sur_siagne': {'lat': 43.6519, 'lon': 6.7933, 'country': 'France', 'types': ['caves', 'medieval', 'gorge', 'scenic']},
            'mons': {'lat': 43.6778, 'lon': 6.7133, 'country': 'France', 'types': ['perched', 'views', 'aqueduct', 'peaceful']},
            'speracedes': {'lat': 43.6489, 'lon': 6.8603, 'country': 'France', 'types': ['authentic', 'pottery', 'quiet', 'provencal']},
            'cabris': {'lat': 43.6556, 'lon': 6.8761, 'country': 'France', 'types': ['panoramic', 'ruins', 'gliding', 'artistic']},
            'peymeinade': {'lat': 43.6394, 'lon': 6.8747, 'country': 'France', 'types': ['residential', 'mimosa', 'quiet', 'provencal']},
            'le_tignet': {'lat': 43.6311, 'lon': 6.8472, 'country': 'France', 'types': ['countryside', 'viaduct', 'hiking', 'peaceful']},
            'tanneron': {'lat': 43.5903, 'lon': 6.8892, 'country': 'France', 'types': ['mimosa', 'forest', 'scenic', 'hiking']},
            'montauroux': {'lat': 43.6178, 'lon': 6.7639, 'country': 'France', 'types': ['bamboo', 'lake', 'golf', 'residential']},
            'callian': {'lat': 43.6233, 'lon': 6.7511, 'country': 'France', 'types': ['castle', 'medieval', 'artistic', 'markets']},
            'tourettes': {'lat': 43.6264, 'lon': 6.9008, 'country': 'France', 'types': ['medieval', 'violet', 'artistic', 'castle']},
            'la_colle_sur_loup': {'lat': 43.6856, 'lon': 7.1031, 'country': 'France', 'types': ['rose', 'perfume', 'village', 'authentic']},
            'chateauneuf_grasse': {'lat': 43.6747, 'lon': 6.9756, 'country': 'France', 'types': ['hilltop', 'views', 'quiet', 'residential']},
            'opio': {'lat': 43.6678, 'lon': 6.9856, 'country': 'France', 'types': ['olive', 'golf', 'quiet', 'provencal']},
            'valbonne': {'lat': 43.6414, 'lon': 7.0086, 'country': 'France', 'types': ['planned', 'tech', 'markets', 'modern']},
            'mougins': {'lat': 43.6003, 'lon': 7.0003, 'country': 'France', 'types': ['gastronomy', 'artistic', 'hilltop', 'luxury']},
            'mouans_sartoux': {'lat': 43.6197, 'lon': 6.9711, 'country': 'France', 'types': ['books', 'castle', 'cultural', 'gardens']},
            'pegomas': {'lat': 43.5933, 'lon': 6.9286, 'country': 'France', 'types': ['mimosa', 'riverside', 'quiet', 'authentic']},
            'la_roquette_sur_siagne': {'lat': 43.5819, 'lon': 6.9544, 'country': 'France', 'types': ['riverside', 'bamboo', 'quiet', 'nature']},
            'mandelieu_la_napoule': {'lat': 43.5361, 'lon': 6.9378, 'country': 'France', 'types': ['coastal', 'marina', 'golf', 'resort']},
            'theoule_sur_mer': {'lat': 43.5072, 'lon': 6.9406, 'country': 'France', 'types': ['coastal', 'red_rocks', 'beaches', 'scenic']},
            'saint_raphael': {'lat': 43.4250, 'lon': 6.7683, 'country': 'France', 'types': ['coastal', 'resort', 'roman', 'beaches']},
            'frejus': {'lat': 43.4333, 'lon': 6.7370, 'country': 'France', 'types': ['roman', 'cathedral', 'historic', 'beaches']},
            'roquebrune_sur_argens': {'lat': 43.4436, 'lon': 6.6378, 'country': 'France', 'types': ['rock', 'village', 'nature', 'hiking']},
            'le_muy': {'lat': 43.4722, 'lon': 6.5658, 'country': 'France', 'types': ['railway', 'museum', 'authentic', 'markets']},
            'les_arcs': {'lat': 43.4633, 'lon': 6.4806, 'country': 'France', 'types': ['medieval', 'wine', 'railway', 'authentic']},
            'trans_en_provence': {'lat': 43.5036, 'lon': 6.4856, 'country': 'France', 'types': ['waterfall', 'wells', 'hiking', 'nature']},
            'la_motte': {'lat': 43.4944, 'lon': 6.5347, 'country': 'France', 'types': ['wine', 'golf', 'countryside', 'quiet']},
            'le_cannet_des_maures': {'lat': 43.3897, 'lon': 6.3439, 'country': 'France', 'types': ['forest', 'chestnuts', 'hiking', 'nature']},
            'le_luc': {'lat': 43.3933, 'lon': 6.3125, 'country': 'France', 'types': ['hexagonal', 'campanile', 'history', 'authentic']},
            'gonfaron': {'lat': 43.3208, 'lon': 6.2892, 'country': 'France', 'types': ['donkeys', 'cork', 'village', 'nature']},
            'pignans': {'lat': 43.3025, 'lon': 6.2269, 'country': 'France', 'types': ['fountains', 'quiet', 'authentic', 'provencal']},
            'carnoules': {'lat': 43.3019, 'lon': 6.1875, 'country': 'France', 'types': ['railway', 'wine', 'countryside', 'quiet']},
            'puget_ville': {'lat': 43.2892, 'lon': 6.1367, 'country': 'France', 'types': ['wine', 'countryside', 'markets', 'authentic']},
            'cuers': {'lat': 43.2375, 'lon': 6.0708, 'country': 'France', 'types': ['citrus', 'fountains', 'provencal', 'markets']},
            'pierrefeu_du_var': {'lat': 43.2244, 'lon': 6.1456, 'country': 'France', 'types': ['wine', 'countryside', 'hiking', 'quiet']},
            'belgentier': {'lat': 43.2456, 'lon': 6.0006, 'country': 'France', 'types': ['gorge', 'caves', 'hiking', 'nature']},
            'sollies_pont': {'lat': 43.1906, 'lon': 6.0408, 'country': 'France', 'types': ['cherries', 'figs', 'festival', 'authentic']},
            'sollies_toucas': {'lat': 43.2078, 'lon': 6.0272, 'country': 'France', 'types': ['hilltop', 'views', 'quiet', 'residential']},
            'sollies_ville': {'lat': 43.1792, 'lon': 6.0361, 'country': 'France', 'types': ['castle', 'church', 'quiet', 'authentic']},
            'la_farlede': {'lat': 43.1694, 'lon': 6.0458, 'country': 'France', 'types': ['olive', 'mills', 'provencal', 'authentic']},
            'la_crau': {'lat': 43.1506, 'lon': 6.0739, 'country': 'France', 'types': ['plain', 'agriculture', 'horses', 'nature']},
            'la_garde': {'lat': 43.1242, 'lon': 6.0103, 'country': 'France', 'types': ['medieval', 'views', 'gardens', 'cultural']},
            'le_pradet': {'lat': 43.1047, 'lon': 6.0231, 'country': 'France', 'types': ['coastal', 'beaches', 'mining', 'hiking']},
            'carqueiranne': {'lat': 43.0950, 'lon': 6.0744, 'country': 'France', 'types': ['coastal', 'beaches', 'quiet', 'residential']},
            'hyeres': {'lat': 43.1203, 'lon': 6.1286, 'country': 'France', 'types': ['palmtrees', 'islands', 'medieval', 'gardens']},
            'la_londe_les_maures': {'lat': 43.1381, 'lon': 6.2339, 'country': 'France', 'types': ['wine', 'beaches', 'marina', 'resort']},
            'bormes_les_mimosas': {'lat': 43.1514, 'lon': 6.3425, 'country': 'France', 'types': ['mimosa', 'medieval', 'beaches', 'flowers']},
            'le_lavandou': {'lat': 43.1378, 'lon': 6.3681, 'country': 'France', 'types': ['beaches', 'fishing', 'resort', 'marina']},
            'rayol_canadel_sur_mer': {'lat': 43.1631, 'lon': 6.4650, 'country': 'France', 'types': ['gardens', 'coastal', 'mediterranean', 'botanic']},
            'cavalaire_sur_mer': {'lat': 43.1742, 'lon': 6.5336, 'country': 'France', 'types': ['beach', 'family', 'marina', 'resort']},
            'la_croix_valmer': {'lat': 43.2078, 'lon': 6.5700, 'country': 'France', 'types': ['beaches', 'wine', 'quiet', 'nature']},
            'gassin': {'lat': 43.2278, 'lon': 6.5853, 'country': 'France', 'types': ['perched', 'views', 'polo', 'luxury']},
            'ramatuelle': {'lat': 43.2150, 'lon': 6.6125, 'country': 'France', 'types': ['beaches', 'vineyards', 'celebrity', 'luxury']},
            'cogolin': {'lat': 43.2514, 'lon': 6.5347, 'country': 'France', 'types': ['pipes', 'carpets', 'marines', 'authentic']},
            'grimaud': {'lat': 43.2733, 'lon': 6.5222, 'country': 'France', 'types': ['castle', 'medieval', 'fairy_tale', 'canals']},
            'port_grimaud': {'lat': 43.2742, 'lon': 6.5819, 'country': 'France', 'types': ['venice_provencal', 'canals', 'boats', 'unique']},
            'sainte_maxime': {'lat': 43.3089, 'lon': 6.6358, 'country': 'France', 'types': ['beach', 'family', 'resort', 'marina']},
            'plan_de_la_tour': {'lat': 43.3381, 'lon': 6.5458, 'country': 'France', 'types': ['village', 'cork', 'markets', 'authentic']},
            'vidauban': {'lat': 43.4264, 'lon': 6.4319, 'country': 'France', 'types': ['wine', 'countryside', 'authentic', 'provencal']},
            'les_mayons': {'lat': 43.3133, 'lon': 6.3569, 'country': 'France', 'types': ['forest', 'chestnuts', 'quiet', 'nature']},
            'collobrieres': {'lat': 43.2378, 'lon': 6.3069, 'country': 'France', 'types': ['chestnuts', 'forest', 'monastery', 'hiking']},
            'la_garde_freinet': {'lat': 43.3175, 'lon': 6.4697, 'country': 'France', 'types': ['cork', 'village', 'hiking', 'views']},
            
            # Italian cities (Liguria region)
            'ventimiglia': {'lat': 43.7903, 'lon': 7.6083, 'country': 'Italy', 'types': ['border', 'markets', 'beaches', 'historic']},
            'bordighera': {'lat': 43.7806, 'lon': 7.6644, 'country': 'Italy', 'types': ['palms', 'british', 'gardens', 'elegant']},
            'ospedaletti': {'lat': 43.8003, 'lon': 7.7169, 'country': 'Italy', 'types': ['flowers', 'cycling', 'quiet', 'coastal']},
            'sanremo': {'lat': 43.8161, 'lon': 7.7761, 'country': 'Italy', 'types': ['festival', 'casino', 'flowers', 'resort']},
            'taggia': {'lat': 43.8481, 'lon': 7.8497, 'country': 'Italy', 'types': ['olives', 'medieval', 'bridges', 'authentic']},
            'arma_di_taggia': {'lat': 43.8331, 'lon': 7.8558, 'country': 'Italy', 'types': ['beach', 'grotto', 'family', 'resort']},
            'bussana_vecchia': {'lat': 43.8358, 'lon': 7.8278, 'country': 'Italy', 'types': ['artist_village', 'ruins', 'bohemian', 'unique']},
            'santo_stefano_al_mare': {'lat': 43.8481, 'lon': 7.9022, 'country': 'Italy', 'types': ['marina', 'quiet', 'beaches', 'authentic']},
            'riva_ligure': {'lat': 43.8478, 'lon': 7.9097, 'country': 'Italy', 'types': ['beach', 'promenade', 'quiet', 'family']},
            'san_lorenzo_al_mare': {'lat': 43.8503, 'lon': 7.9614, 'country': 'Italy', 'types': ['cycling', 'beach', 'quiet', 'modern']},
            'costarainera': {'lat': 43.8619, 'lon': 7.9225, 'country': 'Italy', 'types': ['hilltop', 'views', 'quiet', 'authentic']},
            'cipressa': {'lat': 43.8469, 'lon': 7.9419, 'country': 'Italy', 'types': ['tower', 'views', 'cycling', 'authentic']},
            'lingueglietta': {'lat': 43.8656, 'lon': 7.9472, 'country': 'Italy', 'types': ['medieval', 'stone', 'artistic', 'views']},
            'imperia': {'lat': 43.8897, 'lon': 8.0397, 'country': 'Italy', 'types': ['olive_oil', 'naval', 'beaches', 'historic']},
            'diano_marina': {'lat': 43.9097, 'lon': 8.0811, 'country': 'Italy', 'types': ['beach', 'family', 'resort', 'promenade']},
            'diano_castello': {'lat': 43.9272, 'lon': 8.0744, 'country': 'Italy', 'types': ['medieval', 'castle', 'views', 'authentic']},
            'san_bartolomeo_al_mare': {'lat': 43.9192, 'lon': 8.1097, 'country': 'Italy', 'types': ['beach', 'family', 'quiet', 'resort']},
            'cervo': {'lat': 43.9306, 'lon': 8.1142, 'country': 'Italy', 'types': ['medieval', 'music', 'baroque', 'scenic']},
            'andora': {'lat': 43.9514, 'lon': 8.1456, 'country': 'Italy', 'types': ['beach', 'castle', 'family', 'resort']},
            'laigueglia': {'lat': 43.9783, 'lon': 8.1594, 'country': 'Italy', 'types': ['fishing', 'colorful', 'beach', 'authentic']},
            'alassio': {'lat': 44.0067, 'lon': 8.1722, 'country': 'Italy', 'types': ['beach', 'muretto', 'resort', 'elegant']},
            'albenga': {'lat': 44.0497, 'lon': 8.2142, 'country': 'Italy', 'types': ['roman', 'medieval', 'towers', 'historic']},
            'ceriale': {'lat': 44.0878, 'lon': 8.2283, 'country': 'Italy', 'types': ['beach', 'family', 'quiet', 'resort']},
            'borghetto_santo_spirito': {'lat': 44.1108, 'lon': 8.2406, 'country': 'Italy', 'types': ['beach', 'castle', 'quiet', 'family']},
            'loano': {'lat': 44.1281, 'lon': 8.2586, 'country': 'Italy', 'types': ['beach', 'marina', 'shopping', 'resort']},
            'pietra_ligure': {'lat': 44.1467, 'lon': 8.2797, 'country': 'Italy', 'types': ['beach', 'medical', 'family', 'resort']},
            'borgio_verezzi': {'lat': 44.1606, 'lon': 8.3097, 'country': 'Italy', 'types': ['caves', 'theater', 'medieval', 'scenic']},
            'finale_ligure': {'lat': 44.1689, 'lon': 8.3442, 'country': 'Italy', 'types': ['climbing', 'beach', 'medieval', 'outdoor']},
            'varigotti': {'lat': 44.1831, 'lon': 8.3981, 'country': 'Italy', 'types': ['saracen', 'beach', 'colorful', 'scenic']},
            'noli': {'lat': 44.2011, 'lon': 8.4136, 'country': 'Italy', 'types': ['medieval', 'republic', 'beach', 'historic']},
            'spotorno': {'lat': 44.2253, 'lon': 8.4197, 'country': 'Italy', 'types': ['beach', 'castle', 'family', 'resort']},
            'bergeggi': {'lat': 44.2453, 'lon': 8.4461, 'country': 'Italy', 'types': ['island', 'diving', 'nature', 'marine']},
            'vado_ligure': {'lat': 44.2697, 'lon': 8.4361, 'country': 'Italy', 'types': ['port', 'industrial', 'beaches', 'modern']},
            'savona': {'lat': 44.3075, 'lon': 8.4817, 'country': 'Italy', 'types': ['port', 'fortress', 'ceramic', 'historic']},
            'albissola_marina': {'lat': 44.3331, 'lon': 8.5022, 'country': 'Italy', 'types': ['ceramics', 'beach', 'artistic', 'colorful']},
            'albisola_superiore': {'lat': 44.3364, 'lon': 8.5106, 'country': 'Italy', 'types': ['ceramics', 'artistic', 'workshops', 'authentic']},
            'celle_ligure': {'lat': 44.3428, 'lon': 8.5483, 'country': 'Italy', 'types': ['beach', 'fishing', 'quiet', 'authentic']},
            'varazze': {'lat': 44.3597, 'lon': 8.5783, 'country': 'Italy', 'types': ['beach', 'marina', 'medieval', 'resort']},
            'cogoleto': {'lat': 44.3892, 'lon': 8.6433, 'country': 'Italy', 'types': ['columbus', 'beach', 'quiet', 'residential']},
            'arenzano': {'lat': 44.4053, 'lon': 8.6819, 'country': 'Italy', 'types': ['park', 'beach', 'sanctuary', 'family']},
            'pegli': {'lat': 44.4283, 'lon': 8.8183, 'country': 'Italy', 'types': ['villas', 'parks', 'museums', 'elegant']},
            'sestri_ponente': {'lat': 44.4217, 'lon': 8.8492, 'country': 'Italy', 'types': ['airport', 'shipyard', 'authentic', 'working']},
            'cornigliano': {'lat': 44.4156, 'lon': 8.8694, 'country': 'Italy', 'types': ['industrial', 'transformation', 'authentic', 'urban']},
            'sampierdarena': {'lat': 44.4144, 'lon': 8.8875, 'country': 'Italy', 'types': ['port', 'palaces', 'authentic', 'urban']},
            'nervi': {'lat': 44.3814, 'lon': 9.0339, 'country': 'Italy', 'types': ['parks', 'villas', 'promenade', 'elegant']},
            'bogliasco': {'lat': 44.3781, 'lon': 9.0625, 'country': 'Italy', 'types': ['fishing', 'pebbles', 'authentic', 'picturesque']},
            'pieve_ligure': {'lat': 44.3736, 'lon': 9.0869, 'country': 'Italy', 'types': ['mimosa', 'views', 'quiet', 'residential']},
            'sori': {'lat': 44.3692, 'lon': 9.0967, 'country': 'Italy', 'types': ['beach', 'fishing', 'quiet', 'authentic']},
            'recco': {'lat': 44.3628, 'lon': 9.1428, 'country': 'Italy', 'types': ['focaccia', 'gastronomy', 'beach', 'culinary']},
            'camogli': {'lat': 44.3489, 'lon': 9.1553, 'country': 'Italy', 'types': ['colorful', 'fishing', 'romantic', 'picturesque']},
            'san_fruttuoso': {'lat': 44.3167, 'lon': 9.1750, 'country': 'Italy', 'types': ['abbey', 'christ_abyss', 'boat_only', 'unique']},
            'portofino': {'lat': 44.3036, 'lon': 9.2097, 'country': 'Italy', 'types': ['luxury', 'yachts', 'celebrity', 'exclusive']},
            'paraggi': {'lat': 44.3089, 'lon': 9.2039, 'country': 'Italy', 'types': ['beach', 'exclusive', 'small', 'luxury']},
            'santa_margherita_ligure': {'lat': 44.3350, 'lon': 9.2117, 'country': 'Italy', 'types': ['elegant', 'palm_trees', 'resort', 'sophisticated']},
            'rapallo': {'lat': 44.3494, 'lon': 9.2314, 'country': 'Italy', 'types': ['resort', 'cable_car', 'castle', 'lively']},
            'zoagli': {'lat': 44.3336, 'lon': 9.2700, 'country': 'Italy', 'types': ['silk', 'quiet', 'beach', 'authentic']},
            'chiavari': {'lat': 44.3164, 'lon': 9.3206, 'country': 'Italy', 'types': ['chairs', 'arcades', 'beach', 'historic']},
            'lavagna': {'lat': 44.3086, 'lon': 9.3450, 'country': 'Italy', 'types': ['beach', 'slate', 'family', 'authentic']},
            'cavi_di_lavagna': {'lat': 44.2933, 'lon': 9.3733, 'country': 'Italy', 'types': ['beach', 'tunnels', 'quiet', 'scenic']},
            'sestri_levante': {'lat': 44.2725, 'lon': 9.3978, 'country': 'Italy', 'types': ['two_bays', 'fairytale', 'romantic', 'beach']},
            'riva_trigoso': {'lat': 44.2619, 'lon': 9.4239, 'country': 'Italy', 'types': ['shipyard', 'beach', 'authentic', 'working']},
            'moneglia': {'lat': 44.2417, 'lon': 9.4889, 'country': 'Italy', 'types': ['beach', 'quiet', 'family', 'authentic']},
            'deiva_marina': {'lat': 44.2214, 'lon': 9.5183, 'country': 'Italy', 'types': ['beach', 'family', 'quiet', 'resort']},
            'framura': {'lat': 44.2067, 'lon': 9.5547, 'country': 'Italy', 'types': ['villages', 'hiking', 'quiet', 'authentic']},
            'bonassola': {'lat': 44.1858, 'lon': 9.5850, 'country': 'Italy', 'types': ['beach', 'cycling', 'family', 'peaceful']},
            'levanto': {'lat': 44.1703, 'lon': 9.6114, 'country': 'Italy', 'types': ['surfing', 'beach', 'medieval', 'gateway']},
            'monterosso_al_mare': {'lat': 44.1458, 'lon': 9.6539, 'country': 'Italy', 'types': ['cinque_terre', 'beach', 'largest', 'touristy']},
            'vernazza': {'lat': 44.1347, 'lon': 9.6847, 'country': 'Italy', 'types': ['cinque_terre', 'harbor', 'iconic', 'romantic']},
            'corniglia': {'lat': 44.1194, 'lon': 9.7097, 'country': 'Italy', 'types': ['cinque_terre', 'hilltop', 'quiet', 'vineyard']},
            'manarola': {'lat': 44.1064, 'lon': 9.7272, 'country': 'Italy', 'types': ['cinque_terre', 'wine', 'colorful', 'photogenic']},
            'riomaggiore': {'lat': 44.0994, 'lon': 9.7372, 'country': 'Italy', 'types': ['cinque_terre', 'vertical', 'colorful', 'dramatic']},
            'la_spezia': {'lat': 44.1025, 'lon': 9.8236, 'country': 'Italy', 'types': ['naval', 'museums', 'gateway', 'urban']},
            'portovenere': {'lat': 44.0514, 'lon': 9.8344, 'country': 'Italy', 'types': ['unesco', 'church', 'grotto', 'romantic']},
            'lerici': {'lat': 44.0753, 'lon': 9.9114, 'country': 'Italy', 'types': ['castle', 'beach', 'poets', 'elegant']},
            'san_terenzo': {'lat': 44.0706, 'lon': 9.9311, 'country': 'Italy', 'types': ['beach', 'castle', 'shelley', 'quiet']},
            'tellaro': {'lat': 44.0586, 'lon': 9.9361, 'country': 'Italy', 'types': ['fishing', 'octopus', 'romantic', 'tiny']},
            'montemarcello': {'lat': 44.0708, 'lon': 9.9539, 'country': 'Italy', 'types': ['hilltop', 'park', 'views', 'peaceful']},
            'ameglia': {'lat': 44.0589, 'lon': 9.9997, 'country': 'Italy', 'types': ['river', 'nature', 'quiet', 'authentic']},
            'bocca_di_magra': {'lat': 44.0550, 'lon': 10.0167, 'country': 'Italy', 'types': ['river_mouth', 'beaches', 'boats', 'nature']},
            'sarzana': {'lat': 44.1108, 'lon': 9.9608, 'country': 'Italy', 'types': ['fortress', 'antiques', 'historic', 'markets']},
            
            # Piedmont region (Italy)
            'ventimiglia_alta': {'lat': 43.7958, 'lon': 7.6089, 'country': 'Italy', 'types': ['medieval', 'hilltop', 'views', 'authentic']},
            'airole': {'lat': 43.8703, 'lon': 7.5514, 'country': 'Italy', 'types': ['climbing', 'village', 'valley', 'outdoor']},
            'olivetta_san_michele': {'lat': 43.8792, 'lon': 7.5178, 'country': 'Italy', 'types': ['border', 'nature', 'quiet', 'hiking']},
            'dolceacqua': {'lat': 43.8506, 'lon': 7.6228, 'country': 'Italy', 'types': ['bridge', 'castle', 'wine', 'picturesque']},
            'rocchetta_nervina': {'lat': 43.8936, 'lon': 7.5900, 'country': 'Italy', 'types': ['lakes', 'swimming', 'hiking', 'nature']},
            'isolabona': {'lat': 43.8839, 'lon': 7.6403, 'country': 'Italy', 'types': ['library', 'medieval', 'quiet', 'cultural']},
            'apricale': {'lat': 43.8828, 'lon': 7.6594, 'country': 'Italy', 'types': ['artists', 'medieval', 'theater', 'hilltop']},
            'bajardo': {'lat': 43.9000, 'lon': 7.7108, 'country': 'Italy', 'types': ['highest', 'druids', 'mystical', 'views']},
            'perinaldo': {'lat': 43.8667, 'lon': 7.6667, 'country': 'Italy', 'types': ['astronomy', 'cassini', 'stars', 'hilltop']},
            'seborga': {'lat': 43.8267, 'lon': 7.6956, 'country': 'Italy', 'types': ['principality', 'mint', 'flowers', 'unique']},
            'vallebona': {'lat': 43.8147, 'lon': 7.6619, 'country': 'Italy', 'types': ['quiet', 'authentic', 'valley', 'rural']},
            'soldano': {'lat': 43.8450, 'lon': 7.6575, 'country': 'Italy', 'types': ['wine', 'views', 'quiet', 'authentic']},
            'san_biagio_della_cima': {'lat': 43.8203, 'lon': 7.6492, 'country': 'Italy', 'types': ['wine', 'quiet', 'rural', 'authentic']},
            'camporosso': {'lat': 43.8139, 'lon': 7.6267, 'country': 'Italy', 'types': ['agriculture', 'river', 'authentic', 'quiet']},
            'vallecrosia': {'lat': 43.7844, 'lon': 7.6456, 'country': 'Italy', 'types': ['flowers', 'market', 'beach', 'authentic']},
            'badalucco': {'lat': 43.9169, 'lon': 7.8456, 'country': 'Italy', 'types': ['frescoes', 'bridge', 'art', 'authentic']},
            'montalto_carpasio': {'lat': 43.9222, 'lon': 7.8967, 'country': 'Italy', 'types': ['lavender', 'festival', 'quiet', 'rural']},
            'triora': {'lat': 44.0047, 'lon': 7.7619, 'country': 'Italy', 'types': ['witches', 'medieval', 'museum', 'mysterious']},
            'molini_di_triora': {'lat': 43.9911, 'lon': 7.7569, 'country': 'Italy', 'types': ['mills', 'river', 'quiet', 'nature']},
            'carpasio': {'lat': 43.9408, 'lon': 7.8797, 'country': 'Italy', 'types': ['castle', 'quiet', 'rural', 'authentic']},
            'castellaro': {'lat': 43.8744, 'lon': 7.9006, 'country': 'Italy', 'types': ['hilltop', 'views', 'quiet', 'authentic']},
            'pompeiana': {'lat': 43.8478, 'lon': 7.8914, 'country': 'Italy', 'types': ['museum', 'quiet', 'hilltop', 'authentic']},
            'terzorio': {'lat': 43.8222, 'lon': 7.8906, 'country': 'Italy', 'types': ['monastery', 'quiet', 'rural', 'authentic']},
            'vasia': {'lat': 43.8731, 'lon': 8.0122, 'country': 'Italy', 'types': ['panoramic', 'quiet', 'authentic', 'rural']},
            'pantasina': {'lat': 43.8842, 'lon': 8.0244, 'country': 'Italy', 'types': ['tiny', 'views', 'quiet', 'authentic']},
            'prela': {'lat': 43.9267, 'lon': 8.0700, 'country': 'Italy', 'types': ['spa', 'abandoned', 'nature', 'hiking']},
            'dolcedo': {'lat': 43.9028, 'lon': 7.9492, 'country': 'Italy', 'types': ['bridges', 'olive_oil', 'authentic', 'valley']},
            'valloria': {'lat': 43.8989, 'lon': 7.9306, 'country': 'Italy', 'types': ['painted_doors', 'artistic', 'tiny', 'unique']},
            'pietrabruna': {'lat': 43.8928, 'lon': 7.9478, 'country': 'Italy', 'types': ['tower', 'views', 'quiet', 'authentic']},
            'san_gregorio': {'lat': 43.8814, 'lon': 7.9669, 'country': 'Italy', 'types': ['tiny', 'authentic', 'quiet', 'rural']},
            'vellego': {'lat': 43.9147, 'lon': 7.9878, 'country': 'Italy', 'types': ['remote', 'hiking', 'quiet', 'nature']},
            'costa_bacelega': {'lat': 43.8992, 'lon': 8.0083, 'country': 'Italy', 'types': ['hamlet', 'rural', 'quiet', 'authentic']},
            'torrazza': {'lat': 43.9058, 'lon': 8.0189, 'country': 'Italy', 'types': ['small', 'authentic', 'quiet', 'rural']},
            'cesio': {'lat': 43.9878, 'lon': 8.0847, 'country': 'Italy', 'types': ['views', 'quiet', 'rural', 'authentic']},
            'torria': {'lat': 43.9867, 'lon': 8.0722, 'country': 'Italy', 'types': ['tiny', 'stone', 'quiet', 'authentic']},
            'vessalico': {'lat': 44.0511, 'lon': 7.9594, 'country': 'Italy', 'types': ['garlic', 'festival', 'authentic', 'valley']},
            'pieve_di_teco': {'lat': 44.0458, 'lon': 7.9147, 'country': 'Italy', 'types': ['porticoes', 'theater', 'historic', 'authentic']},
            'pornassio': {'lat': 44.0906, 'lon': 7.8878, 'country': 'Italy', 'types': ['mushrooms', 'castle', 'forest', 'nature']},
            'mendatica': {'lat': 44.0808, 'lon': 7.9097, 'country': 'Italy', 'types': ['cheese', 'mountain', 'hiking', 'authentic']},
            'montegrosso_pian_latte': {'lat': 44.0708, 'lon': 7.8697, 'country': 'Italy', 'types': ['mountain', 'dairy', 'quiet', 'nature']},
            'cosio_di_arroscia': {'lat': 44.0839, 'lon': 7.9319, 'country': 'Italy', 'types': ['bridge', 'valley', 'quiet', 'hiking']},
            'aquila_di_arroscia': {'lat': 44.0933, 'lon': 7.9567, 'country': 'Italy', 'types': ['eagle', 'views', 'tiny', 'authentic']},
            'armo': {'lat': 44.1017, 'lon': 7.8981, 'country': 'Italy', 'types': ['abandoned', 'hamlet', 'hiking', 'remote']},
            'rezzo': {'lat': 44.0211, 'lon': 7.8711, 'country': 'Italy', 'types': ['alpine', 'quiet', 'cheese', 'nature']},
            'lavina': {'lat': 44.0044, 'lon': 7.8467, 'country': 'Italy', 'types': ['hamlet', 'rural', 'quiet', 'authentic']},
            'cenova': {'lat': 43.9969, 'lon': 7.8342, 'country': 'Italy', 'types': ['bridge', 'valley', 'quiet', 'authentic']},
            'montale_ligure': {'lat': 44.1008, 'lon': 7.8542, 'country': 'Italy', 'types': ['mountain', 'views', 'quiet', 'nature']},
            'borgomaro': {'lat': 43.9814, 'lon': 8.0403, 'country': 'Italy', 'types': ['olive_trees', 'views', 'quiet', 'authentic']},
            'aurigo': {'lat': 43.9983, 'lon': 8.0350, 'country': 'Italy', 'types': ['panoramic', 'quiet', 'rural', 'authentic']},
            'poggialto': {'lat': 43.9922, 'lon': 8.0242, 'country': 'Italy', 'types': ['hamlet', 'views', 'quiet', 'authentic']},
            'cantalupo': {'lat': 43.9936, 'lon': 8.0125, 'country': 'Italy', 'types': ['tiny', 'rural', 'quiet', 'authentic']},
            'bestagno': {'lat': 44.0528, 'lon': 8.0400, 'country': 'Italy', 'types': ['castle', 'views', 'quiet', 'authentic']},
            'chiusanico': {'lat': 43.9875, 'lon': 8.0569, 'country': 'Italy', 'types': ['valley', 'olive_oil', 'quiet', 'authentic']},
            'gazzelli': {'lat': 43.9844, 'lon': 8.0461, 'country': 'Italy', 'types': ['hamlet', 'rural', 'quiet', 'authentic']},
            'chiusavecchia': {'lat': 44.0028, 'lon': 8.0678, 'country': 'Italy', 'types': ['medieval', 'castle', 'views', 'authentic']},
            'olivastri': {'lat': 43.9994, 'lon': 8.0542, 'country': 'Italy', 'types': ['hamlet', 'rural', 'quiet', 'authentic']},
            'sarola': {'lat': 43.9722, 'lon': 8.0431, 'country': 'Italy', 'types': ['hamlet', 'views', 'quiet', 'authentic']},
            'torria': {'lat': 43.9867, 'lon': 8.0722, 'country': 'Italy', 'types': ['stone', 'tiny', 'quiet', 'authentic']},
            'zebbi': {'lat': 43.9753, 'lon': 8.0542, 'country': 'Italy', 'types': ['hamlet', 'rural', 'quiet', 'authentic']},
            'san_lazzaro_reale': {'lat': 43.9508, 'lon': 8.0728, 'country': 'Italy', 'types': ['fortified', 'views', 'quiet', 'authentic']},
            'lucinasco': {'lat': 43.9781, 'lon': 8.0806, 'country': 'Italy', 'types': ['olive_groves', 'views', 'quiet', 'authentic']},
            'civezza': {'lat': 43.8850, 'lon': 8.0150, 'country': 'Italy', 'types': ['music_festival', 'views', 'artistic', 'authentic']},
            'piezo': {'lat': 43.8989, 'lon': 8.0367, 'country': 'Italy', 'types': ['tiny', 'views', 'quiet', 'authentic']},
            'colle_san_bartolomeo': {'lat': 43.9161, 'lon': 8.0461, 'country': 'Italy', 'types': ['hilltop', 'views', 'quiet', 'authentic']},
            'caramagna': {'lat': 43.9244, 'lon': 8.0569, 'country': 'Italy', 'types': ['rural', 'olive_oil', 'quiet', 'authentic']},
            'lingueglietta': {'lat': 43.8656, 'lon': 7.9472, 'country': 'Italy', 'types': ['medieval', 'stone', 'artistic', 'views']},
            
            # Tuscany region (Italy) - Northern part near Liguria
            'carrara': {'lat': 44.0794, 'lon': 10.0978, 'country': 'Italy', 'types': ['marble', 'quarries', 'artistic', 'unique']},
            'marina_di_carrara': {'lat': 44.0361, 'lon': 10.0392, 'country': 'Italy', 'types': ['beach', 'marble_port', 'resort', 'modern']},
            'massa': {'lat': 44.0354, 'lon': 10.1393, 'country': 'Italy', 'types': ['ducal', 'castle', 'beach', 'historic']},
            'marina_di_massa': {'lat': 44.0081, 'lon': 10.1028, 'country': 'Italy', 'types': ['beach', 'pier', 'family', 'resort']},
            'montignoso': {'lat': 44.0169, 'lon': 10.1678, 'country': 'Italy', 'types': ['castle', 'aghinolfi', 'quiet', 'panoramic']},
            'forte_dei_marmi': {'lat': 43.9667, 'lon': 10.1667, 'country': 'Italy', 'types': ['luxury', 'beach', 'vip', 'exclusive']},
            'seravezza': {'lat': 43.9994, 'lon': 10.2356, 'country': 'Italy', 'types': ['medici', 'marble', 'artistic', 'authentic']},
            'stazzema': {'lat': 43.9772, 'lon': 10.2733, 'country': 'Italy', 'types': ['memorial', 'mountains', 'hiking', 'history']},
            'pietrasanta': {'lat': 43.9594, 'lon': 10.2278, 'country': 'Italy', 'types': ['artistic', 'sculpture', 'marble', 'cultural']},
            'camaiore': {'lat': 43.9419, 'lon': 10.3031, 'country': 'Italy', 'types': ['beaches', 'hills', 'varied', 'authentic']},
            'viareggio': {'lat': 43.8664, 'lon': 10.2440, 'country': 'Italy', 'types': ['carnival', 'beach', 'liberty', 'resort']},
            'torre_del_lago': {'lat': 43.8242, 'lon': 10.2886, 'country': 'Italy', 'types': ['puccini', 'lake', 'opera', 'cultural']},
            'massarosa': {'lat': 43.8711, 'lon': 10.3411, 'country': 'Italy', 'types': ['hills', 'olive_oil', 'quiet', 'rural']},
            'vecchiano': {'lat': 43.7828, 'lon': 10.3858, 'country': 'Italy', 'types': ['park', 'nature', 'river', 'authentic']},
            'san_giuliano_terme': {'lat': 43.7642, 'lon': 10.4378, 'country': 'Italy', 'types': ['thermal', 'spa', 'pisa_mountains', 'wellness']},
            'calci': {'lat': 43.7250, 'lon': 10.5236, 'country': 'Italy', 'types': ['certosa', 'monastery', 'museum', 'cultural']},
            'vicopisano': {'lat': 43.6869, 'lon': 10.5808, 'country': 'Italy', 'types': ['brunelleschi', 'fortress', 'medieval', 'towers']},
            'buti': {'lat': 43.7289, 'lon': 10.5831, 'country': 'Italy', 'types': ['castle', 'oil', 'chestnuts', 'authentic']},
            'calcinaia': {'lat': 43.6828, 'lon': 10.6158, 'country': 'Italy', 'types': ['ceramics', 'arno', 'authentic', 'industrial']},
            'cascina': {'lat': 43.6739, 'lon': 10.5503, 'country': 'Italy', 'types': ['furniture', 'battle', 'historic', 'authentic']},
            'san_miniato': {'lat': 43.6800, 'lon': 10.8492, 'country': 'Italy', 'types': ['truffle', 'napoleon', 'hilltop', 'gastronomy']},
            'montopoli_in_val_darno': {'lat': 43.6681, 'lon': 10.7483, 'country': 'Italy', 'types': ['ceramics', 'towers', 'quiet', 'authentic']},
            'santa_croce_sullarno': {'lat': 43.7178, 'lon': 10.7842, 'country': 'Italy', 'types': ['leather', 'tanning', 'authentic', 'industrial']},
            'fucecchio': {'lat': 43.7319, 'lon': 10.8097, 'country': 'Italy', 'types': ['marshland', 'nature', 'birds', 'padule']},
            'castelfranco_di_sotto': {'lat': 43.7006, 'lon': 10.7428, 'country': 'Italy', 'types': ['carnival', 'leather', 'authentic', 'traditional']},
            'santa_maria_a_monte': {'lat': 43.7000, 'lon': 10.6881, 'country': 'Italy', 'types': ['hilltop', 'clock', 'views', 'authentic']},
            'pontedera': {'lat': 43.6625, 'lon': 10.6363, 'country': 'Italy', 'types': ['vespa', 'piaggio', 'museum', 'modern']},
            'ponsacco': {'lat': 43.6200, 'lon': 10.6331, 'country': 'Italy', 'types': ['furniture', 'markets', 'authentic', 'commercial']},
            'lari': {'lat': 43.5683, 'lon': 10.5944, 'country': 'Italy', 'types': ['cherries', 'castle', 'medieval', 'hilltop']},
            'peccioli': {'lat': 43.5486, 'lon': 10.7186, 'country': 'Italy', 'types': ['art', 'contemporary', 'hilltop', 'innovative']},
            'terricciola': {'lat': 43.5256, 'lon': 10.6789, 'country': 'Italy', 'types': ['wine', 'strawberries', 'quiet', 'authentic']},
            'lajatico': {'lat': 43.4753, 'lon': 10.7219, 'country': 'Italy', 'types': ['bocelli', 'theater', 'silence', 'cultural']},
            'montecatini_val_di_cecina': {'lat': 43.3906, 'lon': 10.7506, 'country': 'Italy', 'types': ['copper', 'mines', 'tower', 'authentic']},
            'pomarance': {'lat': 43.2994, 'lon': 10.8722, 'country': 'Italy', 'types': ['geothermal', 'energy', 'authentic', 'industrial']},
            'monteverdi_marittimo': {'lat': 43.1783, 'lon': 10.7369, 'country': 'Italy', 'types': ['hilltop', 'views', 'quiet', 'authentic']},
            'castelnuovo_val_di_cecina': {'lat': 43.2133, 'lon': 10.9014, 'country': 'Italy', 'types': ['medieval', 'geothermal', 'quiet', 'authentic']},
            
            # More French Alpine cities
            'saint_gervais_les_bains': {'lat': 45.8925, 'lon': 6.7131, 'country': 'France', 'types': ['spa', 'skiing', 'mont_blanc', 'alpine']},
            'megeve': {'lat': 45.8569, 'lon': 6.6178, 'country': 'France', 'types': ['luxury', 'skiing', 'chic', 'alpine']},
            'les_contamines_montjoie': {'lat': 45.8208, 'lon': 6.7278, 'country': 'France', 'types': ['skiing', 'hiking', 'authentic', 'alpine']},
            'passy': {'lat': 45.9244, 'lon': 6.6878, 'country': 'France', 'types': ['plateau', 'views', 'lakes', 'alpine']},
            'sallanches': {'lat': 45.9436, 'lon': 6.6314, 'country': 'France', 'types': ['gateway', 'mont_blanc', 'authentic', 'alpine']},
            'cordon': {'lat': 45.9206, 'lon': 6.6064, 'country': 'France', 'types': ['balcony', 'views', 'quiet', 'alpine']},
            'combloux': {'lat': 45.8997, 'lon': 6.6456, 'country': 'France', 'types': ['panoramic', 'family', 'authentic', 'alpine']},
            'la_giettaz': {'lat': 45.8664, 'lon': 6.4958, 'country': 'France', 'types': ['pass', 'cheese', 'quiet', 'alpine']},
            'flumet': {'lat': 45.8186, 'lon': 6.5169, 'country': 'France', 'types': ['medieval', 'gorge', 'authentic', 'alpine']},
            'notre_dame_de_bellecombe': {'lat': 45.8097, 'lon': 6.5414, 'country': 'France', 'types': ['skiing', 'summer', 'family', 'alpine']},
            'praz_sur_arly': {'lat': 45.8372, 'lon': 6.5714, 'country': 'France', 'types': ['ski_link', 'views', 'authentic', 'alpine']},
            'crest_voland': {'lat': 45.7947, 'lon': 6.5050, 'country': 'France', 'types': ['skiing', 'hiking', 'quiet', 'alpine']},
            'la_plagne': {'lat': 45.5072, 'lon': 6.6772, 'country': 'France', 'types': ['skiing', 'glacier', 'resort', 'alpine']},
            'peisey_nancroix': {'lat': 45.5508, 'lon': 6.7603, 'country': 'France', 'types': ['paradiski', 'authentic', 'vanoise', 'alpine']},
            'les_arcs': {'lat': 45.5719, 'lon': 6.8294, 'country': 'France', 'types': ['skiing', 'modern', 'car_free', 'alpine']},
            'bourg_saint_maurice': {'lat': 45.6189, 'lon': 6.7683, 'country': 'France', 'types': ['funicular', 'gateway', 'rafting', 'alpine']},
            'seez': {'lat': 45.6258, 'lon': 6.8003, 'country': 'France', 'types': ['baroque', 'passes', 'authentic', 'alpine']},
            'montvalezan': {'lat': 45.6203, 'lon': 6.8461, 'country': 'France', 'types': ['dam', 'views', 'quiet', 'alpine']},
            'la_rosiere': {'lat': 45.6278, 'lon': 6.8506, 'country': 'France', 'types': ['skiing', 'italy_link', 'sunny', 'alpine']},
            'sainte_foy_tarentaise': {'lat': 45.5947, 'lon': 6.8881, 'country': 'France', 'types': ['off_piste', 'authentic', 'wilderness', 'alpine']},
            'tignes': {'lat': 45.4683, 'lon': 6.9083, 'country': 'France', 'types': ['glacier_skiing', 'lake', 'high', 'alpine']},
            'val_disere': {'lat': 45.4481, 'lon': 6.9800, 'country': 'France', 'types': ['luxury_skiing', 'espace_killy', 'chic', 'alpine']},
            'villaroger': {'lat': 45.5572, 'lon': 6.8181, 'country': 'France', 'types': ['authentic', 'quiet', 'traditional', 'alpine']},
            'bonneval_sur_arc': {'lat': 45.3719, 'lon': 7.0472, 'country': 'France', 'types': ['authentic', 'stone', 'remote', 'alpine']},
            'bessans': {'lat': 45.3208, 'lon': 7.0069, 'country': 'France', 'types': ['cross_country', 'devils', 'authentic', 'alpine']},
            'lanslevillard': {'lat': 45.2872, 'lon': 6.9194, 'country': 'France', 'types': ['skiing', 'authentic', 'vanoise', 'alpine']},
            'lanslebourg_mont_cenis': {'lat': 45.2867, 'lon': 6.8814, 'country': 'France', 'types': ['pass', 'fort', 'history', 'alpine']},
            'termignon': {'lat': 45.2758, 'lon': 6.8133, 'country': 'France', 'types': ['vanoise', 'hiking', 'cheese', 'alpine']},
            'sollières_sardières': {'lat': 45.2569, 'lon': 6.8022, 'country': 'France', 'types': ['monolith', 'gorge', 'quiet', 'alpine']},
            'bramans': {'lat': 45.2231, 'lon': 6.7783, 'country': 'France', 'types': ['fort', 'hiking', 'authentic', 'alpine']},
            'avrieux': {'lat': 45.2178, 'lon': 6.7219, 'country': 'France', 'types': ['church', 'frescoes', 'quiet', 'alpine']},
            'villarodin_bourget': {'lat': 45.2369, 'lon': 6.7094, 'country': 'France', 'types': ['telegraph', 'history', 'quiet', 'alpine']},
            'modane': {'lat': 45.2017, 'lon': 6.6544, 'country': 'France', 'types': ['railway', 'tunnel', 'forts', 'alpine']},
            'saint_michel_de_maurienne': {'lat': 45.2189, 'lon': 6.4706, 'country': 'France', 'types': ['beaufort', 'cheese', 'baroque', 'alpine']},
            'valmeinier': {'lat': 45.1861, 'lon': 6.4831, 'country': 'France', 'types': ['skiing', 'authentic', 'family', 'alpine']},
            'valloire': {'lat': 45.1656, 'lon': 6.4297, 'country': 'France', 'types': ['skiing', 'galibier', 'cycling', 'alpine']},
            'saint_sorlin_darves': {'lat': 45.2181, 'lon': 6.2344, 'country': 'France', 'types': ['skiing', 'glacier', 'authentic', 'alpine']},
            'saint_jean_de_maurienne': {'lat': 45.2761, 'lon': 6.3461, 'country': 'France', 'types': ['cathedral', 'opinel', 'cycling', 'alpine']},
            'la_chambre': {'lat': 45.3389, 'lon': 6.2947, 'country': 'France', 'types': ['valley', 'authentic', 'quiet', 'alpine']},
            'saint_etienne_de_cuines': {'lat': 45.3483, 'lon': 6.2731, 'country': 'France', 'types': ['pyramid', 'unique', 'quiet', 'alpine']},
            'la_chapelle': {'lat': 45.3742, 'lon': 6.2842, 'country': 'France', 'types': ['hamlet', 'traditional', 'quiet', 'alpine']},
            'saint_alban_des_villards': {'lat': 45.2792, 'lon': 6.2547, 'country': 'France', 'types': ['skiing', 'quiet', 'authentic', 'alpine']},
            'saint_colomban_des_villards': {'lat': 45.2706, 'lon': 6.2264, 'country': 'France', 'types': ['gypsum', 'hiking', 'quiet', 'alpine']},
            'jarrier': {'lat': 45.2689, 'lon': 6.3214, 'country': 'France', 'types': ['telegraph', 'museum', 'quiet', 'alpine']},
            'montvernier': {'lat': 45.3156, 'lon': 6.3389, 'country': 'France', 'types': ['lacets', 'hairpins', 'spectacular', 'alpine']},
            'hermillon': {'lat': 45.2806, 'lon': 6.3258, 'country': 'France', 'types': ['industry', 'valley', 'authentic', 'alpine']},
            'pontamafrey_montpascal': {'lat': 45.2972, 'lon': 6.3322, 'country': 'France', 'types': ['views', 'quiet', 'traditional', 'alpine']},
            'le_chatel': {'lat': 45.2822, 'lon': 6.2903, 'country': 'France', 'types': ['hamlet', 'stone', 'quiet', 'alpine']},
            'montaimont': {'lat': 45.4056, 'lon': 6.3253, 'country': 'France', 'types': ['remote', 'hiking', 'nature', 'alpine']},
            'montgellafrey': {'lat': 45.1881, 'lon': 6.4997, 'country': 'France', 'types': ['hamlet', 'traditional', 'quiet', 'alpine']},
            'saint_martin_de_la_porte': {'lat': 45.2158, 'lon': 6.5792, 'country': 'France', 'types': ['tunnel', 'baroque', 'quiet', 'alpine']},
            'saint_andre': {'lat': 45.2117, 'lon': 6.6219, 'country': 'France', 'types': ['fort', 'views', 'quiet', 'alpine']},
            'le_freney': {'lat': 45.2053, 'lon': 6.6367, 'country': 'France', 'types': ['hamlet', 'traditional', 'quiet', 'alpine']},
            'fourneaux': {'lat': 45.2728, 'lon': 6.5936, 'country': 'France', 'types': ['dam', 'hiking', 'authentic', 'alpine']},
            'freney': {'lat': 45.2056, 'lon': 6.5978, 'country': 'France', 'types': ['chapel', 'views', 'quiet', 'alpine']},
            'orelle': {'lat': 45.2106, 'lon': 6.5406, 'country': 'France', 'types': ['3_valleys', 'cable_car', 'highest', 'alpine']}
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
        
        # Add randomization for variety in route generation
        import random
        
        # Sort by distance from start point for initial ordering
        from geopy.distance import geodesic
        candidates.sort(key=lambda c: geodesic(
            (start.latitude, start.longitude),
            (c.coordinates.latitude, c.coordinates.longitude)
        ).kilometers)
        
        # Add randomization while maintaining geographic relevance
        # Take the closest candidates but shuffle within groups for variety
        if len(candidates) > 8:
            # Keep closest 12 cities but randomize their order for variety
            close_candidates = candidates[:12]
            random.shuffle(close_candidates)
            return close_candidates[:8]
        else:
            # For smaller lists, add some randomization
            random.shuffle(candidates)
            return candidates[:8]
    
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
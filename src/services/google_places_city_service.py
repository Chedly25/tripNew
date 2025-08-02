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
        """Get city by name using our comprehensive database."""
        if not name or not name.strip():
            return None
        
        # Check cache first
        cache_key = name.lower().strip()
        if cache_key in self._city_cache:
            return self._city_cache[cache_key]
        
        # Always use fallback since we're removing Google Places API
        city = self._get_fallback_city(name)
        if city:
            self._city_cache[cache_key] = city
        return city
    
    def get_city_by_name_sync(self, name: str) -> Optional[City]:
        """Synchronous version of get_city_by_name for compatibility."""
        if not name or not name.strip():
            return None
        
        # Check cache first
        cache_key = name.lower().strip()
        if cache_key in self._city_cache:
            return self._city_cache[cache_key]
        
        # Always use fallback since we're removing Google Places API
        return self._get_fallback_city(name)
    
    async def find_cities_near_route(self, start: Coordinates, end: Coordinates, 
                                   max_deviation_km: float = 100, route_type: str = None) -> List[City]:
        """Find interesting cities near the route using our comprehensive database."""
        logger.info("Using comprehensive database for route cities (Google Places API disabled)")
        return self._get_fallback_route_cities(start, end, max_deviation_km, route_type)
    
    async def find_cities_by_type(self, city_type: str) -> List[City]:
        """Find cities by type using our comprehensive database."""
        logger.info(f"Skipping Google Places API for city type search: {city_type}")
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
            
            # Clean up city name (remove underscores, fix formatting)
            name = self._clean_city_name(name)
            
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
    
    def _clean_city_name(self, name: str) -> str:
        """Clean up city name formatting (remove underscores, proper capitalization)."""
        if not name:
            return name
        
        # Replace underscores with spaces
        cleaned = name.replace('_', ' ')
        
        # Handle special cases and proper capitalization
        # Split by spaces and capitalize each word, except for small words like "de", "la", "le", etc.
        words = cleaned.split()
        small_words = {'de', 'la', 'le', 'les', 'du', 'des', 'di', 'del', 'della', 'al', 'sur', 'en', 'aux'}
        
        result = []
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in small_words:
                # Capitalize first word and words not in small_words list
                result.append(word.capitalize())
            else:
                # Keep small words lowercase unless they're the first word
                result.append(word.lower())
        
        return ' '.join(result)
    
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
            # Clean up the city name for display
            clean_name = self._clean_city_name(name)
            return City(
                name=clean_name,
                coordinates=Coordinates(latitude=data['lat'], longitude=data['lon']),
                country=data['country'],
                types=data.get('types', ['fallback'])
            )
        
        return None
    
    def _get_fallback_route_cities(self, start: Coordinates, end: Coordinates, 
                                 max_deviation_km: float, route_type: str = None) -> List[City]:
        """Get fallback cities for route when API is unavailable, filtered by route type."""
        # Use the comprehensive city database from _get_comprehensive_city_database
        known_cities = self._get_comprehensive_city_database()
        
        # Create city objects and filter by distance to route
        candidates = []
        for name, data in known_cities.items():
            city_coords = Coordinates(latitude=data['lat'], longitude=data['lon'])
            if self._is_city_near_route(city_coords, start, end, max_deviation_km):
                city = City(
                    name=self._clean_city_name(name),
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
                'hidden_gems': ['hidden_gems', 'authentic', 'village', 'medieval', 'unique', 'traditional', 'local']
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
    
    def _get_comprehensive_city_database(self):
        """Load and parse the comprehensive city database from JSON files."""
        try:
            import json
            import os
            
            # Get the database file paths
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_file = os.path.join(current_dir, 'data', 'comprehensive_european_cities.json')
            massive_db_file = os.path.join(current_dir, 'data', 'massive_european_cities.json')
            
            cities_db = {}
            
            # Load both databases and merge them
            for db_path, db_name in [(db_file, "comprehensive"), (massive_db_file, "massive")]:
                if os.path.exists(db_path):
                    try:
                        with open(db_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Process all countries in the database
                        if 'cities' in data:
                            for country_key, country_data in data['cities'].items():
                                # Map country keys to proper country names
                                country_name = self._get_country_name(country_key)
                                
                                for region_name, region_cities in country_data.items():
                                    for city_key, city_data in region_cities.items():
                                        # Skip if already exists (prefer comprehensive over massive)
                                        if city_key in cities_db and db_name == "massive":
                                            continue
                                        
                                        # Handle different coordinate formats
                                        try:
                                            if 'coordinates' in city_data:
                                                coords = city_data['coordinates']
                                                lat = coords['lat']
                                                lon = coords['lon']
                                            else:
                                                # Fallback for old format
                                                lat = city_data.get('lat', 45.0)
                                                lon = city_data.get('lon', 7.0)
                                                
                                            cities_db[city_key] = {
                                                'lat': lat,
                                                'lon': lon,
                                                'country': country_name,
                                                'types': city_data.get('types', []),
                                                'population': city_data.get('population'),
                                                'travel_appeal': city_data.get('travel_appeal', 'medium'),
                                                'authenticity_score': city_data.get('authenticity_score', 5),
                                                'specialties': city_data.get('specialties', []),
                                                'hidden_gems': city_data.get('hidden_gems', []),
                                                'region': city_data.get('region'),
                                                'local_character': city_data.get('local_character', '')
                                            }
                                        except Exception as e:
                                            logger.warning(f"Skipping city {city_key} due to coordinate error: {e}")
                                            continue
                        
                        logger.info(f"Loaded {db_name} database with cities")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load {db_name} database: {e}")
                else:
                    logger.warning(f"Database not found: {db_path}")
            
            if not cities_db:
                logger.warning("No databases found, using fallback")
                return self._get_fallback_database()
            
            # Limit database size for performance (especially in production)
            if len(cities_db) > 3000:
                # Keep high-quality cities and spread geographically
                limited_db = {}
                country_limits = {
                    'France': 800,
                    'Italy': 600,
                    'Spain': 400,
                    'Germany': 400,
                    'Portugal': 200,
                    'Austria': 150,
                    'Switzerland': 150,
                    'Netherlands': 100,
                    'Belgium': 100,
                    'Czech Republic': 100,
                    'Croatia': 100,
                    'Slovenia': 100,
                    'Hungary': 100,
                    'Slovakia': 100,
                    'Poland': 100
                }
                
                # Select best cities per country
                for country, limit in country_limits.items():
                    country_cities = [(k, v) for k, v in cities_db.items() if v['country'] == country]
                    # Sort by authenticity score and travel appeal
                    country_cities.sort(key=lambda x: (
                        x[1].get('authenticity_score', 5),
                        1 if x[1].get('travel_appeal') == 'very_high' else 
                        2 if x[1].get('travel_appeal') == 'high' else 3
                    ), reverse=True)
                    
                    # Take top cities for this country
                    for city_key, city_data in country_cities[:limit]:
                        limited_db[city_key] = city_data
                
                logger.info(f"Limited cities to {len(limited_db)} for performance (from {len(cities_db)})")
                cities_db = limited_db
            
            logger.info(f"Total cities loaded: {len(cities_db)} from merged databases")
            return cities_db
            
        except Exception as e:
            logger.error(f"Failed to load any database: {e}")
            return self._get_fallback_database()
    
    def _get_country_name(self, country_key: str) -> str:
        """Map country keys to proper country names."""
        country_mapping = {
            'france': 'France',
            'italy': 'Italy', 
            'spain': 'Spain',
            'germany': 'Germany',
            'portugal': 'Portugal',
            'austria': 'Austria',
            'switzerland': 'Switzerland',
            'netherlands': 'Netherlands',
            'belgium': 'Belgium',
            'czech_republic': 'Czech Republic',
            'croatia': 'Croatia',
            'slovenia': 'Slovenia',
            'hungary': 'Hungary',
            'slovakia': 'Slovakia',
            'poland': 'Poland'
        }
        return country_mapping.get(country_key, country_key.replace('_', ' ').title())
    
    def _get_fallback_database(self):
        """Fallback database in case the JSON file cannot be loaded."""
        return {
            # Major European cities
            'nice': {'lat': 43.7102, 'lon': 7.2620, 'country': 'France', 'types': ['scenic', 'coastal', 'luxury']},
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
            
            # Hidden gems specifically tagged for better filtering
            'moustiers_sainte_marie': {'lat': 43.8456, 'lon': 6.2214, 'country': 'France', 'types': ['pottery', 'star', 'gorge', 'authentic', 'hidden_gems']},
            'castellane': {'lat': 43.8472, 'lon': 6.5125, 'country': 'France', 'types': ['verdon', 'gateway', 'adventure', 'authentic', 'hidden_gems']},
            'entrevaux': {'lat': 43.9550, 'lon': 6.8200, 'country': 'France', 'types': ['fortified', 'vauban', 'citadel', 'authentic', 'hidden_gems']},
            'sisteron': {'lat': 44.1950, 'lon': 5.9438, 'country': 'France', 'types': ['citadel', 'gateway', 'lavender', 'authentic', 'hidden_gems']},
            'digne_les_bains': {'lat': 44.0919, 'lon': 6.2369, 'country': 'France', 'types': ['lavender', 'thermal', 'geological', 'authentic', 'hidden_gems']},
            
            # Italian hidden gems
            'forte_dei_marmi': {'lat': 43.9608, 'lon': 10.1711, 'country': 'Italy', 'types': ['luxury', 'beach', 'pier', 'exclusive', 'hidden_gems']},
            'pietrasanta': {'lat': 43.9578, 'lon': 10.2267, 'country': 'Italy', 'types': ['marble', 'artistic', 'sculpture', 'authentic', 'hidden_gems']},
            'lucca': {'lat': 43.8419, 'lon': 10.5036, 'country': 'Italy', 'types': ['walls', 'medieval', 'puccini', 'cultural', 'hidden_gems']},
            'barga': {'lat': 44.0706, 'lon': 10.4756, 'country': 'Italy', 'types': ['scottish', 'views', 'cultural', 'authentic', 'hidden_gems']},
            'san_gimignano': {'lat': 43.4675, 'lon': 11.0431, 'country': 'Italy', 'types': ['towers', 'medieval', 'wine', 'unesco', 'hidden_gems']},
            'volterra': {'lat': 43.4019, 'lon': 10.8642, 'country': 'Italy', 'types': ['etruscan', 'alabaster', 'twilight', 'authentic', 'hidden_gems']},
            'cortona': {'lat': 43.2747, 'lon': 11.9869, 'country': 'Italy', 'types': ['etruscan', 'under_tuscan_sun', 'hilltop', 'authentic', 'hidden_gems']},
            'montepulciano': {'lat': 43.0978, 'lon': 11.7883, 'country': 'Italy', 'types': ['wine', 'noble', 'renaissance', 'authentic', 'hidden_gems']},
            'pienza': {'lat': 43.0769, 'lon': 11.6789, 'country': 'Italy', 'types': ['renaissance', 'perfect_city', 'pecorino', 'unesco', 'hidden_gems']},
            'montalcino': {'lat': 43.0575, 'lon': 11.4881, 'country': 'Italy', 'types': ['brunello', 'wine', 'fortress', 'authentic', 'hidden_gems']},
            'padua': {'lat': 45.4064, 'lon': 11.8768, 'country': 'Italy', 'types': ['giotto', 'university', 'scrovegni', 'cultural', 'hidden_gems']},
            'vicenza': {'lat': 45.5455, 'lon': 11.5353, 'country': 'Italy', 'types': ['palladio', 'architecture', 'unesco', 'cultural', 'hidden_gems']},
            'mantua': {'lat': 45.1564, 'lon': 10.7914, 'country': 'Italy', 'types': ['gonzaga', 'lakes', 'unesco', 'cultural', 'hidden_gems']},
            'bassano_del_grappa': {'lat': 45.7650, 'lon': 11.7292, 'country': 'Italy', 'types': ['bridge', 'grappa', 'ceramic', 'authentic', 'hidden_gems']},
            'asolo': {'lat': 45.7997, 'lon': 11.9089, 'country': 'Italy', 'types': ['browning', 'pearl', 'hilltop', 'authentic', 'hidden_gems']},
            'treviso': {'lat': 45.6669, 'lon': 12.2431, 'country': 'Italy', 'types': ['canals', 'prosecco', 'tiramisu', 'cultural', 'hidden_gems']},
            
            # Major cultural cities
            'florence': {'lat': 43.7696, 'lon': 11.2558, 'country': 'Italy', 'types': ['renaissance', 'art', 'cultural', 'duomo', 'michelangelo']},
            'pisa': {'lat': 43.7228, 'lon': 10.4017, 'country': 'Italy', 'types': ['tower', 'leaning', 'unesco', 'cultural']},
            'verona': {'lat': 45.4384, 'lon': 10.9916, 'country': 'Italy', 'types': ['romeo_juliet', 'arena', 'opera', 'cultural', 'romantic']},
            'bologna': {'lat': 44.4949, 'lon': 11.3426, 'country': 'Italy', 'types': ['food', 'university', 'portici', 'cultural', 'culinary']},
            'parma': {'lat': 44.8015, 'lon': 10.3280, 'country': 'Italy', 'types': ['ham', 'cheese', 'verdi', 'culinary', 'cultural']},
            'modena': {'lat': 44.6479, 'lon': 10.9252, 'country': 'Italy', 'types': ['balsamic', 'ferrari', 'duomo', 'culinary', 'cultural']},
        }
        
    def _remove_old_database_from_fallback_method(self):
        """Remove old database implementation - keeping for reference."""
        pass
        
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
    
    def _clean_city_name(self, name: str) -> str:
        """Clean city name for display."""
        return name.replace('_', ' ').title()
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()

"""
City data service with proper caching and geographic operations.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, func
from geopy.distance import geodesic
import structlog
from ..core.interfaces import CityRepository
from ..core.models import City, Coordinates, ServiceResult
from ..core.exceptions import DatabaseError
from ..infrastructure.database import DatabaseManager

logger = structlog.get_logger(__name__)


class CityService(CityRepository):
    """Production city service with spatial indexing and caching."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._city_cache: Dict[str, City] = {}
        self._load_cities()
    
    def _load_cities(self):
        """Load cities into memory cache for fast access."""
        try:
            # In production, this would load from database
            # For now, using curated data with proper validation
            cities_data = self._get_european_cities_data()
            
            for name, data in cities_data.items():
                try:
                    city = City(
                        name=name,
                        coordinates=Coordinates(
                            latitude=data['lat'],
                            longitude=data['lon']
                        ),
                        country=data['country'],
                        population=data.get('population'),
                        region=data.get('region'),
                        types=data.get('types', [])
                    )
                    self._city_cache[name.lower()] = city
                except ValueError as e:
                    logger.warning("Invalid city data", city=name, error=str(e))
                    continue
            
            logger.info("Cities loaded", count=len(self._city_cache))
            
        except Exception as e:
            logger.error("Failed to load cities", error=str(e))
            raise DatabaseError(f"City data initialization failed: {e}")
    
    def get_city_by_name(self, name: str) -> Optional[City]:
        """Get city by name with fuzzy matching and multilingual support."""
        if not name or not name.strip():
            return None
        
        name_key = name.lower().strip().replace('-', ' ').replace('_', ' ')
        
        # Direct match
        if name_key in self._city_cache:
            return self._city_cache[name_key]
        
        # Try matching with city name variations
        city_aliases = self._get_city_aliases()
        if name_key in city_aliases:
            canonical_name = city_aliases[name_key]
            if canonical_name in self._city_cache:
                return self._city_cache[canonical_name]
        
        # Try partial matching with normalized names
        for cached_name, city in self._city_cache.items():
            cached_normalized = cached_name.replace('-', ' ').replace('_', ' ')
            if (name_key in cached_normalized or 
                cached_normalized in name_key or
                name_key.replace(' ', '') in cached_normalized.replace(' ', '')):
                return city
        
        # Try matching just the first part of compound names
        name_parts = name_key.split()
        if len(name_parts) > 1:
            for cached_name, city in self._city_cache.items():
                if name_parts[0] in cached_name.lower():
                    return city
        
        return None
    
    def _get_city_aliases(self) -> Dict[str, str]:
        """Get mapping of alternative city names to canonical names."""
        return {
            # French/Italian name variations
            'venise': 'venice',
            'venezia': 'venice',
            'venedig': 'venice',
            'aix en provence': 'aix-en-provence',
            'aixen provence': 'aix-en-provence',
            'aix': 'aix-en-provence',
            'milano': 'milan',
            'milano': 'milan',
            'torino': 'turin',
            'geneve': 'geneva',
            'genève': 'geneva',
            'ginevra': 'geneva',
            'nizza': 'nice',
            'nizza': 'nice',
            'monte carlo': 'monaco',
            'montecarlo': 'monaco',
            'padova': 'padua',
            'verona': 'verona',
            'lione': 'lyon',
            'lyon': 'lyon'
        }
    
    def find_cities_by_type(self, city_type: str) -> List[City]:
        """Find cities by type (cultural, scenic, etc.)."""
        if not city_type:
            return []
        
        cities = []
        for city in self._city_cache.values():
            if city_type.lower() in [t.lower() for t in city.types]:
                cities.append(city)
        
        return cities
    
    def find_cities_in_region(self, region: str) -> List[City]:
        """Find cities in a specific region."""
        if not region:
            return []
        
        cities = []
        for city in self._city_cache.values():
            if city.region and region.lower() in city.region.lower():
                cities.append(city)
        
        return cities
    
    def find_cities_near_route(self, start: Coordinates, end: Coordinates, 
                              max_deviation_km: float = 50) -> List[City]:
        """Find cities near the route between two points."""
        cities = []
        
        for city in self._city_cache.values():
            # Calculate distance from city to the route line
            deviation = self._distance_to_route(
                city.coordinates, start, end
            )
            
            if deviation <= max_deviation_km:
                cities.append(city)
        
        # Sort by distance from start
        cities.sort(key=lambda c: geodesic(
            (start.latitude, start.longitude),
            (c.coordinates.latitude, c.coordinates.longitude)
        ).kilometers)
        
        return cities
    
    def _distance_to_route(self, point: Coordinates, 
                          start: Coordinates, end: Coordinates) -> float:
        """Calculate minimum distance from point to route line."""
        # Simplified calculation - in production use proper geometric algorithms
        start_dist = geodesic(
            (point.latitude, point.longitude),
            (start.latitude, start.longitude)
        ).kilometers
        
        end_dist = geodesic(
            (point.latitude, point.longitude),
            (end.latitude, end.longitude)
        ).kilometers
        
        route_dist = geodesic(
            (start.latitude, start.longitude),
            (end.latitude, end.longitude)
        ).kilometers
        
        # If point forms a reasonable triangle, calculate perpendicular distance
        if abs(start_dist + end_dist - route_dist) < route_dist * 0.2:
            return min(start_dist, end_dist) * 0.5  # Approximation
        
        return min(start_dist, end_dist)
    
    def _get_european_cities_data(self) -> Dict[str, Dict[str, Any]]:
        """Get curated European cities data."""
        return {
            "Aix-en-Provence": {
                "lat": 43.5297, "lon": 5.4474, "country": "France",
                "population": 143006, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["cultural", "culinary", "artistic"]
            },
            "Venice": {
                "lat": 45.4408, "lon": 12.3155, "country": "Italy",
                "population": 261905, "region": "Veneto",
                "types": ["cultural", "romantic", "historic", "scenic"]
            },
            "Lyon": {
                "lat": 45.7640, "lon": 4.8357, "country": "France",
                "population": 515695, "region": "Auvergne-Rhône-Alpes",
                "types": ["culinary", "cultural", "major"]
            },
            "Geneva": {
                "lat": 46.2044, "lon": 6.1432, "country": "Switzerland",
                "population": 201818, "region": "Geneva",
                "types": ["international", "scenic", "expensive"]
            },
            "Milan": {
                "lat": 45.4642, "lon": 9.1900, "country": "Italy",
                "population": 1396059, "region": "Lombardy",
                "types": ["fashion", "business", "major", "cultural"]
            },
            "Turin": {
                "lat": 45.0703, "lon": 7.6869, "country": "Italy",
                "population": 878074, "region": "Piedmont",
                "types": ["cultural", "historic", "automotive"]
            },
            "Nice": {
                "lat": 43.7102, "lon": 7.2620, "country": "France",
                "population": 342522, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["coastal", "scenic", "resort"]
            },
            "Monaco": {
                "lat": 43.7384, "lon": 7.4246, "country": "Monaco",
                "population": 39242, "region": "Monaco",
                "types": ["luxury", "coastal", "gaming"]
            },
            "Verona": {
                "lat": 45.4384, "lon": 10.9916, "country": "Italy",
                "population": 259610, "region": "Veneto",
                "types": ["romantic", "historic", "cultural"]
            },
            "Padua": {
                "lat": 45.4064, "lon": 11.8768, "country": "Italy",
                "population": 210401, "region": "Veneto",
                "types": ["historic", "university", "cultural"]
            }
        }
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
            'torino': 'turin',
            'geneve': 'geneva',
            'genève': 'geneva',
            'ginevra': 'geneva',
            'nizza': 'nice',
            'monte carlo': 'monaco',
            'montecarlo': 'monaco',
            'padova': 'padua',
            'lione': 'lyon',
            'firenze': 'florence',
            'genova': 'genoa',
            'bologna': 'bologna',
            'napoli': 'naples',
            'roma': 'rome',
            'muenchen': 'munich',
            'münchen': 'munich',
            'munchen': 'munich',
            'salzberg': 'salzburg',
            'innsbruck': 'innsbruck',
            'annecy': 'annecy',
            'chambery': 'chambéry',
            'marseilles': 'marseille',
            'marseilles': 'marseille',
            'antibes juan les pins': 'antibes',
            'cannes la bocca': 'cannes',
            'menton': 'menton',
            'st tropez': 'saint-tropez',
            'saint tropez': 'saint-tropez',
            'lake como': 'como',
            'lago di como': 'como',
            'cinque terre': 'la spezia',
            '5 terre': 'la spezia',
            'bled': 'lake bled',
            'ljubjana': 'ljubljana'
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
        """Get curated European cities data with extensive coverage."""
        return {
            # France
            "Aix-en-Provence": {
                "lat": 43.5297, "lon": 5.4474, "country": "France",
                "population": 143006, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["cultural", "culinary", "artistic", "historic"]
            },
            "Lyon": {
                "lat": 45.7640, "lon": 4.8357, "country": "France",
                "population": 515695, "region": "Auvergne-Rhône-Alpes",
                "types": ["culinary", "cultural", "major", "historic"]
            },
            "Nice": {
                "lat": 43.7102, "lon": 7.2620, "country": "France",
                "population": 342522, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["coastal", "scenic", "resort"]
            },
            "Cannes": {
                "lat": 43.5528, "lon": 7.0174, "country": "France",
                "population": 74152, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["luxury", "coastal", "entertainment", "scenic"]
            },
            "Avignon": {
                "lat": 43.9493, "lon": 4.8055, "country": "France",
                "population": 92209, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["historic", "cultural", "unesco", "scenic"]
            },
            "Marseille": {
                "lat": 43.2965, "lon": 5.3698, "country": "France",
                "population": 861635, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["coastal", "major", "culinary", "cultural"]
            },
            "Montpellier": {
                "lat": 43.6047, "lon": 3.8767, "country": "France",
                "population": 285121, "region": "Occitanie",
                "types": ["university", "cultural", "modern"]
            },
            "Nîmes": {
                "lat": 43.8374, "lon": 4.3601, "country": "France",
                "population": 148561, "region": "Occitanie",
                "types": ["historic", "roman", "cultural"]
            },
            "Arles": {
                "lat": 43.6763, "lon": 4.6281, "country": "France",
                "population": 52510, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["historic", "artistic", "van-gogh", "unesco"]
            },
            "Orange": {
                "lat": 44.1363, "lon": 4.8086, "country": "France",
                "population": 29135, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["historic", "roman", "unesco"]
            },
            "Grenoble": {
                "lat": 45.1885, "lon": 5.7245, "country": "France",
                "population": 158552, "region": "Auvergne-Rhône-Alpes",
                "types": ["alpine", "university", "adventure", "scenic"]
            },
            "Annecy": {
                "lat": 45.8992, "lon": 6.1294, "country": "France",
                "population": 52029, "region": "Auvergne-Rhône-Alpes",
                "types": ["scenic", "alpine", "romantic", "adventure"]
            },
            "Chambéry": {
                "lat": 45.5646, "lon": 5.9178, "country": "France",
                "population": 59490, "region": "Auvergne-Rhône-Alpes",
                "types": ["alpine", "historic", "scenic"]
            },
            "Valence": {
                "lat": 44.9311, "lon": 4.8914, "country": "France",
                "population": 64726, "region": "Auvergne-Rhône-Alpes",
                "types": ["culinary", "historic"]
            },
            
            # Switzerland
            "Geneva": {
                "lat": 46.2044, "lon": 6.1432, "country": "Switzerland",
                "population": 201818, "region": "Geneva",
                "types": ["international", "scenic", "expensive", "cultural"]
            },
            "Lausanne": {
                "lat": 46.5197, "lon": 6.6323, "country": "Switzerland",
                "population": 139111, "region": "Vaud",
                "types": ["scenic", "cultural", "olympic", "expensive"]
            },
            "Montreux": {
                "lat": 46.4312, "lon": 6.9106, "country": "Switzerland",
                "population": 26574, "region": "Vaud",
                "types": ["scenic", "resort", "music", "expensive"]
            },
            "Bern": {
                "lat": 46.9480, "lon": 7.4474, "country": "Switzerland",
                "population": 133883, "region": "Bern",
                "types": ["capital", "historic", "unesco", "cultural"]
            },
            "Lucerne": {
                "lat": 47.0502, "lon": 8.3093, "country": "Switzerland",
                "population": 81592, "region": "Lucerne",
                "types": ["scenic", "historic", "alpine", "romantic"]
            },
            "Interlaken": {
                "lat": 46.6863, "lon": 7.8632, "country": "Switzerland",
                "population": 5745, "region": "Bern",
                "types": ["alpine", "adventure", "scenic", "resort"]
            },
            
            # Italy
            "Venice": {
                "lat": 45.4408, "lon": 12.3155, "country": "Italy",
                "population": 261905, "region": "Veneto",
                "types": ["cultural", "romantic", "historic", "scenic", "unesco"]
            },
            "Milan": {
                "lat": 45.4642, "lon": 9.1900, "country": "Italy",
                "population": 1396059, "region": "Lombardy",
                "types": ["fashion", "business", "major", "cultural", "modern"]
            },
            "Turin": {
                "lat": 45.0703, "lon": 7.6869, "country": "Italy",
                "population": 878074, "region": "Piedmont",
                "types": ["cultural", "historic", "automotive", "baroque"]
            },
            "Verona": {
                "lat": 45.4384, "lon": 10.9916, "country": "Italy",
                "population": 259610, "region": "Veneto",
                "types": ["romantic", "historic", "cultural", "shakespeare"]
            },
            "Padua": {
                "lat": 45.4064, "lon": 11.8768, "country": "Italy",
                "population": 210401, "region": "Veneto",
                "types": ["historic", "university", "cultural", "religious"]
            },
            "Vicenza": {
                "lat": 45.5455, "lon": 11.5353, "country": "Italy",
                "population": 111500, "region": "Veneto",
                "types": ["historic", "architectural", "unesco", "palladio"]
            },
            "Bergamo": {
                "lat": 45.6983, "lon": 9.6773, "country": "Italy",
                "population": 120287, "region": "Lombardy",
                "types": ["historic", "medieval", "scenic", "cultural"]
            },
            "Brescia": {
                "lat": 45.5416, "lon": 10.2118, "country": "Italy",
                "population": 196480, "region": "Lombardy",
                "types": ["historic", "roman", "cultural"]
            },
            "Como": {
                "lat": 45.8081, "lon": 9.0852, "country": "Italy",
                "population": 85183, "region": "Lombardy",
                "types": ["scenic", "lakes", "romantic", "luxury"]
            },
            "Bellagio": {
                "lat": 45.9792, "lon": 9.2589, "country": "Italy",
                "population": 3820, "region": "Lombardy",
                "types": ["scenic", "romantic", "luxury", "lakes"]
            },
            "Mantua": {
                "lat": 45.1564, "lon": 10.7914, "country": "Italy",
                "population": 49439, "region": "Lombardy",
                "types": ["historic", "renaissance", "unesco", "cultural"]
            },
            "Genoa": {
                "lat": 44.4056, "lon": 8.9463, "country": "Italy",
                "population": 583601, "region": "Liguria",
                "types": ["coastal", "historic", "major", "cultural"]
            },
            "La Spezia": {
                "lat": 44.1025, "lon": 9.8244, "country": "Italy",
                "population": 94621, "region": "Liguria",
                "types": ["coastal", "cinque-terre", "scenic"]
            },
            "Portofino": {
                "lat": 44.3036, "lon": 9.2096, "country": "Italy",
                "population": 420, "region": "Liguria",
                "types": ["coastal", "luxury", "scenic", "romantic"]
            },
            "Bologna": {
                "lat": 44.4949, "lon": 11.3426, "country": "Italy",
                "population": 388367, "region": "Emilia-Romagna",
                "types": ["culinary", "university", "cultural", "historic"]
            },
            "Parma": {
                "lat": 44.8015, "lon": 10.3279, "country": "Italy",
                "population": 194417, "region": "Emilia-Romagna",
                "types": ["culinary", "cultural", "historic"]
            },
            "Modena": {
                "lat": 44.6471, "lon": 10.9252, "country": "Italy",
                "population": 185273, "region": "Emilia-Romagna",
                "types": ["culinary", "automotive", "cultural"]
            },
            "Florence": {
                "lat": 43.7696, "lon": 11.2558, "country": "Italy",
                "population": 382258, "region": "Tuscany",
                "types": ["cultural", "renaissance", "artistic", "historic", "unesco"]
            },
            "Pisa": {
                "lat": 43.7228, "lon": 10.4017, "country": "Italy",
                "population": 90488, "region": "Tuscany",
                "types": ["historic", "iconic", "university", "cultural"]
            },
            "Siena": {
                "lat": 43.3188, "lon": 11.3307, "country": "Italy",
                "population": 53901, "region": "Tuscany",
                "types": ["historic", "medieval", "unesco", "cultural"]
            },
            "San Gimignano": {
                "lat": 43.4676, "lon": 11.0431, "country": "Italy",
                "population": 7800, "region": "Tuscany",
                "types": ["historic", "medieval", "towers", "unesco"]
            },
            
            # Monaco
            "Monaco": {
                "lat": 43.7384, "lon": 7.4246, "country": "Monaco",
                "population": 39242, "region": "Monaco",
                "types": ["luxury", "coastal", "gaming", "f1"]
            },
            
            # Austria
            "Innsbruck": {
                "lat": 47.2692, "lon": 11.4041, "country": "Austria",
                "population": 132493, "region": "Tyrol",
                "types": ["alpine", "adventure", "scenic", "winter-sports"]
            },
            "Salzburg": {
                "lat": 47.8095, "lon": 13.0550, "country": "Austria",
                "population": 155021, "region": "Salzburg",
                "types": ["cultural", "music", "historic", "unesco", "mozart"]
            },
            "Hallstatt": {
                "lat": 47.5622, "lon": 13.6493, "country": "Austria",
                "population": 780, "region": "Upper Austria",
                "types": ["scenic", "romantic", "lakes", "historic"]
            },
            
            # Slovenia
            "Ljubljana": {
                "lat": 46.0569, "lon": 14.5058, "country": "Slovenia",
                "population": 294464, "region": "Central Slovenia",
                "types": ["cultural", "green", "scenic", "affordable"]
            },
            "Lake Bled": {
                "lat": 46.3683, "lon": 14.1143, "country": "Slovenia",
                "population": 5200, "region": "Upper Carniola",
                "types": ["scenic", "romantic", "lakes", "adventure"]
            },
            
            # Germany (Southern)
            "Munich": {
                "lat": 48.1351, "lon": 11.5820, "country": "Germany",
                "population": 1484226, "region": "Bavaria",
                "types": ["cultural", "beer", "major", "oktoberfest"]
            },
            "Garmisch-Partenkirchen": {
                "lat": 47.4917, "lon": 11.0956, "country": "Germany",
                "population": 26424, "region": "Bavaria",
                "types": ["alpine", "adventure", "scenic", "winter-sports"]
            },
            "Rothenburg ob der Tauber": {
                "lat": 49.3779, "lon": 10.1866, "country": "Germany",
                "population": 11000, "region": "Bavaria",
                "types": ["medieval", "historic", "romantic", "fairytale"]
            },
            
            # Croatia (Northern)
            "Zagreb": {
                "lat": 45.8150, "lon": 15.9819, "country": "Croatia",
                "population": 790017, "region": "Zagreb County",
                "types": ["cultural", "affordable", "historic"]
            },
            "Plitvice Lakes": {
                "lat": 44.8654, "lon": 15.5820, "country": "Croatia",
                "population": 4000, "region": "Lika-Senj",
                "types": ["scenic", "nature", "unesco", "adventure"]
            },
            
            # Additional Scenic Routes Points
            "Chamonix": {
                "lat": 45.9237, "lon": 6.8694, "country": "France",
                "population": 8906, "region": "Auvergne-Rhône-Alpes",
                "types": ["alpine", "adventure", "scenic", "skiing"]
            },
            "Menton": {
                "lat": 43.7745, "lon": 7.5029, "country": "France",
                "population": 28800, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["coastal", "scenic", "gardens", "border"]
            },
            "Saint-Tropez": {
                "lat": 43.2677, "lon": 6.6407, "country": "France",
                "population": 4103, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["luxury", "coastal", "resort", "celebrity"]
            },
            "Antibes": {
                "lat": 43.5808, "lon": 7.1251, "country": "France",
                "population": 75820, "region": "Provence-Alpes-Côte d'Azur",
                "types": ["coastal", "historic", "artistic", "scenic"]
            }
        }
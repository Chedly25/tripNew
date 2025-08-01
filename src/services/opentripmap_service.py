"""
OpenTripMap API integration for comprehensive city and attraction data.
Provides tourist attractions, points of interest, and geographical data for European cities.
"""
import os
import asyncio
import aiohttp
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import structlog
from ..core.models import Coordinates

logger = structlog.get_logger(__name__)


class OpenTripMapService:
    """Service for accessing OpenTripMap data for cities and attractions."""
    
    def __init__(self):
        self.api_key = os.getenv('OPENTRIPMAP_API_KEY')
        self.base_url = "https://api.opentripmap.com/0.1/en"
        self.session = None
        
        # Country bounding boxes for comprehensive data collection
        self.country_bounds = {
            'france': {
                'name': 'France',
                'code': 'FR',
                'bounds': {'lon_min': -5.5, 'lat_min': 41.3, 'lon_max': 9.6, 'lat_max': 51.1}
            },
            'italy': {
                'name': 'Italy',
                'code': 'IT',
                'bounds': {'lon_min': 6.6, 'lat_min': 35.2, 'lon_max': 18.8, 'lat_max': 47.1}
            },
            'spain': {
                'name': 'Spain',
                'code': 'ES',
                'bounds': {'lon_min': -18.2, 'lat_min': 27.6, 'lon_max': 4.3, 'lat_max': 43.8}
            }
        }
        
        if not self.api_key:
            logger.warning("OpenTripMap API key not configured - service will be limited")
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_city_info(self, city_name: str, country_code: str = None) -> Optional[Dict]:
        """Get basic information about a city."""
        if not self.api_key:
            return self._get_fallback_city_info(city_name, country_code)
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/places/geoname"
            params = {
                'name': city_name,
                'apikey': self.api_key
            }
            
            if country_code:
                params['country'] = country_code
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'OK':
                        return {
                            'name': data.get('name'),
                            'country': data.get('country'),
                            'coordinates': {
                                'latitude': data.get('lat'),
                                'longitude': data.get('lon')
                            },
                            'population': data.get('population'),
                            'timezone': data.get('timezone'),
                            'source': 'opentripmap'
                        }
                
                logger.warning(f"OpenTripMap city lookup failed for {city_name}: {response.status}")
                return self._get_fallback_city_info(city_name, country_code)
                
        except Exception as e:
            logger.error(f"OpenTripMap city lookup error for {city_name}: {e}")
            return self._get_fallback_city_info(city_name, country_code)
    
    async def get_cities_in_country(self, country: str, limit: int = 1000) -> List[Dict]:
        """Get comprehensive list of cities and towns in a country."""
        if not self.api_key:
            return self._get_fallback_cities(country)
        
        country_lower = country.lower()
        if country_lower not in self.country_bounds:
            logger.warning(f"Country {country} not supported")
            return []
        
        country_info = self.country_bounds[country_lower]
        
        # Use a combination of approaches for better city coverage
        cities = []
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Approach 1: Get major cities by searching known city names
            major_cities = self._get_fallback_cities(country)
            for city in major_cities:
                city_info = await self.get_city_info(city['name'], country_info['code'])
                if city_info and city_info.get('source') == 'opentripmap':
                    cities.append(city_info)
                    await asyncio.sleep(0.1)  # Rate limiting
            
            logger.info(f"Found {len(cities)} verified cities in {country}")
            
            # If we didn't get many cities, supplement with fallback data
            if len(cities) < 5:
                fallback_cities = self._get_fallback_cities(country)
                # Add fallback cities that weren't already found
                existing_names = {city['name'].lower() for city in cities}
                for fallback_city in fallback_cities:
                    if fallback_city['name'].lower() not in existing_names:
                        cities.append(fallback_city)
            
            return cities
                
        except Exception as e:
            logger.error(f"OpenTripMap cities lookup error for {country}: {e}")
            return self._get_fallback_cities(country)
    
    async def get_city_attractions(self, coordinates: Coordinates, radius_km: int = 10, 
                                 limit: int = 50, kinds: str = None) -> List[Dict]:
        """Get attractions and points of interest near a city."""
        if not self.api_key:
            return self._get_fallback_attractions(coordinates, limit)
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/places/radius"
            params = {
                'radius': radius_km * 1000,  # Convert km to meters
                'lon': coordinates.longitude,
                'lat': coordinates.latitude,
                'limit': limit,
                'format': 'json',
                'apikey': self.api_key
            }
            
            if kinds:
                params['kinds'] = kinds
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        attractions = []
                        for attraction in data:
                            attraction_data = {
                                'xid': attraction.get('xid'),
                                'name': attraction.get('name', ''),
                                'kinds': attraction.get('kinds', '').split(','),
                                'rating': attraction.get('rate', 0),
                                'distance': attraction.get('dist', 0),
                                'coordinates': {
                                    'latitude': attraction.get('point', {}).get('lat'),
                                    'longitude': attraction.get('point', {}).get('lon')
                                },
                                'wikidata': attraction.get('wikidata'),
                                'source': 'opentripmap'
                            }
                            attractions.append(attraction_data)
                        
                        return attractions
                
                logger.warning(f"OpenTripMap attractions request failed: {response.status}")
                return self._get_fallback_attractions(coordinates, limit)
                
        except Exception as e:
            logger.error(f"OpenTripMap attractions lookup error: {e}")
            return self._get_fallback_attractions(coordinates, limit)
    
    async def get_attraction_details(self, xid: str) -> Optional[Dict]:
        """Get detailed information about a specific attraction."""
        if not self.api_key:
            return None
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/places/xid/{xid}"
            params = {'apikey': self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'xid': data.get('xid'),
                        'name': data.get('name', ''),
                        'address': data.get('address', {}).get('country', ''),
                        'rate': data.get('rate', 0),
                        'kinds': data.get('kinds', '').split(','),
                        'info': data.get('info', {}),
                        'wikipedia': data.get('wikipedia'),
                        'image': data.get('image'),
                        'preview': data.get('preview', {}),
                        'coordinates': {
                            'latitude': data.get('point', {}).get('lat'),
                            'longitude': data.get('point', {}).get('lon')
                        },
                        'source': 'opentripmap'
                    }
                
                logger.warning(f"OpenTripMap attraction details failed for {xid}: {response.status}")
                return None
                
        except Exception as e:
            logger.error(f"OpenTripMap attraction details error for {xid}: {e}")
            return None
    
    async def search_cities_comprehensive(self) -> Dict[str, List[Dict]]:
        """Search for comprehensive city data across France, Italy, and Spain."""
        if not self.api_key:
            return self._get_fallback_comprehensive_cities()
        
        results = {}
        
        for country in ['france', 'italy', 'spain']:
            logger.info(f"Starting comprehensive city search for {country}")
            cities = await self.get_cities_in_country(country, limit=2000)
            results[country] = cities
            
            # Add a small delay to respect API rate limits
            await asyncio.sleep(1)
        
        return results
    
    def _get_fallback_city_info(self, city_name: str, country_code: str = None) -> Dict:
        """Fallback city data when API is unavailable."""
        return {
            'name': city_name,
            'country': country_code or 'Unknown',
            'coordinates': {'latitude': 0.0, 'longitude': 0.0},
            'population': 0,
            'timezone': 'Europe/Paris',
            'source': 'fallback'
        }
    
    def _get_fallback_cities(self, country: str) -> List[Dict]:
        """Fallback cities data when API is unavailable."""
        fallback_cities = {
            'france': [
                # Major cities
                {'name': 'Paris', 'coordinates': {'latitude': 48.8566, 'longitude': 2.3522}},
                {'name': 'Lyon', 'coordinates': {'latitude': 45.7640, 'longitude': 4.8357}},
                {'name': 'Marseille', 'coordinates': {'latitude': 43.2965, 'longitude': 5.3698}},
                {'name': 'Nice', 'coordinates': {'latitude': 43.7102, 'longitude': 7.2620}},
                {'name': 'Toulouse', 'coordinates': {'latitude': 43.6047, 'longitude': 1.4442}},
                {'name': 'Strasbourg', 'coordinates': {'latitude': 48.5734, 'longitude': 7.7521}},
                {'name': 'Bordeaux', 'coordinates': {'latitude': 44.8378, 'longitude': -0.5792}},
                {'name': 'Nantes', 'coordinates': {'latitude': 47.2184, 'longitude': -1.5536}},
                {'name': 'Lille', 'coordinates': {'latitude': 50.6292, 'longitude': 3.0573}},
                {'name': 'Rennes', 'coordinates': {'latitude': 48.1173, 'longitude': -1.6778}},
                # Additional major cities
                {'name': 'Montpellier', 'coordinates': {'latitude': 43.6109, 'longitude': 3.8763}},
                {'name': 'Saint-Étienne', 'coordinates': {'latitude': 45.4397, 'longitude': 4.3872}},
                {'name': 'Le Havre', 'coordinates': {'latitude': 49.4944, 'longitude': 0.1079}},
                {'name': 'Grenoble', 'coordinates': {'latitude': 45.1885, 'longitude': 5.7245}},
                {'name': 'Dijon', 'coordinates': {'latitude': 47.3220, 'longitude': 5.0415}},
                {'name': 'Angers', 'coordinates': {'latitude': 47.4784, 'longitude': -0.5632}},
                {'name': 'Nîmes', 'coordinates': {'latitude': 43.8367, 'longitude': 4.3601}},
                {'name': 'Villeurbanne', 'coordinates': {'latitude': 45.7640, 'longitude': 4.8796}},
                {'name': 'Clermont-Ferrand', 'coordinates': {'latitude': 45.7797, 'longitude': 3.0863}},
                {'name': 'Le Mans', 'coordinates': {'latitude': 48.0077, 'longitude': 0.1996}},
                # Smaller cities and towns
                {'name': 'Aix-en-Provence', 'coordinates': {'latitude': 43.5297, 'longitude': 5.4474}},
                {'name': 'Tours', 'coordinates': {'latitude': 47.3941, 'longitude': 0.6848}},
                {'name': 'Limoges', 'coordinates': {'latitude': 45.8336, 'longitude': 1.2611}},
                {'name': 'Orléans', 'coordinates': {'latitude': 47.9029, 'longitude': 1.9039}},
                {'name': 'Mulhouse', 'coordinates': {'latitude': 47.7508, 'longitude': 7.3359}},
                {'name': 'Caen', 'coordinates': {'latitude': 49.1829, 'longitude': -0.3707}},
                {'name': 'Brest', 'coordinates': {'latitude': 48.3905, 'longitude': -4.4860}},
                {'name': 'Reims', 'coordinates': {'latitude': 49.2583, 'longitude': 4.0317}},
                {'name': 'Nancy', 'coordinates': {'latitude': 48.6921, 'longitude': 6.1844}},
                {'name': 'Avignon', 'coordinates': {'latitude': 43.9509, 'longitude': 4.8059}},
            ],
            'italy': [
                # Major cities
                {'name': 'Rome', 'coordinates': {'latitude': 41.9028, 'longitude': 12.4964}},
                {'name': 'Milan', 'coordinates': {'latitude': 45.4642, 'longitude': 9.1900}},
                {'name': 'Naples', 'coordinates': {'latitude': 40.8518, 'longitude': 14.2681}},
                {'name': 'Turin', 'coordinates': {'latitude': 45.0703, 'longitude': 7.6869}},
                {'name': 'Florence', 'coordinates': {'latitude': 43.7696, 'longitude': 11.2558}},
                {'name': 'Venice', 'coordinates': {'latitude': 45.4408, 'longitude': 12.3155}},
                {'name': 'Bologna', 'coordinates': {'latitude': 44.4949, 'longitude': 11.3426}},
                {'name': 'Genoa', 'coordinates': {'latitude': 44.4056, 'longitude': 8.9463}},
                {'name': 'Palermo', 'coordinates': {'latitude': 38.1157, 'longitude': 13.3615}},
                {'name': 'Bari', 'coordinates': {'latitude': 41.1171, 'longitude': 16.8719}},
                # Additional major cities
                {'name': 'Catania', 'coordinates': {'latitude': 37.5079, 'longitude': 15.0830}},
                {'name': 'Verona', 'coordinates': {'latitude': 45.4384, 'longitude': 10.9916}},
                {'name': 'Messina', 'coordinates': {'latitude': 38.1938, 'longitude': 15.5540}},
                {'name': 'Padua', 'coordinates': {'latitude': 45.4064, 'longitude': 11.8768}},
                {'name': 'Trieste', 'coordinates': {'latitude': 45.6495, 'longitude': 13.7768}},
                {'name': 'Taranto', 'coordinates': {'latitude': 40.4668, 'longitude': 17.2725}},
                {'name': 'Brescia', 'coordinates': {'latitude': 45.5416, 'longitude': 10.2118}},
                {'name': 'Reggio Calabria', 'coordinates': {'latitude': 38.1113, 'longitude': 15.6619}},
                {'name': 'Modena', 'coordinates': {'latitude': 44.6472, 'longitude': 10.9250}},
                {'name': 'Prato', 'coordinates': {'latitude': 43.8777, 'longitude': 11.1025}},
                # Smaller cities and towns
                {'name': 'Parma', 'coordinates': {'latitude': 44.8015, 'longitude': 10.3279}},
                {'name': 'Reggio Emilia', 'coordinates': {'latitude': 44.6966, 'longitude': 10.6309}},
                {'name': 'Perugia', 'coordinates': {'latitude': 43.1122, 'longitude': 12.3888}},
                {'name': 'Livorno', 'coordinates': {'latitude': 43.5482, 'longitude': 10.3116}},
                {'name': 'Ravenna', 'coordinates': {'latitude': 44.4184, 'longitude': 12.2035}},
                {'name': 'Cagliari', 'coordinates': {'latitude': 39.2238, 'longitude': 9.1217}},
                {'name': 'Foggia', 'coordinates': {'latitude': 41.4621, 'longitude': 15.5444}},
                {'name': 'Rimini', 'coordinates': {'latitude': 44.0678, 'longitude': 12.5695}},
                {'name': 'Salerno', 'coordinates': {'latitude': 40.6824, 'longitude': 14.7681}},
                {'name': 'Ferrara', 'coordinates': {'latitude': 44.8381, 'longitude': 11.6198}},
                {'name': 'Sassari', 'coordinates': {'latitude': 40.7259, 'longitude': 8.5590}},
                {'name': 'Latina', 'coordinates': {'latitude': 41.4677, 'longitude': 12.9037}},
                {'name': 'Giugliano in Campania', 'coordinates': {'latitude': 40.9287, 'longitude': 14.2056}},
                {'name': 'Monza', 'coordinates': {'latitude': 45.5845, 'longitude': 9.2744}},
                {'name': 'Syracuse', 'coordinates': {'latitude': 37.0755, 'longitude': 15.2866}},
            ],
            'spain': [
                # Major cities
                {'name': 'Madrid', 'coordinates': {'latitude': 40.4168, 'longitude': -3.7038}},
                {'name': 'Barcelona', 'coordinates': {'latitude': 41.3851, 'longitude': 2.1734}},
                {'name': 'Valencia', 'coordinates': {'latitude': 39.4699, 'longitude': -0.3763}},
                {'name': 'Seville', 'coordinates': {'latitude': 37.3891, 'longitude': -5.9845}},
                {'name': 'Zaragoza', 'coordinates': {'latitude': 41.6488, 'longitude': -0.8891}},
                {'name': 'Málaga', 'coordinates': {'latitude': 36.7213, 'longitude': -4.4214}},
                {'name': 'Murcia', 'coordinates': {'latitude': 37.9922, 'longitude': -1.1307}},
                {'name': 'Palma', 'coordinates': {'latitude': 39.5696, 'longitude': 2.6502}},
                {'name': 'Bilbao', 'coordinates': {'latitude': 43.2627, 'longitude': -2.9253}},
                {'name': 'Alicante', 'coordinates': {'latitude': 38.3452, 'longitude': -0.4810}},
                # Additional major cities
                {'name': 'Las Palmas', 'coordinates': {'latitude': 28.1248, 'longitude': -15.4300}},
                {'name': 'Córdoba', 'coordinates': {'latitude': 37.8882, 'longitude': -4.7794}},
                {'name': 'Valladolid', 'coordinates': {'latitude': 41.6523, 'longitude': -4.7245}},
                {'name': 'Vigo', 'coordinates': {'latitude': 42.2406, 'longitude': -8.7207}},
                {'name': 'Gijón', 'coordinates': {'latitude': 43.5322, 'longitude': -5.6611}},
                {'name': 'Hospitalet de Llobregat', 'coordinates': {'latitude': 41.3598, 'longitude': 2.1074}},
                {'name': 'A Coruña', 'coordinates': {'latitude': 43.3623, 'longitude': -8.4115}},
                {'name': 'Granada', 'coordinates': {'latitude': 37.1773, 'longitude': -3.5986}},
                {'name': 'Vitoria-Gasteiz', 'coordinates': {'latitude': 42.8467, 'longitude': -2.6716}},
                {'name': 'Elche', 'coordinates': {'latitude': 38.2622, 'longitude': -0.7016}},
                # Smaller cities and towns
                {'name': 'Santa Cruz de Tenerife', 'coordinates': {'latitude': 28.4636, 'longitude': -16.2518}},
                {'name': 'Oviedo', 'coordinates': {'latitude': 43.3614, 'longitude': -5.8593}},
                {'name': 'Badalona', 'coordinates': {'latitude': 41.4502, 'longitude': 2.2445}},
                {'name': 'Cartagena', 'coordinates': {'latitude': 37.6063, 'longitude': -0.9864}},
                {'name': 'Móstoles', 'coordinates': {'latitude': 40.3232, 'longitude': -3.8644}},
                {'name': 'Jerez de la Frontera', 'coordinates': {'latitude': 36.6868, 'longitude': -6.1362}},
                {'name': 'Tarrasa', 'coordinates': {'latitude': 41.5633, 'longitude': 2.0086}},
                {'name': 'Sabadell', 'coordinates': {'latitude': 41.5431, 'longitude': 2.1095}},
                {'name': 'Alcalá de Henares', 'coordinates': {'latitude': 40.4817, 'longitude': -3.3649}},
                {'name': 'Pamplona', 'coordinates': {'latitude': 42.8125, 'longitude': -1.6458}},
                {'name': 'Fuenlabrada', 'coordinates': {'latitude': 40.2842, 'longitude': -3.7947}},
                {'name': 'Almería', 'coordinates': {'latitude': 36.8381, 'longitude': -2.4597}},
                {'name': 'San Sebastián', 'coordinates': {'latitude': 43.3183, 'longitude': -1.9812}},
                {'name': 'Burgos', 'coordinates': {'latitude': 42.3440, 'longitude': -3.6969}},
                {'name': 'Albacete', 'coordinates': {'latitude': 38.9942, 'longitude': -1.8564}},
                {'name': 'Santander', 'coordinates': {'latitude': 43.4623, 'longitude': -3.8099}},
                {'name': 'Castellón de la Plana', 'coordinates': {'latitude': 39.9864, 'longitude': -0.0513}},
                {'name': 'Alcorcón', 'coordinates': {'latitude': 40.3459, 'longitude': -3.8248}},
                {'name': 'Getafe', 'coordinates': {'latitude': 40.3057, 'longitude': -3.7327}},
                {'name': 'Salamanca', 'coordinates': {'latitude': 40.9701, 'longitude': -5.6635}},
            ]
        }
        
        cities = fallback_cities.get(country.lower(), [])
        for city in cities:
            city.update({
                'country': self.country_bounds.get(country.lower(), {}).get('code', 'Unknown'),
                'source': 'fallback',
                'types': ['city'],
                'rating': 5
            })
        
        return cities
    
    def _get_fallback_attractions(self, coordinates: Coordinates, limit: int) -> List[Dict]:
        """Fallback attractions data when API is unavailable."""
        return [
            {
                'name': 'Local Attraction',
                'kinds': ['cultural', 'historic'],
                'rating': 4,
                'distance': 500,
                'coordinates': {
                    'latitude': coordinates.latitude,
                    'longitude': coordinates.longitude
                },
                'source': 'fallback'
            }
        ]
    
    def _get_fallback_comprehensive_cities(self) -> Dict[str, List[Dict]]:
        """Fallback comprehensive cities data when API is unavailable."""
        return {
            'france': self._get_fallback_cities('france'),
            'italy': self._get_fallback_cities('italy'),
            'spain': self._get_fallback_cities('spain')
        }


# Global service instance
_opentripmap_service = None

def get_opentripmap_service() -> OpenTripMapService:
    """Get the global OpenTripMap service instance."""
    global _opentripmap_service
    if _opentripmap_service is None:
        _opentripmap_service = OpenTripMapService()
    return _opentripmap_service
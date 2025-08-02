"""
Enhanced City Service integrating multiple free APIs for comprehensive city knowledge.
Combines data from GeoNames, OpenStreetMap, Wikidata, UNESCO, and existing APIs.
"""
import os
import asyncio
import aiohttp
import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import structlog
from ..core.models import City, Coordinates, ServiceResult
from ..core.exceptions import ExternalServiceError

logger = structlog.get_logger(__name__)


@dataclass
class CityEnrichmentData:
    """Extended city data from multiple sources."""
    basic_info: Dict
    population_data: Dict
    cultural_sites: List[Dict]
    unesco_sites: List[Dict]
    climate_info: Dict
    tourism_score: float
    accessibility_info: Dict


class EnhancedCityService:
    """Enhanced city service using multiple free APIs for comprehensive data."""
    
    def __init__(self):
        # No API keys needed for these free services
        self.geonames_username = os.getenv('GEONAMES_USERNAME', 'eurotrip_demo')  # Free registration
        self.session = None
        self._city_cache: Dict[str, CityEnrichmentData] = {}
        
        # API endpoints
        self.apis = {
            'geonames': 'http://api.geonames.org',
            'nominatim': 'https://nominatim.openstreetmap.org',
            'wikidata': 'https://www.wikidata.org/w/api.php',
            'unesco': 'https://whc.unesco.org/api/v1/sites',
            'rest_countries': 'https://restcountries.com/v3.1',
            'europeana': 'https://api.europeana.eu/record/v2'
        }
    
    async def __aenter__(self):
        if not self.session:
            headers = {
                'User-Agent': 'EuroTrip Travel Planner/2.0 (https://eurotrip.com)'
            }
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def enrich_city_data(self, city_name: str, country_code: str = None) -> CityEnrichmentData:
        """Gather comprehensive city data from multiple free APIs."""
        cache_key = f"{city_name.lower()}_{country_code or 'any'}"
        
        if cache_key in self._city_cache:
            return self._city_cache[cache_key]
        
        logger.info(f"Enriching city data for {city_name}")
        
        # Gather data from multiple sources concurrently
        tasks = {
            'geonames': self._get_geonames_data(city_name, country_code),
            'nominatim': self._get_nominatim_data(city_name, country_code),
            'wikidata': self._get_wikidata_info(city_name),
            'unesco': self._get_unesco_sites_nearby(city_name),
            'cultural': self._get_cultural_sites(city_name)
        }
        
        try:
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            
            # Combine results
            enrichment_data = CityEnrichmentData(
                basic_info=self._safe_result(results[0]),
                population_data=self._safe_result(results[0]),
                cultural_sites=self._safe_result(results[2], []),
                unesco_sites=self._safe_result(results[3], []),
                climate_info={},
                tourism_score=self._calculate_tourism_score(results),
                accessibility_info={}
            )
            
            self._city_cache[cache_key] = enrichment_data
            return enrichment_data
            
        except Exception as e:
            logger.error(f"City enrichment failed for {city_name}: {e}")
            return self._get_fallback_enrichment(city_name)
    
    async def _get_geonames_data(self, city_name: str, country_code: str = None) -> Dict:
        """Get comprehensive city data from GeoNames (free with registration)."""
        try:
            url = f"{self.apis['geonames']}/searchJSON"
            params = {
                'q': city_name,
                'maxRows': 10,
                'username': self.geonames_username,
                'featureClass': 'P',  # Cities and villages
                'style': 'FULL'
            }
            
            if country_code:
                params['country'] = country_code
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    geonames = data.get('geonames', [])
                    
                    if geonames:
                        place = geonames[0]  # Best match
                        return {
                            'geonames_id': place.get('geonameId'),
                            'name': place.get('name'),
                            'ascii_name': place.get('asciiName'),
                            'country_name': place.get('countryName'),
                            'country_code': place.get('countryCode'),
                            'admin_area': place.get('adminName1'),
                            'population': place.get('population', 0),
                            'elevation': place.get('elevation'),
                            'timezone': place.get('timezone', {}).get('timeZoneId'),
                            'coordinates': {
                                'latitude': float(place.get('lat', 0)),
                                'longitude': float(place.get('lng', 0))
                            },
                            'feature_code': place.get('fcode'),
                            'source': 'geonames'
                        }
                
                logger.warning(f"GeoNames search failed for {city_name}: {response.status}")
                return {}
                
        except Exception as e:
            logger.error(f"GeoNames API error for {city_name}: {e}")
            return {}
    
    async def _get_nominatim_data(self, city_name: str, country_code: str = None) -> Dict:
        """Get detailed geographic data from OpenStreetMap Nominatim (completely free)."""
        try:
            url = f"{self.apis['nominatim']}/search"
            params = {
                'q': city_name,
                'format': 'json',
                'limit': 5,
                'addressdetails': 1,
                'extratags': 1,
                'namedetails': 1
            }
            
            if country_code:
                params['countrycodes'] = country_code.lower()
            
            # Add delay to respect rate limits (max 1 request per second)
            await asyncio.sleep(1.1)
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data:
                        place = data[0]  # Best match
                        address = place.get('address', {})
                        
                        return {
                            'osm_id': place.get('osm_id'),
                            'osm_type': place.get('osm_type'),
                            'display_name': place.get('display_name'),
                            'city': address.get('city') or address.get('town') or address.get('village'),
                            'state': address.get('state'),
                            'country': address.get('country'),
                            'postcode': address.get('postcode'),
                            'coordinates': {
                                'latitude': float(place.get('lat', 0)),
                                'longitude': float(place.get('lon', 0))
                            },
                            'bounding_box': place.get('boundingbox'),
                            'place_type': place.get('type'),
                            'importance': place.get('importance', 0),
                            'source': 'openstreetmap'
                        }
                
                return {}
                
        except Exception as e:
            logger.error(f"Nominatim API error for {city_name}: {e}")
            return {}
    
    async def _get_wikidata_info(self, city_name: str) -> List[Dict]:
        """Get cultural and historical information from Wikidata (free)."""
        try:
            # Search for the city entity
            search_url = f"{self.apis['wikidata']}"
            search_params = {
                'action': 'wbsearchentities',
                'search': city_name,
                'language': 'en',
                'format': 'json',
                'type': 'item',
                'limit': 5
            }
            
            cultural_sites = []
            
            async with self.session.get(search_url, params=search_params) as response:
                if response.status == 200:
                    data = await response.json()
                    entities = data.get('search', [])
                    
                    for entity in entities:
                        if 'city' in entity.get('description', '').lower():
                            # Get detailed entity data
                            entity_id = entity['id']
                            detail_params = {
                                'action': 'wbgetentities',
                                'ids': entity_id,
                                'format': 'json',
                                'languages': 'en'
                            }
                            
                            async with self.session.get(search_url, params=detail_params) as detail_response:
                                if detail_response.status == 200:
                                    detail_data = await detail_response.json()
                                    entity_data = detail_data.get('entities', {}).get(entity_id, {})
                                    
                                    cultural_sites.append({
                                        'wikidata_id': entity_id,
                                        'name': entity_data.get('labels', {}).get('en', {}).get('value', ''),
                                        'description': entity_data.get('descriptions', {}).get('en', {}).get('value', ''),
                                        'wikipedia_url': self._extract_wikipedia_url(entity_data),
                                        'cultural_significance': self._extract_cultural_properties(entity_data),
                                        'source': 'wikidata'
                                    })
                                    break  # Just get the main city info
            
            return cultural_sites
            
        except Exception as e:
            logger.error(f"Wikidata API error for {city_name}: {e}")
            return []
    
    async def _get_unesco_sites_nearby(self, city_name: str) -> List[Dict]:
        """Get UNESCO World Heritage sites (free API)."""
        try:
            # UNESCO API for world heritage sites
            url = f"{self.apis['unesco']}"
            params = {
                'format': 'json',
                'region': 'europe'  # Focus on European sites
            }
            
            unesco_sites = []
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    sites = data.get('sites', [])
                    
                    # Filter sites that mention the city name
                    for site in sites:
                        site_name = site.get('site', '').lower()
                        location = site.get('location', '').lower()
                        
                        if (city_name.lower() in site_name or 
                            city_name.lower() in location):
                            
                            unesco_sites.append({
                                'unesco_id': site.get('id_no'),
                                'name': site.get('site'),
                                'location': site.get('location'),
                                'criteria': site.get('criteria_txt'),
                                'year_inscribed': site.get('date_inscribed'),
                                'category': site.get('category'),
                                'description': site.get('short_description'),
                                'source': 'unesco'
                            })
            
            return unesco_sites
            
        except Exception as e:
            logger.error(f"UNESCO API error for {city_name}: {e}")
            return []
    
    async def _get_cultural_sites(self, city_name: str) -> List[Dict]:
        """Get cultural sites from multiple sources."""
        # This could integrate with Europeana API, museum APIs, etc.
        # For now, return empty list - can be expanded later
        return []
    
    def _safe_result(self, result: Any, default: Any = None) -> Any:
        """Safely extract result, handling exceptions."""
        if isinstance(result, Exception):
            return default or {}
        return result or default or {}
    
    def _calculate_tourism_score(self, results: List[Any]) -> float:
        """Calculate a tourism attractiveness score based on available data."""
        score = 0.0
        
        # Basic info available
        if not isinstance(results[0], Exception) and results[0]:
            score += 1.0
        
        # Cultural sites available
        if not isinstance(results[2], Exception) and results[2]:
            score += 2.0
        
        # UNESCO sites nearby
        if not isinstance(results[3], Exception) and results[3]:
            score += 3.0
        
        return min(score, 5.0)  # Max score of 5.0
    
    def _extract_wikipedia_url(self, entity_data: Dict) -> str:
        """Extract Wikipedia URL from Wikidata entity."""
        sitelinks = entity_data.get('sitelinks', {})
        en_wiki = sitelinks.get('enwiki', {})
        if en_wiki:
            title = en_wiki.get('title', '')
            return f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        return ""
    
    def _extract_cultural_properties(self, entity_data: Dict) -> Dict:
        """Extract cultural significance properties from Wikidata."""
        # This would parse Wikidata properties for cultural significance
        # For now, return basic info
        return {
            'historic': True,
            'cultural_importance': 'medium'
        }
    
    def _get_fallback_enrichment(self, city_name: str) -> CityEnrichmentData:
        """Fallback enrichment data when APIs fail."""
        return CityEnrichmentData(
            basic_info={'name': city_name, 'source': 'fallback'},
            population_data={},
            cultural_sites=[],
            unesco_sites=[],
            climate_info={},
            tourism_score=2.5,
            accessibility_info={}
        )
    
    async def get_european_cities_bulk(self, limit: int = 1000) -> List[Dict]:
        """Get bulk European city data for database population."""
        logger.info(f"Fetching bulk European city data (limit: {limit})")
        
        european_countries = [
            'FR', 'IT', 'ES', 'DE', 'AT', 'CH', 'BE', 'NL', 'PT', 'PL', 
            'CZ', 'HU', 'HR', 'SI', 'SK', 'RO', 'BG', 'GR', 'MT', 'CY'
        ]
        
        all_cities = []
        
        for country in european_countries:
            try:
                url = f"{self.apis['geonames']}/searchJSON"
                params = {
                    'country': country,
                    'featureClass': 'P',
                    'featureCode': 'PPLA',  # Administrative capitals
                    'maxRows': 50,
                    'username': self.geonames_username,
                    'orderby': 'population'
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        cities = data.get('geonames', [])
                        
                        for city in cities:
                            all_cities.append({
                                'name': city.get('name'),
                                'country': city.get('countryName'),
                                'country_code': city.get('countryCode'),
                                'population': city.get('population', 0),
                                'coordinates': {
                                    'latitude': float(city.get('lat', 0)),
                                    'longitude': float(city.get('lng', 0))
                                },
                                'admin_area': city.get('adminName1'),
                                'feature_code': city.get('fcode'),
                                'source': 'geonames_bulk'
                            })
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Bulk fetch error for {country}: {e}")
                continue
        
        logger.info(f"Fetched {len(all_cities)} European cities")
        return all_cities[:limit]


# Global service instance
_enhanced_city_service = None

def get_enhanced_city_service() -> EnhancedCityService:
    """Get the global enhanced city service instance."""
    global _enhanced_city_service
    if _enhanced_city_service is None:
        _enhanced_city_service = EnhancedCityService()
    return _enhanced_city_service
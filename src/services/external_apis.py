"""
Production-ready external API integrations with circuit breakers and retries.
"""
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..core.models import ServiceResult, Coordinates
from ..core.exceptions import ExternalServiceError, RateLimitError
from ..infrastructure.config import SecureConfigurationService

logger = structlog.get_logger(__name__)


@dataclass
class CircuitBreakerState:
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half-open
    
    @property
    def is_open(self) -> bool:
        if self.state == "open":
            # Auto-recovery after 60 seconds
            if self.last_failure_time and (
                datetime.now() - self.last_failure_time > timedelta(seconds=60)
            ):
                self.state = "half-open"
                return False
            return True
        return False


class CircuitBreaker:
    """Circuit breaker for external API calls."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = CircuitBreakerState()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state.is_open:
            raise ExternalServiceError("Circuit breaker is open", "circuit_breaker")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        self.state.failures = 0
        self.state.state = "closed"
    
    def _on_failure(self):
        self.state.failures += 1
        self.state.last_failure_time = datetime.now()
        if self.state.failures >= self.failure_threshold:
            self.state.state = "open"


class OpenRouteServiceAPI:
    """Production OpenRouteService integration for routing."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openrouteservice.org"):
        self.api_key = api_key
        self.base_url = base_url
        self.circuit_breaker = CircuitBreaker()
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json',
                'User-Agent': 'TravelPlanner/2.0'
            }
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self.session
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def get_route(self, start: Coordinates, end: Coordinates, 
                       profile: str = "driving-car") -> ServiceResult:
        """Get route from OpenRouteService API."""
        try:
            session = await self._get_session()
            
            data = {
                "coordinates": [[start.longitude, start.latitude], [end.longitude, end.latitude]],
                "profile": profile,
                "format": "json",
                "instructions": True,
                "geometry": True,
                "elevation": True
            }
            
            url = f"{self.base_url}/v2/directions/{profile}/json"
            
            async with session.post(url, json=data) as response:
                if response.status == 429:
                    raise RateLimitError("OpenRouteService rate limit exceeded")
                
                if response.status != 200:
                    error_text = await response.text()
                    raise ExternalServiceError(
                        f"OpenRouteService API error: {error_text}",
                        "openroute",
                        response.status
                    )
                
                result = await response.json()
                
                route = result['routes'][0]
                summary = route['summary']
                
                return ServiceResult.success_result({
                    'distance_km': round(summary['distance'] / 1000, 1),
                    'duration_hours': round(summary['duration'] / 3600, 1),
                    'geometry': route['geometry'],
                    'instructions': route['segments'][0]['steps'],
                    'elevation_gain': route.get('elevation_gain', 0),
                    'source': 'openroute'
                })
                
        except Exception as e:
            logger.error("OpenRouteService API error", error=str(e))
            if isinstance(e, (RateLimitError, ExternalServiceError)):
                raise
            raise ExternalServiceError(f"Route calculation failed: {e}", "openroute")
    
    async def get_multi_point_route(self, coordinates: List[Coordinates], 
                                  optimize: bool = True) -> ServiceResult:
        """Get optimized route through multiple points."""
        try:
            session = await self._get_session()
            
            coord_pairs = [[coord.longitude, coord.latitude] for coord in coordinates]
            
            data = {
                "coordinates": coord_pairs,
                "profile": "driving-car",
                "optimize": optimize,
                "format": "json"
            }
            
            url = f"{self.base_url}/v2/directions/driving-car/json"
            
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    raise ExternalServiceError("Multi-point routing failed", "openroute")
                
                result = await response.json()
                route = result['routes'][0]
                
                return ServiceResult.success_result({
                    'total_distance_km': round(route['summary']['distance'] / 1000, 1),
                    'total_duration_hours': round(route['summary']['duration'] / 3600, 1),
                    'segments': route['segments'],
                    'optimized_order': result.get('metadata', {}).get('query', {}).get('coordinates', []),
                    'source': 'openroute'
                })
                
        except Exception as e:
            logger.error("Multi-point routing error", error=str(e))
            raise ExternalServiceError(f"Multi-point routing failed: {e}", "openroute")
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()


class OpenWeatherMapAPI:
    """Production OpenWeatherMap integration."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openweathermap.org/data/2.5"):
        self.api_key = api_key
        self.base_url = base_url
        self.circuit_breaker = CircuitBreaker()
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=15)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def get_weather_forecast(self, coordinates: Coordinates, days: int = 5) -> ServiceResult:
        """Get weather forecast for coordinates."""
        try:
            session = await self._get_session()
            
            # Get current weather
            current_url = f"{self.base_url}/weather"
            current_params = {
                'lat': coordinates.latitude,
                'lon': coordinates.longitude,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            # Get forecast
            forecast_url = f"{self.base_url}/forecast"
            forecast_params = current_params.copy()
            forecast_params['cnt'] = min(days * 8, 40)  # 3-hour intervals, max 5 days
            
            async with session.get(current_url, params=current_params) as current_response:
                if current_response.status == 401:
                    raise ExternalServiceError("Invalid OpenWeatherMap API key", "openweather", 401)
                
                if current_response.status != 200:
                    raise ExternalServiceError("Weather API error", "openweather", current_response.status)
                
                current_data = await current_response.json()
            
            async with session.get(forecast_url, params=forecast_params) as forecast_response:
                if forecast_response.status != 200:
                    raise ExternalServiceError("Forecast API error", "openweather", forecast_response.status)
                
                forecast_data = await forecast_response.json()
            
            # Process weather data
            processed_forecast = []
            for item in forecast_data['list'][:days * 4]:  # Reduce to requested days
                processed_forecast.append({
                    'datetime': item['dt_txt'],
                    'temperature': item['main']['temp'],
                    'feels_like': item['main']['feels_like'],
                    'humidity': item['main']['humidity'],
                    'description': item['weather'][0]['description'],
                    'icon': item['weather'][0]['icon'],
                    'wind_speed': item['wind']['speed'],
                    'precipitation': item.get('rain', {}).get('3h', item.get('snow', {}).get('3h', 0))
                })
            
            return ServiceResult.success_result({
                'current': {
                    'temperature': current_data['main']['temp'],
                    'feels_like': current_data['main']['feels_like'],
                    'humidity': current_data['main']['humidity'],
                    'description': current_data['weather'][0]['description'],
                    'icon': current_data['weather'][0]['icon'],
                    'wind_speed': current_data['wind']['speed'],
                    'city': current_data['name']
                },
                'forecast': processed_forecast,
                'source': 'openweather'
            })
            
        except Exception as e:
            logger.error("Weather API error", error=str(e))
            if isinstance(e, ExternalServiceError):
                raise
            raise ExternalServiceError(f"Weather data unavailable: {e}", "openweather")
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()


class GooglePlacesAPI:
    """Production Google Places integration for accommodations and restaurants."""
    
    def __init__(self, api_key: str, base_url: str = "https://maps.googleapis.com/maps/api/place"):
        self.api_key = api_key
        self.base_url = base_url
        self.circuit_breaker = CircuitBreaker()
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=20)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def search_hotels(self, coordinates: Coordinates, radius: int = 5000) -> ServiceResult:
        """Search for hotels near coordinates."""
        try:
            session = await self._get_session()
            
            url = f"{self.base_url}/nearbysearch/json"
            params = {
                'location': f"{coordinates.latitude},{coordinates.longitude}",
                'radius': radius,
                'type': 'lodging',
                'key': self.api_key
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 403:
                    raise ExternalServiceError("Google Places API quota exceeded", "google_places", 403)
                
                if response.status != 200:
                    raise ExternalServiceError("Places API error", "google_places", response.status)
                
                data = await response.json()
                
                hotels = []
                for place in data.get('results', [])[:20]:  # Limit to 20 results
                    hotel = {
                        'place_id': place['place_id'],
                        'name': place['name'],
                        'rating': place.get('rating', 0),
                        'price_level': place.get('price_level', 0),
                        'vicinity': place.get('vicinity', ''),
                        'types': place.get('types', []),
                        'coordinates': {
                            'lat': place['geometry']['location']['lat'],
                            'lng': place['geometry']['location']['lng']
                        },
                        'photo_reference': place.get('photos', [{}])[0].get('photo_reference') if place.get('photos') else None
                    }
                    hotels.append(hotel)
                
                return ServiceResult.success_result({
                    'hotels': hotels,
                    'total_results': len(hotels),
                    'source': 'google_places'
                })
                
        except Exception as e:
            logger.error("Google Places hotels error", error=str(e))
            if isinstance(e, ExternalServiceError):
                raise
            raise ExternalServiceError(f"Hotel search failed: {e}", "google_places")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def search_restaurants(self, coordinates: Coordinates, radius: int = 2000) -> ServiceResult:
        """Search for restaurants near coordinates."""
        try:
            session = await self._get_session()
            
            url = f"{self.base_url}/nearbysearch/json"
            params = {
                'location': f"{coordinates.latitude},{coordinates.longitude}",
                'radius': radius,
                'type': 'restaurant',
                'key': self.api_key
            }
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise ExternalServiceError("Restaurant search failed", "google_places", response.status)
                
                data = await response.json()
                
                restaurants = []
                for place in data.get('results', [])[:15]:
                    restaurant = {
                        'place_id': place['place_id'],
                        'name': place['name'],
                        'rating': place.get('rating', 0),
                        'price_level': place.get('price_level', 0),
                        'vicinity': place.get('vicinity', ''),
                        'cuisine_types': [t for t in place.get('types', []) if 'restaurant' not in t],
                        'coordinates': {
                            'lat': place['geometry']['location']['lat'],
                            'lng': place['geometry']['location']['lng']
                        }
                    }
                    restaurants.append(restaurant)
                
                return ServiceResult.success_result({
                    'restaurants': restaurants,
                    'total_results': len(restaurants),
                    'source': 'google_places'
                })
                
        except Exception as e:
            logger.error("Google Places restaurants error", error=str(e))
            if isinstance(e, ExternalServiceError):
                raise
            raise ExternalServiceError(f"Restaurant search failed: {e}", "google_places")
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()


class ExternalAPIManager:
    """Manager for all external API services."""
    
    def __init__(self, config_service: SecureConfigurationService):
        self.config = config_service
        self.openroute = None
        self.weather = None
        self.places = None
        self._initialize_apis()
    
    def _initialize_apis(self):
        """Initialize API clients based on available keys."""
        openroute_key = self.config.get_api_key('openroute')
        if openroute_key:
            self.openroute = OpenRouteServiceAPI(openroute_key)
        
        weather_key = self.config.get_api_key('openweather')
        if weather_key:
            self.weather = OpenWeatherMapAPI(weather_key)
        
        places_key = self.config.get_api_key('google_maps')
        if places_key:
            self.places = GooglePlacesAPI(places_key)
    
    async def close_all(self):
        """Close all API sessions."""
        for api in [self.openroute, self.weather, self.places]:
            if api:
                await api.close()
    
    def get_available_services(self) -> Dict[str, bool]:
        """Get status of available services."""
        return {
            'routing': self.openroute is not None,
            'weather': self.weather is not None,
            'places': self.places is not None
        }
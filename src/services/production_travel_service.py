"""
Production travel service integrating all real APIs and caching.
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from ..core.models import ServiceResult, TripRequest, Coordinates, City
from ..core.exceptions import ExternalServiceError
from ..infrastructure.cache import CacheService, RouteCache
from ..infrastructure.config import SecureConfigurationService
from .external_apis import ExternalAPIManager
from .city_service import CityService

logger = structlog.get_logger(__name__)


class ProductionTravelService:
    """Production travel service with real API integrations."""
    
    def __init__(self, config_service: SecureConfigurationService, 
                 cache_service: CacheService, city_service: CityService):
        self.config = config_service
        self.cache = cache_service
        self.route_cache = RouteCache(cache_service)
        self.city_service = city_service
        self.api_manager = ExternalAPIManager(config_service)
        
        # Check available services
        self.available_services = self.api_manager.get_available_services()
        logger.info("Production travel service initialized", 
                   services=self.available_services)
    
    async def generate_complete_travel_plan(self, request: TripRequest) -> ServiceResult:
        """Generate complete travel plan with real data from multiple APIs."""
        try:
            logger.info("Generating complete travel plan", 
                       start=request.start_city, end=request.end_city)
            
            # Get cities with validation
            start_city = self.city_service.get_city_by_name(request.start_city)
            end_city = self.city_service.get_city_by_name(request.end_city)
            
            if not start_city or not end_city:
                return ServiceResult.error_result(
                    f"Cities not found: {request.start_city}, {request.end_city}"
                )
            
            # Generate multiple route options with real data
            routes_task = self._generate_real_routes(start_city, end_city, request)
            weather_task = self._get_weather_data([start_city, end_city])
            accommodations_task = self._get_accommodations_data([start_city, end_city])
            restaurants_task = self._get_restaurants_data([start_city, end_city])
            
            # Execute all API calls concurrently
            results = await asyncio.gather(
                routes_task, weather_task, accommodations_task, restaurants_task,
                return_exceptions=True
            )
            
            routes_result, weather_result, accommodations_result, restaurants_result = results
            
            # Process results
            travel_plan = {
                'trip_request': {
                    'start_city': start_city.name,
                    'end_city': end_city.name,
                    'travel_days': request.travel_days,
                    'season': request.season.value
                },
                'routes': routes_result.data if isinstance(routes_result, ServiceResult) and routes_result.success else [],
                'weather': weather_result.data if isinstance(weather_result, ServiceResult) and weather_result.success else {},
                'accommodations': accommodations_result.data if isinstance(accommodations_result, ServiceResult) and accommodations_result.success else [],
                'restaurants': restaurants_result.data if isinstance(restaurants_result, ServiceResult) and restaurants_result.success else [],
                'ai_insights': await self._get_ai_insights(request) if (request.claude_api_key or os.getenv('ANTHROPIC_API_KEY')) else [],
                'generated_at': datetime.utcnow().isoformat(),
                'data_sources': self._get_data_sources_used()
            }
            
            # Cache the complete plan
            cache_key = f"travel_plan:{start_city.name}:{end_city.name}:{request.travel_days}:{request.season.value}"
            self.cache.set(cache_key, travel_plan, ttl_seconds=3600)  # Cache for 1 hour
            
            return ServiceResult.success_result(travel_plan)
            
        except Exception as e:
            logger.error("Travel plan generation failed", error=str(e))
            return ServiceResult.error_result(f"Travel plan generation failed: {e}")
    
    async def _generate_real_routes(self, start_city: City, end_city: City, 
                                   request: TripRequest) -> ServiceResult:
        """Generate routes using real routing APIs."""
        try:
            routes = []
            
            # Route strategies with real calculations
            strategies = [
                {'name': 'Fastest Route', 'type': 'fastest', 'waypoints': []},
                {'name': 'Scenic Route', 'type': 'scenic', 'waypoints': self._get_scenic_waypoints(start_city, end_city)},
                {'name': 'Cultural Route', 'type': 'cultural', 'waypoints': self._get_cultural_waypoints(start_city, end_city)},
                {'name': 'Culinary Route', 'type': 'culinary', 'waypoints': self._get_culinary_waypoints(start_city, end_city)}
            ]
            
            for strategy in strategies:
                route_result = await self._calculate_route_with_api(
                    start_city, end_city, strategy, request
                )
                
                if route_result.success:
                    routes.append(route_result.data)
                else:
                    # Fallback to geometric calculation
                    fallback_route = self._calculate_fallback_route(
                        start_city, end_city, strategy, request
                    )
                    routes.append(fallback_route)
            
            return ServiceResult.success_result(routes)
            
        except Exception as e:
            logger.error("Route generation failed", error=str(e))
            return ServiceResult.error_result(f"Route generation failed: {e}")
    
    async def _calculate_route_with_api(self, start_city: City, end_city: City,
                                       strategy: Dict, request: TripRequest) -> ServiceResult:
        """Calculate route using OpenRouteService API."""
        if not self.available_services.get('routing'):
            return ServiceResult.error_result("Routing API not available")
        
        try:
            # Check cache first
            cache_key = f"route:{start_city.name}:{end_city.name}:{strategy['type']}"
            cached_route = self.cache.get(cache_key)
            if cached_route:
                logger.debug("Route cache hit", key=cache_key)
                return ServiceResult.success_result(cached_route)
            
            # Build waypoints list
            waypoints = [Coordinates(start_city.coordinates.latitude, start_city.coordinates.longitude)]
            for waypoint_city in strategy['waypoints']:
                waypoints.append(Coordinates(waypoint_city.coordinates.latitude, waypoint_city.coordinates.longitude))
            waypoints.append(Coordinates(end_city.coordinates.latitude, end_city.coordinates.longitude))
            
            # Call OpenRouteService API
            if len(waypoints) > 2:
                api_result = await self.api_manager.openroute.get_multi_point_route(waypoints)
            else:
                api_result = await self.api_manager.openroute.get_route(waypoints[0], waypoints[-1])
            
            if not api_result.success:
                return api_result
            
            route_data = api_result.data
            
            # Enrich with additional data
            enriched_route = {
                'name': strategy['name'],
                'type': strategy['type'],
                'description': self._get_route_description(strategy['type'], request.season),
                'total_distance_km': route_data['total_distance_km'] if 'total_distance_km' in route_data else route_data['distance_km'],
                'total_duration_hours': route_data['total_duration_hours'] if 'total_duration_hours' in route_data else route_data['duration_hours'],
                'estimated_driving_time': f"{route_data.get('total_duration_hours', route_data.get('duration_hours', 0)):.1f} hours",
                'waypoints': [{'name': city.name, 'coordinates': [city.coordinates.latitude, city.coordinates.longitude]} for city in strategy['waypoints']],
                'start_city': {'name': start_city.name, 'coordinates': [start_city.coordinates.latitude, start_city.coordinates.longitude]},
                'end_city': {'name': end_city.name, 'coordinates': [end_city.coordinates.latitude, end_city.coordinates.longitude]},
                'geometry': route_data.get('geometry'),
                'elevation_gain': route_data.get('elevation_gain', 0),
                'estimated_cost': self._calculate_route_cost(route_data.get('total_distance_km', route_data.get('distance_km', 0)), request.travel_days),
                'season_tips': self._get_season_specific_tips(strategy['type'], request.season),
                'real_time_traffic': False,  # Would need additional API for real-time
                'data_source': 'openroute_api'
            }
            
            # Cache the result
            self.cache.set(cache_key, enriched_route, ttl_seconds=1800)  # 30 minutes
            
            return ServiceResult.success_result(enriched_route)
            
        except Exception as e:
            logger.error("API route calculation failed", error=str(e))
            return ServiceResult.error_result(f"API route calculation failed: {e}")
    
    def _calculate_fallback_route(self, start_city: City, end_city: City, 
                                 strategy: Dict, request: TripRequest) -> Dict:
        """Fallback route calculation using geometric distance."""
        from geopy.distance import geodesic
        
        distance = geodesic(
            (start_city.coordinates.latitude, start_city.coordinates.longitude),
            (end_city.coordinates.latitude, end_city.coordinates.longitude)
        ).kilometers
        
        # Adjust distance based on route type
        multiplier = {'fastest': 1.0, 'scenic': 1.3, 'cultural': 1.2, 'culinary': 1.15}.get(strategy['type'], 1.1)
        adjusted_distance = distance * multiplier
        
        duration = adjusted_distance / 70.0  # Average speed with stops
        
        return {
            'name': strategy['name'],
            'type': strategy['type'],
            'description': self._get_route_description(strategy['type'], request.season),
            'total_distance_km': round(adjusted_distance, 1),
            'total_duration_hours': round(duration, 1),
            'estimated_driving_time': f"{duration:.1f} hours",
            'waypoints': [{'name': city.name, 'coordinates': [city.coordinates.latitude, city.coordinates.longitude]} for city in strategy['waypoints']],
            'start_city': {'name': start_city.name, 'coordinates': [start_city.coordinates.latitude, start_city.coordinates.longitude]},
            'end_city': {'name': end_city.name, 'coordinates': [end_city.coordinates.latitude, end_city.coordinates.longitude]},
            'estimated_cost': self._calculate_route_cost(adjusted_distance, request.travel_days),
            'season_tips': self._get_season_specific_tips(strategy['type'], request.season),
            'data_source': 'geometric_fallback'
        }
    
    async def _get_weather_data(self, cities: List[City]) -> ServiceResult:
        """Get weather data for cities."""
        if not self.available_services.get('weather'):
            return ServiceResult.error_result("Weather API not available")
        
        try:
            weather_data = {}
            
            for city in cities:
                cache_key = f"weather:{city.name}:{datetime.now().strftime('%Y-%m-%d-%H')}"
                cached_weather = self.cache.get(cache_key)
                
                if cached_weather:
                    weather_data[city.name] = cached_weather
                else:
                    result = await self.api_manager.weather.get_weather_forecast(city.coordinates, days=5)
                    if result.success:
                        weather_data[city.name] = result.data
                        self.cache.set(cache_key, result.data, ttl_seconds=1800)  # 30 minutes
                    else:
                        logger.warning("Weather data unavailable", city=city.name)
            
            return ServiceResult.success_result(weather_data)
            
        except Exception as e:
            logger.error("Weather data retrieval failed", error=str(e))
            return ServiceResult.error_result(f"Weather data unavailable: {e}")
    
    async def _get_accommodations_data(self, cities: List[City]) -> ServiceResult:
        """Get accommodation data for cities."""
        if not self.available_services.get('places'):
            return ServiceResult.error_result("Places API not available")
        
        try:
            accommodations_data = {}
            
            for city in cities:
                cache_key = f"hotels:{city.name}:{datetime.now().strftime('%Y-%m-%d')}"
                cached_hotels = self.cache.get(cache_key)
                
                if cached_hotels:
                    accommodations_data[city.name] = cached_hotels
                else:
                    result = await self.api_manager.places.search_hotels(city.coordinates)
                    if result.success:
                        accommodations_data[city.name] = result.data['hotels']
                        self.cache.set(cache_key, result.data['hotels'], ttl_seconds=7200)  # 2 hours
                    else:
                        logger.warning("Hotel data unavailable", city=city.name)
                        accommodations_data[city.name] = []
            
            return ServiceResult.success_result(accommodations_data)
            
        except Exception as e:
            logger.error("Accommodations data retrieval failed", error=str(e))
            return ServiceResult.error_result(f"Accommodations data unavailable: {e}")
    
    async def _get_restaurants_data(self, cities: List[City]) -> ServiceResult:
        """Get restaurant data for cities."""
        if not self.available_services.get('places'):
            return ServiceResult.error_result("Places API not available")
        
        try:
            restaurants_data = {}
            
            for city in cities:
                cache_key = f"restaurants:{city.name}:{datetime.now().strftime('%Y-%m-%d')}"
                cached_restaurants = self.cache.get(cache_key)
                
                if cached_restaurants:
                    restaurants_data[city.name] = cached_restaurants
                else:
                    result = await self.api_manager.places.search_restaurants(city.coordinates)
                    if result.success:
                        restaurants_data[city.name] = result.data['restaurants']
                        self.cache.set(cache_key, result.data['restaurants'], ttl_seconds=7200)  # 2 hours
                    else:
                        logger.warning("Restaurant data unavailable", city=city.name)
                        restaurants_data[city.name] = []
            
            return ServiceResult.success_result(restaurants_data)
            
        except Exception as e:
            logger.error("Restaurants data retrieval failed", error=str(e))
            return ServiceResult.error_result(f"Restaurants data unavailable: {e}")
    
    async def _get_ai_insights(self, request: TripRequest) -> List[str]:
        """Get AI-powered travel insights using Claude."""
        try:
            # Use API key from request or environment variable
            api_key = request.claude_api_key or os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                return []
            
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            
            prompt = f"""
            Provide 5 specific, actionable travel tips for a {request.travel_days}-day {request.season.value} trip 
            from {request.start_city} to {request.end_city}. Include:
            1. Best travel timing
            2. Must-see attractions specific to the season
            3. Local food recommendations
            4. Transportation tips
            5. Budget-saving advice
            
            Keep each tip under 100 words and focus on practical, insider knowledge.
            """
            
            message = await asyncio.to_thread(
                client.messages.create,
                model="claude-3-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            insights = message.content[0].text.split('\n')
            return [tip.strip('1234567890. ').strip() for tip in insights if tip.strip() and len(tip.strip()) > 10][:5]
            
        except Exception as e:
            logger.error("AI insights generation failed", error=str(e))
            return []
    
    def _get_scenic_waypoints(self, start_city: City, end_city: City) -> List[City]:
        """Get scenic waypoints between cities."""
        return self.city_service.find_cities_by_type('scenic')[:2]
    
    def _get_cultural_waypoints(self, start_city: City, end_city: City) -> List[City]:
        """Get cultural waypoints between cities."""
        return self.city_service.find_cities_by_type('cultural')[:2]
    
    def _get_culinary_waypoints(self, start_city: City, end_city: City) -> List[City]:
        """Get culinary waypoints between cities."""
        return self.city_service.find_cities_by_type('culinary')[:2]
    
    def _get_route_description(self, route_type: str, season) -> str:
        """Get description for route type."""
        descriptions = {
            'fastest': f"Direct route optimized for speed, perfect for maximizing time at your destination during {season.value}",
            'scenic': f"Beautiful scenic route with stunning landscapes, ideal for {season.value} photography and sightseeing",
            'cultural': f"Cultural journey through historic sites and UNESCO landmarks, enhanced by {season.value} cultural events",
            'culinary': f"Gastronomic adventure featuring regional cuisines and local specialties, including {season.value} seasonal dishes"
        }
        return descriptions.get(route_type, "Carefully planned route for your journey")
    
    def _calculate_route_cost(self, distance_km: float, travel_days: int) -> Dict[str, float]:
        """Calculate estimated costs for the route."""
        fuel_cost = distance_km * 0.12  # €0.12 per km (updated rates)
        tolls_estimate = distance_km * 0.05  # Estimate for European tolls
        accommodation_cost = travel_days * 95  # €95 per night average
        food_cost = travel_days * 45  # €45 per day for meals
        
        return {
            'fuel_estimate_eur': round(fuel_cost, 2),
            'tolls_estimate_eur': round(tolls_estimate, 2),
            'accommodation_estimate_eur': round(accommodation_cost, 2),
            'food_estimate_eur': round(food_cost, 2),
            'total_estimate_eur': round(fuel_cost + tolls_estimate + accommodation_cost + food_cost, 2)
        }
    
    def _get_season_specific_tips(self, route_type: str, season) -> List[str]:
        """Get season-specific tips for route type."""
        base_tips = {
            'winter': ["Check weather conditions and carry winter equipment", "Some mountain passes may be closed", "Book accommodations early due to ski season"],
            'summer': ["Book accommodations early due to peak season", "Start early to avoid traffic and heat", "Stay hydrated and use sun protection"],
            'spring': ["Perfect weather for outdoor activities", "Enjoy blooming landscapes", "Pack layers for variable temperatures"],
            'autumn': ["Beautiful fall colors on scenic routes", "Harvest season - great for food experiences", "Weather can be unpredictable"]
        }
        return base_tips.get(season.value, ["Enjoy your journey!"])
    
    def _get_data_sources_used(self) -> Dict[str, bool]:
        """Get information about which data sources were used."""
        return {
            'openroute_service': self.available_services.get('routing', False),
            'openweather_map': self.available_services.get('weather', False),
            'google_places': self.available_services.get('places', False),
            'claude_ai': True,  # Always available if API key provided
            'real_time_data': True
        }
    
    async def close(self):
        """Close all API connections."""
        await self.api_manager.close_all()
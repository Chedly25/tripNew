"""
Main travel planning service orchestrating all components.
"""
from typing import List, Dict, Any
import asyncio
import structlog
from ..core.interfaces import TravelPlannerService
from ..core.models import TripRequest, ServiceResult, TravelRoute, RouteType
from ..core.exceptions import TravelPlannerException
from .google_places_city_service import GooglePlacesCityService
from .route_service import ProductionRouteService
from .validation_service import ValidationService
from .itinerary_generator import ItineraryGenerator
from .hidden_gems_service import HiddenGemsService
from .enhanced_intermediate_city_service import get_enhanced_intermediate_city_service
from .city_description_service import get_city_description_service

logger = structlog.get_logger(__name__)


class TravelPlannerServiceImpl(TravelPlannerService):
    """Main travel planning service with proper architecture."""
    
    def __init__(self, city_service: GooglePlacesCityService, route_service: ProductionRouteService,
                 validation_service: ValidationService):
        self.city_service = city_service
        self.route_service = route_service
        self.validation_service = validation_service
        # Initialize enhanced intermediate city service
        self.enhanced_intermediate_service = get_enhanced_intermediate_city_service()
        # Initialize city description service
        self.description_service = get_city_description_service()
        # Initialize itinerary generator
        hidden_gems_service = HiddenGemsService(city_service)
        self.itinerary_generator = ItineraryGenerator(city_service, hidden_gems_service)
        self._route_strategies = self._initialize_route_strategies()
    
    def generate_routes(self, request: TripRequest) -> ServiceResult:
        """Generate multiple route options for the trip request."""
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an event loop, need to use different approach
                logger.info("Already in event loop, using sync fallback for route generation")
                return self._generate_routes_sync(request)
            except RuntimeError:
                # No running loop, can use asyncio.run
                return asyncio.run(self._generate_routes_async(request))
        except Exception as e:
            logger.error("Route generation failed", error=str(e))
            return ServiceResult.error_result(f"Route generation failed: {e}")
    
    async def _generate_routes_async(self, request: TripRequest) -> ServiceResult:
        """Async route generation using Google Places API."""
        try:
            logger.info("Generating routes", 
                       start=request.start_city, 
                       end=request.end_city,
                       days=request.travel_days)
            
            # Get start and end cities using async API calls
            start_city = await self.city_service.get_city_by_name(request.start_city)
            if not start_city:
                return ServiceResult.error_result(f"Start city not found: {request.start_city}")
            
            end_city = await self.city_service.get_city_by_name(request.end_city)
            if not end_city:
                return ServiceResult.error_result(f"End city not found: {request.end_city}")
            
            # Generate routes for different strategies concurrently
            route_tasks = []
            for strategy in self._route_strategies:
                task = self._generate_route_for_strategy_async(
                    strategy, start_city, end_city, request
                )
                route_tasks.append(task)
            
            # Wait for all route generation tasks to complete
            route_results = await asyncio.gather(*route_tasks, return_exceptions=True)
            
            routes = []
            for i, result in enumerate(route_results):
                if isinstance(result, Exception):
                    logger.error(f"Route generation failed for {self._route_strategies[i]['name']}", 
                               error=str(result))
                    continue
                
                if result and result.success:
                    routes.append(result.data)
                else:
                    logger.warning("Route generation failed", 
                                 strategy=self._route_strategies[i]['name'],
                                 error=result.error_message if result else "Unknown error")
            
            if not routes:
                return ServiceResult.error_result("No routes could be generated")
            
            return ServiceResult.success_result({
                'routes': routes,
                'request': request,
                'start_city': start_city,
                'end_city': end_city
            })
            
        except Exception as e:
            logger.error("Async route generation failed", error=str(e))
            return ServiceResult.error_result(f"Route generation failed: {e}")
    
    def _generate_routes_sync(self, request: TripRequest) -> ServiceResult:
        """Sync route generation using fallback city service."""
        try:
            logger.info("Generating routes synchronously", 
                       start=request.start_city, 
                       end=request.end_city,
                       days=request.travel_days)
            
            # Get start and end cities using sync fallback
            start_city = self.city_service._get_fallback_city(request.start_city)
            if not start_city:
                return ServiceResult.error_result(f"Start city not found: {request.start_city}")
            
            end_city = self.city_service._get_fallback_city(request.end_city)
            if not end_city:
                return ServiceResult.error_result(f"End city not found: {request.end_city}")
            
            # Generate routes for different strategies
            routes = []
            for strategy in self._route_strategies:
                try:
                    route_result = self._generate_route_for_strategy(
                        strategy, start_city, end_city, request
                    )
                    
                    if route_result.success:
                        routes.append(route_result.data)
                    else:
                        logger.warning("Route generation failed", 
                                     strategy=strategy['name'],
                                     error=route_result.error_message)
                
                except Exception as e:
                    logger.error(f"Route generation failed for {strategy['name']}", 
                               error=str(e))
                    continue
            
            if not routes:
                return ServiceResult.error_result("No routes could be generated")
            
            return ServiceResult.success_result({
                'routes': routes,
                'request': request,
                'start_city': start_city,
                'end_city': end_city
            })
            
        except Exception as e:
            logger.error("Sync route generation failed", error=str(e))
            return ServiceResult.error_result(f"Route generation failed: {e}")
    
    def get_route_details(self, route_id: str) -> ServiceResult:
        """Get detailed information for a specific route."""
        # Implementation for route details
        # This would typically load from cache or database
        return ServiceResult.error_result("Route details not implemented")
    
    async def _generate_route_for_strategy_async(self, strategy: Dict, start_city, end_city, 
                                               request: TripRequest) -> ServiceResult:
        """Generate a route for a specific strategy using async API calls."""
        try:
            # Find intermediate cities based on strategy using async API
            intermediate_cities = await self._find_intermediate_cities_async(
                strategy, start_city, end_city, request
            )
            
            # Calculate route through all cities
            all_cities = [start_city] + intermediate_cities + [end_city]
            route_result = self.route_service.optimize_multi_city_route(all_cities)
            
            if not route_result.success:
                return route_result
            
            route_data = route_result.data
            
            # Create travel route object
            travel_route = TravelRoute(
                route_type=RouteType(strategy['type']),
                segments=route_data['segments'],
                total_distance_km=route_data['total_distance_km'],
                total_duration_hours=route_data['total_duration_hours'],
                intermediate_cities=intermediate_cities,
                description=strategy['description']
            )
            
            # Enrich with additional data and generate complete itinerary
            enriched_route = await self._enrich_route_with_itinerary(travel_route, request, strategy, start_city, end_city)
            
            return ServiceResult.success_result(enriched_route)
            
        except Exception as e:
            logger.error("Async strategy route generation failed", 
                        strategy=strategy['name'], error=str(e))
            return ServiceResult.error_result(f"Route generation failed: {e}")
    
    def _generate_route_for_strategy(self, strategy: Dict, start_city, end_city, 
                                   request: TripRequest) -> ServiceResult:
        """Generate a route for a specific strategy."""
        try:
            # Find intermediate cities based on strategy
            intermediate_cities = self._find_intermediate_cities(
                strategy, start_city, end_city, request
            )
            
            # Calculate route through all cities
            all_cities = [start_city] + intermediate_cities + [end_city]
            route_result = self.route_service.optimize_multi_city_route(all_cities)
            
            if not route_result.success:
                return route_result
            
            route_data = route_result.data
            
            # Create travel route object
            travel_route = TravelRoute(
                route_type=RouteType(strategy['type']),
                segments=route_data['segments'],
                total_distance_km=route_data['total_distance_km'],
                total_duration_hours=route_data['total_duration_hours'],
                intermediate_cities=intermediate_cities,
                description=strategy['description']
            )
            
            # Enrich with additional data and generate complete itinerary
            enriched_route = self._enrich_route_with_itinerary_sync(travel_route, request, strategy, start_city, end_city)
            
            return ServiceResult.success_result(enriched_route)
            
        except Exception as e:
            logger.error("Strategy route generation failed", 
                        strategy=strategy['name'], error=str(e))
            return ServiceResult.error_result(f"Route generation failed: {e}")
    
    def _calculate_optimal_city_count(self, strategy_type: str, trip_days: int) -> int:
        """Calculate optimal number of intermediate cities based on trip duration and type."""
        
        # Base ratios: cities per day for different route types
        base_ratios = {
            'scenic': 0.4,      # Scenic routes: spend more time in fewer places to enjoy views
            'cultural': 0.6,    # Cultural routes: more cities to see different heritage sites
            'adventure': 0.3,   # Adventure routes: fewer cities, more time for activities
            'culinary': 0.5,    # Culinary routes: moderate pace to savor local cuisine
            'romantic': 0.3,    # Romantic routes: fewer cities, more time to relax
            'hidden_gems': 0.4  # Hidden gems: moderate pace to discover authentic places
        }
        
        ratio = base_ratios.get(strategy_type, 0.4)  # Default ratio
        
        # Calculate base city count
        base_count = max(1, int(trip_days * ratio))
        
        # Apply constraints based on trip duration
        if trip_days <= 3:
            # Short trips: 1-2 intermediate cities max
            return min(base_count, 2)
        elif trip_days <= 7:
            # Week-long trips: 2-4 intermediate cities
            return min(base_count, 4)
        elif trip_days <= 14:
            # Two-week trips: 3-8 intermediate cities
            return min(base_count, 8)
        else:
            # Long trips: 4-12 intermediate cities
            return min(max(base_count, 4), 12)
    
    def _find_intermediate_cities(self, strategy: Dict, start_city, end_city, 
                                request: TripRequest) -> List:
        """Find intermediate cities using enhanced multi-source algorithm."""
        strategy_type = strategy['type']
        
        # Calculate optimal number of intermediate cities based on trip duration and type
        max_cities = self._calculate_optimal_city_count(strategy_type, request.travel_days)
        
        logger.info("Enhanced city selection", 
                   strategy=strategy_type, 
                   trip_days=request.travel_days, 
                   max_cities=max_cities)
        
        try:
            # Use enhanced intermediate city service for better selection
            enhanced_cities = self._find_intermediate_cities_enhanced_sync(
                strategy, start_city, end_city, request, max_cities
            )
            
            if enhanced_cities:
                logger.info(f"Enhanced service found {len(enhanced_cities)} cities")
                return enhanced_cities
            
        except Exception as e:
            logger.warning(f"Enhanced service failed, using fallback: {e}")
        
        # Fallback to original method if enhanced service fails
        logger.info("Using fallback city selection method")
        nearby_cities = self.city_service._get_fallback_route_cities(
            start_city.coordinates, end_city.coordinates, max_deviation_km=120, route_type=strategy_type
        )
        
        if strategy_type == 'scenic':
            # Find scenic cities: alpine, lakes, romantic, resort
            scenic_types = ['scenic', 'alpine', 'lakes', 'romantic', 'resort', 'coastal']
            candidates = [c for c in nearby_cities if any(t in c.types for t in scenic_types)]
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'cultural':
            # Find cultural/historic cities: unesco, historic, cultural, artistic
            cultural_types = ['cultural', 'historic', 'unesco', 'artistic', 'renaissance', 'medieval', 'roman']
            candidates = [c for c in nearby_cities if any(t in c.types for t in cultural_types)]
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'adventure':
            # Find adventure cities: alpine, adventure, winter-sports, nature
            adventure_types = ['adventure', 'alpine', 'winter-sports', 'nature', 'skiing', 'outdoor']
            candidates = [c for c in nearby_cities if any(t in c.types for t in adventure_types)]
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'culinary':
            # Find culinary destinations
            culinary_types = ['culinary', 'wine', 'food', 'gastronomy']
            candidates = [c for c in nearby_cities if any(t in c.types for t in culinary_types)]
            # If not enough culinary-specific cities, add cultural cities (often have great food)
            if len(candidates) < 2:
                cultural_cities = [c for c in nearby_cities if 'cultural' in c.types]
                candidates.extend(cultural_cities[:2])
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'romantic':
            # Find romantic destinations
            romantic_types = ['romantic', 'scenic', 'lakes', 'coastal', 'luxury', 'historic']
            candidates = [c for c in nearby_cities if any(t in c.types for t in romantic_types)]
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'hidden_gems':
            # Find lesser-known, authentic destinations
            hidden_gem_types = ['hidden', 'local', 'authentic', 'village', 'traditional', 'offbeat']
            candidates = [c for c in nearby_cities if any(t in c.types for t in hidden_gem_types)]
            # If not enough hidden gems, look for smaller towns and medieval places
            if len(candidates) < 2:
                small_town_types = ['medieval', 'village', 'traditional', 'rural', 'authentic']
                more_candidates = [c for c in nearby_cities if any(t in c.types for t in small_town_types)]
                candidates.extend(more_candidates[:3])
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        else:
            # Default: select diverse cities near route
            return self._select_diverse_cities(nearby_cities, max_cities=max_cities, route_type=strategy_type, request=request)
    
    def _find_intermediate_cities_enhanced_sync(self, strategy: Dict, start_city, end_city, 
                                              request: TripRequest, max_cities: int) -> List:
        """Synchronous wrapper for enhanced intermediate city selection."""
        try:
            # Check if we can run async
            try:
                loop = asyncio.get_running_loop()
                # We're in an event loop, create a task
                logger.info("Using thread pool for enhanced city selection")
                import concurrent.futures
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            self.enhanced_intermediate_service.find_optimal_intermediate_cities(
                                start_city, end_city, request, strategy['type'], max_cities
                            )
                        )
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    return future.result(timeout=30)  # 30 second timeout
                    
            except RuntimeError:
                # No running loop, can use asyncio.run directly
                return asyncio.run(
                    self.enhanced_intermediate_service.find_optimal_intermediate_cities(
                        start_city, end_city, request, strategy['type'], max_cities
                    )
                )
                
        except Exception as e:
            logger.error(f"Enhanced city selection failed: {e}")
            return []
    
    async def _find_intermediate_cities_async(self, strategy: Dict, start_city, end_city, 
                                            request: TripRequest) -> List:
        """Find intermediate cities based on route strategy using async Google Places API."""
        strategy_type = strategy['type']
        
        # Calculate optimal number of intermediate cities based on trip duration and type
        max_cities = self._calculate_optimal_city_count(strategy_type, request.travel_days)
        
        logger.info("Dynamic city calculation (async)", 
                   strategy=strategy_type, 
                   trip_days=request.travel_days, 
                   max_cities=max_cities)
        
        # Get cities near the route using async API calls, filtered by route type
        nearby_cities = await self.city_service.find_cities_near_route(
            start_city.coordinates, end_city.coordinates, max_deviation_km=120, route_type=strategy_type
        )
        
        if strategy_type == 'scenic':
            # Find scenic cities: alpine, lakes, romantic, resort
            scenic_types = ['scenic', 'alpine', 'lakes', 'romantic', 'resort', 'coastal']
            candidates = [c for c in nearby_cities if any(t in c.types for t in scenic_types)]
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'cultural':
            # Find cultural/historic cities: unesco, historic, cultural, artistic
            cultural_types = ['cultural', 'historic', 'unesco', 'artistic', 'renaissance', 'medieval', 'roman']
            candidates = [c for c in nearby_cities if any(t in c.types for t in cultural_types)]
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'adventure':
            # Find adventure cities: alpine, adventure, winter-sports, nature
            adventure_types = ['adventure', 'alpine', 'winter-sports', 'nature', 'skiing', 'outdoor']
            candidates = [c for c in nearby_cities if any(t in c.types for t in adventure_types)]
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'culinary':
            # Find culinary destinations
            culinary_types = ['culinary', 'wine', 'food', 'gastronomy']
            candidates = [c for c in nearby_cities if any(t in c.types for t in culinary_types)]
            # If not enough culinary-specific cities, add cultural cities (often have great food)
            if len(candidates) < 2:
                cultural_cities = [c for c in nearby_cities if 'cultural' in c.types]
                candidates.extend(cultural_cities[:2])
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'romantic':
            # Find romantic destinations
            romantic_types = ['romantic', 'scenic', 'lakes', 'coastal', 'luxury', 'historic']
            candidates = [c for c in nearby_cities if any(t in c.types for t in romantic_types)]
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        elif strategy_type == 'hidden_gems':
            # Find lesser-known, authentic destinations
            hidden_gem_types = ['hidden', 'local', 'authentic', 'village', 'traditional', 'offbeat']
            candidates = [c for c in nearby_cities if any(t in c.types for t in hidden_gem_types)]
            # If not enough hidden gems, look for smaller towns and medieval places
            if len(candidates) < 2:
                small_town_types = ['medieval', 'village', 'traditional', 'rural', 'authentic']
                more_candidates = [c for c in nearby_cities if any(t in c.types for t in small_town_types)]
                candidates.extend(more_candidates[:3])
            return self._select_diverse_cities(candidates, max_cities=max_cities, route_type=strategy_type, request=request)
        
        else:
            # Default: select diverse cities near route
            return self._select_diverse_cities(nearby_cities, max_cities=max_cities, route_type=strategy_type, request=request)
    
    def _select_diverse_cities(self, candidates: List, max_cities: int, route_type: str = None, 
                             request = None) -> List:
        """Select diverse cities using ML recommendations when possible."""
        if not candidates:
            return []
        
        if len(candidates) <= max_cities:
            return candidates
        
        # Try to use ML recommendation system for intelligent selection
        try:
            from .ml_recommendation_service import MLRecommendationService, TripPreference
            
            if hasattr(self, 'ml_service') and self.ml_service:
                ml_service = self.ml_service
            else:
                # Initialize ML service if not available
                ml_service = MLRecommendationService(self.city_service)
                self.ml_service = ml_service
            
            # If we have request and route_type, use ML recommendations
            if request and route_type:
                trip_preferences = TripPreference(
                    budget_range=getattr(request, 'budget_range', 'mid-range'),
                    duration_days=getattr(request, 'travel_days', 7),
                    travel_style=route_type,
                    season=getattr(request, 'season', 'summer'),
                    group_size=2,
                    activity_preferences=getattr(request, 'interests', []),
                    previous_trips=[]
                )
                
                # Use moderate exploration for general route planning
                exploration_factor = 0.25
                
                # Create a temporary city service with just our candidates
                temp_service = type(self.city_service)(None)
                temp_service._city_cache = {city.name: city for city in candidates}
                temp_ml_service = MLRecommendationService(temp_service)
                
                # Get smart recommendations from our candidate pool
                ml_result = temp_ml_service.get_smart_recommendations(
                    preferences=trip_preferences,
                    start_city="dummy_start",  # Won't be used since we're filtering candidates
                    end_city="dummy_end",      # Won't be used since we're filtering candidates
                    exploration_factor=exploration_factor
                )
                
                if ml_result.success:
                    recommendations = ml_result.data['recommendations']
                    selected = [rec['city'] for rec in recommendations[:max_cities]]
                    logger.info("Used ML city selection", 
                               method="ml_diverse_selection",
                               cities_selected=len(selected))
                    return selected
                
        except Exception as e:
            logger.warning("ML city selection failed, using fallback", error=str(e))
        
        # Fallback to enhanced random selection with quality weighting
        import random
        
        # Sort by rating/popularity if available (handle None ratings)
        sorted_candidates = sorted(candidates, 
                                 key=lambda c: getattr(c, 'rating', None) or 0, 
                                 reverse=True)
        
        # Take top candidates (e.g., top 75% by rating) for quality selection
        quality_pool_size = max(max_cities * 2, len(sorted_candidates) // 2)
        quality_candidates = sorted_candidates[:quality_pool_size]
        
        # Shuffle the quality pool for randomization while maintaining quality
        random.shuffle(quality_candidates)
        
        selected = []
        used_countries = set()
        
        # First, try to get cities from different countries for diversity
        for city in quality_candidates:
            if len(selected) >= max_cities:
                break
            
            # Handle None country values
            city_country = city.country if city.country is not None else 'Unknown'
            
            if city_country not in used_countries:
                selected.append(city)
                used_countries.add(city_country)
        
        # If we still need more cities, randomly select from remaining quality candidates
        remaining_slots = max_cities - len(selected)
        if remaining_slots > 0:
            remaining_candidates = [c for c in quality_candidates if c not in selected]
            if remaining_candidates:
                # Randomly select from remaining candidates
                random.shuffle(remaining_candidates)
                selected.extend(remaining_candidates[:remaining_slots])
        
        return selected
    
    def _filter_cities_by_route(self, cities: List, start_city, end_city, 
                              max_cities: int = 2) -> List:
        """Filter cities to those reasonably close to the route."""
        if not cities:
            return []
        
        # Remove start and end cities from candidates
        candidates = [c for c in cities if c.name not in [start_city.name, end_city.name]]
        
        # Find cities near the route
        near_route = self.city_service.find_cities_near_route(
            start_city.coordinates, end_city.coordinates, max_deviation_km=100
        )
        
        # Get intersection of type-based and route-based cities
        filtered = [c for c in candidates if c.name in [nr.name for nr in near_route]]
        
        return filtered[:max_cities]
    
    def _enrich_route_data(self, route: TravelRoute, request: TripRequest, strategy: Dict = None) -> Dict[str, Any]:
        """Enrich route with additional data for frontend."""
        # Use strategy data if available for richer information
        strategy_name = strategy['name'] if strategy else route.route_type.value.replace('_', ' ').title() + ' Route'
        strategy_highlights = strategy.get('highlights', []) if strategy else []
        strategy_ideal_for = strategy.get('ideal_for', '') if strategy else ''
        
        return {
            'route_type': route.route_type.value,
            'name': strategy_name,
            'description': route.description,
            'total_distance_km': route.total_distance_km,
            'total_duration_hours': route.total_duration_hours,
            'estimated_driving_time': f"{route.total_duration_hours:.1f} hours",
            'start_city': {
                'name': route.start_city.name,
                'coordinates': [route.start_city.coordinates.latitude, 
                              route.start_city.coordinates.longitude]
            },
            'end_city': {
                'name': route.end_city.name,
                'coordinates': [route.end_city.coordinates.latitude, 
                              route.end_city.coordinates.longitude]
            },
            'intermediate_cities': self._enhance_cities_with_descriptions(
                route.intermediate_cities, strategy.get('type', 'scenic'), request
            ),
            'highlights': strategy_highlights,
            'ideal_for': strategy_ideal_for,
            'season_tips': self._get_season_tips(route, request.season),
            'estimated_cost': self._estimate_route_cost(route, request)
        }
    
    async def _enrich_route_with_itinerary(self, route: TravelRoute, request: TripRequest, 
                                         strategy: Dict, start_city, end_city) -> Dict[str, Any]:
        """Enrich route with complete itinerary data."""
        # Get basic route enrichment
        enriched_route = self._enrich_route_data(route, request, strategy)
        
        # Convert intermediate cities to format expected by itinerary generator
        intermediate_cities_for_itinerary = []
        for city in route.intermediate_cities:
            intermediate_cities_for_itinerary.append({
                'city': {
                    'name': city.name,
                    'country': city.country,
                    'region': city.region,
                    'coordinates': [city.coordinates.latitude, city.coordinates.longitude],
                    'types': city.types
                },
                'stay_duration': {'recommended_nights': 1},
                'recommendation_score': 4.0,
                'why_visit': [f'Perfect for {strategy["name"].lower()} experience'],
                'best_for': strategy.get('highlights', []),
            })
        
        # Generate complete day-by-day itinerary for this specific route
        itinerary_result = await self.itinerary_generator.generate_complete_itinerary(
            start_city, end_city, request, trip_type="away"
        )
        
        if itinerary_result.success:
            itinerary_data = itinerary_result.data
            # Use route-specific intermediate cities instead of generic ones
            enriched_route['daily_itinerary'] = await self.itinerary_generator._create_daily_itinerary(
                start_city, end_city, intermediate_cities_for_itinerary, request
            )
            enriched_route['trip_summary'] = itinerary_data.get('trip_summary', {})
            enriched_route['travel_tips'] = itinerary_data.get('travel_tips', {})
        
        return enriched_route
    
    def _enrich_route_with_itinerary_sync(self, route: TravelRoute, request: TripRequest, 
                                        strategy: Dict, start_city, end_city) -> Dict[str, Any]:
        """Enrich route with complete itinerary data (sync version)."""
        # Get basic route enrichment
        enriched_route = self._enrich_route_data(route, request, strategy)
        
        # Convert intermediate cities to format expected by itinerary generator
        intermediate_cities_for_itinerary = []
        for city in route.intermediate_cities:
            intermediate_cities_for_itinerary.append({
                'city': {
                    'name': city.name,
                    'country': city.country,
                    'region': city.region,
                    'coordinates': [city.coordinates.latitude, city.coordinates.longitude],
                    'types': city.types
                },
                'stay_duration': {'recommended_nights': 1},
                'recommendation_score': 4.0,
                'why_visit': [f'Perfect for {strategy["name"].lower()} experience'],
                'best_for': strategy.get('highlights', []),
            })
        
        # Generate complete day-by-day itinerary for this specific route (sync version)
        try:
            # Use asyncio.run for the async itinerary generation
            import asyncio
            itinerary_data = asyncio.run(self.itinerary_generator._create_daily_itinerary(
                start_city, end_city, intermediate_cities_for_itinerary, request
            ))
            enriched_route['daily_itinerary'] = itinerary_data
        except Exception as e:
            logger.error(f"Failed to generate sync itinerary: {e}")
            enriched_route['daily_itinerary'] = []
        
        return enriched_route
    
    def _enhance_cities_with_descriptions(self, cities: List, route_type: str, request) -> List[Dict]:
        """Enhance cities with AI-generated descriptions."""
        try:
            enhanced_cities = []
            for city in cities:
                # Get description synchronously (the service handles async internally)
                import asyncio
                try:
                    # Try to get existing event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in an async context, create task
                        import concurrent.futures
                        def get_desc():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(
                                    self.description_service.get_city_description(city, route_type, request)
                                )
                            finally:
                                new_loop.close()
                        
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            description = executor.submit(get_desc).result(timeout=10)
                    else:
                        # No running loop
                        description = asyncio.run(
                            self.description_service.get_city_description(city, route_type, request)
                        )
                except Exception:
                    # Fallback: run in new event loop
                    description = asyncio.run(
                        self.description_service.get_city_description(city, route_type, request)
                    )
                
                enhanced_city = {
                    'name': city.name,
                    'country': city.country,
                    'coordinates': [city.coordinates.latitude, city.coordinates.longitude],
                    'types': city.types,
                    'region': city.region,
                    'description': {
                        'short': description.short_description,
                        'detailed': description.detailed_description,
                        'highlights': description.highlights,
                        'best_for': description.best_for,
                        'hidden_gems': description.hidden_gems,
                        'practical_info': description.practical_info,
                        'why_visit': description.why_visit_reason,
                        'photo_keywords': description.photo_keywords
                    }
                }
                enhanced_cities.append(enhanced_city)
            
            return enhanced_cities
            
        except Exception as e:
            logger.warning(f"Failed to enhance cities with descriptions: {e}")
            # Fallback to basic city data
            return [
                {
                    'name': city.name,
                    'country': city.country,
                    'coordinates': [city.coordinates.latitude, city.coordinates.longitude],
                    'types': city.types,
                    'region': city.region,
                    'description': {
                        'short': f"A charming destination in {city.country}",
                        'why_visit': f"Experience the unique character of {city.name}"
                    }
                }
                for city in cities
            ]
    
    def _get_season_tips(self, route: TravelRoute, season) -> List[str]:
        """Get season-specific tips for the route."""
        tips = []
        
        # Handle both enum and string seasons
        season_value = season.value if hasattr(season, 'value') else season
        
        if season_value == 'winter':
            tips.append("Check weather conditions and carry winter equipment")
            tips.append("Some mountain passes may be closed")
        elif season_value == 'summer':
            tips.append("Book accommodations early due to high season")
            tips.append("Consider early morning starts to avoid traffic")
        elif season_value == 'spring':
            tips.append("Perfect weather for outdoor activities")
            tips.append("Check for seasonal road closures in mountainous areas")
        elif season_value == 'autumn':
            tips.append("Beautiful fall foliage but weather can be unpredictable")
            tips.append("Book accommodations early for popular destinations")
        
        return tips
    
    def _estimate_route_cost(self, route: TravelRoute, request: TripRequest) -> Dict[str, float]:
        """Estimate costs for the route."""
        # Basic cost estimation
        fuel_cost = route.total_distance_km * 0.08  # €0.08 per km
        accommodation_cost = request.travel_days * 80  # €80 per night average
        
        return {
            'fuel_estimate': round(fuel_cost, 2),
            'accommodation_estimate': round(accommodation_cost, 2),
            'total_estimate': round(fuel_cost + accommodation_cost, 2)
        }
    
    def _initialize_route_strategies(self) -> List[Dict[str, Any]]:
        """Initialize route strategy configurations."""
        return [
            {
                'name': 'Scenic Mountain & Lakes Route',
                'type': 'scenic',
                'description': 'Journey through breathtaking Alpine landscapes, pristine lakes, and mountain vistas. Perfect for nature lovers and photographers.',
                'highlights': ['Mountain passes', 'Lake views', 'Scenic overlooks', 'National parks'],
                'ideal_for': 'Nature enthusiasts, photographers, romantic getaways'
            },
            {
                'name': 'Cultural Heritage Route',
                'type': 'cultural',
                'description': 'Explore UNESCO World Heritage sites, historic city centers, and cultural landmarks spanning centuries of European history.',
                'highlights': ['UNESCO sites', 'Historic centers', 'Museums', 'Architecture'],
                'ideal_for': 'History buffs, art lovers, cultural explorers'
            },
            {
                'name': 'Adventure & Activities Route',
                'type': 'adventure',
                'description': 'Action-packed journey featuring outdoor activities like hiking, skiing, water sports, and unique experiences.',
                'highlights': ['Outdoor activities', 'Adventure sports', 'Unique experiences', 'Active exploration'],
                'ideal_for': 'Thrill seekers, active travelers, outdoor enthusiasts'
            },
            {
                'name': 'Culinary & Wine Route',
                'type': 'culinary',
                'description': 'Savor Europe\'s finest cuisines, visit local markets, wine regions, and discover gastronomic treasures.',
                'highlights': ['Local cuisine', 'Wine regions', 'Food markets', 'Cooking experiences'],
                'ideal_for': 'Food lovers, wine enthusiasts, culinary explorers'
            },
            {
                'name': 'Romantic Escape Route',
                'type': 'romantic',
                'description': 'Intimate journey through Europe\'s most romantic destinations, perfect for couples seeking enchanting experiences.',
                'highlights': ['Romantic settings', 'Intimate venues', 'Sunset views', 'Couple activities'],
                'ideal_for': 'Couples, honeymoons, romantic getaways'
            },
            {
                'name': 'Hidden Gems Route',
                'type': 'hidden_gems',
                'description': 'Discover Europe\'s best-kept secrets and off-the-beaten-path destinations that most tourists never see.',
                'highlights': ['Lesser-known towns', 'Local secrets', 'Unique experiences', 'Authentic culture'],
                'ideal_for': 'Adventurous explorers, authentic travel seekers, curious wanderers'
            }
        ]
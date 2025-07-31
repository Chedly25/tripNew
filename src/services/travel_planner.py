"""
Main travel planning service orchestrating all components.
"""
from typing import List, Dict, Any
import structlog
from ..core.interfaces import TravelPlannerService
from ..core.models import TripRequest, ServiceResult, TravelRoute, RouteType
from ..core.exceptions import TravelPlannerException
from .city_service import CityService
from .route_service import ProductionRouteService
from .validation_service import ValidationService

logger = structlog.get_logger(__name__)


class TravelPlannerServiceImpl(TravelPlannerService):
    """Main travel planning service with proper architecture."""
    
    def __init__(self, city_service: CityService, route_service: ProductionRouteService,
                 validation_service: ValidationService):
        self.city_service = city_service
        self.route_service = route_service
        self.validation_service = validation_service
        self._route_strategies = self._initialize_route_strategies()
    
    def generate_routes(self, request: TripRequest) -> ServiceResult:
        """Generate multiple route options for the trip request."""
        try:
            logger.info("Generating routes", 
                       start=request.start_city, 
                       end=request.end_city,
                       days=request.travel_days)
            
            # Get start and end cities
            start_city = self.city_service.get_city_by_name(request.start_city)
            if not start_city:
                return ServiceResult.error_result(f"Start city not found: {request.start_city}")
            
            end_city = self.city_service.get_city_by_name(request.end_city)
            if not end_city:
                return ServiceResult.error_result(f"End city not found: {request.end_city}")
            
            # Generate routes for different strategies
            routes = []
            for strategy in self._route_strategies:
                route_result = self._generate_route_for_strategy(
                    strategy, start_city, end_city, request
                )
                if route_result.success:
                    routes.append(route_result.data)
                else:
                    logger.warning("Route generation failed", 
                                 strategy=strategy['name'],
                                 error=route_result.error_message)
            
            if not routes:
                return ServiceResult.error_result("No routes could be generated")
            
            return ServiceResult.success_result({
                'routes': routes,
                'request': request,
                'start_city': start_city,
                'end_city': end_city
            })
            
        except Exception as e:
            logger.error("Route generation failed", error=str(e))
            return ServiceResult.error_result(f"Route generation failed: {e}")
    
    def get_route_details(self, route_id: str) -> ServiceResult:
        """Get detailed information for a specific route."""
        # Implementation for route details
        # This would typically load from cache or database
        return ServiceResult.error_result("Route details not implemented")
    
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
            
            # Enrich with additional data
            enriched_route = self._enrich_route_data(travel_route, request)
            
            return ServiceResult.success_result(enriched_route)
            
        except Exception as e:
            logger.error("Strategy route generation failed", 
                        strategy=strategy['name'], error=str(e))
            return ServiceResult.error_result(f"Route generation failed: {e}")
    
    def _find_intermediate_cities(self, strategy: Dict, start_city, end_city, 
                                request: TripRequest) -> List:
        """Find intermediate cities based on route strategy."""
        strategy_type = strategy['type']
        
        if strategy_type == 'fastest':
            # Direct route - no intermediates
            return []
        
        elif strategy_type == 'scenic':
            # Find scenic cities near the route
            cities = self.city_service.find_cities_by_type('scenic')
            return self._filter_cities_by_route(cities, start_city, end_city, max_cities=2)
        
        elif strategy_type == 'cultural':
            # Find cultural/historic cities
            cities = self.city_service.find_cities_by_type('cultural')
            return self._filter_cities_by_route(cities, start_city, end_city, max_cities=3)
        
        elif strategy_type == 'culinary':
            # Find culinary destinations
            cities = self.city_service.find_cities_by_type('culinary')
            return self._filter_cities_by_route(cities, start_city, end_city, max_cities=2)
        
        else:
            # Default: find cities near route
            return self.city_service.find_cities_near_route(
                start_city.coordinates, end_city.coordinates, max_deviation_km=80
            )[:2]  # Limit to 2 cities
    
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
    
    def _enrich_route_data(self, route: TravelRoute, request: TripRequest) -> Dict[str, Any]:
        """Enrich route with additional data for frontend."""
        return {
            'route_type': route.route_type.value,
            'name': route.route_type.value.replace('_', ' ').title() + ' Route',
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
            'intermediate_cities': [
                {
                    'name': city.name,
                    'coordinates': [city.coordinates.latitude, city.coordinates.longitude],
                    'types': city.types
                }
                for city in route.intermediate_cities
            ],
            'season_tips': self._get_season_tips(route, request.season),
            'estimated_cost': self._estimate_route_cost(route, request)
        }
    
    def _get_season_tips(self, route: TravelRoute, season) -> List[str]:
        """Get season-specific tips for the route."""
        tips = []
        
        if season.value == 'winter':
            tips.append("Check weather conditions and carry winter equipment")
            tips.append("Some mountain passes may be closed")
        elif season.value == 'summer':
            tips.append("Book accommodations early due to high season")
            tips.append("Consider early morning starts to avoid traffic")
        
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
                'name': 'Fastest Direct Route',
                'type': 'fastest',
                'description': 'Optimize for minimal driving time and maximum time at destinations'
            },
            {
                'name': 'Scenic Route',
                'type': 'scenic',
                'description': 'Beautiful landscapes and scenic viewpoints along the way'
            },
            {
                'name': 'Cultural Route',
                'type': 'cultural',
                'description': 'Visit UNESCO World Heritage sites and cultural landmarks'
            },
            {
                'name': 'Culinary Route',
                'type': 'culinary',
                'description': 'Experience regional cuisines and local food traditions'
            },
            {
                'name': 'Budget Route',
                'type': 'budget',
                'description': 'Cost-optimized route with affordable stops and accommodations'
            }
        ]
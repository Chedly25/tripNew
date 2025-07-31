"""
Advanced route optimization engine that combines real-world data from all services
to generate optimal European roadtrip routes based on multiple criteria.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import math
import logging
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.routing_service import RoutingService
from services.weather_service import WeatherService
from services.event_service import EventService
from services.accommodation_service import AccommodationService
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class RouteStop:
    """Represents a stop along the route"""
    name: str
    lat: float
    lon: float
    arrival_date: datetime
    departure_date: datetime
    nights: int
    city_type: str  # 'major', 'medium', 'small'
    recommended_duration: float  # hours to spend exploring

@dataclass
class RouteSegment:
    """Represents a segment between two stops"""
    from_stop: str
    to_stop: str
    distance_km: float
    duration_hours: float
    fuel_cost: float
    toll_cost: float
    weather_score: float
    traffic_delay_minutes: float

@dataclass
class OptimizedRoute:
    """Complete optimized route with all details"""
    route_id: str
    name: str
    strategy: str
    total_distance_km: float
    total_duration_hours: float
    total_cost: float
    stops: List[RouteStop]
    segments: List[RouteSegment]
    weather_score: float
    event_score: float
    overall_score: float
    accommodation_costs: Dict[str, Any]
    events: Dict[str, List[Dict]]
    best_travel_dates: List[datetime]
    highlights: List[str]
    warnings: List[str]

class RouteOptimizer:
    """Advanced route optimization engine"""
    
    def __init__(self):
        self.routing_service = RoutingService()
        self.weather_service = WeatherService()
        self.event_service = EventService()
        self.accommodation_service = AccommodationService()
        
        # Route strategies with their priorities
        self.strategies = {
            'fastest': {
                'traffic_weight': 0.5,
                'event_weight': 0.1,
                'weather_weight': 0.2,
                'cost_weight': 0.2,
                'scenic_weight': 0.0
            },
            'scenic': {
                'traffic_weight': 0.1,
                'event_weight': 0.2,
                'weather_weight': 0.3,
                'cost_weight': 0.1,
                'scenic_weight': 0.3
            },
            'cultural': {
                'traffic_weight': 0.1,
                'event_weight': 0.4,
                'weather_weight': 0.2,
                'cost_weight': 0.1,
                'scenic_weight': 0.2
            },
            'budget': {
                'traffic_weight': 0.2,
                'event_weight': 0.1,
                'weather_weight': 0.2,
                'cost_weight': 0.5,
                'scenic_weight': 0.0
            },
            'weather_optimized': {
                'traffic_weight': 0.1,
                'event_weight': 0.2,
                'weather_weight': 0.5,
                'cost_weight': 0.1,
                'scenic_weight': 0.1
            },
            'event_focused': {
                'traffic_weight': 0.1,
                'event_weight': 0.5,
                'weather_weight': 0.2,
                'cost_weight': 0.1,
                'scenic_weight': 0.1
            },
            'adventure': {
                'traffic_weight': 0.1,
                'event_weight': 0.3,
                'weather_weight': 0.3,
                'cost_weight': 0.1,
                'scenic_weight': 0.2
            },
            'luxury': {
                'traffic_weight': 0.2,
                'event_weight': 0.3,
                'weather_weight': 0.2,
                'cost_weight': 0.0,
                'scenic_weight': 0.3
            }
        }
    
    async def optimize_routes(self, start_city: str, end_city: str, 
                            intermediate_cities: List[str],
                            travel_days: int, start_date: datetime,
                            budget_level: str = 'mid_range',
                            travel_style: str = 'cultural') -> List[OptimizedRoute]:
        """Generate multiple optimized routes using different strategies"""
        
        logger.info(f"Starting route optimization: {start_city} -> {end_city}")
        
        # Geocode all cities
        all_cities = [start_city] + intermediate_cities + [end_city]
        city_coords = await self._geocode_cities(all_cities)
        
        if not city_coords:
            raise ValueError("Could not geocode cities")
        
        # Generate routes for all strategies
        optimized_routes = []
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for strategy_name, weights in self.strategies.items():
                future = executor.submit(
                    self._optimize_single_route,
                    strategy_name, weights, city_coords, travel_days,
                    start_date, budget_level, travel_style
                )
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    route = future.result()
                    if route:
                        optimized_routes.append(route)
                except Exception as e:
                    logger.error(f"Route optimization error: {e}")
        
        # Sort by overall score
        optimized_routes.sort(key=lambda r: r.overall_score, reverse=True)
        
        return optimized_routes[:8]  # Return top 8 routes
    
    async def _geocode_cities(self, cities: List[str]) -> Dict[str, Tuple[float, float]]:
        """Geocode all cities in parallel"""
        city_coords = {}
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(self.routing_service.geocode_city, city): city 
                for city in cities
            }
            
            for future in as_completed(futures):
                city = futures[future]
                try:
                    result = future.result()
                    if result:
                        city_coords[city] = (result['lat'], result['lon'])
                    else:
                        logger.warning(f"Could not geocode {city}")
                except Exception as e:
                    logger.error(f"Geocoding error for {city}: {e}")
        
        return city_coords
    
    def _optimize_single_route(self, strategy: str, weights: Dict[str, float],
                              city_coords: Dict[str, Tuple[float, float]],
                              travel_days: int, start_date: datetime,
                              budget_level: str, travel_style: str) -> Optional[OptimizedRoute]:
        """Optimize a single route using the given strategy"""
        
        try:
            cities = list(city_coords.keys())
            
            # Create route stops with optimized timing
            stops = self._create_route_stops(cities, city_coords, travel_days, start_date, strategy)
            
            # Calculate route segments
            segments = self._calculate_route_segments(stops, weights)
            
            # Get comprehensive data
            route_data = self._gather_route_data(stops, start_date, budget_level)
            
            # Calculate scores
            scores = self._calculate_route_scores(segments, route_data, weights)
            
            # Generate highlights and warnings
            highlights, warnings = self._generate_insights(route_data, segments, strategy)
            
            # Create optimized route object
            route = OptimizedRoute(
                route_id=f"route_{strategy}_{int(datetime.now().timestamp())}",
                name=self._generate_route_name(strategy, cities),
                strategy=strategy,
                total_distance_km=sum(s.distance_km for s in segments),
                total_duration_hours=sum(s.duration_hours for s in segments),
                total_cost=self._calculate_total_cost(segments, route_data['accommodation_costs']),
                stops=stops,
                segments=segments,
                weather_score=scores['weather_score'],
                event_score=scores['event_score'],
                overall_score=scores['overall_score'],
                accommodation_costs=route_data['accommodation_costs'],
                events=route_data['events'],
                best_travel_dates=[stop.arrival_date for stop in stops],
                highlights=highlights,
                warnings=warnings
            )
            
            return route
            
        except Exception as e:
            logger.error(f"Error optimizing {strategy} route: {e}")
            return None
    
    def _create_route_stops(self, cities: List[str], 
                           city_coords: Dict[str, Tuple[float, float]],
                           travel_days: int, start_date: datetime,
                           strategy: str) -> List[RouteStop]:
        """Create optimized route stops with timing"""
        
        stops = []
        current_date = start_date
        
        # Calculate days per city based on strategy
        days_distribution = self._distribute_travel_days(cities, travel_days, strategy)
        
        for i, city in enumerate(cities):
            if city not in city_coords:
                continue
                
            lat, lon = city_coords[city]
            days_in_city = days_distribution[i]
            
            # Determine city type
            city_type = self._classify_city(city)
            
            # Calculate recommended exploration time
            recommended_hours = self._get_recommended_exploration_time(city, city_type, strategy)
            
            if i == 0:  # Start city
                departure_date = current_date + timedelta(days=days_in_city)
                nights = days_in_city - 1 if days_in_city > 1 else 0
            elif i == len(cities) - 1:  # End city
                departure_date = current_date + timedelta(days=days_in_city)
                nights = days_in_city
            else:  # Intermediate city
                departure_date = current_date + timedelta(days=days_in_city)
                nights = days_in_city - 1 if days_in_city > 0 else 0
            
            stop = RouteStop(
                name=city,
                lat=lat,
                lon=lon,
                arrival_date=current_date,
                departure_date=departure_date,
                nights=nights,
                city_type=city_type,
                recommended_duration=recommended_hours
            )
            
            stops.append(stop)
            current_date = departure_date
        
        return stops
    
    def _distribute_travel_days(self, cities: List[str], total_days: int, strategy: str) -> List[int]:
        """Distribute travel days among cities based on strategy"""
        
        num_cities = len(cities)
        if num_cities <= 2:
            return [total_days // 2, total_days - total_days // 2]
        
        # Base distribution
        base_days = max(1, total_days // num_cities)
        remaining_days = total_days - (base_days * num_cities)
        
        distribution = [base_days] * num_cities
        
        # Strategy-based adjustments
        if strategy == 'cultural':
            # Give more time to major cultural cities
            major_cities = ['paris', 'rome', 'barcelona', 'vienna', 'florence']
            for i, city in enumerate(cities):
                if city.lower() in major_cities and remaining_days > 0:
                    distribution[i] += 1
                    remaining_days -= 1
        
        elif strategy == 'scenic':
            # More even distribution for scenic routes
            pass  # Keep base distribution
        
        elif strategy == 'fastest':
            # Minimize intermediate stops
            if num_cities > 2:
                # Give extra days to start and end cities
                distribution[0] += remaining_days // 2
                distribution[-1] += remaining_days - remaining_days // 2
                remaining_days = 0
        
        # Distribute any remaining days
        for i in range(remaining_days):
            distribution[i % num_cities] += 1
        
        return distribution
    
    def _classify_city(self, city: str) -> str:
        """Classify city size/importance"""
        major_cities = ['paris', 'rome', 'barcelona', 'madrid', 'milan', 'vienna', 'munich', 'berlin']
        medium_cities = ['florence', 'venice', 'nice', 'lyon', 'seville', 'prague', 'salzburg']
        
        city_lower = city.lower()
        if city_lower in major_cities:
            return 'major'
        elif city_lower in medium_cities:
            return 'medium'
        else:
            return 'small'
    
    def _get_recommended_exploration_time(self, city: str, city_type: str, strategy: str) -> float:
        """Get recommended hours to explore a city"""
        base_hours = {
            'major': 16,
            'medium': 12,
            'small': 8
        }
        
        hours = base_hours[city_type]
        
        # Strategy adjustments
        if strategy == 'cultural':
            hours *= 1.3
        elif strategy == 'fastest':
            hours *= 0.7
        elif strategy == 'scenic':
            hours *= 1.1
        
        return hours
    
    def _calculate_route_segments(self, stops: List[RouteStop], 
                                 weights: Dict[str, float]) -> List[RouteSegment]:
        """Calculate route segments between stops"""
        segments = []
        
        for i in range(len(stops) - 1):
            from_stop = stops[i]
            to_stop = stops[i + 1]
            
            # Get routing data
            route_data = self.routing_service.get_route_with_traffic(
                (from_stop.lat, from_stop.lon),
                (to_stop.lat, to_stop.lon),
                departure_time=from_stop.departure_date
            )
            
            if route_data:
                # Get weather for travel day
                weather_forecast = self.weather_service.get_weather_forecast(
                    from_stop.lat, from_stop.lon, 1
                )
                weather_score = weather_forecast['current']['score'] if weather_forecast else 0.7
                
                # Estimate costs
                country = self._get_country_from_city(from_stop.name)
                fuel_cost = self.routing_service.estimate_fuel_cost(
                    route_data['distance_km'], country
                )
                toll_cost = self.routing_service.estimate_toll_cost(
                    route_data['distance_km'], country
                )
                
                segment = RouteSegment(
                    from_stop=from_stop.name,
                    to_stop=to_stop.name,
                    distance_km=route_data['distance_km'],
                    duration_hours=route_data['duration_in_traffic_hours'],
                    fuel_cost=fuel_cost,
                    toll_cost=toll_cost,
                    weather_score=weather_score,
                    traffic_delay_minutes=route_data['traffic_delay_minutes']
                )
                
                segments.append(segment)
        
        return segments
    
    def _get_country_from_city(self, city: str) -> str:
        """Get country from city name (simplified mapping)"""
        city_country_map = {
            'paris': 'france', 'lyon': 'france', 'nice': 'france', 'marseille': 'france',
            'rome': 'italy', 'milan': 'italy', 'florence': 'italy', 'venice': 'italy',
            'barcelona': 'spain', 'madrid': 'spain', 'seville': 'spain', 'valencia': 'spain',
            'berlin': 'germany', 'munich': 'germany', 'hamburg': 'germany',
            'vienna': 'austria', 'salzburg': 'austria',
            'zurich': 'switzerland', 'geneva': 'switzerland'
        }
        
        return city_country_map.get(city.lower(), 'france')  # Default to France
    
    def _gather_route_data(self, stops: List[RouteStop], start_date: datetime, 
                          budget_level: str) -> Dict[str, Any]:
        """Gather comprehensive data for the route"""
        
        cities = [stop.name for stop in stops]
        city_coords = [(stop.name, stop.lat, stop.lon) for stop in stops]
        
        # Get events for all cities
        events = self.event_service.get_events_for_route(
            city_coords, start_date, start_date + timedelta(days=14)
        )
        
        # Get accommodation costs
        nights_per_city = [stop.nights for stop in stops]
        accommodation_costs = self.accommodation_service.estimate_accommodation_costs(
            cities, nights_per_city, budget_level
        )
        
        return {
            'events': events,
            'accommodation_costs': accommodation_costs
        }
    
    def _calculate_route_scores(self, segments: List[RouteSegment], 
                               route_data: Dict[str, Any],
                               weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate comprehensive route scores"""
        
        # Weather score (average of all segments)
        weather_score = sum(s.weather_score for s in segments) / len(segments) if segments else 0.7
        
        # Event score
        event_score = self.event_service.calculate_route_event_score(
            [s.from_stop for s in segments] + [segments[-1].to_stop] if segments else [],
            route_data['events']
        )
        
        # Traffic efficiency score (lower delay = higher score)
        avg_delay = sum(s.traffic_delay_minutes for s in segments) / len(segments) if segments else 0
        traffic_score = max(0, 1.0 - (avg_delay / 60))  # Normalize by hour
        
        # Cost efficiency score
        total_cost = self._calculate_total_cost(segments, route_data['accommodation_costs'])
        cost_score = max(0, 1.0 - (total_cost / 2000))  # Normalize by €2000
        
        # Scenic score (based on route diversity and city types)
        scenic_score = 0.8  # Base score, would be enhanced with real scenic data
        
        # Calculate weighted overall score
        overall_score = (
            weather_score * weights['weather_weight'] +
            event_score * weights['event_weight'] +
            traffic_score * weights['traffic_weight'] +
            cost_score * weights['cost_weight'] +
            scenic_score * weights['scenic_weight']
        )
        
        return {
            'weather_score': weather_score,
            'event_score': event_score,
            'traffic_score': traffic_score,
            'cost_score': cost_score,
            'scenic_score': scenic_score,
            'overall_score': overall_score
        }
    
    def _calculate_total_cost(self, segments: List[RouteSegment], 
                             accommodation_costs: Dict[str, Any]) -> float:
        """Calculate total trip cost"""
        
        # Transportation costs
        transport_cost = sum(s.fuel_cost + s.toll_cost for s in segments)
        
        # Accommodation costs
        accommodation_cost = accommodation_costs.get('total_cost', 0)
        
        # Add estimated food and activities (€50 per day per person)
        # This would be more sophisticated with real data
        estimated_days = len(segments) + 2
        food_activities_cost = estimated_days * 50
        
        return transport_cost + accommodation_cost + food_activities_cost
    
    def _generate_route_name(self, strategy: str, cities: List[str]) -> str:
        """Generate a descriptive route name"""
        
        strategy_names = {
            'fastest': 'Express Route',
            'scenic': 'Scenic Journey',
            'cultural': 'Cultural Discovery',
            'budget': 'Budget Adventure',
            'weather_optimized': 'Perfect Weather Route',
            'event_focused': 'Festival & Events Tour',
            'adventure': 'Adventure Trail',
            'luxury': 'Luxury Experience'
        }
        
        base_name = strategy_names.get(strategy, strategy.title())
        
        if len(cities) >= 2:
            return f"{base_name}: {cities[0]} to {cities[-1]}"
        else:
            return base_name
    
    def _generate_insights(self, route_data: Dict[str, Any], 
                          segments: List[RouteSegment], 
                          strategy: str) -> Tuple[List[str], List[str]]:
        """Generate route highlights and warnings"""
        
        highlights = []
        warnings = []
        
        # Event highlights
        total_events = sum(len(events) for events in route_data['events'].values())
        if total_events > 5:
            highlights.append(f"Rich cultural calendar with {total_events} events")
        
        # Weather highlights/warnings
        avg_weather = sum(s.weather_score for s in segments) / len(segments) if segments else 0.7
        if avg_weather > 0.8:
            highlights.append("Excellent weather conditions expected")
        elif avg_weather < 0.4:
            warnings.append("Poor weather conditions - consider postponing")
        
        # Traffic warnings
        high_traffic_segments = [s for s in segments if s.traffic_delay_minutes > 30]
        if high_traffic_segments:
            warnings.append(f"Heavy traffic expected on {len(high_traffic_segments)} segments")
        
        # Cost insights
        total_cost = self._calculate_total_cost(segments, route_data['accommodation_costs'])
        if total_cost > 1500:
            warnings.append("High trip cost - consider budget optimizations")
        elif total_cost < 600:
            highlights.append("Excellent value for money")
        
        # Strategy-specific insights
        if strategy == 'cultural':
            major_events = []
            for events in route_data['events'].values():
                major_events.extend([e for e in events if e.get('impact_score', 0) > 1.5])
            if major_events:
                highlights.append(f"Features {len(major_events)} major cultural events")
        
        return highlights, warnings
    
    def get_route_alternatives(self, base_route: OptimizedRoute, 
                              num_alternatives: int = 3) -> List[OptimizedRoute]:
        """Generate alternative routes based on a base route"""
        
        alternatives = []
        
        # Try different strategies
        alternative_strategies = ['scenic', 'budget', 'weather_optimized']
        
        for strategy in alternative_strategies[:num_alternatives]:
            if strategy != base_route.strategy:
                # Create alternative with different weights
                weights = self.strategies[strategy]
                
                # Recalculate scores with new weights
                scores = self._calculate_route_scores(
                    base_route.segments, 
                    {
                        'events': base_route.events,
                        'accommodation_costs': base_route.accommodation_costs
                    },
                    weights
                )
                
                # Create alternative route
                alt_route = OptimizedRoute(
                    route_id=f"alt_{strategy}_{int(datetime.now().timestamp())}",
                    name=self._generate_route_name(strategy, [s.name for s in base_route.stops]),
                    strategy=strategy,
                    total_distance_km=base_route.total_distance_km,
                    total_duration_hours=base_route.total_duration_hours,
                    total_cost=base_route.total_cost,
                    stops=base_route.stops,
                    segments=base_route.segments,
                    weather_score=scores['weather_score'],
                    event_score=scores['event_score'],
                    overall_score=scores['overall_score'],
                    accommodation_costs=base_route.accommodation_costs,
                    events=base_route.events,
                    best_travel_dates=base_route.best_travel_dates,
                    highlights=base_route.highlights,
                    warnings=base_route.warnings
                )
                
                alternatives.append(alt_route)
        
        return alternatives
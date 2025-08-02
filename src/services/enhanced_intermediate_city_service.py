"""
Enhanced Intermediate City Selection Service

Combines multiple data sources, smart algorithms, and user preferences
to select optimal intermediate cities for travel routes.
"""
import asyncio
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog

from ..core.models import City, Coordinates, TripRequest
from .enhanced_city_service import get_enhanced_city_service
from .opentripmap_service import get_opentripmap_service
from .ml_recommendation_service import MLRecommendationService, TripPreference
from .preference_scoring_service import get_preference_scoring_service, UserPreferences
from .route_optimization_service import get_route_optimization_service

logger = structlog.get_logger(__name__)


@dataclass
class CityScore:
    """Comprehensive scoring for intermediate cities."""
    city: City
    distance_score: float       # How well positioned along route
    preference_score: float     # Match to user preferences  
    diversity_score: float      # Adds variety to route
    popularity_score: float     # Tourist appeal
    accessibility_score: float  # Ease of access
    timing_score: float         # Seasonal/time relevance
    budget_score: float         # Fits budget constraints
    total_score: float          # Weighted combination
    reasons: List[str]          # Why this city was selected


@dataclass
class RouteOptimization:
    """Route optimization settings."""
    max_detour_km: float = 50   # Max detour from direct route
    min_stop_distance_km: float = 80  # Min distance between stops
    max_stop_distance_km: float = 200 # Max distance between stops
    prefer_even_spacing: bool = True   # Prefer evenly spaced stops


class EnhancedIntermediateCityService:
    """Advanced intermediate city selection with multi-source integration."""
    
    def __init__(self, city_service, ml_service: MLRecommendationService = None):
        self.city_service = city_service
        self.enhanced_city_service = get_enhanced_city_service()
        self.opentripmap_service = get_opentripmap_service()
        self.ml_service = ml_service or MLRecommendationService(city_service)
        self.preference_service = get_preference_scoring_service()
        self.route_optimizer = get_route_optimization_service()
        
        # Scoring weights for different factors
        self.scoring_weights = {
            'distance': 0.25,      # Route positioning
            'preference': 0.30,    # User preference match
            'diversity': 0.15,     # Route variety
            'popularity': 0.15,    # Tourist appeal
            'accessibility': 0.05, # Ease of access
            'timing': 0.05,        # Seasonal relevance
            'budget': 0.05         # Budget fit
        }
    
    async def find_optimal_intermediate_cities(
        self, 
        start_city: City, 
        end_city: City, 
        request: TripRequest,
        route_type: str,
        max_cities: int = 6
    ) -> List[City]:
        """Find optimal intermediate cities using enhanced multi-source algorithm."""
        
        logger.info("Finding optimal intermediate cities", 
                   start=start_city.name, 
                   end=end_city.name, 
                   route_type=route_type,
                   max_cities=max_cities)
        
        # Step 1: Gather candidates from multiple sources
        candidates = await self._gather_candidate_cities(
            start_city, end_city, request, route_type
        )
        
        if not candidates:
            logger.warning("No candidate cities found")
            return []
        
        logger.info(f"Found {len(candidates)} candidate cities")
        
        # Step 2: Score all candidates comprehensively
        scored_cities = await self._score_candidates(
            candidates, start_city, end_city, request, route_type
        )
        
        # Step 3: Advanced route optimization using multiple algorithms
        optimized_route = await self._advanced_route_optimization(
            scored_cities, start_city, end_city, max_cities, route_type, request
        )
        
        # Step 4: Final validation and adjustments
        final_cities = self._validate_and_adjust_route(
            optimized_route, start_city, end_city, max_cities
        )
        
        logger.info(f"Selected {len(final_cities)} intermediate cities", 
                   cities=[city.city.name for city in final_cities])
        
        return [scored_city.city for scored_city in final_cities]
    
    async def _gather_candidate_cities(
        self, 
        start_city: City, 
        end_city: City, 
        request: TripRequest,
        route_type: str
    ) -> List[City]:
        """Gather candidate cities from multiple sources."""
        
        all_candidates = []
        
        # Source 1: Enhanced city service with enriched data
        try:
            enhanced_candidates = await self._get_enhanced_service_candidates(
                start_city, end_city, route_type
            )
            all_candidates.extend(enhanced_candidates)
            logger.info(f"Enhanced service: {len(enhanced_candidates)} candidates")
        except Exception as e:
            logger.error(f"Enhanced service failed: {e}")
        
        # Source 2: OpenTripMap attractions and cities
        try:
            otm_candidates = await self._get_opentripmap_candidates(
                start_city, end_city, route_type
            )
            all_candidates.extend(otm_candidates)
            logger.info(f"OpenTripMap: {len(otm_candidates)} candidates")
        except Exception as e:
            logger.error(f"OpenTripMap service failed: {e}")
        
        # Source 3: Fallback comprehensive database
        try:
            fallback_candidates = self._get_fallback_candidates(
                start_city, end_city, route_type
            )
            all_candidates.extend(fallback_candidates)
            logger.info(f"Fallback: {len(fallback_candidates)} candidates")
        except Exception as e:
            logger.error(f"Fallback service failed: {e}")
        
        # Deduplicate and filter by route proximity
        unique_candidates = self._deduplicate_candidates(all_candidates)
        route_candidates = self._filter_by_route_proximity(
            unique_candidates, start_city, end_city
        )
        
        return route_candidates
    
    async def _get_enhanced_service_candidates(
        self, start_city: City, end_city: City, route_type: str
    ) -> List[City]:
        """Get candidates from enhanced city service."""
        candidates = []
        
        try:
            async with self.enhanced_city_service:
                # Get bulk European cities
                bulk_cities = await self.enhanced_city_service.get_european_cities_bulk(
                    limit=500
                )
                
                # Convert to City objects and filter by route type
                for city_data in bulk_cities:
                    if self._matches_route_type(city_data, route_type):
                        city = self._convert_to_city_object(city_data, source='enhanced')
                        if city:
                            candidates.append(city)
                
        except Exception as e:
            logger.error(f"Enhanced city service error: {e}")
        
        return candidates
    
    async def _get_opentripmap_candidates(
        self, start_city: City, end_city: City, route_type: str
    ) -> List[City]:
        """Get candidates from OpenTripMap service."""
        candidates = []
        
        try:
            async with self.opentripmap_service:
                # Search for cities in each relevant country
                countries = self._determine_countries_for_route(start_city, end_city)
                
                for country in countries:
                    country_cities = await self.opentripmap_service.get_cities_in_country(
                        country, limit=100
                    )
                    
                    for city_data in country_cities:
                        if self._matches_route_type(city_data, route_type):
                            city = self._convert_to_city_object(city_data, source='opentripmap')
                            if city:
                                candidates.append(city)
                
        except Exception as e:
            logger.error(f"OpenTripMap service error: {e}")
        
        return candidates
    
    def _get_fallback_candidates(
        self, start_city: City, end_city: City, route_type: str
    ) -> List[City]:
        """Get candidates from fallback city database."""
        try:
            return self.city_service._get_fallback_route_cities(
                start_city.coordinates, 
                end_city.coordinates, 
                max_deviation_km=150, 
                route_type=route_type
            )
        except Exception as e:
            logger.error(f"Fallback candidates error: {e}")
            return []
    
    async def _score_candidates(
        self, 
        candidates: List[City], 
        start_city: City, 
        end_city: City, 
        request: TripRequest,
        route_type: str
    ) -> List[CityScore]:
        """Score all candidate cities comprehensively."""
        
        scored_cities = []
        
        # Pre-calculate route information
        route_info = self._calculate_route_info(start_city, end_city)
        
        for city in candidates:
            try:
                score = await self._calculate_city_score(
                    city, start_city, end_city, request, route_type, route_info
                )
                scored_cities.append(score)
            except Exception as e:
                logger.warning(f"Failed to score city {city.name}: {e}")
        
        # Sort by total score
        scored_cities.sort(key=lambda x: x.total_score, reverse=True)
        
        return scored_cities
    
    async def _calculate_city_score(
        self, 
        city: City, 
        start_city: City, 
        end_city: City, 
        request: TripRequest,
        route_type: str,
        route_info: Dict
    ) -> CityScore:
        """Calculate comprehensive score for a city."""
        
        reasons = []
        
        # Distance score: how well positioned along route
        distance_score = self._calculate_distance_score(
            city, start_city, end_city, route_info
        )
        if distance_score > 0.7:
            reasons.append("Well positioned along route")
        
        # Preference score: match to user preferences
        preference_score = await self._calculate_preference_score(
            city, request, route_type
        )
        if preference_score > 0.8:
            reasons.append(f"Excellent match for {route_type} style")
        
        # Diversity score: adds variety to route
        diversity_score = self._calculate_diversity_score(
            city, route_type
        )
        if diversity_score > 0.7:
            reasons.append("Adds unique character to route")
        
        # Popularity score: tourist appeal
        popularity_score = self._calculate_popularity_score(city)
        if popularity_score > 0.8:
            reasons.append("Popular destination")
        elif popularity_score < 0.3:
            reasons.append("Hidden gem")
        
        # Accessibility score: ease of access
        accessibility_score = self._calculate_accessibility_score(city)
        
        # Timing score: seasonal/time relevance
        timing_score = self._calculate_timing_score(city, request)
        
        # Budget score: fits budget constraints
        budget_score = self._calculate_budget_score(city, request)
        
        # Calculate weighted total score
        total_score = (
            distance_score * self.scoring_weights['distance'] +
            preference_score * self.scoring_weights['preference'] +
            diversity_score * self.scoring_weights['diversity'] +
            popularity_score * self.scoring_weights['popularity'] +
            accessibility_score * self.scoring_weights['accessibility'] +
            timing_score * self.scoring_weights['timing'] +
            budget_score * self.scoring_weights['budget']
        )
        
        return CityScore(
            city=city,
            distance_score=distance_score,
            preference_score=preference_score,
            diversity_score=diversity_score,
            popularity_score=popularity_score,
            accessibility_score=accessibility_score,
            timing_score=timing_score,
            budget_score=budget_score,
            total_score=total_score,
            reasons=reasons
        )
    
    async def _optimize_route_selection(
        self, 
        scored_cities: List[CityScore], 
        start_city: City, 
        end_city: City, 
        max_cities: int,
        request: TripRequest
    ) -> List[CityScore]:
        """Optimize selection using route constraints and ML recommendations."""
        
        if len(scored_cities) <= max_cities:
            return scored_cities
        
        # Try ML-enhanced selection first
        try:
            ml_selection = await self._ml_enhanced_selection(
                scored_cities, start_city, end_city, max_cities, request
            )
            if ml_selection:
                return ml_selection
        except Exception as e:
            logger.warning(f"ML selection failed, using fallback: {e}")
        
        # Fallback to greedy selection with route optimization
        return self._greedy_route_optimization(
            scored_cities, start_city, end_city, max_cities
        )
    
    async def _ml_enhanced_selection(
        self, 
        scored_cities: List[CityScore], 
        start_city: City, 
        end_city: City, 
        max_cities: int,
        request: TripRequest
    ) -> Optional[List[CityScore]]:
        """Use ML recommendations for intelligent selection."""
        
        try:
            # Create trip preferences
            trip_preferences = TripPreference(
                budget_range=getattr(request, 'budget_range', 'mid-range'),
                duration_days=getattr(request, 'travel_days', 7),
                travel_style=getattr(request, 'route_type', 'scenic'),
                season=self._determine_season(),
                group_size=getattr(request, 'group_size', 2),
                activity_preferences=getattr(request, 'interests', []),
                previous_trips=[]
            )
            
            # Get ML recommendations
            candidate_cities = [score.city for score in scored_cities[:max_cities * 2]]
            
            ml_result = self.ml_service.get_smart_recommendations(
                preferences=trip_preferences,
                start_city=start_city.name,
                end_city=end_city.name,
                exploration_factor=0.3  # Moderate exploration
            )
            
            if ml_result.success and ml_result.data.get('recommended_cities'):
                recommended_names = [city['name'] for city in ml_result.data['recommended_cities']]
                
                # Select scored cities that match ML recommendations
                selected = []
                for scored_city in scored_cities:
                    if scored_city.city.name in recommended_names and len(selected) < max_cities:
                        selected.append(scored_city)
                
                if len(selected) >= max_cities // 2:  # At least half filled
                    return selected[:max_cities]
            
        except Exception as e:
            logger.error(f"ML enhanced selection error: {e}")
        
        return None
    
    def _greedy_route_optimization(
        self, 
        scored_cities: List[CityScore], 
        start_city: City, 
        end_city: City, 
        max_cities: int
    ) -> List[CityScore]:
        """Greedy selection with route optimization constraints."""
        
        selected = []
        remaining = scored_cities.copy()
        
        route_opt = RouteOptimization()
        
        while len(selected) < max_cities and remaining:
            best_candidate = None
            best_score = -1
            
            for candidate in remaining:
                # Check route constraints
                if not self._satisfies_route_constraints(
                    candidate, selected, start_city, end_city, route_opt
                ):
                    continue
                
                # Calculate composite score including spacing
                composite_score = self._calculate_composite_score(
                    candidate, selected, start_city, end_city
                )
                
                if composite_score > best_score:
                    best_score = composite_score
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                break  # No more valid candidates
        
        return selected
    
    def _apply_final_optimization(
        self, 
        selected_cities: List[CityScore], 
        start_city: City, 
        end_city: City, 
        max_cities: int
    ) -> List[CityScore]:
        """Apply final optimization for spacing and route logic."""
        
        if len(selected_cities) <= max_cities:
            return selected_cities
        
        # Sort by route position for optimal sequencing
        route_ordered = self._sort_by_route_position(
            selected_cities, start_city, end_city
        )
        
        # Apply final spacing optimization
        final_selection = self._optimize_spacing(
            route_ordered, start_city, end_city, max_cities
        )
        
        return final_selection
    
    async def _advanced_route_optimization(
        self,
        scored_cities: List[CityScore],
        start_city: City,
        end_city: City,
        max_cities: int,
        route_type: str,
        request: TripRequest
    ) -> List[CityScore]:
        """Advanced route optimization using multiple algorithms."""
        
        logger.info("Starting advanced route optimization")
        
        # Prepare data for optimization
        candidate_cities = [scored_city.city for scored_city in scored_cities]
        city_scores = {scored_city.city.name: scored_city.total_score for scored_city in scored_cities}
        
        try:
            # Use the route optimization service
            optimized_route = self.route_optimizer.optimize_route(
                start_city=start_city,
                end_city=end_city,
                candidate_cities=candidate_cities,
                max_cities=max_cities,
                route_type=route_type,
                city_scores=city_scores
            )
            
            logger.info(f"Route optimization completed using {optimized_route.optimization_method}")
            logger.info(f"Performance: {optimized_route.performance_metrics}")
            logger.info(f"Explanation: {optimized_route.routing_explanation}")
            
            # Convert back to CityScore objects
            optimized_scored_cities = []
            for city in optimized_route.cities:
                # Find the original scored city
                original_scored = next(
                    (sc for sc in scored_cities if sc.city.name == city.name), 
                    None
                )
                if original_scored:
                    optimized_scored_cities.append(original_scored)
            
            return optimized_scored_cities
            
        except Exception as e:
            logger.error(f"Advanced route optimization failed: {e}")
            # Fallback to simpler optimization
            return await self._fallback_route_optimization(
                scored_cities, start_city, end_city, max_cities, request
            )
    
    async def _fallback_route_optimization(
        self,
        scored_cities: List[CityScore],
        start_city: City,
        end_city: City,
        max_cities: int,
        request: TripRequest
    ) -> List[CityScore]:
        """Fallback route optimization method."""
        
        logger.info("Using fallback route optimization")
        
        # Simple greedy selection with constraints
        selected = []
        remaining = scored_cities.copy()
        
        route_opt = RouteOptimization()
        
        while len(selected) < max_cities and remaining:
            best_candidate = None
            best_score = -1
            
            for candidate in remaining:
                # Check route constraints
                if not self._satisfies_route_constraints(
                    candidate, selected, start_city, end_city, route_opt
                ):
                    continue
                
                # Calculate composite score including spacing
                composite_score = self._calculate_composite_score(
                    candidate, selected, start_city, end_city
                )
                
                if composite_score > best_score:
                    best_score = composite_score
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                break
        
        return selected
    
    def _validate_and_adjust_route(
        self,
        optimized_cities: List[CityScore],
        start_city: City,
        end_city: City,
        max_cities: int
    ) -> List[CityScore]:
        """Validate and make final adjustments to the optimized route."""
        
        if not optimized_cities:
            return []
        
        # Ensure we don't exceed max cities
        if len(optimized_cities) > max_cities:
            optimized_cities = optimized_cities[:max_cities]
        
        # Validate minimum distances
        validated_cities = []
        min_distance = 50  # km
        
        for city_score in optimized_cities:
            is_valid = True
            
            # Check distance from start city
            if self._calculate_distance(city_score.city.coordinates, start_city.coordinates) < min_distance:
                is_valid = False
            
            # Check distance from end city  
            if self._calculate_distance(city_score.city.coordinates, end_city.coordinates) < min_distance:
                is_valid = False
            
            # Check distance from other selected cities
            for selected in validated_cities:
                if self._calculate_distance(city_score.city.coordinates, selected.city.coordinates) < min_distance:
                    is_valid = False
                    break
            
            if is_valid:
                validated_cities.append(city_score)
        
        logger.info(f"Route validation: {len(optimized_cities)} -> {len(validated_cities)} cities")
        
        return validated_cities
    
    # Helper methods for scoring and optimization
    
    def _calculate_distance_score(
        self, city: City, start_city: City, end_city: City, route_info: Dict
    ) -> float:
        """Calculate how well positioned the city is along the route."""
        
        # Distance from city to direct route line
        route_distance = self._distance_to_route(city, start_city, end_city)
        max_acceptable_distance = 100  # km
        
        if route_distance > max_acceptable_distance:
            return 0.0
        
        # Prefer cities closer to the route
        distance_score = 1.0 - (route_distance / max_acceptable_distance)
        
        # Bonus for good positioning along route
        position_score = self._calculate_route_position_score(
            city, start_city, end_city
        )
        
        return (distance_score * 0.7) + (position_score * 0.3)
    
    async def _calculate_preference_score(
        self, city: City, request: TripRequest, route_type: str
    ) -> float:
        """Calculate how well the city matches user preferences using advanced scoring."""
        
        try:
            # Create user preferences from request
            user_preferences = self.preference_service.create_user_preferences_from_request(request)
            
            # Get contextual factors
            contextual_factors = self.preference_service.get_contextual_factors()
            
            # Calculate comprehensive personalization score
            personalization_score = self.preference_service.calculate_personalization_score(
                city, user_preferences, contextual_factors, request
            )
            
            # Use the overall score as the preference score
            return personalization_score.overall_score
            
        except Exception as e:
            logger.warning(f"Advanced preference scoring failed for {city.name}: {e}")
            # Fallback to basic scoring
            return self._calculate_basic_preference_score(city, request, route_type)
    
    def _calculate_basic_preference_score(
        self, city: City, request: TripRequest, route_type: str
    ) -> float:
        """Fallback basic preference calculation."""
        
        base_score = 0.5
        
        # Route type matching
        if hasattr(city, 'types') and city.types:
            type_match_score = self._calculate_type_match_score(city.types, route_type)
            base_score += type_match_score * 0.4
        
        # Interest matching
        if hasattr(request, 'interests') and request.interests:
            interest_score = self._calculate_interest_match_score(city, request.interests)
            base_score += interest_score * 0.3
        
        # Duration appropriateness
        if hasattr(request, 'travel_days'):
            duration_score = self._calculate_duration_appropriateness(city, request.travel_days)
            base_score += duration_score * 0.2
        
        # Group size appropriateness
        if hasattr(request, 'group_size'):
            group_score = self._calculate_group_appropriateness(city, request.group_size)
            base_score += group_score * 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_diversity_score(self, city: City, route_type: str) -> float:
        """Calculate how much diversity the city adds to the route."""
        
        diversity_factors = {
            'cultural_significance': self._has_cultural_significance(city),
            'natural_beauty': self._has_natural_beauty(city),
            'unique_features': self._has_unique_features(city),
            'local_authenticity': self._has_local_authenticity(city),
            'architectural_interest': self._has_architectural_interest(city)
        }
        
        diversity_score = sum(diversity_factors.values()) / len(diversity_factors)
        
        # Bonus for contrasting with route type
        contrast_bonus = self._calculate_contrast_bonus(city, route_type)
        
        return min(diversity_score + contrast_bonus, 1.0)
    
    def _calculate_popularity_score(self, city: City) -> float:
        """Calculate tourist appeal and popularity score."""
        
        popularity_indicators = {
            'unesco_status': 0.3 if self._is_unesco_site(city) else 0.0,
            'capital_status': 0.2 if self._is_capital_city(city) else 0.0,
            'population_size': self._normalize_population(city),
            'tourist_infrastructure': self._assess_tourist_infrastructure(city),
            'cultural_importance': self._assess_cultural_importance(city)
        }
        
        return sum(popularity_indicators.values()) / len(popularity_indicators)
    
    def _calculate_accessibility_score(self, city: City) -> float:
        """Calculate ease of access score."""
        
        accessibility_factors = {
            'transportation_access': 0.8,  # Assume good European transport
            'parking_availability': 0.7,   # Assume reasonable parking
            'tourist_facilities': 0.8,     # Assume good facilities
            'language_accessibility': 0.9, # European tourist areas
            'digital_connectivity': 0.9    # Good European connectivity
        }
        
        return sum(accessibility_factors.values()) / len(accessibility_factors)
    
    def _calculate_timing_score(self, city: City, request: TripRequest) -> float:
        """Calculate seasonal and timing relevance."""
        
        base_score = 0.8  # Most European cities good year-round
        
        # Seasonal adjustments
        season = self._determine_season()
        if hasattr(city, 'types') and city.types:
            if season == 'winter' and any(t in city.types for t in ['skiing', 'alpine', 'winter-sports']):
                base_score += 0.2
            elif season == 'summer' and any(t in city.types for t in ['coastal', 'beach', 'resort']):
                base_score += 0.2
            elif season in ['spring', 'autumn'] and any(t in city.types for t in ['scenic', 'gardens', 'nature']):
                base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_budget_score(self, city: City, request: TripRequest) -> float:
        """Calculate budget appropriateness."""
        
        # Default to mid-range scoring
        budget_range = getattr(request, 'budget_range', 'mid-range')
        
        city_cost_level = self._estimate_city_cost_level(city)
        
        if budget_range == 'budget' and city_cost_level <= 2:
            return 1.0
        elif budget_range == 'mid-range' and 2 <= city_cost_level <= 4:
            return 1.0
        elif budget_range == 'luxury' and city_cost_level >= 3:
            return 1.0
        else:
            return 0.6  # Still acceptable but not optimal
    
    # Additional helper methods continue...
    
    def _matches_route_type(self, city_data: Dict, route_type: str) -> bool:
        """Check if city matches the route type."""
        if not route_type or not city_data.get('types'):
            return True
        
        city_types = city_data.get('types', [])
        
        type_mappings = {
            'scenic': ['scenic', 'alpine', 'lakes', 'romantic', 'resort', 'coastal', 'natural'],
            'cultural': ['cultural', 'historic', 'unesco', 'artistic', 'renaissance', 'medieval', 'roman', 'museums'],
            'adventure': ['adventure', 'alpine', 'winter-sports', 'nature', 'skiing', 'outdoor', 'hiking'],
            'culinary': ['culinary', 'wine', 'food', 'gastronomy', 'markets', 'regional'],
            'romantic': ['romantic', 'scenic', 'lakes', 'coastal', 'luxury', 'historic', 'gardens']
        }
        
        relevant_types = type_mappings.get(route_type, [])
        return any(city_type in relevant_types for city_type in city_types)
    
    def _convert_to_city_object(self, city_data: Dict, source: str) -> Optional[City]:
        """Convert city data to City object."""
        try:
            name = city_data.get('name', '')
            if not name:
                return None
            
            # Handle different coordinate formats
            coords = city_data.get('coordinates', {})
            if isinstance(coords, dict):
                lat = coords.get('latitude') or coords.get('lat')
                lng = coords.get('longitude') or coords.get('lng') or coords.get('lon')
            else:
                lat, lng = None, None
            
            if not lat or not lng:
                return None
            
            return City(
                name=name,
                coordinates=Coordinates(latitude=float(lat), longitude=float(lng)),
                country=city_data.get('country', ''),
                region=city_data.get('region', ''),
                types=city_data.get('types', []),
                rating=city_data.get('rating', 5)
            )
        except Exception as e:
            logger.warning(f"Failed to convert city data: {e}")
            return None
    
    def _determine_countries_for_route(self, start_city: City, end_city: City) -> List[str]:
        """Determine relevant countries for the route."""
        countries = set()
        
        if start_city.country:
            countries.add(start_city.country.lower())
        if end_city.country:
            countries.add(end_city.country.lower())
        
        # Add neighboring countries for cross-border routes
        country_neighbors = {
            'france': ['spain', 'italy', 'switzerland', 'germany'],
            'italy': ['france', 'switzerland', 'austria'],
            'spain': ['france', 'portugal'],
            'germany': ['france', 'switzerland', 'austria'],
            'switzerland': ['france', 'italy', 'germany', 'austria'],
            'austria': ['italy', 'switzerland', 'germany']
        }
        
        for country in list(countries):
            neighbors = country_neighbors.get(country, [])
            countries.update(neighbors[:2])  # Add up to 2 neighbors
        
        return list(countries)[:5]  # Limit to 5 countries max
    
    def _deduplicate_candidates(self, candidates: List[City]) -> List[City]:
        """Remove duplicate cities based on name and proximity."""
        unique_cities = []
        seen_names = set()
        
        for city in candidates:
            city_key = city.name.lower().replace(' ', '').replace('-', '')
            
            if city_key in seen_names:
                continue
            
            # Check for nearby duplicates (within 10km)
            is_duplicate = False
            for existing_city in unique_cities:
                if self._calculate_distance(city.coordinates, existing_city.coordinates) < 10:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_cities.append(city)
                seen_names.add(city_key)
        
        return unique_cities
    
    def _filter_by_route_proximity(
        self, candidates: List[City], start_city: City, end_city: City
    ) -> List[City]:
        """Filter candidates by proximity to route."""
        max_distance = 120  # km from route
        
        filtered = []
        for city in candidates:
            distance_to_route = self._distance_to_route(city, start_city, end_city)
            if distance_to_route <= max_distance:
                filtered.append(city)
        
        return filtered
    
    def _calculate_route_info(self, start_city: City, end_city: City) -> Dict:
        """Pre-calculate route information for optimization."""
        total_distance = self._calculate_distance(
            start_city.coordinates, end_city.coordinates
        )
        
        return {
            'total_distance': total_distance,
            'midpoint': Coordinates(
                latitude=(start_city.coordinates.latitude + end_city.coordinates.latitude) / 2,
                longitude=(start_city.coordinates.longitude + end_city.coordinates.longitude) / 2
            )
        }
    
    def _distance_to_route(self, city: City, start_city: City, end_city: City) -> float:
        """Calculate perpendicular distance from city to route line."""
        # Simplified distance to line calculation
        # Using point-to-line distance formula
        
        x1, y1 = start_city.coordinates.latitude, start_city.coordinates.longitude
        x2, y2 = end_city.coordinates.latitude, end_city.coordinates.longitude
        x0, y0 = city.coordinates.latitude, city.coordinates.longitude
        
        # Distance from point to line formula
        numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        denominator = math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)
        
        if denominator == 0:
            return self._calculate_distance(city.coordinates, start_city.coordinates)
        
        distance_degrees = numerator / denominator
        
        # Convert to approximate kilometers (rough conversion)
        distance_km = distance_degrees * 111  # 1 degree ≈ 111 km
        
        return distance_km
    
    def _calculate_distance(self, coord1: Coordinates, coord2: Coordinates) -> float:
        """Calculate distance between two coordinates in km."""
        # Haversine formula
        R = 6371  # Earth's radius in km
        
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _determine_season(self) -> str:
        """Determine current season."""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'
    
    # Placeholder methods for comprehensive scoring
    # These would be implemented with more sophisticated logic
    
    def _calculate_route_position_score(self, city: City, start_city: City, end_city: City) -> float:
        return 0.7  # Placeholder
    
    def _calculate_type_match_score(self, city_types: List[str], route_type: str) -> float:
        return 0.8  # Placeholder
    
    def _calculate_interest_match_score(self, city: City, interests: List[str]) -> float:
        return 0.6  # Placeholder
    
    def _calculate_duration_appropriateness(self, city: City, travel_days: int) -> float:
        return 0.7  # Placeholder
    
    def _calculate_group_appropriateness(self, city: City, group_size: int) -> float:
        return 0.8  # Placeholder
    
    def _has_cultural_significance(self, city: City) -> float:
        return 0.6  # Placeholder
    
    def _has_natural_beauty(self, city: City) -> float:
        return 0.7  # Placeholder
    
    def _has_unique_features(self, city: City) -> float:
        return 0.5  # Placeholder
    
    def _has_local_authenticity(self, city: City) -> float:
        return 0.8  # Placeholder
    
    def _has_architectural_interest(self, city: City) -> float:
        return 0.6  # Placeholder
    
    def _calculate_contrast_bonus(self, city: City, route_type: str) -> float:
        return 0.1  # Placeholder
    
    def _is_unesco_site(self, city: City) -> bool:
        return 'unesco' in getattr(city, 'types', [])
    
    def _is_capital_city(self, city: City) -> bool:
        return any(t in getattr(city, 'types', []) for t in ['capital', 'administrative'])
    
    def _normalize_population(self, city: City) -> float:
        return 0.5  # Placeholder
    
    def _assess_tourist_infrastructure(self, city: City) -> float:
        return 0.7  # Placeholder
    
    def _assess_cultural_importance(self, city: City) -> float:
        return 0.6  # Placeholder
    
    def _estimate_city_cost_level(self, city: City) -> int:
        """Estimate cost level 1-5 (1=budget, 5=luxury)."""
        return 3  # Default to mid-range
    
    def _satisfies_route_constraints(
        self, candidate: CityScore, selected: List[CityScore], 
        start_city: City, end_city: City, route_opt: RouteOptimization
    ) -> bool:
        """Check if candidate satisfies route optimization constraints."""
        
        # Check minimum distance from other selected cities
        for selected_city in selected:
            distance = self._calculate_distance(
                candidate.city.coordinates, selected_city.city.coordinates
            )
            if distance < route_opt.min_stop_distance_km:
                return False
        
        # Check maximum detour from direct route
        detour = self._distance_to_route(candidate.city, start_city, end_city)
        if detour > route_opt.max_detour_km:
            return False
        
        return True
    
    def _calculate_composite_score(
        self, candidate: CityScore, selected: List[CityScore], 
        start_city: City, end_city: City
    ) -> float:
        """Calculate composite score including spacing optimization."""
        
        base_score = candidate.total_score
        
        # Spacing bonus/penalty
        spacing_score = self._calculate_spacing_score(
            candidate, selected, start_city, end_city
        )
        
        return base_score * 0.8 + spacing_score * 0.2
    
    def _calculate_spacing_score(
        self, candidate: CityScore, selected: List[CityScore], 
        start_city: City, end_city: City
    ) -> float:
        """Calculate how well spaced the candidate would be."""
        
        if not selected:
            return 0.8  # Good default for first selection
        
        # Calculate ideal spacing
        total_distance = self._calculate_distance(start_city.coordinates, end_city.coordinates)
        ideal_spacing = total_distance / (len(selected) + 2)  # +2 for start and end
        
        # Find closest selected city
        min_distance = float('inf')
        for selected_city in selected:
            distance = self._calculate_distance(
                candidate.city.coordinates, selected_city.city.coordinates
            )
            min_distance = min(min_distance, distance)
        
        # Score based on how close to ideal spacing
        spacing_ratio = min_distance / ideal_spacing
        if 0.5 <= spacing_ratio <= 1.5:
            return 1.0  # Optimal spacing
        elif 0.3 <= spacing_ratio <= 2.0:
            return 0.7  # Acceptable spacing
        else:
            return 0.3  # Poor spacing
    
    def _sort_by_route_position(
        self, cities: List[CityScore], start_city: City, end_city: City
    ) -> List[CityScore]:
        """Sort cities by their position along the route."""
        
        def route_position(city_score: CityScore) -> float:
            # Calculate how far along the route this city is (0.0 to 1.0)
            city = city_score.city
            
            # Project city onto route line
            start_to_city = self._calculate_distance(start_city.coordinates, city.coordinates)
            start_to_end = self._calculate_distance(start_city.coordinates, end_city.coordinates)
            
            if start_to_end == 0:
                return 0.0
            
            return min(start_to_city / start_to_end, 1.0)
        
        return sorted(cities, key=route_position)
    
    def _optimize_spacing(
        self, cities: List[CityScore], start_city: City, end_city: City, max_cities: int
    ) -> List[CityScore]:
        """Optimize final spacing of selected cities."""
        
        if len(cities) <= max_cities:
            return cities
        
        # Use dynamic programming or greedy approach for optimal spacing
        # For now, simple even distribution
        total_route_length = len(cities)
        step = max(1, total_route_length // max_cities)
        
        optimized = []
        for i in range(0, min(len(cities), max_cities * step), step):
            optimized.append(cities[i])
        
        # Ensure we don't exceed max_cities
        return optimized[:max_cities]


# Global service instance
_enhanced_intermediate_service = None

def get_enhanced_intermediate_city_service() -> EnhancedIntermediateCityService:
    """Get the global enhanced intermediate city service instance."""
    global _enhanced_intermediate_service
    if _enhanced_intermediate_service is None:
        from .google_places_city_service import GooglePlacesCityService
        from .ml_recommendation_service import MLRecommendationService
        
        city_service = GooglePlacesCityService()
        ml_service = MLRecommendationService(city_service)
        _enhanced_intermediate_service = EnhancedIntermediateCityService(city_service, ml_service)
    return _enhanced_intermediate_service
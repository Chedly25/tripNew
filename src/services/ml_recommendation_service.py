"""
ML-based trip recommendation service using collaborative filtering and content-based filtering.
"""
import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
try:
    import structlog
except ImportError:
    import logging as structlog
    structlog.get_logger = lambda name: logging.getLogger(name)

from ..core.models import City, Coordinates, ServiceResult
from .city_service import CityService

logger = structlog.get_logger(__name__)

@dataclass
class TripPreference:
    """User trip preferences for ML recommendations."""
    budget_range: str  # 'budget', 'mid-range', 'luxury'
    duration_days: int
    travel_style: str  # 'scenic', 'cultural', 'adventure', 'culinary', etc.
    season: str  # 'spring', 'summer', 'autumn', 'winter'
    group_size: int = 2
    activity_preferences: List[str] = None
    previous_trips: List[str] = None  # Cities visited before

class MLRecommendationService:
    """ML-powered trip recommendation service."""
    
    def __init__(self, city_service: CityService):
        self.city_service = city_service
        self.user_profiles = {}  # Store user preferences
        self.trip_history = {}   # Store completed trips
        self.city_features = {}  # Store city feature vectors
        self.initialize_city_features()
    
    def initialize_city_features(self):
        """Initialize city feature vectors for ML recommendations."""
        cities = list(self.city_service._city_cache.values())
        
        for city in cities:
            features = self._extract_city_features(city)
            self.city_features[city.name] = features
    
    def _extract_city_features(self, city: City) -> Dict[str, float]:
        """Extract numerical features from a city for ML processing."""
        features = {
            # Population score (normalized)
            'population_score': self._normalize_population(city.population),
            
            # Type-based features
            'scenic_score': 1.0 if city.types and any(t in ['scenic', 'alpine', 'coastal', 'lakes'] for t in city.types) else 0.0,
            'cultural_score': 1.0 if city.types and any(t in ['cultural', 'historic', 'unesco', 'artistic'] for t in city.types) else 0.0,
            'culinary_score': 1.0 if city.types and any(t in ['culinary', 'wine', 'food'] for t in city.types) else 0.0,
            'adventure_score': 1.0 if city.types and any(t in ['adventure', 'alpine', 'outdoor'] for t in city.types) else 0.0,
            'romantic_score': 1.0 if city.types and any(t in ['romantic', 'luxury', 'scenic'] for t in city.types) else 0.0,
            
            # Enhanced features (if available)
            'rating': (getattr(city, 'rating', None) or 4.0) / 5.0,  # Normalize to 0-1
            'unesco': 1.0 if getattr(city, 'unesco', False) else 0.0,
            'elevation_score': self._normalize_elevation(getattr(city, 'elevation_m', 0)),
            'accessibility_score': self._score_accessibility(getattr(city, 'accessibility', None)),
            'cost_score': self._score_cost_level(getattr(city, 'cost_level', None)),
            'tourist_density_score': self._score_tourist_density(getattr(city, 'tourist_density', None)),
            'walking_city': 1.0 if getattr(city, 'walking_city', True) else 0.0,
            
            # Geographic features
            'latitude': city.coordinates.latitude / 90.0,  # Normalize
            'longitude': city.coordinates.longitude / 180.0,  # Normalize
            
            # Country features (one-hot encoding for major countries)
            'france': 1.0 if city.country == 'France' else 0.0,
            'italy': 1.0 if city.country == 'Italy' else 0.0,
            'spain': 1.0 if city.country == 'Spain' else 0.0,
            'germany': 1.0 if city.country == 'Germany' else 0.0,
            'switzerland': 1.0 if city.country == 'Switzerland' else 0.0,
        }
        
        return features
    
    def _normalize_population(self, population: Optional[int]) -> float:
        """Normalize population to 0-1 scale."""
        if not population:
            return 0.5  # Default for unknown
        
        # Log scale normalization for population
        log_pop = math.log10(max(population, 1000))  # Min 1000 to avoid log(0)
        return min(1.0, log_pop / 7.0)  # 10M population = 1.0
    
    def _normalize_elevation(self, elevation_m: Optional[int]) -> float:
        """Normalize elevation to 0-1 scale."""
        if elevation_m is None:
            return 0.0
        return min(1.0, elevation_m / 3000.0)  # 3000m = 1.0
    
    def _score_accessibility(self, accessibility: Optional[str]) -> float:
        """Convert accessibility to numerical score."""
        if not accessibility:
            return 0.5
        
        scores = {
            'excellent': 1.0,
            'good': 0.8,
            'moderate': 0.6,
            'limited': 0.3,
            'difficult': 0.1
        }
        return scores.get(accessibility.lower(), 0.5)
    
    def _score_cost_level(self, cost_level: Optional[str]) -> float:
        """Convert cost level to numerical score (higher = more expensive)."""
        if not cost_level:
            return 0.5
        
        scores = {
            'budget': 0.2,
            'affordable': 0.4,
            'moderate': 0.6,
            'expensive': 0.8,
            'luxury': 1.0
        }
        return scores.get(cost_level.lower(), 0.5)
    
    def _score_tourist_density(self, tourist_density: Optional[str]) -> float:
        """Convert tourist density to numerical score."""
        if not tourist_density:
            return 0.5
        
        scores = {
            'low': 0.2,
            'moderate': 0.5,
            'high': 0.8,
            'very_high': 1.0
        }
        return scores.get(tourist_density.lower(), 0.5)
    
    def get_smart_recommendations(self, preferences: TripPreference, 
                                start_city: str, end_city: str) -> ServiceResult:
        """Get ML-powered trip recommendations."""
        try:
            logger.info("Generating smart recommendations", 
                       start=start_city, end=end_city, 
                       style=preferences.travel_style,
                       budget=preferences.budget_range)
            
            # Get user preference vector
            user_vector = self._create_user_preference_vector(preferences)
            
            # Get candidate cities along the route
            start_city_obj = self.city_service.get_city_by_name_sync(start_city)
            end_city_obj = self.city_service.get_city_by_name_sync(end_city)
            
            if not start_city_obj or not end_city_obj:
                return ServiceResult.error_result("Could not find start or end city")
            
            # Find intermediate cities
            candidate_cities = self._find_route_candidates(start_city_obj, end_city_obj)
            
            # Score cities using ML algorithms
            scored_cities = []
            for city in candidate_cities:
                if city.name in self.city_features:
                    city_vector = self.city_features[city.name]
                    
                    # Content-based filtering score
                    content_score = self._calculate_content_similarity(user_vector, city_vector)
                    
                    # Collaborative filtering score (if we have user history)
                    collab_score = self._calculate_collaborative_score(city.name, preferences)
                    
                    # Seasonal adjustment
                    seasonal_score = self._calculate_seasonal_score(city, preferences.season)
                    
                    # Budget compatibility
                    budget_score = self._calculate_budget_compatibility(city, preferences.budget_range)
                    
                    # Route optimization score
                    route_score = self._calculate_route_optimization_score(
                        city, start_city_obj, end_city_obj
                    )
                    
                    # Combined score with weights
                    final_score = (
                        content_score * 0.4 +
                        collab_score * 0.2 +
                        seasonal_score * 0.15 +
                        budget_score * 0.15 +
                        route_score * 0.1
                    )
                    
                    scored_cities.append({
                        'city': city,
                        'score': final_score,
                        'reasons': self._generate_recommendation_reasons(
                            city, preferences, content_score, seasonal_score, budget_score
                        )
                    })
            
            # Sort by score and select top recommendations
            scored_cities.sort(key=lambda x: x['score'], reverse=True)
            
            # Select diverse recommendations (avoid clustering)
            selected_cities = self._select_diverse_recommendations(
                scored_cities, preferences.duration_days
            )
            
            return ServiceResult.success_result({
                'recommendations': selected_cities[:5],  # Top 5
                'algorithm_info': {
                    'method': 'hybrid_ml_filtering',
                    'features_used': len(user_vector),
                    'candidates_evaluated': len(candidate_cities),
                    'personalization_level': 'high' if self._has_user_history(preferences) else 'medium'
                }
            })
            
        except Exception as e:
            logger.error("Smart recommendations failed", error=str(e))
            return ServiceResult.error_result(f"Recommendation engine failed: {e}")
    
    def _create_user_preference_vector(self, preferences: TripPreference) -> Dict[str, float]:
        """Create a preference vector for the user based on their input."""
        vector = {
            'scenic_score': 1.0 if preferences.travel_style == 'scenic' else 0.2,
            'cultural_score': 1.0 if preferences.travel_style == 'cultural' else 0.2,
            'culinary_score': 1.0 if preferences.travel_style == 'culinary' else 0.2,
            'adventure_score': 1.0 if preferences.travel_style == 'adventure' else 0.2,
            'romantic_score': 1.0 if preferences.travel_style == 'romantic' else 0.2,
            
            # Budget preferences
            'cost_preference': self._budget_to_cost_preference(preferences.budget_range),
            
            # Duration-based preferences
            'duration_factor': min(1.0, preferences.duration_days / 14.0),  # Normalize to 2 weeks
            
            # Seasonal preferences
            'summer_season': 1.0 if preferences.season == 'summer' else 0.0,
            'winter_season': 1.0 if preferences.season == 'winter' else 0.0,
            'spring_season': 1.0 if preferences.season == 'spring' else 0.0,
            'autumn_season': 1.0 if preferences.season == 'autumn' else 0.0,
            
            # Group size preferences
            'group_size_factor': min(1.0, preferences.group_size / 6.0),  # Normalize to max 6
            
            # Activity preferences
            'unesco_preference': 0.8 if preferences.travel_style in ['cultural', 'scenic'] else 0.3,
            'walking_preference': 0.9,  # Most travelers prefer walkable cities
            'accessibility_preference': 0.7,  # Prefer accessible destinations
        }
        
        return vector
    
    def _budget_to_cost_preference(self, budget_range: str) -> float:
        """Convert budget range to cost preference score."""
        mapping = {
            'budget': 0.2,      # Prefer low-cost destinations
            'mid-range': 0.5,   # Balanced preference
            'luxury': 0.8       # Prefer high-end destinations
        }
        return mapping.get(budget_range, 0.5)
    
    def _calculate_content_similarity(self, user_vector: Dict[str, float], 
                                    city_vector: Dict[str, float]) -> float:
        """Calculate cosine similarity between user preferences and city features."""
        # Get common features
        common_features = set(user_vector.keys()) & set(city_vector.keys())
        
        if not common_features:
            return 0.5  # Default similarity
        
        # Calculate dot product and magnitudes
        dot_product = sum(user_vector[feature] * city_vector[feature] 
                         for feature in common_features)
        
        user_magnitude = math.sqrt(sum(user_vector[feature] ** 2 
                                     for feature in common_features))
        city_magnitude = math.sqrt(sum(city_vector[feature] ** 2 
                                     for feature in common_features))
        
        if user_magnitude == 0 or city_magnitude == 0:
            return 0.5
        
        similarity = dot_product / (user_magnitude * city_magnitude)
        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
    
    def _calculate_collaborative_score(self, city_name: str, 
                                     preferences: TripPreference) -> float:
        """Calculate collaborative filtering score based on similar users."""
        # Simplified collaborative filtering
        # In a real implementation, this would use user-item interaction data
        
        # For now, use a pseudo-collaborative score based on popular destinations
        popular_destinations = {
            'Paris': 0.95,
            'Rome': 0.93,
            'Barcelona': 0.91,
            'Florence': 0.89,
            'Venice': 0.87,
            'Amsterdam': 0.85,
            'Prague': 0.83,
            'Vienna': 0.81,
            'Budapest': 0.79,
            'Lisbon': 0.77
        }
        
        base_score = popular_destinations.get(city_name, 0.5)
        
        # Adjust based on travel style popularity
        style_adjustments = {
            'cultural': 0.1,   # Cultural travelers often go to popular places
            'scenic': -0.05,   # Scenic travelers might prefer less popular spots
            'adventure': -0.1, # Adventure travelers often go off-beaten-path
            'hidden_gems': -0.2  # Hidden gem seekers avoid popular places
        }
        
        adjustment = style_adjustments.get(preferences.travel_style, 0.0)
        return max(0.0, min(1.0, base_score + adjustment))
    
    def _calculate_seasonal_score(self, city: City, season: str) -> float:
        """Calculate how well a city matches the travel season."""
        # Base seasonal preferences
        seasonal_bonuses = {
            'spring': {
                'scenic': 0.9,
                'cultural': 0.8,
                'coastal': 0.7
            },
            'summer': {
                'coastal': 1.0,
                'scenic': 0.9,
                'resort': 0.9,
                'lakes': 0.8
            },
            'autumn': {
                'scenic': 1.0,
                'cultural': 0.9,
                'culinary': 0.8,
                'wine': 0.9
            },
            'winter': {
                'cultural': 0.9,
                'historic': 0.8,
                'alpine': 0.7,  # Depends on winter sports
                'museums': 0.9
            }
        }
        
        season_prefs = seasonal_bonuses.get(season, {})
        
        if not city.types:
            return 0.6  # Neutral score
        
        # Calculate average seasonal score for city's types
        scores = []
        for city_type in city.types:
            scores.append(season_prefs.get(city_type, 0.6))
        
        return sum(scores) / len(scores) if scores else 0.6
    
    def _calculate_budget_compatibility(self, city: City, budget_range: str) -> float:
        """Calculate how well a city matches the budget range."""
        city_cost = getattr(city, 'cost_level', 'moderate')
        
        # Compatibility matrix
        compatibility = {
            ('budget', 'budget'): 1.0,
            ('budget', 'affordable'): 0.8,
            ('budget', 'moderate'): 0.5,
            ('budget', 'expensive'): 0.2,
            ('budget', 'luxury'): 0.1,
            
            ('mid-range', 'budget'): 0.7,
            ('mid-range', 'affordable'): 0.9,
            ('mid-range', 'moderate'): 1.0,
            ('mid-range', 'expensive'): 0.8,
            ('mid-range', 'luxury'): 0.4,
            
            ('luxury', 'budget'): 0.3,
            ('luxury', 'affordable'): 0.5,
            ('luxury', 'moderate'): 0.7,
            ('luxury', 'expensive'): 0.9,
            ('luxury', 'luxury'): 1.0,
        }
        
        return compatibility.get((budget_range, city_cost), 0.6)
    
    def _calculate_route_optimization_score(self, city: City, 
                                          start_city: City, end_city: City) -> float:
        """Calculate how well a city fits into the route optimization."""
        # Calculate route deviation (lower is better)
        deviation = self._calculate_route_deviation(
            city.coordinates, start_city.coordinates, end_city.coordinates
        )
        
        # Convert deviation to score (0-1, where 1 is best)
        if deviation <= 50:  # Within 50km of direct route
            return 1.0
        elif deviation <= 100:  # Within 100km
            return 0.8
        elif deviation <= 150:  # Within 150km
            return 0.5
        else:
            return 0.2  # Too far from route
    
    def _calculate_route_deviation(self, point: Coordinates, 
                                 start: Coordinates, end: Coordinates) -> float:
        """Calculate how far a point deviates from the direct route."""
        # Simple distance calculation (in real implementation, use proper geographic distance)
        
        # Distance from start to point
        start_to_point = math.sqrt(
            (point.latitude - start.latitude) ** 2 + 
            (point.longitude - start.longitude) ** 2
        ) * 111  # Rough km conversion
        
        # Distance from point to end
        point_to_end = math.sqrt(
            (end.latitude - point.latitude) ** 2 + 
            (end.longitude - point.longitude) ** 2
        ) * 111
        
        # Direct distance from start to end
        direct_distance = math.sqrt(
            (end.latitude - start.latitude) ** 2 + 
            (end.longitude - start.longitude) ** 2
        ) * 111
        
        # Deviation is the extra distance
        return max(0, (start_to_point + point_to_end) - direct_distance)
    
    def _find_route_candidates(self, start_city: City, end_city: City) -> List[City]:
        """Find candidate cities along the route."""
        all_cities = list(self.city_service._city_cache.values())
        candidates = []
        
        for city in all_cities:
            if city.name in [start_city.name, end_city.name]:
                continue
            
            # Check if city is reasonably along the route
            deviation = self._calculate_route_deviation(
                city.coordinates, start_city.coordinates, end_city.coordinates
            )
            
            if deviation <= 200:  # Within 200km of direct route
                candidates.append(city)
        
        return candidates
    
    def _generate_recommendation_reasons(self, city: City, preferences: TripPreference,
                                       content_score: float, seasonal_score: float,
                                       budget_score: float) -> List[str]:
        """Generate human-readable reasons for recommending this city."""
        reasons = []
        
        # Content-based reasons
        if content_score > 0.7:
            if preferences.travel_style == 'scenic' and city.types:
                if any(t in ['scenic', 'alpine', 'coastal'] for t in city.types):
                    reasons.append(f"Perfect for scenic lovers with breathtaking {city.types[0]} beauty")
            
            if preferences.travel_style == 'cultural' and city.types:
                if any(t in ['cultural', 'historic', 'unesco'] for t in city.types):
                    reasons.append(f"Rich {city.types[0]} heritage matches your cultural interests")
        
        # Seasonal reasons
        if seasonal_score > 0.8:
            reasons.append(f"Exceptional destination during {preferences.season}")
        
        # Budget reasons
        if budget_score > 0.8:
            reasons.append(f"Great value for {preferences.budget_range} travelers")
        
        # Special features
        if getattr(city, 'unesco', False):
            reasons.append("UNESCO World Heritage site")
        
        rating = getattr(city, 'rating', None) or 0
        if rating > 4.5:
            reasons.append(f"Highly rated destination ({rating}/5)")
        
        # Default reason if no specific ones
        if not reasons:
            reasons.append(f"Well-positioned stop in the beautiful {city.region or city.country} region")
        
        return reasons[:3]  # Limit to top 3 reasons
    
    def _select_diverse_recommendations(self, scored_cities: List[Dict], 
                                      duration_days: int) -> List[Dict]:
        """Select diverse recommendations to avoid clustering."""
        if not scored_cities:
            return []
        
        selected = []
        min_distance_km = max(50, 200 - (duration_days * 10))  # Adjust based on trip length
        
        for candidate in scored_cities:
            if len(selected) >= 5:  # Max 5 recommendations
                break
            
            city = candidate['city']
            
            # Check distance from already selected cities
            too_close = False
            for selected_item in selected:
                selected_city = selected_item['city']
                distance = self._calculate_city_distance(city, selected_city)
                
                if distance < min_distance_km:
                    too_close = True
                    break
            
            if not too_close:
                selected.append(candidate)
        
        return selected
    
    def _calculate_city_distance(self, city1: City, city2: City) -> float:
        """Calculate approximate distance between two cities in km."""
        lat_diff = city1.coordinates.latitude - city2.coordinates.latitude
        lng_diff = city1.coordinates.longitude - city2.coordinates.longitude
        
        # Rough distance calculation
        return math.sqrt(lat_diff ** 2 + lng_diff ** 2) * 111  # ~111 km per degree
    
    def _has_user_history(self, preferences: TripPreference) -> bool:
        """Check if user has travel history for better personalization."""
        return bool(preferences.previous_trips)
    
    def learn_from_trip(self, user_id: str, trip_data: Dict[str, Any]):
        """Learn from completed trips to improve future recommendations."""
        try:
            # Store trip data for collaborative filtering
            if user_id not in self.trip_history:
                self.trip_history[user_id] = []
            
            self.trip_history[user_id].append({
                'timestamp': datetime.now().isoformat(),
                'cities': trip_data.get('cities', []),
                'preferences': trip_data.get('preferences', {}),
                'rating': trip_data.get('user_rating', 0)
            })
            
            logger.info("Learned from trip", user_id=user_id, cities=len(trip_data.get('cities', [])))
            
        except Exception as e:
            logger.error("Failed to learn from trip", error=str(e))
    
    def get_personalized_suggestions(self, user_id: str, preferences: TripPreference) -> List[str]:
        """Get personalized city suggestions based on user history."""
        if user_id not in self.trip_history:
            return []
        
        user_trips = self.trip_history[user_id]
        suggestions = []
        
        # Analyze user's travel patterns
        visited_cities = set()
        preferred_types = []
        
        for trip in user_trips:
            if trip.get('rating', 0) >= 4:  # Only consider well-rated trips
                for city_name in trip.get('cities', []):
                    visited_cities.add(city_name)
                    city = self.city_service.get_city_by_name_sync(city_name)
                    if city and city.types:
                        preferred_types.extend(city.types)
        
        # Find similar cities user hasn't visited
        type_counts = {}
        for t in preferred_types:
            type_counts[t] = type_counts.get(t, 0) + 1
        
        # Get top preferred types
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Find cities with these types that user hasn't visited
        for city in self.city_service._city_cache.values():
            if city.name not in visited_cities and city.types:
                for type_name, _ in top_types:
                    if type_name in city.types:
                        suggestions.append(city.name)
                        break
        
        return suggestions[:10]  # Top 10 suggestions
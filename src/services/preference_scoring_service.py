"""
Real-time Preference Scoring Service

Advanced personalization and preference matching for intermediate city selection.
Uses machine learning, user behavior analysis, and contextual factors.
"""
import json
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import structlog

from ..core.models import City, TripRequest, Coordinates

logger = structlog.get_logger(__name__)


@dataclass
class UserPreferences:
    """Comprehensive user preference profile."""
    # Basic preferences
    budget_range: str = 'mid-range'  # 'budget', 'mid-range', 'luxury'
    travel_style: str = 'balanced'   # 'relaxed', 'balanced', 'packed'
    group_type: str = 'couple'       # 'solo', 'couple', 'family', 'friends'
    
    # Interest weights (0.0 to 1.0)
    cultural_interest: float = 0.7
    natural_beauty_interest: float = 0.6
    culinary_interest: float = 0.8
    adventure_interest: float = 0.4
    relaxation_interest: float = 0.5
    nightlife_interest: float = 0.3
    shopping_interest: float = 0.2
    art_interest: float = 0.6
    history_interest: float = 0.7
    architecture_interest: float = 0.6
    
    # Accommodation preferences
    accommodation_type: str = 'hotel'  # 'hotel', 'boutique', 'hostel', 'airbnb', 'luxury'
    location_preference: str = 'center'  # 'center', 'quiet', 'trendy', 'local'
    
    # Activity preferences
    preferred_pace: str = 'moderate'  # 'slow', 'moderate', 'fast'
    crowd_tolerance: str = 'moderate'  # 'low', 'moderate', 'high'
    authenticity_preference: float = 0.7  # 0.0 (touristy) to 1.0 (authentic)
    
    # Accessibility and practical preferences
    mobility_requirements: List[str] = field(default_factory=list)
    dietary_restrictions: List[str] = field(default_factory=list)
    language_preferences: List[str] = field(default_factory=list)
    
    # Historical behavior
    previously_visited: List[str] = field(default_factory=list)
    highly_rated_cities: List[str] = field(default_factory=list)
    avoided_city_types: List[str] = field(default_factory=list)


@dataclass
class ContextualFactors:
    """Current contextual factors affecting preferences."""
    season: str
    weather_conditions: Optional[str] = None
    local_events: List[Dict] = field(default_factory=list)
    crowd_levels: Optional[str] = None  # 'low', 'moderate', 'high'
    economic_conditions: Optional[str] = None
    safety_level: Optional[str] = None
    current_trends: List[str] = field(default_factory=list)


@dataclass
class CityPersonalizationScore:
    """Detailed personalization scoring for a city."""
    city: City
    overall_score: float
    
    # Component scores
    interest_match_score: float
    budget_compatibility_score: float
    style_match_score: float
    contextual_relevance_score: float
    uniqueness_score: float
    accessibility_score: float
    timing_score: float
    
    # Explanation
    positive_factors: List[str] = field(default_factory=list)
    negative_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence_level: float = 0.8


class RealTimePreferenceScoringService:
    """Advanced preference scoring with real-time personalization."""
    
    def __init__(self):
        self.user_profiles: Dict[str, UserPreferences] = {}
        self.city_profiles: Dict[str, Dict] = {}
        self.scoring_models = self._initialize_scoring_models()
        self.contextual_factors_cache: Dict[str, ContextualFactors] = {}
        
        # Load pre-computed city characteristics
        self._load_city_characteristics()
    
    def _initialize_scoring_models(self) -> Dict[str, Any]:
        """Initialize scoring models and weights."""
        return {
            'interest_weights': {
                'cultural': ['cultural', 'historic', 'unesco', 'museums', 'heritage'],
                'natural': ['scenic', 'nature', 'lakes', 'mountains', 'parks', 'alpine'],
                'culinary': ['culinary', 'food', 'wine', 'markets', 'gastronomy'],
                'adventure': ['adventure', 'outdoor', 'sports', 'hiking', 'skiing'],
                'relaxation': ['spa', 'thermal', 'peaceful', 'resort', 'quiet'],
                'nightlife': ['nightlife', 'bars', 'clubs', 'entertainment'],
                'shopping': ['shopping', 'fashion', 'markets', 'boutiques'],
                'art': ['artistic', 'galleries', 'contemporary', 'creative'],
                'history': ['historic', 'ancient', 'medieval', 'roman', 'heritage'],
                'architecture': ['architectural', 'buildings', 'palaces', 'churches']
            },
            'budget_indicators': {
                'luxury': ['luxury', 'exclusive', 'premium', 'high-end'],
                'mid-range': ['cultural', 'historic', 'scenic', 'traditional'],
                'budget': ['authentic', 'local', 'village', 'rural', 'simple']
            },
            'style_indicators': {
                'relaxed': ['peaceful', 'quiet', 'spa', 'resort', 'calm'],
                'balanced': ['cultural', 'scenic', 'historic', 'traditional'],
                'packed': ['vibrant', 'busy', 'metropolitan', 'dynamic']
            }
        }
    
    def _load_city_characteristics(self):
        """Load detailed city characteristics for scoring."""
        # This would typically load from a database or API
        # For now, we'll use a representative sample
        self.city_profiles = {
            'paris': {
                'characteristics': {
                    'cultural_richness': 0.95,
                    'culinary_excellence': 0.90,
                    'art_scene': 0.95,
                    'architecture_beauty': 0.90,
                    'romantic_appeal': 0.90,
                    'luxury_level': 0.85,
                    'crowd_level': 0.90,
                    'authenticity': 0.60,
                    'safety': 0.80,
                    'accessibility': 0.85
                },
                'seasonal_factors': {
                    'spring': 0.90,
                    'summer': 0.95,
                    'autumn': 0.85,
                    'winter': 0.75
                },
                'cost_level': 4,  # 1-5 scale
                'ideal_duration': 3  # days
            },
            'annecy': {
                'characteristics': {
                    'natural_beauty': 0.95,
                    'romantic_appeal': 0.85,
                    'peaceful_atmosphere': 0.90,
                    'outdoor_activities': 0.80,
                    'authenticity': 0.85,
                    'culinary_scene': 0.70,
                    'crowd_level': 0.40,
                    'safety': 0.95,
                    'accessibility': 0.75
                },
                'seasonal_factors': {
                    'spring': 0.85,
                    'summer': 0.95,
                    'autumn': 0.80,
                    'winter': 0.60
                },
                'cost_level': 3,
                'ideal_duration': 2
            },
            'florence': {
                'characteristics': {
                    'cultural_richness': 0.95,
                    'art_scene': 0.98,
                    'architecture_beauty': 0.95,
                    'culinary_excellence': 0.85,
                    'historic_significance': 0.95,
                    'luxury_level': 0.70,
                    'crowd_level': 0.85,
                    'authenticity': 0.80,
                    'safety': 0.85,
                    'accessibility': 0.80
                },
                'seasonal_factors': {
                    'spring': 0.90,
                    'summer': 0.85,  # Hot and crowded
                    'autumn': 0.95,
                    'winter': 0.80
                },
                'cost_level': 3,
                'ideal_duration': 3
            }
        }
    
    def calculate_personalization_score(
        self, 
        city: City, 
        user_preferences: UserPreferences,
        contextual_factors: ContextualFactors,
        trip_request: TripRequest
    ) -> CityPersonalizationScore:
        """Calculate comprehensive personalization score for a city."""
        
        # Get city profile
        city_profile = self.city_profiles.get(city.name.lower(), self._generate_default_profile(city))
        
        # Calculate component scores
        interest_score = self._calculate_interest_match_score(
            city, city_profile, user_preferences
        )
        budget_score = self._calculate_budget_compatibility_score(
            city, city_profile, user_preferences
        )
        style_score = self._calculate_style_match_score(
            city, city_profile, user_preferences
        )
        contextual_score = self._calculate_contextual_relevance_score(
            city, city_profile, contextual_factors
        )
        uniqueness_score = self._calculate_uniqueness_score(
            city, user_preferences
        )
        accessibility_score = self._calculate_accessibility_score(
            city, city_profile, user_preferences
        )
        timing_score = self._calculate_timing_score(
            city, city_profile, contextual_factors, trip_request
        )
        
        # Weight and combine scores
        weights = {
            'interest': 0.30,
            'budget': 0.15,
            'style': 0.15,
            'contextual': 0.15,
            'uniqueness': 0.10,
            'accessibility': 0.05,
            'timing': 0.10
        }
        
        overall_score = (
            interest_score * weights['interest'] +
            budget_score * weights['budget'] +
            style_score * weights['style'] +
            contextual_score * weights['contextual'] +
            uniqueness_score * weights['uniqueness'] +
            accessibility_score * weights['accessibility'] +
            timing_score * weights['timing']
        )
        
        # Generate explanations
        positive_factors, negative_factors, recommendations = self._generate_explanations(
            city, city_profile, user_preferences, {
                'interest': interest_score,
                'budget': budget_score,
                'style': style_score,
                'contextual': contextual_score,
                'uniqueness': uniqueness_score,
                'accessibility': accessibility_score,
                'timing': timing_score
            }
        )
        
        # Calculate confidence level
        confidence = self._calculate_confidence_level(city, city_profile)
        
        return CityPersonalizationScore(
            city=city,
            overall_score=overall_score,
            interest_match_score=interest_score,
            budget_compatibility_score=budget_score,
            style_match_score=style_score,
            contextual_relevance_score=contextual_score,
            uniqueness_score=uniqueness_score,
            accessibility_score=accessibility_score,
            timing_score=timing_score,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            recommendations=recommendations,
            confidence_level=confidence
        )
    
    def _calculate_interest_match_score(
        self, 
        city: City, 
        city_profile: Dict, 
        user_preferences: UserPreferences
    ) -> float:
        """Calculate how well the city matches user interests."""
        
        score = 0.0
        total_weight = 0.0
        
        interest_mappings = {
            'cultural_interest': 'cultural_richness',
            'natural_beauty_interest': 'natural_beauty',
            'culinary_interest': 'culinary_excellence',
            'adventure_interest': 'outdoor_activities',
            'art_interest': 'art_scene',
            'history_interest': 'historic_significance'
        }
        
        characteristics = city_profile.get('characteristics', {})
        
        for user_interest, city_characteristic in interest_mappings.items():
            user_weight = getattr(user_preferences, user_interest, 0.5)
            city_strength = characteristics.get(city_characteristic, 0.5)
            
            score += user_weight * city_strength
            total_weight += user_weight
        
        # Normalize by total weight
        if total_weight > 0:
            score = score / total_weight
        
        # Add bonus for perfect matches
        city_types = getattr(city, 'types', [])
        interest_keywords = self.scoring_models['interest_weights']
        
        bonus = 0.0
        for interest_type, keywords in interest_keywords.items():
            user_interest_level = getattr(user_preferences, f"{interest_type}_interest", 0.5)
            if user_interest_level > 0.7:  # Strong interest
                type_match = any(keyword in city_types for keyword in keywords)
                if type_match:
                    bonus += 0.1 * user_interest_level
        
        return min(score + bonus, 1.0)
    
    def _calculate_budget_compatibility_score(
        self, 
        city: City, 
        city_profile: Dict, 
        user_preferences: UserPreferences
    ) -> float:
        """Calculate budget compatibility score."""
        
        city_cost_level = city_profile.get('cost_level', 3)  # 1-5 scale
        user_budget = user_preferences.budget_range
        
        budget_mappings = {
            'budget': (1, 2),      # Cost levels 1-2
            'mid-range': (2, 4),   # Cost levels 2-4
            'luxury': (4, 5)       # Cost levels 4-5
        }
        
        min_cost, max_cost = budget_mappings.get(user_budget, (2, 4))
        
        if min_cost <= city_cost_level <= max_cost:
            # Perfect budget match
            return 1.0
        elif city_cost_level < min_cost:
            # City is cheaper than preferred (might be good)
            if user_budget == 'luxury':
                return 0.3  # Luxury travelers might not want budget places
            else:
                return 0.8  # Generally good to save money
        else:
            # City is more expensive than budget
            overage = city_cost_level - max_cost
            return max(0.2, 1.0 - (overage * 0.3))  # Penalty for being over budget
    
    def _calculate_style_match_score(
        self, 
        city: City, 
        city_profile: Dict, 
        user_preferences: UserPreferences
    ) -> float:
        """Calculate travel style compatibility."""
        
        characteristics = city_profile.get('characteristics', {})
        user_style = user_preferences.travel_style
        
        style_scores = {
            'relaxed': (
                characteristics.get('peaceful_atmosphere', 0.5) * 0.4 +
                (1.0 - characteristics.get('crowd_level', 0.5)) * 0.3 +
                characteristics.get('spa_wellness', 0.5) * 0.3
            ),
            'balanced': (
                characteristics.get('cultural_richness', 0.5) * 0.3 +
                characteristics.get('accessibility', 0.5) * 0.3 +
                characteristics.get('variety_activities', 0.7) * 0.4
            ),
            'packed': (
                characteristics.get('variety_activities', 0.7) * 0.4 +
                characteristics.get('vibrant_atmosphere', 0.6) * 0.3 +
                characteristics.get('accessibility', 0.5) * 0.3
            )
        }
        
        base_score = style_scores.get(user_style, 0.6)
        
        # Add crowd tolerance factor
        crowd_level = characteristics.get('crowd_level', 0.5)
        crowd_tolerance = user_preferences.crowd_tolerance
        
        if crowd_tolerance == 'low' and crowd_level > 0.7:
            base_score *= 0.7  # Penalty for high crowds with low tolerance
        elif crowd_tolerance == 'high' and crowd_level < 0.3:
            base_score *= 0.9  # Slight penalty for low energy with high tolerance
        
        return min(base_score, 1.0)
    
    def _calculate_contextual_relevance_score(
        self, 
        city: City, 
        city_profile: Dict, 
        contextual_factors: ContextualFactors
    ) -> float:
        """Calculate relevance based on current context."""
        
        score = 0.7  # Base score
        
        # Seasonal relevance
        seasonal_factors = city_profile.get('seasonal_factors', {})
        season_score = seasonal_factors.get(contextual_factors.season, 0.7)
        score = (score + season_score) / 2
        
        # Event relevance
        if contextual_factors.local_events:
            event_bonus = min(0.2, len(contextual_factors.local_events) * 0.05)
            score += event_bonus
        
        # Weather conditions
        if contextual_factors.weather_conditions:
            weather_adjustments = {
                'sunny': 0.1,
                'rainy': -0.1,
                'cloudy': 0.0,
                'hot': -0.05,
                'cold': -0.05,
                'perfect': 0.15
            }
            weather_adj = weather_adjustments.get(contextual_factors.weather_conditions, 0.0)
            score += weather_adj
        
        # Current trends
        if contextual_factors.current_trends:
            city_types = getattr(city, 'types', [])
            trend_match = any(trend.lower() in ' '.join(city_types).lower() 
                            for trend in contextual_factors.current_trends)
            if trend_match:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_uniqueness_score(
        self, 
        city: City, 
        user_preferences: UserPreferences
    ) -> float:
        """Calculate uniqueness and novelty score."""
        
        # Check if user has been there before
        if city.name.lower() in [prev.lower() for prev in user_preferences.previously_visited]:
            return 0.2  # Low score for repeat visits
        
        # Check authenticity preference
        authenticity = user_preferences.authenticity_preference
        city_types = getattr(city, 'types', [])
        
        authentic_indicators = ['authentic', 'local', 'hidden', 'traditional', 'village']
        touristy_indicators = ['tourist', 'popular', 'crowded', 'commercial']
        
        authentic_score = sum(1 for indicator in authentic_indicators if indicator in city_types)
        touristy_score = sum(1 for indicator in touristy_indicators if indicator in city_types)
        
        if authentic_score > touristy_score:
            authenticity_score = authenticity
        elif touristy_score > authentic_score:
            authenticity_score = 1.0 - authenticity
        else:
            authenticity_score = 0.6  # Neutral
        
        # Unique features bonus
        unique_indicators = ['unique', 'rare', 'exceptional', 'extraordinary', 'one-of-a-kind']
        uniqueness_bonus = sum(0.1 for indicator in unique_indicators if indicator in city_types)
        
        return min(authenticity_score + uniqueness_bonus, 1.0)
    
    def _calculate_accessibility_score(
        self, 
        city: City, 
        city_profile: Dict, 
        user_preferences: UserPreferences
    ) -> float:
        """Calculate accessibility score based on user needs."""
        
        base_accessibility = city_profile.get('characteristics', {}).get('accessibility', 0.8)
        
        # Apply mobility requirements
        if user_preferences.mobility_requirements:
            # This would check specific accessibility features
            # For now, use a general adjustment
            mobility_penalty = len(user_preferences.mobility_requirements) * 0.1
            base_accessibility *= (1.0 - mobility_penalty)
        
        # Language considerations
        if user_preferences.language_preferences:
            # European cities generally have good English support
            language_bonus = 0.1
            base_accessibility += language_bonus
        
        return min(base_accessibility, 1.0)
    
    def _calculate_timing_score(
        self, 
        city: City, 
        city_profile: Dict, 
        contextual_factors: ContextualFactors,
        trip_request: TripRequest
    ) -> float:
        """Calculate timing appropriateness score."""
        
        score = 0.8  # Base score
        
        # Ideal duration matching
        ideal_duration = city_profile.get('ideal_duration', 2)
        trip_duration = getattr(trip_request, 'travel_days', 7)
        
        if trip_duration >= ideal_duration:
            duration_score = 1.0
        else:
            duration_score = 0.6  # Still okay but not ideal
        
        score = (score + duration_score) / 2
        
        # Seasonal timing
        seasonal_factors = city_profile.get('seasonal_factors', {})
        season_score = seasonal_factors.get(contextual_factors.season, 0.7)
        score = (score + season_score) / 2
        
        return score
    
    def _generate_explanations(
        self, 
        city: City, 
        city_profile: Dict, 
        user_preferences: UserPreferences,
        component_scores: Dict[str, float]
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate human-readable explanations for the scoring."""
        
        positive_factors = []
        negative_factors = []
        recommendations = []
        
        # Analyze component scores
        if component_scores['interest'] > 0.8:
            positive_factors.append("Excellent match for your interests")
        elif component_scores['interest'] < 0.4:
            negative_factors.append("Limited appeal for your interests")
        
        if component_scores['budget'] > 0.8:
            positive_factors.append("Perfect fit for your budget")
        elif component_scores['budget'] < 0.4:
            negative_factors.append("May exceed your budget preferences")
            recommendations.append("Consider budget-friendly accommodation options")
        
        if component_scores['uniqueness'] > 0.8:
            positive_factors.append("Offers unique and authentic experiences")
        
        if component_scores['timing'] > 0.8:
            positive_factors.append("Ideal timing for your visit")
        elif component_scores['timing'] < 0.5:
            recommendations.append("Consider visiting during peak season for better experience")
        
        # City-specific recommendations
        characteristics = city_profile.get('characteristics', {})
        
        if characteristics.get('culinary_excellence', 0) > 0.8:
            recommendations.append("Don't miss the local culinary scene")
        
        if characteristics.get('art_scene', 0) > 0.8:
            recommendations.append("Explore the vibrant art galleries and museums")
        
        if characteristics.get('outdoor_activities', 0) > 0.8:
            recommendations.append("Perfect for outdoor activities and nature excursions")
        
        return positive_factors, negative_factors, recommendations
    
    def _calculate_confidence_level(self, city: City, city_profile: Dict) -> float:
        """Calculate confidence level in the scoring."""
        
        # Higher confidence for cities with detailed profiles
        profile_completeness = len(city_profile.get('characteristics', {})) / 10
        
        # Higher confidence for cities with types information
        types_confidence = 0.8 if getattr(city, 'types', []) else 0.4
        
        # Base confidence
        base_confidence = 0.7
        
        return min((base_confidence + profile_completeness + types_confidence) / 3, 1.0)
    
    def _generate_default_profile(self, city: City) -> Dict:
        """Generate a default profile for cities not in the database."""
        return {
            'characteristics': {
                'cultural_richness': 0.6,
                'natural_beauty': 0.5,
                'culinary_excellence': 0.6,
                'accessibility': 0.7,
                'safety': 0.8,
                'authenticity': 0.7
            },
            'seasonal_factors': {
                'spring': 0.8,
                'summer': 0.8,
                'autumn': 0.7,
                'winter': 0.6
            },
            'cost_level': 3,
            'ideal_duration': 2
        }
    
    def get_contextual_factors(self, region: str = "europe") -> ContextualFactors:
        """Get current contextual factors for the region."""
        
        # Determine current season
        month = datetime.now().month
        if month in [12, 1, 2]:
            season = 'winter'
        elif month in [3, 4, 5]:
            season = 'spring'
        elif month in [6, 7, 8]:
            season = 'summer'
        else:
            season = 'autumn'
        
        # This would typically fetch real-time data
        return ContextualFactors(
            season=season,
            weather_conditions='pleasant',
            local_events=[],
            crowd_levels='moderate',
            current_trends=['sustainable travel', 'local experiences']
        )
    
    def create_user_preferences_from_request(self, trip_request: TripRequest) -> UserPreferences:
        """Create user preferences from trip request."""
        
        # Extract preferences from request attributes
        budget_range = getattr(trip_request, 'budget_range', 'mid-range')
        interests = getattr(trip_request, 'interests', [])
        
        # Create base preferences
        preferences = UserPreferences(budget_range=budget_range)
        
        # Adjust interest weights based on stated interests
        if 'culture' in interests:
            preferences.cultural_interest = 0.9
            preferences.art_interest = 0.8
            preferences.history_interest = 0.9
        
        if 'food' in interests:
            preferences.culinary_interest = 0.9
        
        if 'nature' in interests:
            preferences.natural_beauty_interest = 0.9
            preferences.adventure_interest = 0.7
        
        if 'art' in interests:
            preferences.art_interest = 0.9
            preferences.cultural_interest = 0.8
        
        if 'relaxation' in interests:
            preferences.relaxation_interest = 0.9
            preferences.preferred_pace = 'slow'
        
        return preferences


# Global service instance
_preference_scoring_service = None

def get_preference_scoring_service() -> RealTimePreferenceScoringService:
    """Get the global preference scoring service instance."""
    global _preference_scoring_service
    if _preference_scoring_service is None:
        _preference_scoring_service = RealTimePreferenceScoringService()
    return _preference_scoring_service
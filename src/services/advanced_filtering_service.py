"""
Advanced Filtering Service

Real-time filtering for intermediate city selection based on time, budget,
accessibility, and dynamic conditions.
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog

from ..core.models import City, TripRequest, Coordinates

logger = structlog.get_logger(__name__)


@dataclass
class FilterCriteria:
    """Comprehensive filtering criteria."""
    # Time-based filters
    season: Optional[str] = None
    time_of_day: Optional[str] = None
    opening_hours_required: bool = False
    avoid_peak_times: bool = False
    
    # Budget filters
    budget_range: Optional[str] = None
    max_cost_per_day: Optional[float] = None
    include_free_activities: bool = True
    
    # Accessibility filters
    wheelchair_accessible: bool = False
    public_transport_access: bool = False
    parking_available: bool = False
    family_friendly: bool = False
    
    # Safety and practical filters
    safety_level_min: Optional[str] = None
    language_barrier_tolerance: Optional[str] = None
    crowd_level_preference: Optional[str] = None
    
    # Experience filters
    avoid_tourist_traps: bool = False
    prioritize_local_experiences: bool = False
    cultural_significance_min: Optional[float] = None
    
    # Dynamic filters
    weather_dependent: bool = False
    event_coincidence: bool = False
    real_time_conditions: bool = True


@dataclass
class FilterResult:
    """Result of filtering operation."""
    filtered_cities: List[City]
    filter_explanations: Dict[str, str]
    rejected_cities: Dict[str, List[str]]  # City name -> reasons
    filter_statistics: Dict[str, int]


class AdvancedFilteringService:
    """Advanced filtering with real-time conditions and dynamic criteria."""
    
    def __init__(self):
        self.filter_cache: Dict[str, FilterResult] = {}
        self.real_time_data_cache: Dict[str, Dict] = {}
        self.last_cache_update = datetime.now()
        
        # Initialize filter databases
        self._initialize_filter_databases()
    
    def _initialize_filter_databases(self):
        """Initialize comprehensive filter databases."""
        
        # Budget information (cost level 1-5)
        self.city_budget_info = {
            'paris': {'cost_level': 4, 'daily_budget': {'budget': 80, 'mid-range': 150, 'luxury': 300}},
            'nice': {'cost_level': 4, 'daily_budget': {'budget': 70, 'mid-range': 130, 'luxury': 250}},
            'florence': {'cost_level': 3, 'daily_budget': {'budget': 60, 'mid-range': 110, 'luxury': 200}},
            'annecy': {'cost_level': 3, 'daily_budget': {'budget': 65, 'mid-range': 120, 'luxury': 220}},
            'venice': {'cost_level': 4, 'daily_budget': {'budget': 75, 'mid-range': 140, 'luxury': 280}},
            'rome': {'cost_level': 3, 'daily_budget': {'budget': 65, 'mid-range': 125, 'luxury': 230}},
            'barcelona': {'cost_level': 3, 'daily_budget': {'budget': 60, 'mid-range': 115, 'luxury': 210}},
            'madrid': {'cost_level': 3, 'daily_budget': {'budget': 55, 'mid-range': 105, 'luxury': 190}}
        }
        
        # Accessibility information
        self.city_accessibility_info = {
            'paris': {
                'wheelchair_accessible': True,
                'public_transport': 'excellent',
                'parking': 'limited',
                'family_friendly': True,
                'language_barrier': 'low'
            },
            'nice': {
                'wheelchair_accessible': True,
                'public_transport': 'good',
                'parking': 'moderate',
                'family_friendly': True,
                'language_barrier': 'low'
            },
            'florence': {
                'wheelchair_accessible': False,  # Historic center challenges
                'public_transport': 'good',
                'parking': 'limited',
                'family_friendly': True,
                'language_barrier': 'moderate'
            },
            'annecy': {
                'wheelchair_accessible': True,
                'public_transport': 'limited',
                'parking': 'good',
                'family_friendly': True,
                'language_barrier': 'moderate'
            }
        }
        
        # Safety information
        self.city_safety_info = {
            'paris': {'safety_level': 'good', 'tourist_safety': 'high'},
            'nice': {'safety_level': 'excellent', 'tourist_safety': 'high'},
            'florence': {'safety_level': 'excellent', 'tourist_safety': 'high'},
            'annecy': {'safety_level': 'excellent', 'tourist_safety': 'high'},
            'venice': {'safety_level': 'good', 'tourist_safety': 'high'},
            'rome': {'safety_level': 'good', 'tourist_safety': 'moderate'},
            'barcelona': {'safety_level': 'good', 'tourist_safety': 'moderate'},
            'madrid': {'safety_level': 'good', 'tourist_safety': 'high'}
        }
        
        # Seasonal appropriateness
        self.city_seasonal_info = {
            'paris': {
                'spring': 0.9, 'summer': 0.95, 'autumn': 0.85, 'winter': 0.75,
                'weather_dependent': False
            },
            'nice': {
                'spring': 0.85, 'summer': 0.95, 'autumn': 0.90, 'winter': 0.70,
                'weather_dependent': True
            },
            'florence': {
                'spring': 0.90, 'summer': 0.80, 'autumn': 0.95, 'winter': 0.80,
                'weather_dependent': False
            },
            'annecy': {
                'spring': 0.85, 'summer': 0.95, 'autumn': 0.80, 'winter': 0.60,
                'weather_dependent': True
            }
        }
        
        # Tourist density and authenticity
        self.city_experience_info = {
            'paris': {'tourist_density': 'very_high', 'authenticity_score': 0.6, 'local_experience': 0.7},
            'nice': {'tourist_density': 'high', 'authenticity_score': 0.7, 'local_experience': 0.8},
            'florence': {'tourist_density': 'very_high', 'authenticity_score': 0.6, 'local_experience': 0.6},
            'annecy': {'tourist_density': 'moderate', 'authenticity_score': 0.85, 'local_experience': 0.9},
            'venice': {'tourist_density': 'extreme', 'authenticity_score': 0.4, 'local_experience': 0.5},
            'rome': {'tourist_density': 'very_high', 'authenticity_score': 0.6, 'local_experience': 0.7}
        }
    
    async def apply_advanced_filters(
        self, 
        cities: List[City], 
        filter_criteria: FilterCriteria,
        trip_request: TripRequest
    ) -> FilterResult:
        """Apply comprehensive advanced filtering to city list."""
        
        logger.info("Applying advanced filters", criteria=filter_criteria)
        
        # Update real-time data if needed
        await self._update_real_time_data(cities)
        
        filtered_cities = cities.copy()
        rejected_cities = {}
        filter_explanations = {}
        filter_statistics = {}
        
        # Apply each filter category
        filtered_cities, time_rejects = await self._apply_time_filters(
            filtered_cities, filter_criteria
        )
        rejected_cities.update(time_rejects)
        filter_statistics['time_filtered'] = len(time_rejects)
        
        filtered_cities, budget_rejects = self._apply_budget_filters(
            filtered_cities, filter_criteria, trip_request
        )
        rejected_cities.update(budget_rejects)
        filter_statistics['budget_filtered'] = len(budget_rejects)
        
        filtered_cities, accessibility_rejects = self._apply_accessibility_filters(
            filtered_cities, filter_criteria
        )
        rejected_cities.update(accessibility_rejects)
        filter_statistics['accessibility_filtered'] = len(accessibility_rejects)
        
        filtered_cities, safety_rejects = self._apply_safety_filters(
            filtered_cities, filter_criteria
        )
        rejected_cities.update(safety_rejects)
        filter_statistics['safety_filtered'] = len(safety_rejects)
        
        filtered_cities, experience_rejects = self._apply_experience_filters(
            filtered_cities, filter_criteria
        )
        rejected_cities.update(experience_rejects)
        filter_statistics['experience_filtered'] = len(experience_rejects)
        
        filtered_cities, dynamic_rejects = await self._apply_dynamic_filters(
            filtered_cities, filter_criteria
        )
        rejected_cities.update(dynamic_rejects)
        filter_statistics['dynamic_filtered'] = len(dynamic_rejects)
        
        # Generate explanations
        filter_explanations = self._generate_filter_explanations(
            filter_criteria, filter_statistics
        )
        
        logger.info(f"Filtering complete: {len(cities)} -> {len(filtered_cities)} cities")
        
        return FilterResult(
            filtered_cities=filtered_cities,
            filter_explanations=filter_explanations,
            rejected_cities=rejected_cities,
            filter_statistics=filter_statistics
        )
    
    async def _apply_time_filters(
        self, cities: List[City], criteria: FilterCriteria
    ) -> Tuple[List[City], Dict[str, List[str]]]:
        """Apply time-based filters."""
        
        filtered_cities = []
        rejected_cities = {}
        
        current_season = self._get_current_season()
        
        for city in cities:
            reject_reasons = []
            
            # Seasonal appropriateness
            if criteria.season:
                seasonal_info = self.city_seasonal_info.get(city.name.lower(), {})
                season_score = seasonal_info.get(criteria.season, 0.5)
                
                if season_score < 0.6:  # Below acceptable threshold
                    reject_reasons.append(f"Not ideal for {criteria.season} season")
            
            # Weather dependency
            if criteria.weather_dependent:
                seasonal_info = self.city_seasonal_info.get(city.name.lower(), {})
                if seasonal_info.get('weather_dependent', False) and current_season == 'winter':
                    reject_reasons.append("Weather-dependent activities not available in winter")
            
            # Peak time avoidance
            if criteria.avoid_peak_times:
                if current_season == 'summer':
                    experience_info = self.city_experience_info.get(city.name.lower(), {})
                    if experience_info.get('tourist_density') in ['very_high', 'extreme']:
                        reject_reasons.append("Avoiding peak tourist season")
            
            if reject_reasons:
                rejected_cities[city.name] = reject_reasons
            else:
                filtered_cities.append(city)
        
        return filtered_cities, rejected_cities
    
    def _apply_budget_filters(
        self, cities: List[City], criteria: FilterCriteria, trip_request: TripRequest
    ) -> Tuple[List[City], Dict[str, List[str]]]:
        """Apply budget-based filters."""
        
        filtered_cities = []
        rejected_cities = {}
        
        for city in cities:
            reject_reasons = []
            
            city_budget = self.city_budget_info.get(city.name.lower(), {})
            
            # Budget range filter
            if criteria.budget_range:
                daily_budgets = city_budget.get('daily_budget', {})
                city_daily_cost = daily_budgets.get(criteria.budget_range, 0)
                
                if criteria.max_cost_per_day and city_daily_cost > criteria.max_cost_per_day:
                    reject_reasons.append(f"Daily cost €{city_daily_cost} exceeds budget €{criteria.max_cost_per_day}")
            
            # Cost level filter
            cost_level = city_budget.get('cost_level', 3)
            budget_range = criteria.budget_range or getattr(trip_request, 'budget_range', 'mid-range')
            
            if budget_range == 'budget' and cost_level > 3:
                reject_reasons.append("City too expensive for budget travel")
            elif budget_range == 'luxury' and cost_level < 3:
                reject_reasons.append("City may not meet luxury standards")
            
            if reject_reasons:
                rejected_cities[city.name] = reject_reasons
            else:
                filtered_cities.append(city)
        
        return filtered_cities, rejected_cities
    
    def _apply_accessibility_filters(
        self, cities: List[City], criteria: FilterCriteria
    ) -> Tuple[List[City], Dict[str, List[str]]]:
        """Apply accessibility filters."""
        
        filtered_cities = []
        rejected_cities = {}
        
        for city in cities:
            reject_reasons = []
            
            accessibility_info = self.city_accessibility_info.get(city.name.lower(), {})
            
            # Wheelchair accessibility
            if criteria.wheelchair_accessible:
                if not accessibility_info.get('wheelchair_accessible', False):
                    reject_reasons.append("Limited wheelchair accessibility")
            
            # Public transport requirement
            if criteria.public_transport_access:
                transport_quality = accessibility_info.get('public_transport', 'unknown')
                if transport_quality in ['poor', 'limited', 'unknown']:
                    reject_reasons.append("Insufficient public transport")
            
            # Parking requirement
            if criteria.parking_available:
                parking_availability = accessibility_info.get('parking', 'unknown')
                if parking_availability in ['limited', 'poor', 'unknown']:
                    reject_reasons.append("Limited parking availability")
            
            # Family-friendly requirement
            if criteria.family_friendly:
                if not accessibility_info.get('family_friendly', True):
                    reject_reasons.append("Not suitable for families")
            
            if reject_reasons:
                rejected_cities[city.name] = reject_reasons
            else:
                filtered_cities.append(city)
        
        return filtered_cities, rejected_cities
    
    def _apply_safety_filters(
        self, cities: List[City], criteria: FilterCriteria
    ) -> Tuple[List[City], Dict[str, List[str]]]:
        """Apply safety and practical filters."""
        
        filtered_cities = []
        rejected_cities = {}
        
        for city in cities:
            reject_reasons = []
            
            safety_info = self.city_safety_info.get(city.name.lower(), {})
            accessibility_info = self.city_accessibility_info.get(city.name.lower(), {})
            
            # Safety level requirement
            if criteria.safety_level_min:
                safety_level = safety_info.get('safety_level', 'unknown')
                safety_levels = ['poor', 'fair', 'good', 'excellent']
                
                min_index = safety_levels.index(criteria.safety_level_min) if criteria.safety_level_min in safety_levels else 2
                current_index = safety_levels.index(safety_level) if safety_level in safety_levels else 1
                
                if current_index < min_index:
                    reject_reasons.append(f"Safety level {safety_level} below minimum {criteria.safety_level_min}")
            
            # Language barrier tolerance
            if criteria.language_barrier_tolerance:
                language_barrier = accessibility_info.get('language_barrier', 'moderate')
                
                if criteria.language_barrier_tolerance == 'low' and language_barrier in ['high', 'very_high']:
                    reject_reasons.append("Language barrier too high")
            
            if reject_reasons:
                rejected_cities[city.name] = reject_reasons
            else:
                filtered_cities.append(city)
        
        return filtered_cities, rejected_cities
    
    def _apply_experience_filters(
        self, cities: List[City], criteria: FilterCriteria
    ) -> Tuple[List[City], Dict[str, List[str]]]:
        """Apply experience and authenticity filters."""
        
        filtered_cities = []
        rejected_cities = {}
        
        for city in cities:
            reject_reasons = []
            
            experience_info = self.city_experience_info.get(city.name.lower(), {})
            
            # Avoid tourist traps
            if criteria.avoid_tourist_traps:
                tourist_density = experience_info.get('tourist_density', 'moderate')
                if tourist_density in ['very_high', 'extreme']:
                    reject_reasons.append("High tourist density - potential tourist trap")
            
            # Prioritize local experiences
            if criteria.prioritize_local_experiences:
                local_score = experience_info.get('local_experience', 0.5)
                if local_score < 0.7:
                    reject_reasons.append("Limited authentic local experiences")
            
            # Cultural significance minimum
            if criteria.cultural_significance_min:
                # Use authenticity score as proxy for cultural significance
                cultural_score = experience_info.get('authenticity_score', 0.5)
                if cultural_score < criteria.cultural_significance_min:
                    reject_reasons.append(f"Cultural significance {cultural_score:.1f} below minimum {criteria.cultural_significance_min}")
            
            # Crowd level preference
            if criteria.crowd_level_preference:
                tourist_density = experience_info.get('tourist_density', 'moderate')
                
                if criteria.crowd_level_preference == 'low' and tourist_density in ['high', 'very_high', 'extreme']:
                    reject_reasons.append("Crowd level too high for preference")
                elif criteria.crowd_level_preference == 'high' and tourist_density in ['low', 'very_low']:
                    reject_reasons.append("Crowd level too low for preference")
            
            if reject_reasons:
                rejected_cities[city.name] = reject_reasons
            else:
                filtered_cities.append(city)
        
        return filtered_cities, rejected_cities
    
    async def _apply_dynamic_filters(
        self, cities: List[City], criteria: FilterCriteria
    ) -> Tuple[List[City], Dict[str, List[str]]]:
        """Apply dynamic real-time filters."""
        
        filtered_cities = []
        rejected_cities = {}
        
        if not criteria.real_time_conditions:
            return cities, {}
        
        for city in cities:
            reject_reasons = []
            
            # Real-time conditions (simulated)
            real_time_data = self.real_time_data_cache.get(city.name.lower(), {})
            
            # Weather conditions
            current_weather = real_time_data.get('weather', {})
            if criteria.weather_dependent and current_weather.get('condition') == 'severe':
                reject_reasons.append("Severe weather conditions")
            
            # Event coincidence
            if criteria.event_coincidence:
                events = real_time_data.get('events', [])
                if not events:
                    reject_reasons.append("No special events during visit")
            
            # Transportation disruptions
            transport_status = real_time_data.get('transport_disruptions', False)
            if transport_status:
                reject_reasons.append("Current transportation disruptions")
            
            if reject_reasons:
                rejected_cities[city.name] = reject_reasons
            else:
                filtered_cities.append(city)
        
        return filtered_cities, rejected_cities
    
    async def _update_real_time_data(self, cities: List[City]):
        """Update real-time data for cities (simulated)."""
        
        # Check if cache needs updating (every 30 minutes)
        if datetime.now() - self.last_cache_update < timedelta(minutes=30):
            return
        
        logger.info("Updating real-time data for cities")
        
        for city in cities:
            # Simulate real-time data updates
            self.real_time_data_cache[city.name.lower()] = {
                'weather': {
                    'condition': 'clear',  # clear, cloudy, rainy, severe
                    'temperature': 22,
                    'updated': datetime.now().isoformat()
                },
                'events': [
                    {'name': 'Local Festival', 'type': 'cultural', 'date': 'today'}
                ] if city.name.lower() in ['annecy', 'nice'] else [],
                'transport_disruptions': False,
                'crowd_level': 'moderate',
                'updated': datetime.now().isoformat()
            }
        
        self.last_cache_update = datetime.now()
    
    def _generate_filter_explanations(
        self, criteria: FilterCriteria, statistics: Dict[str, int]
    ) -> Dict[str, str]:
        """Generate human-readable filter explanations."""
        
        explanations = {}
        
        total_filtered = sum(statistics.values())
        if total_filtered > 0:
            explanations['overview'] = f"Applied {len([k for k, v in statistics.items() if v > 0])} filter categories, filtering {total_filtered} cities"
        
        if statistics.get('budget_filtered', 0) > 0:
            explanations['budget'] = f"Filtered {statistics['budget_filtered']} cities outside budget range"
        
        if statistics.get('accessibility_filtered', 0) > 0:
            explanations['accessibility'] = f"Filtered {statistics['accessibility_filtered']} cities not meeting accessibility requirements"
        
        if statistics.get('experience_filtered', 0) > 0:
            explanations['experience'] = f"Filtered {statistics['experience_filtered']} cities not matching experience preferences"
        
        if statistics.get('time_filtered', 0) > 0:
            explanations['timing'] = f"Filtered {statistics['time_filtered']} cities not suitable for current timing"
        
        if statistics.get('dynamic_filtered', 0) > 0:
            explanations['real_time'] = f"Filtered {statistics['dynamic_filtered']} cities due to current conditions"
        
        return explanations
    
    def _get_current_season(self) -> str:
        """Get current season."""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'
    
    def create_filter_criteria_from_request(self, trip_request: TripRequest) -> FilterCriteria:
        """Create filter criteria from trip request."""
        
        criteria = FilterCriteria()
        
        # Extract criteria from request
        criteria.budget_range = getattr(trip_request, 'budget_range', 'mid-range')
        criteria.season = self._get_current_season()
        
        # Set defaults based on common preferences
        interests = getattr(trip_request, 'interests', [])
        
        if 'authentic' in interests:
            criteria.prioritize_local_experiences = True
            criteria.avoid_tourist_traps = True
        
        if 'family' in interests:
            criteria.family_friendly = True
            criteria.safety_level_min = 'good'
        
        if 'budget' in interests:
            criteria.include_free_activities = True
            criteria.max_cost_per_day = 80.0
        
        if 'accessibility' in interests:
            criteria.wheelchair_accessible = True
            criteria.public_transport_access = True
        
        # Weather dependency for outdoor activities
        if any(interest in interests for interest in ['nature', 'outdoor', 'adventure']):
            criteria.weather_dependent = True
        
        return criteria
    
    def get_filter_recommendations(self, trip_request: TripRequest) -> Dict[str, Any]:
        """Get filter recommendations based on trip characteristics."""
        
        recommendations = {
            'suggested_filters': [],
            'optional_filters': [],
            'explanations': {}
        }
        
        # Analyze trip request
        duration = getattr(trip_request, 'travel_days', 7)
        budget = getattr(trip_request, 'budget_range', 'mid-range')
        interests = getattr(trip_request, 'interests', [])
        
        # Duration-based recommendations
        if duration <= 3:
            recommendations['suggested_filters'].append('avoid_distant_cities')
            recommendations['explanations']['avoid_distant_cities'] = "Short trip - focus on nearby destinations"
        
        # Budget-based recommendations
        if budget == 'budget':
            recommendations['suggested_filters'].append('include_free_activities')
            recommendations['explanations']['include_free_activities'] = "Budget travel - prioritize free attractions"
        
        # Interest-based recommendations
        if 'family' in interests:
            recommendations['suggested_filters'].append('family_friendly')
            recommendations['explanations']['family_friendly'] = "Family travel - ensure child-friendly destinations"
        
        if 'culture' in interests:
            recommendations['optional_filters'].append('cultural_significance_min')
            recommendations['explanations']['cultural_significance_min'] = "Cultural interest - prioritize historically significant cities"
        
        return recommendations


# Global service instance
_advanced_filtering_service = None

def get_advanced_filtering_service() -> AdvancedFilteringService:
    """Get the global advanced filtering service instance."""
    global _advanced_filtering_service
    if _advanced_filtering_service is None:
        _advanced_filtering_service = AdvancedFilteringService()
    return _advanced_filtering_service
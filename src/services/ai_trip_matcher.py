"""AI Trip Matcher Service - Matches trip parameters to perfect routes."""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio

from models.trip_models import TripRequest, ServiceResult
from services.city_description_service import CityDescriptionService
from services.google_places_city_service import GooglePlacesCityService
from services.travel_planner import TravelPlanner

logger = logging.getLogger(__name__)


@dataclass
class TripConstraints:
    """User constraints for trip matching."""
    duration_days: int
    budget_total: float
    budget_currency: str = "EUR"
    travel_month: Optional[str] = None
    group_type: Optional[str] = None  # solo, couple, family, friends
    must_include: List[str] = None  # specific cities or countries
    avoid: List[str] = None  # things to avoid
    interests: List[str] = None  # culture, nature, food, etc.


@dataclass
class MatchedTrip:
    """A matched trip with scoring and explanation."""
    route: Dict
    match_score: float  # 0-100
    pros: List[str]
    cons: List[str]
    estimated_cost: Dict[str, float]
    best_for: List[str]
    unique_selling_points: List[str]


class AITripMatcher:
    """AI-powered trip matching based on constraints."""
    
    def __init__(self, travel_planner: TravelPlanner, city_service: GooglePlacesCityService, 
                 description_service: CityDescriptionService):
        self.travel_planner = travel_planner
        self.city_service = city_service
        self.description_service = description_service
        
        # Trip templates for different scenarios
        self.trip_templates = {
            'budget_backpacker': {
                'style': 'hidden_gems',
                'pace': 'moderate',
                'accommodation': 'hostels',
                'focus': ['authentic', 'affordable', 'social']
            },
            'romantic_escape': {
                'style': 'romantic',
                'pace': 'relaxed',
                'accommodation': 'boutique',
                'focus': ['intimate', 'scenic', 'memorable']
            },
            'cultural_immersion': {
                'style': 'cultural',
                'pace': 'moderate',
                'accommodation': 'local',
                'focus': ['museums', 'history', 'traditions']
            },
            'adventure_seeker': {
                'style': 'adventure',
                'pace': 'active',
                'accommodation': 'varied',
                'focus': ['outdoor', 'adrenaline', 'nature']
            },
            'foodie_tour': {
                'style': 'foodie',
                'pace': 'relaxed',
                'accommodation': 'central',
                'focus': ['cuisine', 'markets', 'restaurants']
            },
            'family_friendly': {
                'style': 'scenic',
                'pace': 'relaxed',
                'accommodation': 'family',
                'focus': ['safe', 'educational', 'fun']
            }
        }
    
    async def match_trips(self, constraints: TripConstraints) -> List[MatchedTrip]:
        """Generate multiple matched trips based on constraints."""
        matched_trips = []
        
        # Determine suitable trip templates based on constraints
        suitable_templates = self._get_suitable_templates(constraints)
        
        # Generate routes for each suitable template
        tasks = []
        for template_name, template in suitable_templates:
            task = self._generate_matched_trip(constraints, template_name, template)
            tasks.append(task)
        
        # Run all generations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors and sort by match score
        for result in results:
            if isinstance(result, MatchedTrip):
                matched_trips.append(result)
            else:
                logger.error(f"Failed to generate trip: {result}")
        
        # Sort by match score
        matched_trips.sort(key=lambda x: x.match_score, reverse=True)
        
        return matched_trips[:3]  # Return top 3 matches
    
    def _get_suitable_templates(self, constraints: TripConstraints) -> List[Tuple[str, Dict]]:
        """Determine which trip templates suit the constraints."""
        suitable = []
        
        # Budget analysis
        daily_budget = constraints.budget_total / constraints.duration_days
        is_budget = daily_budget < 100
        is_luxury = daily_budget > 300
        
        # Group type analysis
        if constraints.group_type == 'couple':
            suitable.append(('romantic_escape', self.trip_templates['romantic_escape']))
        elif constraints.group_type == 'family':
            suitable.append(('family_friendly', self.trip_templates['family_friendly']))
        
        # Interest-based matching
        if constraints.interests:
            if any(interest in ['food', 'cuisine', 'wine'] for interest in constraints.interests):
                suitable.append(('foodie_tour', self.trip_templates['foodie_tour']))
            if any(interest in ['culture', 'history', 'art'] for interest in constraints.interests):
                suitable.append(('cultural_immersion', self.trip_templates['cultural_immersion']))
            if any(interest in ['nature', 'hiking', 'outdoor'] for interest in constraints.interests):
                suitable.append(('adventure_seeker', self.trip_templates['adventure_seeker']))
        
        # Budget-based additions
        if is_budget:
            suitable.append(('budget_backpacker', self.trip_templates['budget_backpacker']))
        
        # Default options if no specific matches
        if not suitable:
            suitable = [
                ('cultural_immersion', self.trip_templates['cultural_immersion']),
                ('romantic_escape', self.trip_templates['romantic_escape']),
                ('adventure_seeker', self.trip_templates['adventure_seeker'])
            ]
        
        return suitable
    
    async def _generate_matched_trip(self, constraints: TripConstraints, 
                                   template_name: str, template: Dict) -> MatchedTrip:
        """Generate a single matched trip based on template."""
        try:
            # Find suitable start and end cities based on constraints
            start_city, end_city = await self._find_route_endpoints(constraints)
            
            # Create trip request based on template
            trip_request = TripRequest(
                start_location=start_city.name,
                end_location=end_city.name,
                duration=f"{constraints.duration_days} days",
                budget=self._get_budget_level(constraints),
                interests=[template['style']],
                travel_style=template['style'],
                pace='moderate',
                accommodation_type='mid-range',
                group_size=self._get_group_size(constraints.group_type),
                accessibility_needs=False,
                dietary_restrictions=[],
                language_preferences=['English'],
                must_see_attractions=[],
                avoid_list=constraints.avoid or []
            )
            
            # Generate route using existing planner
            result = await self.travel_planner.plan_trip_async(trip_request)
            
            if result.data and result.data.get('routes'):
                route = result.data['routes'][0]  # Take first route
                
                # Calculate match score and analysis
                match_score = self._calculate_match_score(route, constraints, template)
                pros, cons = self._analyze_route_fit(route, constraints, template)
                estimated_cost = self._estimate_costs(route, constraints)
                best_for = self._determine_best_for(route, template)
                usps = self._extract_unique_selling_points(route, template_name)
                
                return MatchedTrip(
                    route=route,
                    match_score=match_score,
                    pros=pros,
                    cons=cons,
                    estimated_cost=estimated_cost,
                    best_for=best_for,
                    unique_selling_points=usps
                )
            
        except Exception as e:
            logger.error(f"Failed to generate matched trip for {template_name}: {e}")
            raise
    
    async def _find_route_endpoints(self, constraints: TripConstraints) -> Tuple:
        """Find suitable start and end cities based on constraints."""
        # Get comprehensive city database
        all_cities = self.city_service._get_comprehensive_city_database()
        
        # Filter by must_include if specified
        if constraints.must_include:
            # Logic to find cities in specified countries/regions
            suitable_cities = [
                city for city in all_cities
                if any(location.lower() in city.country.lower() 
                      for location in constraints.must_include)
            ]
        else:
            suitable_cities = all_cities
        
        # For now, select popular combinations based on duration
        if constraints.duration_days <= 5:
            # Shorter trips - closer cities
            start = next(c for c in suitable_cities if c.name == "Paris")
            end = next(c for c in suitable_cities if c.name == "Amsterdam")
        elif constraints.duration_days <= 10:
            # Medium trips
            start = next(c for c in suitable_cities if c.name == "Barcelona")
            end = next(c for c in suitable_cities if c.name == "Rome")
        else:
            # Longer trips - further apart
            start = next(c for c in suitable_cities if c.name == "London")
            end = next(c for c in suitable_cities if c.name == "Athens")
        
        return start, end
    
    def _get_budget_level(self, constraints: TripConstraints) -> str:
        """Convert numeric budget to level."""
        daily_budget = constraints.budget_total / constraints.duration_days
        if daily_budget < 100:
            return "budget"
        elif daily_budget < 200:
            return "moderate"
        else:
            return "luxury"
    
    def _get_group_size(self, group_type: str) -> str:
        """Convert group type to size."""
        if group_type == "solo":
            return "1"
        elif group_type == "couple":
            return "2"
        elif group_type == "family":
            return "4+"
        else:
            return "2-4"
    
    def _calculate_match_score(self, route: Dict, constraints: TripConstraints, 
                             template: Dict) -> float:
        """Calculate how well the route matches constraints."""
        score = 50.0  # Base score
        
        # Budget fit (20 points)
        estimated_daily = self._estimate_daily_cost(route, template)
        actual_daily = constraints.budget_total / constraints.duration_days
        budget_ratio = min(estimated_daily / actual_daily, actual_daily / estimated_daily)
        score += budget_ratio * 20
        
        # Duration fit (20 points)
        if route.get('total_days', 0) == constraints.duration_days:
            score += 20
        else:
            diff = abs(route.get('total_days', 0) - constraints.duration_days)
            score += max(0, 20 - diff * 5)
        
        # Interest alignment (10 points)
        if constraints.interests:
            style_match = any(
                interest.lower() in template['style'].lower() 
                for interest in constraints.interests
            )
            if style_match:
                score += 10
        
        return min(100, max(0, score))
    
    def _analyze_route_fit(self, route: Dict, constraints: TripConstraints, 
                          template: Dict) -> Tuple[List[str], List[str]]:
        """Analyze pros and cons of the route for constraints."""
        pros = []
        cons = []
        
        # Analyze cities
        num_cities = len(route.get('intermediate_cities', []))
        if num_cities > 0:
            pros.append(f"Visits {num_cities} carefully selected destinations")
        
        # Budget analysis
        estimated_daily = self._estimate_daily_cost(route, template)
        actual_daily = constraints.budget_total / constraints.duration_days
        if estimated_daily < actual_daily * 0.8:
            pros.append("Leaves room in budget for spontaneous experiences")
        elif estimated_daily > actual_daily * 1.2:
            cons.append("May exceed budget without careful planning")
        
        # Style match
        if template['style'] == 'hidden_gems':
            pros.append("Features off-the-beaten-path destinations")
        elif template['style'] == 'romantic':
            pros.append("Includes romantic cities and scenic routes")
        
        # Duration
        if route.get('total_days', 0) == constraints.duration_days:
            pros.append("Perfectly fits your available time")
        
        return pros, cons
    
    def _estimate_costs(self, route: Dict, constraints: TripConstraints) -> Dict[str, float]:
        """Estimate costs for the route."""
        days = constraints.duration_days
        
        # Basic estimates (can be refined with real data)
        return {
            'accommodation': days * 80,  # €80/night average
            'food': days * 50,  # €50/day for meals
            'transport': route.get('total_distance_km', 1000) * 0.15,  # €0.15/km
            'activities': days * 30,  # €30/day for activities
            'total': 0  # Will be summed
        }
    
    def _estimate_daily_cost(self, route: Dict, template: Dict) -> float:
        """Estimate daily cost based on route and template."""
        base_cost = 100  # Base €100/day
        
        # Adjust by template
        if template['accommodation'] == 'hostels':
            base_cost *= 0.6
        elif template['accommodation'] == 'boutique':
            base_cost *= 1.5
        
        if template['style'] == 'foodie':
            base_cost *= 1.3
        elif template['style'] == 'budget':
            base_cost *= 0.7
        
        return base_cost
    
    def _determine_best_for(self, route: Dict, template: Dict) -> List[str]:
        """Determine who this trip is best for."""
        best_for = []
        
        if template['style'] == 'romantic':
            best_for.extend(['Couples', 'Honeymoons', 'Anniversaries'])
        elif template['style'] == 'adventure':
            best_for.extend(['Active travelers', 'Nature lovers', 'Photographers'])
        elif template['style'] == 'cultural':
            best_for.extend(['History buffs', 'Art lovers', 'Culture seekers'])
        elif template['style'] == 'hidden_gems':
            best_for.extend(['Experienced travelers', 'Authentic seekers', 'Slow travelers'])
        
        return best_for
    
    def _extract_unique_selling_points(self, route: Dict, template_name: str) -> List[str]:
        """Extract unique selling points of the route."""
        usps = []
        
        # Template-specific USPs
        template_usps = {
            'romantic_escape': [
                "Hand-picked romantic destinations",
                "Perfect balance of culture and relaxation",
                "Scenic routes through charming landscapes"
            ],
            'cultural_immersion': [
                "UNESCO World Heritage sites included",
                "Local cultural experiences prioritized",
                "Historical route through Europe's heritage"
            ],
            'adventure_seeker': [
                "Access to outdoor activities",
                "Mountain and nature destinations",
                "Flexible itinerary for spontaneous adventures"
            ],
            'foodie_tour': [
                "Culinary hotspots on the route",
                "Regional specialties in each city",
                "Market and restaurant recommendations"
            ],
            'budget_backpacker': [
                "Affordable hidden gems",
                "Hostel-friendly destinations",
                "Free activities and attractions highlighted"
            ]
        }
        
        return template_usps.get(template_name, [
            "Carefully curated route",
            "Balance of popular and hidden destinations",
            "Flexible itinerary"
        ])
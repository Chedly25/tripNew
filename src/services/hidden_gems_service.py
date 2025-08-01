"""
Hidden gems discovery and intermediate city suggestion service.
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import structlog
from geopy.distance import geodesic
from ..core.models import City, Coordinates, ServiceResult, TripRequest
from ..core.exceptions import TravelPlannerException
from .city_service import CityService

logger = structlog.get_logger(__name__)


class HiddenGemsService:
    """Service for discovering hidden gems and suggesting intermediate cities."""
    
    def __init__(self, city_service: CityService):
        self.city_service = city_service
    
    async def suggest_intermediate_cities(self, start_city: City, end_city: City, 
                                        trip_request: TripRequest, trip_type: str = "home") -> ServiceResult:
        """
        Suggest intermediate cities based on travel days and nights distribution.
        
        For HOME trips:
        - 3-day trip with 2 nights at destination: 1st night should be at intermediate city
        - Must return home, so intermediate stops are en route
        
        For AWAY trips:
        - Standard distribution based on total days and destination nights
        - No requirement to return to starting point
        """
        try:
            logger.info("Suggesting intermediate cities", 
                       start=start_city.name, end=end_city.name,
                       total_days=trip_request.travel_days, trip_type=trip_type)
            
            # Calculate available nights for intermediate stops
            nights_at_destination = getattr(trip_request, 'nights_at_destination', 2)
            total_travel_days = trip_request.travel_days
            
            # Calculate intermediate nights based on trip type
            if trip_type == "home":
                # For home trips, we need to account for return journey
                # Available nights = total_days - nights_at_destination - 1 (return day)
                intermediate_nights = max(0, total_travel_days - nights_at_destination - 1)
                
                # For 3-day trips from home with 2 nights at destination, force 1 intermediate night
                if total_travel_days == 3 and nights_at_destination == 2:
                    intermediate_nights = 1
                    logger.info("Home trip: forcing 1 intermediate night for 3-day/2-destination-night trip")
            else:
                # For away trips, standard calculation
                intermediate_nights = max(0, total_travel_days - nights_at_destination - 1)  # -1 for travel day
            
            if intermediate_nights <= 0:
                return ServiceResult.success_result({
                    'intermediate_cities': [],
                    'night_distribution': {
                        'destination_nights': nights_at_destination,
                        'intermediate_nights': 0,
                        'message': 'Direct travel recommended for this duration'
                    }
                })
            
            # Find candidate cities along the route
            candidate_cities = await self._find_route_cities(
                start_city, end_city, intermediate_nights
            )
            
            # Score and rank cities
            scored_cities = await self._score_intermediate_cities(
                candidate_cities, start_city, end_city, trip_request
            )
            
            # Select best intermediate cities
            selected_cities = self._select_optimal_cities(
                scored_cities, intermediate_nights, trip_request
            )
            
            # Create detailed recommendations
            recommendations = await self._create_city_recommendations(
                selected_cities, trip_request
            )
            
            return ServiceResult.success_result({
                'intermediate_cities': recommendations,
                'night_distribution': {
                    'destination_nights': nights_at_destination,
                    'intermediate_nights': intermediate_nights,
                    'cities_count': len(recommendations),
                    'total_nights': nights_at_destination + intermediate_nights
                },
                'route_optimization': {
                    'total_distance_km': self._calculate_total_distance(
                        start_city, selected_cities, end_city
                    ),
                    'estimated_driving_hours': self._calculate_total_driving_time(
                        start_city, selected_cities, end_city
                    )
                }
            })
            
        except Exception as e:
            logger.error("Failed to suggest intermediate cities", error=str(e))
            return ServiceResult.error_result(f"Intermediate city suggestion failed: {e}")
    
    async def discover_hidden_gems(self, region_cities: List[City], 
                                 trip_request: TripRequest) -> ServiceResult:
        """Discover hidden gems in the travel region."""
        try:
            hidden_gems = []
            
            # Filter cities by hidden gem characteristics
            for city in region_cities:
                gem_score = self._calculate_gem_score(city, trip_request)
                if gem_score >= 7.0:  # High threshold for hidden gems
                    gem_info = await self._create_hidden_gem_info(city, trip_request)
                    hidden_gems.append(gem_info)
            
            # Sort by gem score
            hidden_gems.sort(key=lambda x: x['gem_score'], reverse=True)
            
            return ServiceResult.success_result({
                'hidden_gems': hidden_gems[:5],  # Top 5 hidden gems
                'discovery_criteria': {
                    'population_threshold': 'Under 100,000',
                    'unique_features': 'Cultural, scenic, or culinary significance',
                    'accessibility': 'Within reasonable driving distance',
                    'season_relevance': f'Optimized for {trip_request.season.value}'
                }
            })
            
        except Exception as e:
            logger.error("Hidden gems discovery failed", error=str(e))
            return ServiceResult.error_result(f"Hidden gems discovery failed: {e}")
    
    async def _find_route_cities(self, start_city: City, end_city: City, 
                               max_stops: int) -> List[City]:
        """Find cities along the route between start and end."""
        # Get all cities within reasonable distance from the route
        all_cities = list(self.city_service._city_cache.values())
        route_cities = []
        
        for city in all_cities:
            if city.name in [start_city.name, end_city.name]:
                continue
            
            # Calculate if city is reasonably along the route
            deviation_km = self._calculate_route_deviation(
                city.coordinates, start_city.coordinates, end_city.coordinates
            )
            
            # Include cities within 100km of the direct route
            if deviation_km <= 100:
                route_cities.append(city)
        
        return route_cities[:max_stops * 3]  # Get more candidates than needed
    
    def _calculate_route_deviation(self, point: Coordinates, 
                                 start: Coordinates, end: Coordinates) -> float:
        """Calculate how far a point deviates from the direct route."""
        # Distance from start to point
        start_to_point = geodesic(
            (start.latitude, start.longitude),
            (point.latitude, point.longitude)
        ).kilometers
        
        # Distance from point to end
        point_to_end = geodesic(
            (point.latitude, point.longitude),
            (end.latitude, end.longitude)
        ).kilometers
        
        # Direct distance from start to end
        direct_distance = geodesic(
            (start.latitude, start.longitude),
            (end.latitude, end.longitude)
        ).kilometers
        
        # Deviation is the extra distance by going through this point
        return max(0, (start_to_point + point_to_end) - direct_distance)
    
    async def _score_intermediate_cities(self, cities: List[City], 
                                       start_city: City, end_city: City,
                                       trip_request: TripRequest) -> List[Dict]:
        """Score cities based on various criteria for intermediate stops."""
        scored_cities = []
        
        for city in cities:
            score = 0.0
            reasons = []
            
            # Population score (prefer smaller, more authentic cities)
            if city.population:
                if city.population < 50000:
                    score += 3.0
                    reasons.append("Intimate small town atmosphere")
                elif city.population < 200000:
                    score += 2.0
                    reasons.append("Charming mid-size city")
                else:
                    score += 1.0
            
            # Type-based scoring
            if city.types:
                type_scores = {
                    'cultural': 2.5,
                    'historic': 2.0,
                    'scenic': 2.5,
                    'culinary': 2.0,
                    'artistic': 1.5,
                    'romantic': 1.5,
                    'coastal': 2.0 if trip_request.season.value in ['summer', 'spring'] else 1.0
                }
                
                for city_type in city.types:
                    if city_type in type_scores:
                        score += type_scores[city_type]
                        reasons.append(f"Excellent {city_type} destination")
            
            # Distance from route (prefer cities closer to optimal route)
            deviation = self._calculate_route_deviation(
                city.coordinates, start_city.coordinates, end_city.coordinates
            )
            if deviation < 30:
                score += 2.0
                reasons.append("Perfectly positioned on your route")
            elif deviation < 60:
                score += 1.0
                reasons.append("Minor detour with great rewards")
            
            # Season relevance
            season_bonus = self._get_season_score(city, trip_request.season.value)
            score += season_bonus
            if season_bonus > 0:
                reasons.append(f"Exceptional during {trip_request.season.value}")
            
            scored_cities.append({
                'city': city,
                'score': score,
                'reasons': reasons,
                'route_deviation_km': deviation
            })
        
        return sorted(scored_cities, key=lambda x: x['score'], reverse=True)
    
    def _select_optimal_cities(self, scored_cities: List[Dict], 
                             max_cities: int, trip_request: TripRequest) -> List[City]:
        """Select optimal intermediate cities avoiding clustering."""
        if not scored_cities or max_cities <= 0:
            return []
        
        selected = []
        min_distance_km = 80  # Minimum distance between selected cities
        
        for candidate in scored_cities:
            if len(selected) >= max_cities:
                break
            
            city = candidate['city']
            
            # Check distance from already selected cities
            too_close = False
            for selected_city in selected:
                distance = geodesic(
                    (city.coordinates.latitude, city.coordinates.longitude),
                    (selected_city.coordinates.latitude, selected_city.coordinates.longitude)
                ).kilometers
                
                if distance < min_distance_km:
                    too_close = True
                    break
            
            if not too_close:
                selected.append(city)
        
        return selected
    
    async def _create_city_recommendations(self, cities: List[City], 
                                         trip_request: TripRequest) -> List[Dict]:
        """Create detailed recommendations for intermediate cities."""
        recommendations = []
        
        for city in cities:
            # Create comprehensive city information
            recommendation = {
                'city': {
                    'name': city.name,
                    'country': city.country,
                    'region': city.region,
                    'coordinates': [city.coordinates.latitude, city.coordinates.longitude],
                    'population': city.population,
                    'types': city.types
                },
                'recommendation_score': self._calculate_gem_score(city, trip_request),
                'why_visit': self._get_visit_reasons(city, trip_request),
                'best_for': self._get_best_activities(city, trip_request),
                'stay_duration': self._suggest_stay_duration(city, trip_request),
                'season_highlights': self._get_seasonal_highlights(city, trip_request.season.value),
                'local_specialties': self._get_local_specialties(city),
                'hidden_gems_nearby': await self._find_nearby_attractions(city),
                'travel_tips': self._get_travel_tips(city, trip_request)
            }
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _calculate_gem_score(self, city: City, trip_request: TripRequest) -> float:
        """Calculate how much of a 'hidden gem' this city is."""
        score = 5.0  # Base score
        
        # Population factor (smaller = more hidden)
        if city.population:
            if city.population < 30000:
                score += 3.0
            elif city.population < 100000:
                score += 2.0
            elif city.population < 300000:
                score += 1.0
        
        # Type bonuses
        type_bonuses = {
            'scenic': 2.0,
            'cultural': 1.5,
            'historic': 1.5,
            'culinary': 1.0,
            'artistic': 1.0,
            'romantic': 0.5
        }
        
        if city.types:
            for city_type in city.types:
                score += type_bonuses.get(city_type, 0)
        
        # Season relevance
        score += self._get_season_score(city, trip_request.season.value)
        
        return min(10.0, score)  # Cap at 10
    
    def _get_season_score(self, city: City, season: str) -> float:
        """Get seasonal relevance score."""
        if not city.types:
            return 0.0
        
        season_bonuses = {
            'spring': {'scenic': 1.0, 'cultural': 0.5},
            'summer': {'coastal': 2.0, 'scenic': 1.5, 'romantic': 1.0},
            'autumn': {'scenic': 2.0, 'culinary': 1.0, 'cultural': 0.5},
            'winter': {'cultural': 1.0, 'historic': 0.5}
        }
        
        bonus = 0.0
        for city_type in city.types:
            bonus += season_bonuses.get(season, {}).get(city_type, 0)
        
        return bonus
    
    def _get_visit_reasons(self, city: City, trip_request: TripRequest) -> List[str]:
        """Get reasons why someone should visit this city."""
        reasons = []
        
        # Type-based reasons
        type_reasons = {
            'cultural': f"Rich cultural heritage and museums perfect for {trip_request.season.value}",
            'historic': "Fascinating historical sites and architecture",
            'scenic': f"Breathtaking landscapes ideal for {trip_request.season.value} photography",
            'culinary': "Outstanding local cuisine and traditional specialties",
            'artistic': "Vibrant arts scene and local crafts",
            'romantic': "Intimate atmosphere perfect for couples",
            'coastal': "Beautiful waterfront and maritime culture"
        }
        
        if city.types:
            for city_type in city.types:
                if city_type in type_reasons:
                    reasons.append(type_reasons[city_type])
        
        # Size-based reasons
        if city.population and city.population < 50000:
            reasons.append("Authentic small-town experience away from tourist crowds")
        
        # Location-based reasons
        reasons.append(f"Perfectly positioned in the beautiful {city.region} region")
        
        return reasons[:3]  # Top 3 reasons
    
    def _get_best_activities(self, city: City, trip_request: TripRequest) -> List[str]:
        """Get best activities for this city."""
        activities = []
        
        activity_map = {
            'cultural': ['Visit local museums', 'Explore historic districts', 'Attend cultural events'],
            'historic': ['Tour ancient architecture', 'Walk medieval streets', 'Visit historical landmarks'],
            'scenic': ['Photography walks', 'Scenic viewpoints', 'Nature exploration'],
            'culinary': ['Food tours', 'Local markets', 'Traditional restaurants'],
            'artistic': ['Art galleries', 'Local workshops', 'Street art tours'],
            'romantic': ['Sunset walks', 'Cozy cafés', 'Romantic viewpoints'],
            'coastal': ['Waterfront promenades', 'Harbor tours', 'Seafood dining']
        }
        
        if city.types:
            for city_type in city.types:
                if city_type in activity_map:
                    activities.extend(activity_map[city_type])
        
        # Add season-specific activities
        season_activities = {
            'spring': ['Garden visits', 'Flower festivals'],
            'summer': ['Outdoor dining', 'Evening strolls'],
            'autumn': ['Harvest festivals', 'Fall foliage walks'],
            'winter': ['Cozy indoor attractions', 'Winter markets']
        }
        
        activities.extend(season_activities.get(trip_request.season.value, []))
        
        return list(set(activities))[:4]  # Top 4 unique activities
    
    def _suggest_stay_duration(self, city: City, trip_request: TripRequest) -> Dict[str, Any]:
        """Suggest how long to stay in this city."""
        base_hours = 6  # Base exploration time
        
        # Adjust based on city characteristics
        if city.types:
            if 'cultural' in city.types:
                base_hours += 4
            if 'historic' in city.types:
                base_hours += 3
            if 'scenic' in city.types:
                base_hours += 2
            if 'culinary' in city.types:
                base_hours += 2
        
        # Convert to nights
        if base_hours <= 8:
            nights = 1
            suggestion = "Perfect for a one-night stop"
        elif base_hours <= 16:
            nights = 1
            suggestion = "One night with a full day of exploration"
        else:
            nights = 2
            suggestion = "Worth spending two nights to fully appreciate"
        
        return {
            'recommended_nights': nights,
            'estimated_exploration_hours': base_hours,
            'suggestion': suggestion
        }
    
    def _get_seasonal_highlights(self, city: City, season: str) -> List[str]:
        """Get seasonal highlights for the city."""
        highlights = {
            'spring': ['Blooming gardens', 'Mild weather for walking', 'Fewer crowds'],
            'summer': ['Long daylight hours', 'Outdoor events', 'Perfect weather'],
            'autumn': ['Beautiful fall colors', 'Harvest season', 'Comfortable temperatures'],
            'winter': ['Cozy atmosphere', 'Winter festivities', 'Indoor cultural activities']
        }
        
        base_highlights = highlights.get(season, [])
        
        # Add city-specific seasonal features
        if city.types:
            if 'coastal' in city.types and season == 'summer':
                base_highlights.append('Perfect beach weather')
            if 'scenic' in city.types and season in ['spring', 'autumn']:
                base_highlights.append('Spectacular landscape colors')
            if 'cultural' in city.types and season == 'winter':
                base_highlights.append('Rich indoor cultural experiences')
        
        return base_highlights
    
    def _get_local_specialties(self, city: City) -> List[str]:
        """Get local specialties based on region and country."""
        specialties = []
        
        # Country-based specialties
        country_specialties = {
            'France': ['Local wines', 'Artisanal cheeses', 'Traditional pastries'],
            'Italy': ['Regional pasta dishes', 'Local wines', 'Gelato'],
            'Switzerland': ['Swiss chocolates', 'Mountain cheeses', 'Local wines'],
            'Monaco': ['Mediterranean cuisine', 'Fine dining', 'Luxury shopping']
        }
        
        specialties.extend(country_specialties.get(city.country, ['Local cuisine', 'Regional specialties']))
        
        # Add type-specific specialties
        if city.types:
            if 'culinary' in city.types:
                specialties.extend(['Michelin-rated restaurants', 'Local food markets'])
            if 'coastal' in city.types:
                specialties.extend(['Fresh seafood', 'Maritime specialties'])
            if 'cultural' in city.types:
                specialties.extend(['Local crafts', 'Traditional arts'])
        
        return list(set(specialties))[:4]
    
    async def _find_nearby_attractions(self, city: City) -> List[str]:
        """Find hidden attractions near the city."""
        # This could integrate with external APIs in a full implementation
        # For now, return region-based attractions
        
        region_attractions = {
            'Provence-Alpes-Côte d\'Azur': [
                'Lavender fields', 'Medieval hilltop villages', 'Roman ruins'
            ],
            'Veneto': [
                'Venetian villas', 'Wine estates', 'Historic canals'
            ],
            'Lombardy': [
                'Lake Como shores', 'Historic villas', 'Mountain views'
            ],
            'Piedmont': [
                'Truffle regions', 'Historic castles', 'Wine cellars'
            ]
        }
        
        return region_attractions.get(city.region, [
            'Local nature trails', 'Historic sites', 'Scenic viewpoints'
        ])
    
    def _get_travel_tips(self, city: City, trip_request: TripRequest) -> List[str]:
        """Get practical travel tips for the city."""
        tips = []
        
        # Population-based tips
        if city.population and city.population < 50000:
            tips.append("Book accommodations in advance - limited options in small towns")
            tips.append("Learn a few local phrases - locals appreciate the effort")
        
        # Season-based tips
        season_tips = {
            'spring': ['Pack layers for variable weather', 'Book early for Easter holidays'],
            'summer': ['Make dinner reservations early', 'Carry water and sun protection'],
            'autumn': ['Weather can change quickly - pack accordingly', 'Perfect photography conditions'],
            'winter': ['Limited daylight hours - plan accordingly', 'Many outdoor attractions may be closed']
        }
        
        tips.extend(season_tips.get(trip_request.season.value, []))
        
        # Type-based tips
        if city.types:
            if 'cultural' in city.types:
                tips.append("Check museum opening hours and local holidays")
            if 'culinary' in city.types:
                tips.append("Try to eat where locals eat for authentic experiences")
            if 'scenic' in city.types:
                tips.append("Bring a camera - incredible photo opportunities")
        
        return tips[:3]  # Top 3 tips
    
    def _calculate_total_distance(self, start_city: City, 
                                intermediate_cities: List[City], 
                                end_city: City) -> float:
        """Calculate total distance including intermediate stops."""
        total_km = 0.0
        previous_city = start_city
        
        for city in intermediate_cities + [end_city]:
            distance = geodesic(
                (previous_city.coordinates.latitude, previous_city.coordinates.longitude),
                (city.coordinates.latitude, city.coordinates.longitude)
            ).kilometers
            total_km += distance
            previous_city = city
        
        return round(total_km, 1)
    
    def _calculate_total_driving_time(self, start_city: City, 
                                    intermediate_cities: List[City], 
                                    end_city: City) -> float:
        """Calculate total driving time including intermediate stops."""
        total_distance = self._calculate_total_distance(start_city, intermediate_cities, end_city)
        # Assume average speed of 70 km/h including stops
        return round(total_distance / 70.0, 1)
    
    async def _create_hidden_gem_info(self, city: City, trip_request: TripRequest) -> Dict:
        """Create detailed hidden gem information."""
        return {
            'city': {
                'name': city.name,
                'country': city.country,
                'region': city.region,
                'population': city.population,
                'coordinates': [city.coordinates.latitude, city.coordinates.longitude]
            },
            'gem_score': self._calculate_gem_score(city, trip_request),
            'why_hidden': self._explain_hidden_nature(city),
            'unique_features': self._get_unique_features(city),
            'best_time_to_visit': self._get_best_visit_time(city, trip_request.season.value),
            'insider_tips': self._get_insider_tips(city),
            'estimated_visit_duration': self._suggest_stay_duration(city, trip_request)
        }
    
    def _explain_hidden_nature(self, city: City) -> str:
        """Explain why this city is considered a hidden gem."""
        if city.population and city.population < 30000:
            return "A charming small town rarely found in guidebooks, offering authentic local experiences"
        elif city.population and city.population < 100000:
            return "Often overlooked by tourists despite its remarkable character and attractions"
        else:
            return "Has hidden neighborhoods and experiences that most visitors miss"
    
    def _get_unique_features(self, city: City) -> List[str]:
        """Get unique features that make this city special."""
        features = []
        
        if city.types:
            feature_map = {
                'scenic': 'Breathtaking natural beauty and landscapes',
                'cultural': 'Rich cultural heritage and local traditions',
                'historic': 'Well-preserved historical architecture and sites',
                'culinary': 'Outstanding local cuisine and food traditions',
                'artistic': 'Vibrant local arts and crafts scene',
                'romantic': 'Intimate and romantic atmosphere',
                'coastal': 'Beautiful waterfront and maritime culture'
            }
            
            for city_type in city.types:
                if city_type in feature_map:
                    features.append(feature_map[city_type])
        
        # Add region-specific features
        if city.region:
            features.append(f"Authentic {city.region} regional character")
        
        return features[:3]
    
    def _get_best_visit_time(self, city: City, current_season: str) -> str:
        """Get the best time to visit based on city characteristics."""
        if city.types:
            if 'coastal' in city.types:
                return "Late spring through early autumn for the best weather"
            elif 'scenic' in city.types:
                return "Spring and autumn for the most spectacular scenery"
            elif 'cultural' in city.types:
                return "Year-round, though spring and autumn offer the best balance"
        
        return f"Your chosen {current_season} season is perfect for visiting"
    
    def _get_insider_tips(self, city: City) -> List[str]:
        """Get insider tips for the city."""
        tips = []
        
        if city.population and city.population < 50000:
            tips.extend([
                "Visit the local market on market day for the best atmosphere",
                "Ask locals for restaurant recommendations - they know the best spots"
            ])
        
        tips.extend([
            "Explore beyond the main square to find hidden corners",
            f"Try the regional specialties - {city.region} has unique flavors"
        ])
        
        if city.types and 'cultural' in city.types:
            tips.append("Visit during local festivals for the most authentic experience")
        
        return tips[:3]
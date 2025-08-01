"""
Comprehensive travel itinerary generator with day-by-day planning.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from ..core.models import City, Coordinates, ServiceResult, TripRequest
from ..core.exceptions import TravelPlannerException
from .hidden_gems_service import HiddenGemsService
from .city_service import CityService

logger = structlog.get_logger(__name__)


class ItineraryGenerator:
    """Generate detailed day-by-day travel itineraries."""
    
    def __init__(self, city_service: CityService, hidden_gems_service: HiddenGemsService):
        self.city_service = city_service
        self.hidden_gems_service = hidden_gems_service
    
    async def generate_complete_itinerary(self, start_city: City, end_city: City,
                                        trip_request: TripRequest, trip_type: str = "home") -> ServiceResult:
        """Generate a complete day-by-day itinerary."""
        try:
            logger.info("Generating complete itinerary",
                       start=start_city.name, end=end_city.name,
                       days=trip_request.travel_days)
            
            # Get intermediate cities and night distribution
            intermediate_result = await self.hidden_gems_service.suggest_intermediate_cities(
                start_city, end_city, trip_request, trip_type
            )
            
            if not intermediate_result.success:
                return intermediate_result
            
            intermediate_data = intermediate_result.data
            intermediate_cities = intermediate_data.get('intermediate_cities', [])
            
            # Generate day-by-day itinerary
            daily_itinerary = await self._create_daily_itinerary(
                start_city, end_city, intermediate_cities, trip_request
            )
            
            # Generate travel timeline
            timeline = self._create_travel_timeline(daily_itinerary, trip_request)
            
            # Create packing suggestions
            packing_list = self._generate_packing_suggestions(
                daily_itinerary, trip_request
            )
            
            # Generate budget breakdown
            budget_breakdown = await self._generate_budget_breakdown(
                daily_itinerary, trip_request
            )
            
            # Create travel tips
            travel_tips = await self._generate_comprehensive_travel_tips(
                daily_itinerary, trip_request
            )
            
            return ServiceResult.success_result({
                'daily_itinerary': daily_itinerary,
                'intermediate_cities': intermediate_cities,
                'night_distribution': intermediate_data.get('night_distribution', {}),
                'timeline': timeline,
                'packing_suggestions': packing_list,
                'budget_breakdown': budget_breakdown,
                'travel_tips': travel_tips,
                'trip_summary': {
                    'total_days': trip_request.travel_days,
                    'cities_visited': len(intermediate_cities) + 2,  # +2 for start and end
                    'total_nights': trip_request.travel_days - 1,
                    'trip_type': self._classify_trip_type(trip_request, intermediate_cities)
                }
            })
            
        except Exception as e:
            logger.error("Itinerary generation failed", error=str(e))
            return ServiceResult.error_result(f"Itinerary generation failed: {e}")
    
    async def _create_daily_itinerary(self, start_city: City, end_city: City,
                                    intermediate_cities: List[Dict],
                                    trip_request: TripRequest) -> List[Dict]:
        """Create detailed day-by-day itinerary."""
        daily_plan = []
        current_day = 1
        
        # Extract night distribution
        nights_at_destination = getattr(trip_request, 'nights_at_destination', 2)
        total_days = trip_request.travel_days
        
        # Day 1: Departure and travel to first stop
        if intermediate_cities:
            first_stop = intermediate_cities[0]
            # Convert city dict back to City object for travel calculations
            first_city_data = first_stop['city']
            first_city_obj = City(
                name=first_city_data['name'],
                coordinates=Coordinates(
                    latitude=first_city_data['coordinates'][0],
                    longitude=first_city_data['coordinates'][1]
                ),
                country=first_city_data['country'],
                region=first_city_data.get('region'),
                types=first_city_data.get('types', [])
            )
            day_1 = await self._create_travel_day(
                current_day, start_city, first_city_obj, 
                trip_request, "departure_travel"
            )
        else:
            # Direct travel to destination
            day_1 = await self._create_travel_day(
                current_day, start_city, end_city,
                trip_request, "direct_travel"
            )
        
        daily_plan.append(day_1)
        current_day += 1
        
        # Intermediate days
        if intermediate_cities:
            for i, intermediate_city in enumerate(intermediate_cities):
                city_info = intermediate_city['city']
                stay_duration = intermediate_city.get('stay_duration', {}).get('recommended_nights', 1)
                
                # Days spent in intermediate city
                for night in range(stay_duration):
                    is_arrival_day = night == 0
                    day_plan = await self._create_city_exploration_day(
                        current_day, city_info, intermediate_city,
                        trip_request, is_arrival_day
                    )
                    daily_plan.append(day_plan)
                    current_day += 1
                
                # Travel day to next destination (if not the last intermediate city)
                if i < len(intermediate_cities) - 1:
                    next_city_data = intermediate_cities[i + 1]['city']
                    next_city_obj = City(
                        name=next_city_data['name'],
                        coordinates=Coordinates(
                            latitude=next_city_data['coordinates'][0],
                            longitude=next_city_data['coordinates'][1]
                        ),
                        country=next_city_data['country'],
                        region=next_city_data.get('region'),
                        types=next_city_data.get('types', [])
                    )
                    current_city_obj = City(
                        name=city_info['name'],
                        coordinates=Coordinates(
                            latitude=city_info['coordinates'][0],
                            longitude=city_info['coordinates'][1]
                        ),
                        country=city_info['country'],
                        region=city_info.get('region'),
                        types=city_info.get('types', [])
                    )
                    travel_day = await self._create_travel_day(
                        current_day, current_city_obj, next_city_obj,
                        trip_request, "intermediate_travel"
                    )
                    daily_plan.append(travel_day)
                    current_day += 1
                else:
                    # Travel to final destination
                    current_city_obj = City(
                        name=city_info['name'],
                        coordinates=Coordinates(
                            latitude=city_info['coordinates'][0],
                            longitude=city_info['coordinates'][1]
                        ),
                        country=city_info['country'],
                        region=city_info.get('region'),
                        types=city_info.get('types', [])
                    )
                    travel_day = await self._create_travel_day(
                        current_day, current_city_obj, end_city,
                        trip_request, "final_approach"
                    )
                    daily_plan.append(travel_day)
                    current_day += 1
        
        # Days at final destination
        remaining_days = total_days - current_day + 1
        for day in range(remaining_days):
            is_arrival_day = day == 0 and intermediate_cities  # Only if coming from intermediate city
            is_departure_day = day == remaining_days - 1
            
            destination_day = await self._create_destination_day(
                current_day, end_city, trip_request,
                is_arrival_day, is_departure_day, day + 1
            )
            daily_plan.append(destination_day)
            current_day += 1
        
        return daily_plan
    
    async def _create_travel_day(self, day_number: int, from_city: City, to_city: City,
                               trip_request: TripRequest, travel_type: str) -> Dict:
        """Create a travel day itinerary."""
        from geopy.distance import geodesic
        
        distance = geodesic(
            (from_city.coordinates.latitude, from_city.coordinates.longitude),
            (to_city.coordinates.latitude, to_city.coordinates.longitude)
        ).kilometers
        
        driving_time = distance / 70.0  # Average speed with stops
        
        activities = []
        
        if travel_type == "departure_travel":
            activities = [
                {
                    'time': '09:00',
                    'activity': f'Departure from {from_city.name}',
                    'description': 'Final preparations and check-out',
                    'duration': '1 hour',
                    'type': 'logistics'
                },
                {
                    'time': '10:00',
                    'activity': 'Scenic drive begins',
                    'description': f'Beautiful {trip_request.season.value} landscapes en route',
                    'duration': f'{driving_time:.1f} hours',
                    'type': 'travel'
                },
                {
                    'time': f'{int(10 + driving_time):02d}:00',
                    'activity': f'Arrival in {to_city.name}',
                    'description': 'Check-in and first exploration',
                    'duration': '2 hours',
                    'type': 'arrival'
                }
            ]
        
        elif travel_type == "direct_travel":
            activities = [
                {
                    'time': '09:00',
                    'activity': f'Departure from {from_city.name}',
                    'description': 'Begin your European adventure',
                    'duration': '1 hour',
                    'type': 'logistics'
                },
                {
                    'time': '10:00',
                    'activity': f'Direct route to {to_city.name}',
                    'description': f'Enjoy the {trip_request.season.value} scenery',
                    'duration': f'{driving_time:.1f} hours',
                    'type': 'travel'
                },
                {
                    'time': f'{int(10 + driving_time):02d}:00',
                    'activity': f'Arrival and exploration of {to_city.name}',
                    'description': 'Start discovering your destination',
                    'duration': 'Rest of day',
                    'type': 'exploration'
                }
            ]
        
        else:  # intermediate_travel or final_approach
            activities = [
                {
                    'time': '10:00',
                    'activity': f'Morning departure from {from_city.name}',
                    'description': 'Continue your journey',
                    'duration': '1 hour',
                    'type': 'logistics'
                },
                {
                    'time': '11:00',
                    'activity': f'Travel to {to_city.name}',
                    'description': 'Scenic route with possible stops',
                    'duration': f'{driving_time:.1f} hours',
                    'type': 'travel'
                },
                {
                    'time': f'{int(11 + driving_time):02d}:00',
                    'activity': f'Arrival in {to_city.name}',
                    'description': 'Settlement and initial exploration',
                    'duration': 'Afternoon',
                    'type': 'arrival'
                }
            ]
        
        return {
            'day': day_number,
            'date': self._calculate_date(day_number),
            'type': 'travel_day',
            'title': f'Travel from {from_city.name} to {to_city.name}',
            'location': {
                'from': from_city.name,
                'to': to_city.name,
                'distance_km': round(distance, 1),
                'estimated_driving_time': f'{driving_time:.1f} hours'
            },
            'activities': activities,
            'accommodation': {
                'city': to_city.name,
                'type': 'Check-in upon arrival',
                'booking_tip': 'Book accommodations in advance, especially during peak season'
            },
            'meals': self._suggest_travel_day_meals(from_city, to_city, trip_request),
            'tips': self._get_travel_day_tips(from_city, to_city, trip_request),
            'weather_consideration': f'Check weather for {trip_request.season.value} driving conditions'
        }
    
    async def _create_city_exploration_day(self, day_number: int, city: Dict,
                                         city_details: Dict, trip_request: TripRequest,
                                         is_arrival_day: bool) -> Dict:
        """Create a city exploration day."""
        city_name = city['name']
        activities = []
        
        if is_arrival_day:
            activities.append({
                'time': '14:00',
                'activity': f'Arrival and settling in {city_name}',
                'description': 'Check-in and get oriented',
                'duration': '1 hour',
                'type': 'logistics'
            })
            start_time = 15
        else:
            start_time = 9
        
        # Add city-specific activities based on types
        city_activities = self._generate_city_activities(city, city_details, trip_request, start_time)
        activities.extend(city_activities)
        
        return {
            'day': day_number,
            'date': self._calculate_date(day_number),
            'type': 'exploration_day',
            'title': f'Discover {city_name}',
            'location': {
                'city': city_name,
                'country': city['country'],
                'region': city['region']
            },
            'activities': activities,
            'accommodation': {
                'city': city_name,
                'nights': 1,
                'type': 'Intimate local accommodation recommended'
            },
            'meals': self._suggest_city_meals(city, trip_request),
            'hidden_gems': city_details.get('hidden_gems_nearby', []),
            'local_specialties': city_details.get('local_specialties', []),
            'tips': city_details.get('travel_tips', []),
            'why_special': city_details.get('why_visit', [])
        }
    
    async def _create_destination_day(self, day_number: int, destination_city: City,
                                    trip_request: TripRequest, is_arrival_day: bool,
                                    is_departure_day: bool, destination_day_number: int) -> Dict:
        """Create a destination city day."""
        activities = []
        
        if is_arrival_day:
            activities.append({
                'time': '14:00',
                'activity': f'Welcome to {destination_city.name}!',
                'description': 'Check-in and first impressions',
                'duration': '2 hours',
                'type': 'arrival'
            })
            start_time = 16
        else:
            start_time = 9
        
        if is_departure_day:
            activities.extend([
                {
                    'time': '09:00',
                    'activity': 'Final exploration and souvenir shopping',
                    'description': 'Last chance to experience the city',
                    'duration': '3 hours',
                    'type': 'exploration'
                },
                {
                    'time': '14:00',
                    'activity': 'Departure preparations',
                    'description': 'Check-out and journey home',
                    'duration': '2 hours',
                    'type': 'departure'
                }
            ])
        else:
            # Full day activities
            destination_activities = self._generate_destination_activities(
                destination_city, trip_request, start_time, destination_day_number
            )
            activities.extend(destination_activities)
        
        day_title = f'Day {destination_day_number} in {destination_city.name}'
        if is_departure_day:
            day_title += ' (Departure)'
        
        return {
            'day': day_number,
            'date': self._calculate_date(day_number),
            'type': 'destination_day',
            'title': day_title,
            'location': {
                'city': destination_city.name,
                'country': destination_city.country,
                'is_main_destination': True
            },
            'activities': activities,
            'accommodation': {
                'city': destination_city.name,
                'nights': 0 if is_departure_day else 1,
                'type': 'Premium accommodation recommended for main destination'
            },
            'meals': self._suggest_destination_meals(destination_city, trip_request, destination_day_number),
            'destination_highlights': self._get_destination_highlights(destination_city, destination_day_number),
            'tips': self._get_destination_tips(destination_city, trip_request, is_departure_day)
        }
    
    def _generate_city_activities(self, city: Dict, city_details: Dict,
                                trip_request: TripRequest, start_time: int) -> List[Dict]:
        """Generate activities for a city based on its characteristics."""
        activities = []
        current_time = start_time
        
        best_activities = city_details.get('best_for', [])
        city_types = city.get('types', [])
        
        # Morning activity
        if 'cultural' in city_types:
            activities.append({
                'time': f'{current_time:02d}:00',
                'activity': 'Cultural exploration',
                'description': 'Visit local museums and cultural sites',
                'duration': '2.5 hours',
                'type': 'cultural'
            })
        elif 'historic' in city_types:
            activities.append({
                'time': f'{current_time:02d}:00',
                'activity': 'Historical walk',
                'description': 'Explore historic districts and architecture',
                'duration': '2.5 hours',
                'type': 'historic'
            })
        elif 'scenic' in city_types:
            activities.append({
                'time': f'{current_time:02d}:00',
                'activity': 'Scenic exploration',
                'description': 'Photography and nature walks',
                'duration': '2.5 hours',
                'type': 'scenic'
            })
        else:
            activities.append({
                'time': f'{current_time:02d}:00',
                'activity': 'City center exploration',
                'description': 'Discover the heart of the city',
                'duration': '2.5 hours',
                'type': 'exploration'
            })
        
        current_time += 3
        
        # Lunch break
        activities.append({
            'time': f'{current_time:02d}:00',
            'activity': 'Local lunch experience',
            'description': 'Try regional specialties at a local restaurant',
            'duration': '1.5 hours',
            'type': 'dining'
        })
        
        current_time += 2
        
        # Afternoon activity
        if 'culinary' in city_types:
            activities.append({
                'time': f'{current_time:02d}:00',
                'activity': 'Culinary discovery',
                'description': 'Food markets and local specialties',
                'duration': '2 hours',
                'type': 'culinary'
            })
        elif 'artistic' in city_types:
            activities.append({
                'time': f'{current_time:02d}:00',
                'activity': 'Arts and crafts exploration',
                'description': 'Local galleries and artisan workshops',
                'duration': '2 hours',
                'type': 'artistic'
            })
        else:
            activities.append({
                'time': f'{current_time:02d}:00',
                'activity': 'Hidden gems discovery',
                'description': 'Explore lesser-known attractions',
                'duration': '2 hours',
                'type': 'hidden_gems'
            })
        
        return activities
    
    def _generate_destination_activities(self, city: City, trip_request: TripRequest,
                                       start_time: int, day_number: int) -> List[Dict]:
        """Generate activities for the main destination."""
        activities = []
        current_time = start_time
        
        # Day-specific activities
        if day_number == 1:
            # First day - major attractions
            activities.extend([
                {
                    'time': f'{current_time:02d}:00',
                    'activity': f'Iconic {city.name} experience',
                    'description': 'Visit the most famous landmarks',
                    'duration': '3 hours',
                    'type': 'iconic'
                },
                {
                    'time': f'{current_time + 4:02d}:00',
                    'activity': 'Traditional lunch',
                    'description': 'Experience authentic local cuisine',
                    'duration': '1.5 hours',
                    'type': 'dining'
                },
                {
                    'time': f'{current_time + 6:02d}:00',
                    'activity': 'Neighborhood exploration',
                    'description': 'Discover local districts and culture',
                    'duration': '2.5 hours',
                    'type': 'exploration'
                }
            ])
        else:
            # Subsequent days - deeper exploration
            activities.extend([
                {
                    'time': f'{current_time:02d}:00',
                    'activity': f'Deep dive into {city.name}',
                    'description': 'Explore hidden corners and local favorites',
                    'duration': '3 hours',
                    'type': 'deep_exploration'
                },
                {
                    'time': f'{current_time + 4:02d}:00',
                    'activity': 'Leisurely lunch',
                    'description': 'Relax and people-watch at a local café',
                    'duration': '1.5 hours',
                    'type': 'dining'
                },
                {
                    'time': f'{current_time + 6:02d}:00',
                    'activity': 'Special interest exploration',
                    'description': 'Focus on your personal interests',
                    'duration': '2.5 hours',
                    'type': 'personalized'
                }
            ])
        
        return activities
    
    def _suggest_travel_day_meals(self, from_city: City, to_city: City,
                                trip_request: TripRequest) -> List[Dict]:
        """Suggest meals for travel days."""
        return [
            {
                'type': 'breakfast',
                'suggestion': f'Light breakfast in {from_city.name} before departure',
                'location': 'Hotel or local café'
            },
            {
                'type': 'lunch',
                'suggestion': 'Roadside restaurant or packed lunch',
                'location': 'En route'
            },
            {
                'type': 'dinner',
                'suggestion': f'Welcome dinner in {to_city.name}',
                'location': 'Local restaurant recommendation'
            }
        ]
    
    def _suggest_city_meals(self, city: Dict, trip_request: TripRequest) -> List[Dict]:
        """Suggest meals for city exploration days."""
        return [
            {
                'type': 'breakfast',
                'suggestion': 'Local café or hotel breakfast',
                'location': f'{city["name"]} city center'
            },
            {
                'type': 'lunch',
                'suggestion': 'Traditional regional restaurant',
                'location': 'Historic district'
            },
            {
                'type': 'dinner',
                'suggestion': 'Highly-rated local establishment',
                'location': 'Local recommendation'
            }
        ]
    
    def _suggest_destination_meals(self, city: City, trip_request: TripRequest,
                                 day_number: int) -> List[Dict]:
        """Suggest meals for destination days."""
        if day_number == 1:
            return [
                {
                    'type': 'breakfast',
                    'suggestion': 'Premium hotel breakfast',
                    'location': 'Hotel'
                },
                {
                    'type': 'lunch',
                    'suggestion': f'Iconic {city.name} restaurant',
                    'location': 'Tourist district'
                },
                {
                    'type': 'dinner',
                    'suggestion': 'Fine dining experience',
                    'location': 'Michelin recommended'
                }
            ]
        else:
            return [
                {
                    'type': 'breakfast',
                    'suggestion': 'Local market breakfast',
                    'location': 'Local market'
                },
                {
                    'type': 'lunch',
                    'suggestion': 'Hidden gem restaurant',
                    'location': 'Local neighborhood'
                },
                {
                    'type': 'dinner',
                    'suggestion': 'Traditional local tavern',
                    'location': 'Off the beaten path'
                }
            ]
    
    def _get_travel_day_tips(self, from_city: City, to_city: City,
                           trip_request: TripRequest) -> List[str]:
        """Get tips for travel days."""
        return [
            f'Check weather conditions for {trip_request.season.value} driving',
            'Keep important documents easily accessible',
            'Plan for regular stops every 2 hours',
            'Have local currency for tolls and emergencies'
        ]
    
    def _get_destination_highlights(self, city: City, day_number: int) -> List[str]:
        """Get highlights for destination days."""
        if day_number == 1:
            return [
                f'First impressions of {city.name}',
                'Major landmark visits',
                'Cultural orientation',
                'Local cuisine introduction'
            ]
        else:
            return [
                'Hidden neighborhoods',
                'Local experiences',
                'Artisan workshops',
                'Authentic dining'
            ]
    
    def _get_destination_tips(self, city: City, trip_request: TripRequest,
                           is_departure_day: bool) -> List[str]:
        """Get tips for destination days."""
        tips = [
            f'Best explored during {trip_request.season.value} season',
            'Book popular restaurants in advance',
            'Learn a few local phrases'
        ]
        
        if is_departure_day:
            tips.extend([
                'Allow extra time for departure preparations',
                'Check traffic conditions for departure time',
                'Keep receipts for expense tracking'
            ])
        
        return tips
    
    def _create_travel_timeline(self, daily_itinerary: List[Dict],
                              trip_request: TripRequest) -> Dict:
        """Create a travel timeline overview."""
        timeline = {
            'trip_duration': f'{trip_request.travel_days} days',
            'travel_days': len([day for day in daily_itinerary if day['type'] == 'travel_day']),
            'exploration_days': len([day for day in daily_itinerary if day['type'] == 'exploration_day']),
            'destination_days': len([day for day in daily_itinerary if day['type'] == 'destination_day']),
            'milestones': []
        }
        
        for day in daily_itinerary:
            if day['type'] == 'travel_day':
                timeline['milestones'].append({
                    'day': day['day'],
                    'type': 'travel',
                    'description': day['title'],
                    'icon': 'fas fa-route'
                })
            elif day['type'] == 'exploration_day':
                timeline['milestones'].append({
                    'day': day['day'],
                    'type': 'exploration',
                    'description': day['title'],
                    'icon': 'fas fa-map-marked-alt'
                })
            elif day['type'] == 'destination_day':
                timeline['milestones'].append({
                    'day': day['day'],
                    'type': 'destination',
                    'description': day['title'],
                    'icon': 'fas fa-star'
                })
        
        return timeline
    
    def _generate_packing_suggestions(self, daily_itinerary: List[Dict],
                                    trip_request: TripRequest) -> Dict:
        """Generate packing suggestions based on itinerary."""
        essentials = [
            'Valid passport/ID',
            'Travel insurance documents',
            'Driver\'s license',
            'Credit cards and some cash',
            'Phone charger and adapter',
            'Comfortable walking shoes'
        ]
        
        seasonal_items = {
            'spring': ['Light jacket', 'Umbrella', 'Layers for variable weather'],
            'summer': ['Sunscreen', 'Hat', 'Light breathable clothing', 'Sunglasses'],
            'autumn': ['Warm jacket', 'Scarf', 'Waterproof shoes'],
            'winter': ['Heavy coat', 'Gloves', 'Warm hat', 'Thermal layers']
        }
        
        activity_specific = []
        
        # Analyze activities for specific needs
        for day in daily_itinerary:
            activities = day.get('activities', [])
            for activity in activities:
                if activity['type'] == 'scenic':
                    activity_specific.append('Camera for landscapes')
                elif activity['type'] == 'cultural':
                    activity_specific.append('Respectful attire for cultural sites')
                elif activity['type'] == 'dining':
                    activity_specific.append('Smart casual clothes for dining')
        
        return {
            'essentials': essentials,
            'seasonal': seasonal_items.get(trip_request.season.value, []),
            'activity_specific': list(set(activity_specific)),
            'packing_tips': [
                'Pack light - you can buy forgotten items',
                'Bring versatile pieces that mix and match',
                'Pack one nice outfit for special dinners',
                'Leave space for souvenirs'
            ]
        }
    
    async def _generate_budget_breakdown(self, daily_itinerary: List[Dict],
                                       trip_request: TripRequest) -> Dict:
        """Generate budget breakdown."""
        days = trip_request.travel_days
        
        # Estimate costs (in EUR)
        accommodation_per_night = 120  # Average mid-range
        meals_per_day = 60  # Three meals
        activities_per_day = 40  # Attractions and experiences
        transport_per_day = 30  # Local transport and fuel
        
        total_accommodation = (days - 1) * accommodation_per_night  # -1 for departure day
        total_meals = days * meals_per_day
        total_activities = days * activities_per_day
        total_transport = days * transport_per_day
        
        miscellaneous = (total_accommodation + total_meals + total_activities + total_transport) * 0.15
        
        return {
            'accommodation': {
                'amount': total_accommodation,
                'description': f'{days - 1} nights accommodation'
            },
            'meals': {
                'amount': total_meals,
                'description': f'{days} days of dining'
            },
            'activities': {
                'amount': total_activities,
                'description': 'Attractions and experiences'
            },
            'transport': {
                'amount': total_transport,
                'description': 'Fuel, tolls, and local transport'
            },
            'miscellaneous': {
                'amount': round(miscellaneous),
                'description': 'Shopping, tips, and unexpected expenses'
            },
            'total_estimated': round(total_accommodation + total_meals + total_activities + total_transport + miscellaneous),
            'budget_tips': [
                'Book accommodations early for better rates',
                'Mix fine dining with local casual spots',
                'Look for city tourism cards for attraction discounts',
                'Keep 20% buffer for unexpected expenses'
            ]
        }
    
    async def _generate_comprehensive_travel_tips(self, daily_itinerary: List[Dict],
                                                trip_request: TripRequest) -> Dict:
        """Generate comprehensive travel tips."""
        return {
            'before_departure': [
                'Verify passport validity (6+ months remaining)',
                'Notify banks of travel plans',
                'Download offline maps and translation apps',
                'Research local customs and etiquette',
                'Check weather forecasts for packing'
            ],
            'during_travel': [
                'Keep digital and physical copies of important documents',
                'Stay flexible with your itinerary',
                'Try to learn basic local phrases',
                'Respect local customs and dress codes',
                'Stay hydrated and take breaks while driving'
            ],
            'cultural_tips': [
                'Dining times vary by country - research local customs',
                'Tipping practices differ across Europe',
                'Many shops close on Sundays or have limited hours',
                'Public transport is often more efficient than driving in city centers'
            ],
            'safety_tips': [
                'Share your itinerary with someone at home',
                'Keep emergency contacts easily accessible',
                'Be aware of common tourist scams',
                'Have emergency funds in multiple forms',
                'Trust your instincts about situations and places'
            ],
            'season_specific': self._get_season_specific_tips(trip_request.season.value)
        }
    
    def _get_season_specific_tips(self, season: str) -> List[str]:
        """Get season-specific travel tips."""
        tips = {
            'spring': [
                'Weather can be unpredictable - pack layers',
                'Great season for outdoor activities',
                'Fewer crowds than summer',
                'Some mountain passes may still be closed'
            ],
            'summer': [
                'Book accommodations well in advance',
                'Start sightseeing early to avoid crowds and heat',
                'Stay hydrated and use sun protection',
                'Expect higher prices during peak season'
            ],
            'autumn': [
                'Perfect weather for walking and sightseeing',
                'Beautiful fall colors for photography',
                'Harvest season - great food experiences',
                'Weather can change quickly in mountains'
            ],
            'winter': [
                'Shorter daylight hours - plan accordingly',
                'Some attractions may have reduced hours',
                'Perfect for cozy indoor experiences',
                'Check road conditions for mountain travel'
            ]
        }
        
        return tips.get(season, [])
    
    def _classify_trip_type(self, trip_request: TripRequest,
                          intermediate_cities: List[Dict]) -> str:
        """Classify the type of trip based on itinerary."""
        days = trip_request.travel_days
        intermediate_count = len(intermediate_cities)
        
        if days <= 3:
            return "Weekend Getaway"
        elif days <= 5:
            if intermediate_count == 0:
                return "City Focus Trip"
            else:
                return "Multi-City Explorer"
        elif days <= 7:
            return "Classic European Tour"
        else:
            return "Grand European Adventure"
    
    def _calculate_date(self, day_number: int) -> str:
        """Calculate date string for day number (placeholder)."""
        # In a real implementation, this would use actual departure date
        base_date = datetime.now()
        trip_date = base_date + timedelta(days=day_number - 1)
        return trip_date.strftime("%A, %B %d")
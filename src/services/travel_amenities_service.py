"""
Travel amenities service for hotels, restaurants, and fuel consumption.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
from ..core.models import City, ServiceResult, TripRequest
from ..core.exceptions import TravelPlannerException
from .real_places_service import RealPlacesService

logger = structlog.get_logger(__name__)


class TravelAmenitiesService:
    """Service for managing travel amenities like hotels, restaurants, and fuel."""
    
    def __init__(self):
        self.places_service = RealPlacesService()
    
    async def get_comprehensive_accommodations(self, cities: List[City], 
                                             trip_request: TripRequest) -> ServiceResult:
        """Get comprehensive hotel recommendations for all cities."""
        try:
            accommodations = {}
            
            for city in cities:
                city_hotels = await self._get_city_accommodations(city, trip_request)
                if city_hotels:
                    accommodations[city.name] = city_hotels
            
            return ServiceResult.success_result(accommodations)
            
        except Exception as e:
            logger.error("Failed to get accommodations", error=str(e))
            return ServiceResult.error_result(f"Accommodations lookup failed: {e}")
    
    async def get_comprehensive_restaurants(self, cities: List[City], 
                                          trip_request: TripRequest) -> ServiceResult:
        """Get comprehensive restaurant recommendations for all cities."""
        try:
            restaurants = {}
            
            for city in cities:
                city_restaurants = await self._get_city_restaurants(city, trip_request)
                if city_restaurants:
                    restaurants[city.name] = city_restaurants
            
            return ServiceResult.success_result(restaurants)
            
        except Exception as e:
            logger.error("Failed to get restaurants", error=str(e))
            return ServiceResult.error_result(f"Restaurant lookup failed: {e}")
    
    async def calculate_fuel_consumption(self, routes: List[Dict], 
                                       trip_request: TripRequest) -> ServiceResult:
        """Calculate detailed fuel consumption for all routes."""
        try:
            fuel_analysis = []
            
            for route in routes:
                route_analysis = self._analyze_route_fuel_consumption(route, trip_request)
                fuel_analysis.append(route_analysis)
            
            return ServiceResult.success_result({
                'route_analyses': fuel_analysis,
                'comparison': self._create_fuel_comparison(fuel_analysis),
                'eco_tips': self._get_eco_friendly_tips()
            })
            
        except Exception as e:
            logger.error("Failed to calculate fuel consumption", error=str(e))
            return ServiceResult.error_result(f"Fuel calculation failed: {e}")
    
    async def _get_city_accommodations(self, city: City, 
                                     trip_request: TripRequest) -> List[Dict]:
        """Get accommodation recommendations for a specific city."""
        # In a real implementation, this would call external APIs
        # For now, generate realistic data based on city characteristics
        
        accommodations = []
        
        # Generate hotels based on city population and types
        if city.population and city.population > 100000:
            # Large city - more hotel options
            hotels_data = [
                {
                    'name': f'Grand Hotel {city.name}',
                    'type': 'luxury',
                    'rating': 4.5,
                    'price_level': 4,
                    'vicinity': f'{city.name} City Center',
                    'amenities': ['spa', 'restaurant', 'fitness', 'wifi'],
                    'price_range': '€180-250/night',
                    'booking_link': 'booking.com',
                    'description': 'Luxury accommodation in the heart of the city'
                },
                {
                    'name': f'Boutique {city.name}',
                    'type': 'boutique',
                    'rating': 4.2,
                    'price_level': 3,
                    'vicinity': f'Historic {city.name}',
                    'amenities': ['restaurant', 'wifi', 'concierge'],
                    'price_range': '€120-180/night',
                    'booking_link': 'booking.com',
                    'description': 'Charming boutique hotel with local character'
                },
                {
                    'name': f'{city.name} Business Hotel',
                    'type': 'business',
                    'rating': 4.0,
                    'price_level': 3,
                    'vicinity': f'{city.name} Business District',
                    'amenities': ['business center', 'wifi', 'parking'],
                    'price_range': '€90-140/night',
                    'booking_link': 'booking.com',
                    'description': 'Modern business hotel with excellent facilities'
                }
            ]
        else:
            # Smaller city - fewer but more authentic options
            hotels_data = [
                {
                    'name': f'Hotel {city.name} Historic',
                    'type': 'historic',
                    'rating': 4.3,
                    'price_level': 3,
                    'vicinity': f'Historic {city.name}',
                    'amenities': ['restaurant', 'wifi', 'historic charm'],
                    'price_range': '€100-150/night',
                    'booking_link': 'booking.com',
                    'description': 'Historic hotel with authentic local character'
                },
                {
                    'name': f'{city.name} Family Inn',
                    'type': 'family',
                    'rating': 4.0,
                    'price_level': 2,
                    'vicinity': f'{city.name} Center',
                    'amenities': ['family rooms', 'wifi', 'breakfast'],
                    'price_range': '€70-120/night',
                    'booking_link': 'booking.com',
                    'description': 'Comfortable family-run accommodation'
                }
            ]
        
        # Add season-specific recommendations
        season_factor = self._get_season_accommodation_factor(trip_request.season.value)
        for hotel in hotels_data:
            hotel['seasonal_notes'] = season_factor['notes']
            hotel['availability'] = season_factor['availability']
            accommodations.append(hotel)
        
        return accommodations
    
    async def _get_city_restaurants(self, city: City, 
                                  trip_request: TripRequest) -> List[Dict]:
        """Get restaurant recommendations for a specific city."""
        restaurants = []
        
        # Base restaurants for any city
        base_restaurants = [
            {
                'name': f'La {city.name}',
                'cuisine_types': ['local', 'traditional'],
                'rating': 4.4,
                'price_level': 3,
                'vicinity': f'{city.name} Old Town',
                'specialties': self._get_local_specialties(city),
                'price_range': '€25-45/person',
                'reservation': 'recommended',
                'description': 'Authentic local cuisine in traditional setting'
            },
            {
                'name': f'Bistro {city.name}',
                'cuisine_types': ['bistro', 'european'],
                'rating': 4.1,
                'price_level': 2,
                'vicinity': f'{city.name} Center',
                'specialties': ['seasonal menu', 'local wines'],
                'price_range': '€18-30/person',
                'reservation': 'optional',
                'description': 'Cozy bistro with seasonal European dishes'
            }
        ]
        
        # Add cuisine based on country
        country_specific = self._get_country_specific_restaurants(city)
        restaurants.extend(base_restaurants)
        restaurants.extend(country_specific)
        
        # Add season-specific options
        seasonal_restaurants = self._get_seasonal_restaurants(city, trip_request.season.value)
        restaurants.extend(seasonal_restaurants)
        
        return restaurants[:6]  # Return top 6 recommendations
    
    def _analyze_route_fuel_consumption(self, route: Dict, 
                                      trip_request: TripRequest) -> Dict:
        """Analyze fuel consumption for a specific route."""
        distance_km = route.get('total_distance_km', 0)
        
        # Vehicle efficiency assumptions (can be made configurable)
        vehicle_profiles = {
            'compact': {'consumption': 6.0, 'tank_size': 45, 'fuel_type': 'petrol'},
            'mid_size': {'consumption': 7.5, 'tank_size': 55, 'fuel_type': 'petrol'},
            'suv': {'consumption': 9.0, 'tank_size': 70, 'fuel_type': 'petrol'},
            'electric': {'consumption': 20.0, 'tank_size': 60, 'fuel_type': 'electric'}  # kWh/100km
        }
        
        # Default to mid-size car
        vehicle = vehicle_profiles['mid_size']
        
        # Calculate consumption
        fuel_needed = (distance_km * vehicle['consumption']) / 100
        
        # Fuel prices by country (average)
        fuel_prices = {
            'France': {'petrol': 1.65, 'diesel': 1.55, 'electric': 0.18},
            'Italy': {'petrol': 1.70, 'diesel': 1.58, 'electric': 0.22},
            'Switzerland': {'petrol': 1.85, 'diesel': 1.75, 'electric': 0.25},
            'Monaco': {'petrol': 1.75, 'diesel': 1.65, 'electric': 0.20}
        }
        
        # Estimate average fuel price along route
        avg_fuel_price = 1.68  # Average European price
        
        total_fuel_cost = fuel_needed * avg_fuel_price
        
        # Calculate CO2 emissions
        co2_per_liter = 2.31  # kg CO2 per liter of petrol
        co2_emissions = fuel_needed * co2_per_liter
        
        return {
            'route_name': route.get('name', 'Route'),
            'distance_km': distance_km,
            'fuel_consumption': {
                'liters': round(fuel_needed, 1),
                'cost_eur': round(total_fuel_cost, 2),
                'cost_per_100km': round((fuel_needed * avg_fuel_price) / (distance_km / 100), 2) if distance_km > 0 else 0
            },
            'environmental': {
                'co2_emissions_kg': round(co2_emissions, 1),
                'co2_per_km': round(co2_emissions / distance_km, 3) if distance_km > 0 else 0
            },
            'fuel_stops': self._estimate_fuel_stops(distance_km, vehicle['tank_size'], vehicle['consumption']),
            'vehicle_profile': vehicle,
            'recommendations': self._get_fuel_saving_tips(distance_km, trip_request.season.value)
        }
    
    def _create_fuel_comparison(self, analyses: List[Dict]) -> Dict:
        """Create a comparison table of fuel consumption across routes."""
        if not analyses:
            return {}
        
        comparison = {
            'most_efficient': min(analyses, key=lambda x: x['fuel_consumption']['liters']),
            'least_efficient': max(analyses, key=lambda x: x['fuel_consumption']['liters']),
            'cheapest': min(analyses, key=lambda x: x['fuel_consumption']['cost_eur']),
            'most_expensive': max(analyses, key=lambda x: x['fuel_consumption']['cost_eur']),
            'eco_friendly': min(analyses, key=lambda x: x['environmental']['co2_emissions_kg']),
            'summary': {
                'total_routes': len(analyses),
                'avg_consumption': round(sum(a['fuel_consumption']['liters'] for a in analyses) / len(analyses), 1),
                'avg_cost': round(sum(a['fuel_consumption']['cost_eur'] for a in analyses) / len(analyses), 2),
                'avg_co2': round(sum(a['environmental']['co2_emissions_kg'] for a in analyses) / len(analyses), 1)
            }
        }
        
        return comparison
    
    def _estimate_fuel_stops(self, distance_km: float, tank_size: float, 
                           consumption_per_100km: float) -> List[Dict]:
        """Estimate where fuel stops might be needed."""
        range_km = (tank_size / consumption_per_100km) * 100 * 0.8  # 80% of tank capacity
        
        if distance_km <= range_km:
            return [{'stop_needed': False, 'message': 'No fuel stops needed for this distance'}]
        
        stops_needed = int(distance_km / range_km)
        stops = []
        
        for i in range(stops_needed):
            stop_distance = (i + 1) * range_km
            stops.append({
                'stop_number': i + 1,
                'distance_km': round(stop_distance, 0),
                'estimated_cost': round((tank_size * 0.8) * 1.68, 2),  # 80% fill-up
                'recommendation': f'Fuel stop around {stop_distance:.0f}km mark'
            })
        
        return stops
    
    def _get_season_accommodation_factor(self, season: str) -> Dict:
        """Get seasonal factors for accommodations."""
        factors = {
            'summer': {
                'availability': 'low',
                'notes': 'Peak season - book well in advance, higher prices expected',
                'price_multiplier': 1.3
            },
            'winter': {
                'availability': 'high',
                'notes': 'Off-season rates available, some resort areas may have limited services',
                'price_multiplier': 0.8
            },
            'spring': {
                'availability': 'good',
                'notes': 'Pleasant season with moderate pricing and good availability',
                'price_multiplier': 1.0
            },
            'autumn': {
                'availability': 'good',
                'notes': 'Shoulder season with competitive rates and good availability',
                'price_multiplier': 0.9
            }
        }
        
        return factors.get(season, factors['spring'])
    
    def _get_local_specialties(self, city: City) -> List[str]:
        """Get local specialties based on city/country."""
        country_specialties = {
            'France': ['coq au vin', 'bouillabaisse', 'ratatouille', 'local cheeses'],
            'Italy': ['risotto', 'osso buco', 'local pasta', 'regional wines'],
            'Switzerland': ['fondue', 'raclette', 'rösti', 'local cheeses'],
            'Monaco': ['barbajuan', 'socca', 'Mediterranean fish', 'French pastries']
        }
        
        return country_specialties.get(city.country, ['local dishes', 'regional specialties'])
    
    def _get_country_specific_restaurants(self, city: City) -> List[Dict]:
        """Get country-specific restaurant recommendations."""
        country_restaurants = {
            'France': [
                {
                    'name': f'Le Gourmet {city.name}',
                    'cuisine_types': ['french', 'fine dining'],
                    'rating': 4.6,
                    'price_level': 4,
                    'vicinity': f'{city.name} Center',
                    'specialties': ['french cuisine', 'wine pairing'],
                    'price_range': '€45-80/person',
                    'reservation': 'required',
                    'description': 'Upscale French dining with extensive wine list'
                }
            ],
            'Italy': [
                {
                    'name': f'Trattoria {city.name}',
                    'cuisine_types': ['italian', 'trattoria'],
                    'rating': 4.3,
                    'price_level': 2,
                    'vicinity': f'{city.name} Historic Center',
                    'specialties': ['homemade pasta', 'local wines'],
                    'price_range': '€20-35/person',
                    'reservation': 'recommended',
                    'description': 'Family-run trattoria with authentic Italian dishes'
                }
            ]
        }
        
        return country_restaurants.get(city.country, [])
    
    def _get_seasonal_restaurants(self, city: City, season: str) -> List[Dict]:
        """Get seasonal restaurant recommendations."""
        seasonal_options = {
            'summer': [
                {
                    'name': f'{city.name} Terrace',
                    'cuisine_types': ['outdoor dining', 'seasonal'],
                    'rating': 4.0,
                    'price_level': 3,
                    'vicinity': f'{city.name} Riverside',
                    'specialties': ['grilled dishes', 'summer cocktails'],
                    'price_range': '€22-40/person',
                    'reservation': 'recommended',
                    'description': 'Beautiful terrace dining perfect for summer evenings'
                }
            ],
            'winter': [
                {
                    'name': f'{city.name} Cozy Corner',
                    'cuisine_types': ['comfort food', 'seasonal'],
                    'rating': 4.2,
                    'price_level': 2,
                    'vicinity': f'{city.name} Old Quarter',
                    'specialties': ['hearty stews', 'mulled wine'],
                    'price_range': '€18-32/person',
                    'reservation': 'optional',
                    'description': 'Warm, cozy atmosphere perfect for winter dining'
                }
            ]
        }
        
        return seasonal_options.get(season, [])
    
    def _get_fuel_saving_tips(self, distance_km: float, season: str) -> List[str]:
        """Get fuel-saving tips based on route and season."""
        tips = [
            'Maintain steady speeds between 90-110 km/h for optimal fuel efficiency',
            'Check tire pressure before departure - properly inflated tires save fuel',
            'Remove unnecessary weight from the vehicle',
            'Use cruise control on highways when possible'
        ]
        
        if distance_km > 500:
            tips.append('Consider overnight stops to avoid driver fatigue and aggressive driving')
        
        season_tips = {
            'summer': ['Use A/C efficiently - highway speeds: A/C on, city speeds: windows down'],
            'winter': ['Allow engine to warm up briefly, but avoid extended idling'],
            'spring': ['Take advantage of mild weather - consider windows down for ventilation'],
            'autumn': ['Be aware of wet road conditions that may affect fuel efficiency']
        }
        
        tips.extend(season_tips.get(season, []))
        
        return tips
    
    def _get_eco_friendly_tips(self) -> List[str]:
        """Get general eco-friendly travel tips."""
        return [
            'Consider carpooling or train travel for more eco-friendly options',
            'Offset your carbon footprint through verified carbon offset programs',
            'Choose accommodations with green certifications',
            'Support local businesses to reduce transportation of goods',
            'Pack reusable water bottles and shopping bags',
            'Use public transportation in cities when possible'
        ]
"""
Local transportation integration service.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import structlog
from ..core.database import get_database
from ..core.exceptions import ValidationError, ServiceError

logger = structlog.get_logger(__name__)


class TransportationService:
    """Handles local transportation information and integration."""
    
    def __init__(self):
        self.db = get_database()
        self.cache_duration_hours = 24  # Cache data for 24 hours
    
    def get_city_transportation(self, city_name: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Get comprehensive transportation information for a city."""
        try:
            # Check cache first
            if not force_refresh:
                cached_data = self._get_cached_data(city_name)
                if cached_data:
                    return cached_data
            
            # Generate transportation data (in production, this would call external APIs)
            transport_data = self._generate_transport_data(city_name)
            
            # Cache the data
            self._cache_data(city_name, transport_data)
            
            return transport_data
            
        except Exception as e:
            logger.error(f"Failed to get transportation data: {e}")
            raise ServiceError(f"Failed to get transportation data: {str(e)}")
    
    def _get_cached_data(self, city_name: str) -> Optional[Dict[str, Any]]:
        """Get cached transportation data if available and not expired."""
        try:
            with self.db.get_connection() as conn:
                # Get all transport types for the city
                cached_entries = conn.execute('''
                    SELECT * FROM transportation_cache
                    WHERE city_name = ? AND expires_at > CURRENT_TIMESTAMP
                ''', (city_name,)).fetchall()
                
                if not cached_entries:
                    return None
                
                # Combine all transport types
                combined_data = {
                    'city': city_name,
                    'last_updated': None,
                    'public_transit': None,
                    'parking': None,
                    'bike_share': None,
                    'taxi_rideshare': None,
                    'car_rental': None,
                    'ferries': None
                }
                
                for entry in cached_entries:
                    transport_type = entry['transport_type']
                    data = json.loads(entry['data'])
                    combined_data[transport_type] = data
                    
                    # Track the most recent update
                    if not combined_data['last_updated'] or entry['cached_at'] > combined_data['last_updated']:
                        combined_data['last_updated'] = entry['cached_at']
                
                return combined_data
                
        except Exception as e:
            logger.error(f"Failed to get cached data: {e}")
            return None
    
    def _cache_data(self, city_name: str, transport_data: Dict[str, Any]):
        """Cache transportation data."""
        try:
            expires_at = datetime.now() + timedelta(hours=self.cache_duration_hours)
            
            with self.db.get_connection() as conn:
                # Cache each transport type separately
                for transport_type, data in transport_data.items():
                    if transport_type in ['city', 'last_updated']:
                        continue
                    
                    if data:
                        # Delete existing cache for this type
                        conn.execute('''
                            DELETE FROM transportation_cache
                            WHERE city_name = ? AND transport_type = ?
                        ''', (city_name, transport_type))
                        
                        # Insert new cache
                        conn.execute('''
                            INSERT INTO transportation_cache (
                                city_name, transport_type, data, expires_at
                            ) VALUES (?, ?, ?, ?)
                        ''', (city_name, transport_type, json.dumps(data), expires_at))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to cache data: {e}")
    
    def _generate_transport_data(self, city_name: str) -> Dict[str, Any]:
        """Generate comprehensive transportation data for a city."""
        # In production, this would call various transportation APIs
        # For now, we'll return structured sample data
        
        return {
            'city': city_name,
            'last_updated': datetime.now().isoformat(),
            
            'public_transit': {
                'available': True,
                'systems': [
                    {
                        'type': 'metro',
                        'name': f'{city_name} Metro',
                        'lines': 5,
                        'stations': 89,
                        'operating_hours': '5:30 AM - 12:30 AM',
                        'ticket_types': [
                            {'name': 'Single Ticket', 'price': 2.40, 'currency': 'EUR'},
                            {'name': 'Day Pass', 'price': 8.80, 'currency': 'EUR'},
                            {'name': '3-Day Pass', 'price': 19.20, 'currency': 'EUR'},
                            {'name': 'Weekly Pass', 'price': 35.00, 'currency': 'EUR'}
                        ],
                        'payment_methods': ['Cash', 'Card', 'Mobile App'],
                        'accessibility': 'Most stations wheelchair accessible'
                    },
                    {
                        'type': 'bus',
                        'name': f'{city_name} Bus Network',
                        'routes': 150,
                        'night_service': True,
                        'ticket_integration': True
                    },
                    {
                        'type': 'tram',
                        'name': f'{city_name} Tram',
                        'lines': 12,
                        'ticket_integration': True
                    }
                ],
                'apps': [
                    {'name': f'{city_name} Transit', 'ios': True, 'android': True},
                    {'name': 'Citymapper', 'ios': True, 'android': True}
                ],
                'tips': [
                    'Buy multi-day passes for better value',
                    'Download offline maps in the transit app',
                    'Validate tickets before boarding'
                ]
            },
            
            'parking': {
                'street_parking': {
                    'available': True,
                    'payment_required': True,
                    'hours': 'Mon-Sat 9AM-8PM',
                    'average_price': 2.50,
                    'currency': 'EUR',
                    'payment_methods': ['Coins', 'Card', 'App']
                },
                'parking_garages': [
                    {
                        'name': 'Central Parking',
                        'capacity': 500,
                        'price_per_hour': 3.50,
                        'price_per_day': 25.00,
                        'location': 'City Center',
                        'ev_charging': True
                    },
                    {
                        'name': 'Station Parking',
                        'capacity': 800,
                        'price_per_hour': 2.50,
                        'price_per_day': 18.00,
                        'location': 'Main Station'
                    }
                ],
                'park_and_ride': [
                    {
                        'name': 'P+R North',
                        'capacity': 1000,
                        'price_per_day': 5.00,
                        'includes_transit': True
                    }
                ],
                'apps': ['ParkNow', 'EasyPark'],
                'tips': [
                    'Use Park & Ride for cheaper all-day parking',
                    'Book parking garages online for discounts',
                    'Check for resident-only zones'
                ]
            },
            
            'bike_share': {
                'available': True,
                'system_name': f'{city_name} Bike',
                'stations': 250,
                'bikes_available': 3000,
                'ebikes_available': 500,
                'pricing': [
                    {'duration': '30 min', 'price': 1.50},
                    {'duration': '1 hour', 'price': 3.00},
                    {'duration': 'Day pass', 'price': 12.00},
                    {'duration': 'Weekly pass', 'price': 25.00}
                ],
                'app_required': True,
                'helmet_provided': False,
                'tips': [
                    'First 30 minutes often free with subscription',
                    'Check bike condition before unlocking',
                    'Park only at designated stations'
                ]
            },
            
            'taxi_rideshare': {
                'taxi': {
                    'available': True,
                    'booking_methods': ['Street hail', 'Phone', 'App'],
                    'base_fare': 4.50,
                    'per_km': 2.20,
                    'night_surcharge': '20%',
                    'airport_surcharge': 5.00,
                    'apps': ['MyTaxi', 'Free Now']
                },
                'rideshare': {
                    'available': True,
                    'services': ['Uber', 'Bolt'],
                    'average_wait': '5-10 minutes',
                    'price_vs_taxi': 'Usually 10-20% cheaper'
                },
                'tips': [
                    'Taxis accept card payments',
                    'Book airport transfers in advance',
                    'Compare prices between services'
                ]
            },
            
            'car_rental': {
                'available': True,
                'major_companies': ['Hertz', 'Avis', 'Europcar', 'Sixt'],
                'local_companies': [f'{city_name} Rent'],
                'average_daily_rate': {
                    'economy': 35.00,
                    'compact': 45.00,
                    'suv': 75.00
                },
                'requirements': [
                    'Valid driver\'s license',
                    'Credit card',
                    'Minimum age 21 (25 for some categories)'
                ],
                'insurance_tips': [
                    'Check if your credit card provides coverage',
                    'Consider excess insurance',
                    'Document any existing damage'
                ]
            },
            
            'ferries': None  # Will be populated for coastal cities
        }
    
    def calculate_route_options(self, start: Dict[str, Any], end: Dict[str, Any], 
                              preferences: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Calculate different transportation options between two points."""
        try:
            if not preferences:
                preferences = {}
            
            # Calculate distance (simplified)
            distance_km = self._calculate_distance(
                start.get('lat'), start.get('lon'),
                end.get('lat'), end.get('lon')
            )
            
            options = []
            
            # Walking option (if under 2km)
            if distance_km <= 2:
                options.append({
                    'mode': 'walking',
                    'duration_min': int(distance_km * 12),  # ~5km/h walking speed
                    'distance_km': distance_km,
                    'cost': 0,
                    'instructions': f'Walk {distance_km:.1f}km',
                    'carbon_emissions': 0
                })
            
            # Public transit option
            options.append({
                'mode': 'public_transit',
                'duration_min': int(distance_km * 3 + 10),  # Rough estimate
                'distance_km': distance_km,
                'cost': 2.40,  # Single ticket
                'instructions': 'Take Metro Line 2 to Central, transfer to Bus 45',
                'carbon_emissions': distance_km * 0.05  # kg CO2
            })
            
            # Taxi option
            taxi_cost = 4.50 + (distance_km * 2.20)
            options.append({
                'mode': 'taxi',
                'duration_min': int(distance_km * 2.5),  # Traffic considered
                'distance_km': distance_km,
                'cost': round(taxi_cost, 2),
                'instructions': 'Taxi available at designated stands or via app',
                'carbon_emissions': distance_km * 0.15
            })
            
            # Bike option (if under 10km)
            if distance_km <= 10:
                options.append({
                    'mode': 'bike_share',
                    'duration_min': int(distance_km * 4),  # ~15km/h average
                    'distance_km': distance_km,
                    'cost': 3.00 if distance_km * 4 > 30 else 1.50,
                    'instructions': f'Bike stations available - {distance_km:.1f}km ride',
                    'carbon_emissions': 0
                })
            
            # Car option
            options.append({
                'mode': 'car',
                'duration_min': int(distance_km * 2),
                'distance_km': distance_km,
                'cost': distance_km * 0.20,  # Fuel estimate
                'instructions': 'Drive via fastest route',
                'carbon_emissions': distance_km * 0.20,
                'parking_note': 'Additional parking fees may apply'
            })
            
            # Sort by preference
            sort_key = preferences.get('optimize_for', 'duration')
            if sort_key == 'cost':
                options.sort(key=lambda x: x['cost'])
            elif sort_key == 'carbon':
                options.sort(key=lambda x: x['carbon_emissions'])
            else:
                options.sort(key=lambda x: x['duration_min'])
            
            return options
            
        except Exception as e:
            logger.error(f"Failed to calculate route options: {e}")
            raise ServiceError(f"Failed to calculate route options: {str(e)}")
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in km (simplified)."""
        # Simplified calculation - in production use proper geodesic distance
        import math
        
        R = 6371  # Earth's radius in km
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        
        a = (math.sin(dLat/2) * math.sin(dLat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dLon/2) * math.sin(dLon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def get_toll_information(self, route: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get toll information for a driving route."""
        try:
            # In production, this would use toll calculation APIs
            total_toll = 0
            toll_points = []
            
            # Simulate toll calculation
            for i in range(len(route) - 1):
                if i % 3 == 0:  # Simulate toll points
                    toll_points.append({
                        'location': f'Toll Point {i+1}',
                        'price': 2.50 + (i * 0.50),
                        'payment_methods': ['Cash', 'Card', 'Electronic toll']
                    })
                    total_toll += toll_points[-1]['price']
            
            return {
                'total_toll': round(total_toll, 2),
                'currency': 'EUR',
                'toll_points': toll_points,
                'electronic_toll_available': True,
                'tips': [
                    'Get electronic toll device for faster passage',
                    'Keep small change ready for cash-only tolls',
                    'Some toll roads have alternative free routes'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get toll information: {e}")
            raise ServiceError(f"Failed to get toll information: {str(e)}")
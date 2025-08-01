"""
Real Places Service using Google Places API for authentic hotel and restaurant data.
This replaces the fake data generation with actual business listings.
"""
import os
import requests
import structlog
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
import asyncio
import aiohttp
from ..core.models import City, ServiceResult, TripRequest
from ..core.exceptions import TravelPlannerException

logger = structlog.get_logger(__name__)


class RealPlacesService:
    """Service for fetching real hotel and restaurant data from Google Places API."""
    
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.session = None
        
        if not self.google_api_key:
            logger.warning("Google Places API key not configured - will use fallback data")
    
    async def get_hotels_for_city(self, city: City, trip_request: TripRequest) -> List[Dict]:
        """Get real hotel data for a city using Google Places API."""
        if not self.google_api_key:
            logger.warning(f"No Google API key - using fallback for hotels in {city.name}")
            return self._get_fallback_hotels(city)
        
        try:
            hotels = []
            
            # Search for hotels near the city
            search_results = await self._search_places(
                location=f"{city.coordinates[0]},{city.coordinates[1]}" if city.coordinates else city.name,
                radius=5000,  # 5km radius
                place_type="lodging",
                keyword="hotel"
            )
            
            # Get detailed information for each hotel
            for place in search_results[:10]:  # Limit to top 10 results
                details = await self._get_place_details(place['place_id'])
                if details:
                    hotel_data = self._format_hotel_data(details, city.name)
                    if hotel_data:
                        hotels.append(hotel_data)
            
            # If we don't have enough results, search for more types
            if len(hotels) < 5:
                additional_results = await self._search_places(
                    location=f"{city.coordinates[0]},{city.coordinates[1]}" if city.coordinates else city.name,
                    radius=8000,  # Expand radius
                    place_type="lodging",
                    keyword="accommodation"
                )
                
                for place in additional_results[:5]:
                    if place['place_id'] not in [h.get('place_id') for h in hotels]:
                        details = await self._get_place_details(place['place_id'])
                        if details:
                            hotel_data = self._format_hotel_data(details, city.name)
                            if hotel_data:
                                hotels.append(hotel_data)
            
            logger.info(f"Found {len(hotels)} real hotels for {city.name}")
            return hotels[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Failed to fetch hotels for {city.name}: {e}")
            return self._get_fallback_hotels(city)
    
    async def get_restaurants_for_city(self, city: City, trip_request: TripRequest) -> List[Dict]:
        """Get real restaurant data for a city using Google Places API."""
        if not self.google_api_key:
            logger.warning(f"No Google API key - using fallback for restaurants in {city.name}")
            return self._get_fallback_restaurants(city)
        
        try:
            restaurants = []
            
            # Search for different types of restaurants
            search_types = [
                ("restaurant", "restaurant"),
                ("restaurant", "local cuisine"),
                ("restaurant", "fine dining"),
                ("cafe", "cafe"),
            ]
            
            for place_type, keyword in search_types:
                search_results = await self._search_places(
                    location=f"{city.coordinates[0]},{city.coordinates[1]}" if city.coordinates else city.name,
                    radius=3000,  # 3km radius for restaurants
                    place_type=place_type,
                    keyword=keyword
                )
                
                # Get detailed information for top results
                for place in search_results[:3]:  # 3 per category
                    if place['place_id'] not in [r.get('place_id') for r in restaurants]:
                        details = await self._get_place_details(place['place_id'])
                        if details:
                            restaurant_data = self._format_restaurant_data(details, city.name)
                            if restaurant_data:
                                restaurants.append(restaurant_data)
            
            logger.info(f"Found {len(restaurants)} real restaurants for {city.name}")
            return restaurants[:12]  # Return top 12
            
        except Exception as e:
            logger.error(f"Failed to fetch restaurants for {city.name}: {e}")
            return self._get_fallback_restaurants(city)
    
    async def _search_places(self, location: str, radius: int, place_type: str, 
                           keyword: str = None) -> List[Dict]:
        """Search for places using Google Places API."""
        url = f"{self.base_url}/nearbysearch/json"
        
        params = {
            'location': location,
            'radius': radius,
            'type': place_type,
            'key': self.google_api_key
        }
        
        if keyword:
            params['keyword'] = keyword
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', [])
                else:
                    logger.error(f"Places API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Places search error: {e}")
            return []
    
    async def _get_place_details(self, place_id: str) -> Optional[Dict]:
        """Get detailed information for a specific place."""
        url = f"{self.base_url}/details/json"
        
        params = {
            'place_id': place_id,
            'fields': 'name,rating,user_ratings_total,price_level,vicinity,formatted_address,geometry,opening_hours,photos,website,formatted_phone_number,types',
            'key': self.google_api_key
        }
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result')
                else:
                    logger.error(f"Place details API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Place details error: {e}")
            return None
    
    def _format_hotel_data(self, place_details: Dict, city_name: str) -> Optional[Dict]:
        """Format Google Places data into hotel format."""
        try:
            # Extract basic information
            name = place_details.get('name', 'Unknown Hotel')
            rating = place_details.get('rating', 0)
            rating_count = place_details.get('user_ratings_total', 0)
            price_level = place_details.get('price_level', 2)  # 1-4 scale
            vicinity = place_details.get('vicinity', city_name)
            
            # Skip if rating is too low or no ratings
            if rating < 3.0 and rating_count < 10:
                return None
            
            # Determine hotel type based on name and price level
            hotel_type = self._determine_hotel_type(name, price_level)
            
            # Estimate price range based on price level and city
            price_range = self._estimate_price_range(price_level, city_name)
            
            # Extract amenities from types
            amenities = self._extract_amenities(place_details.get('types', []))
            
            return {
                'name': name,
                'type': hotel_type,
                'rating': round(rating, 1),
                'price_level': price_level,
                'price_range': price_range,
                'vicinity': vicinity,
                'address': place_details.get('formatted_address', vicinity),
                'amenities': amenities,
                'rating_count': rating_count,
                'phone': place_details.get('formatted_phone_number'),
                'website': place_details.get('website'),
                'place_id': place_details.get('place_id'),
                'source': 'google_places',
                'coordinates': self._extract_coordinates(place_details.get('geometry', {})),
                'photos': self._extract_photo_references(place_details.get('photos', [])),
                'opening_hours': self._extract_opening_hours(place_details.get('opening_hours', {}))
            }
            
        except Exception as e:
            logger.error(f"Error formatting hotel data: {e}")
            return None
    
    def _format_restaurant_data(self, place_details: Dict, city_name: str) -> Optional[Dict]:
        """Format Google Places data into restaurant format."""
        try:
            name = place_details.get('name', 'Unknown Restaurant')
            rating = place_details.get('rating', 0)
            rating_count = place_details.get('user_ratings_total', 0)
            price_level = place_details.get('price_level', 2)
            vicinity = place_details.get('vicinity', city_name)
            
            # Skip if rating is too low
            if rating < 3.5 and rating_count < 20:
                return None
            
            # Extract cuisine types from place types
            cuisine_types = self._extract_cuisine_types(place_details.get('types', []))
            
            return {
                'name': name,
                'rating': round(rating, 1),
                'price_level': price_level,
                'vicinity': vicinity,
                'address': place_details.get('formatted_address', vicinity),
                'cuisine_types': cuisine_types,
                'rating_count': rating_count,
                'phone': place_details.get('formatted_phone_number'),
                'website': place_details.get('website'),
                'place_id': place_details.get('place_id'),
                'source': 'google_places',
                'coordinates': self._extract_coordinates(place_details.get('geometry', {})),
                'photos': self._extract_photo_references(place_details.get('photos', [])),
                'opening_hours': self._extract_opening_hours(place_details.get('opening_hours', {}))
            }
            
        except Exception as e:
            logger.error(f"Error formatting restaurant data: {e}")
            return None
    
    def _determine_hotel_type(self, name: str, price_level: int) -> str:
        """Determine hotel type based on name and price level."""
        name_lower = name.lower()
        
        if any(word in name_lower for word in ['hostel', 'backpack']):
            return 'hostel'
        elif any(word in name_lower for word in ['boutique', 'design', 'luxury']) or price_level >= 4:
            return 'boutique'
        elif any(word in name_lower for word in ['resort', 'spa']):
            return 'resort'
        elif any(word in name_lower for word in ['apartment', 'studio', 'suite']):
            return 'apartment'
        elif any(word in name_lower for word in ['b&b', 'bed and breakfast', 'guesthouse']):
            return 'bed_and_breakfast'
        else:
            return 'hotel'
    
    def _estimate_price_range(self, price_level: int, city_name: str) -> str:
        """Estimate price range based on Google's price level and city."""
        # City multiplier for major European cities
        major_cities = ['paris', 'london', 'rome', 'barcelona', 'amsterdam', 'vienna']
        multiplier = 1.3 if city_name.lower() in major_cities else 1.0
        
        base_ranges = {
            1: (30, 60),    # Budget
            2: (60, 120),   # Mid-range
            3: (120, 200),  # Expensive
            4: (200, 400)   # Very expensive
        }
        
        min_price, max_price = base_ranges.get(price_level, (60, 120))
        min_price = int(min_price * multiplier)
        max_price = int(max_price * multiplier)
        
        return f"€{min_price}-{max_price}/night"
    
    def _extract_amenities(self, place_types: List[str]) -> List[str]:
        """Extract likely amenities from place types."""
        amenities = ['WiFi']  # Assume all hotels have WiFi
        
        type_to_amenities = {
            'spa': ['Spa', 'Wellness Center'],
            'gym': ['Fitness Center'],
            'restaurant': ['Restaurant'],
            'bar': ['Bar'],
            'parking': ['Parking'],
            'airport_shuttle': ['Airport Shuttle'],
            'laundry': ['Laundry Service']
        }
        
        for place_type in place_types:
            if place_type in type_to_amenities:
                amenities.extend(type_to_amenities[place_type])
        
        # Add common amenities based on hotel characteristics
        amenities.extend(['Reception', '24/7 Front Desk'])
        
        return list(set(amenities))  # Remove duplicates
    
    def _extract_cuisine_types(self, place_types: List[str]) -> List[str]:
        """Extract cuisine types from Google Places types."""
        cuisine_mapping = {
            'restaurant': ['International'],
            'meal_takeaway': ['Takeaway'],
            'cafe': ['Cafe', 'Coffee'],
            'bakery': ['Bakery', 'Pastries'],
            'bar': ['Bar', 'Drinks'],
            'night_club': ['Nightlife'],
            'italian_restaurant': ['Italian'],
            'french_restaurant': ['French'],
            'chinese_restaurant': ['Chinese'],
            'japanese_restaurant': ['Japanese'],
            'indian_restaurant': ['Indian'],
            'mexican_restaurant': ['Mexican'],
            'pizza_restaurant': ['Pizza'],
            'seafood_restaurant': ['Seafood'],
            'vegetarian_restaurant': ['Vegetarian'],
            'fast_food_restaurant': ['Fast Food']
        }
        
        cuisines = []
        for place_type in place_types:
            if place_type in cuisine_mapping:
                cuisines.extend(cuisine_mapping[place_type])
        
        return list(set(cuisines)) if cuisines else ['International']
    
    def _extract_coordinates(self, geometry: Dict) -> Optional[Tuple[float, float]]:
        """Extract coordinates from geometry data."""
        try:
            location = geometry.get('location', {})
            lat = location.get('lat')
            lng = location.get('lng')
            if lat and lng:
                return (lat, lng)
        except:
            pass
        return None
    
    def _extract_photo_references(self, photos: List[Dict]) -> List[str]:
        """Extract photo references for later use."""
        return [photo.get('photo_reference') for photo in photos[:3] if photo.get('photo_reference')]
    
    def _extract_opening_hours(self, opening_hours: Dict) -> Optional[Dict]:
        """Extract opening hours information."""
        if opening_hours.get('weekday_text'):
            return {
                'weekday_text': opening_hours['weekday_text'],
                'open_now': opening_hours.get('open_now', False)
            }
        return None
    
    def _get_fallback_hotels(self, city: City) -> List[Dict]:
        """Generate minimal fallback hotels when API is unavailable."""
        logger.warning(f"Using fallback hotel data for {city.name}")
        return [
            {
                'name': f'Hotels in {city.name}',
                'type': 'hotel',
                'rating': 'N/A',
                'price_level': 'N/A',
                'price_range': 'Check booking sites',
                'vicinity': f'{city.name} city center',
                'amenities': ['WiFi'],
                'source': 'fallback',
                'note': 'Real hotel data requires Google Places API key'
            }
        ]
    
    def _get_fallback_restaurants(self, city: City) -> List[Dict]:
        """Generate minimal fallback restaurants when API is unavailable."""
        logger.warning(f"Using fallback restaurant data for {city.name}")
        return [
            {
                'name': f'Restaurants in {city.name}',
                'rating': 'N/A',
                'price_level': 'N/A',
                'vicinity': f'{city.name} city center',
                'cuisine_types': ['Local cuisine'],
                'source': 'fallback',
                'note': 'Real restaurant data requires Google Places API key'
            }
        ]
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
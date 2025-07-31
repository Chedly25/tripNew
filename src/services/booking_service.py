"""
Booking.com API integration for hotel recommendations.
Alternative: RapidAPI Booking.com or Hotels.com APIs
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import structlog
from ..core.models import Coordinates

logger = structlog.get_logger(__name__)


class BookingService:
    """Service for finding hotels using Booking.com API."""
    
    def __init__(self):
        # Using RapidAPI's Booking.com endpoint (free tier available)
        self.api_key = os.getenv('RAPIDAPI_KEY')  # RapidAPI key for Booking.com
        self.base_url = "https://booking-com.p.rapidapi.com/v1"
        self.session = None
        
        if not self.api_key:
            logger.warning("Booking API key not configured - using fallback data")
    
    async def find_hotels(self, coordinates: Coordinates, city_name: str, 
                         checkin_date: str = None, checkout_date: str = None, 
                         limit: int = 10) -> List[Dict]:
        """Find hotels near the given coordinates."""
        if not self.api_key:
            return self._get_fallback_hotels(city_name, limit)
        
        # Default dates if not provided
        if not checkin_date:
            checkin = datetime.now() + timedelta(days=30)
            checkin_date = checkin.strftime('%Y-%m-%d')
        
        if not checkout_date:
            checkout = datetime.now() + timedelta(days=31)
            checkout_date = checkout.strftime('%Y-%m-%d')
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # First, get destination ID
            dest_id = await self._get_destination_id(city_name)
            if not dest_id:
                return self._get_fallback_hotels(city_name, limit)
            
            # Then search for hotels
            url = f"{self.base_url}/hotels/search"
            params = {
                'dest_id': dest_id,
                'order_by': 'review_score',
                'adults_number': 2,
                'checkin_date': checkin_date,
                'checkout_date': checkout_date,
                'filter_by_currency': 'EUR',
                'locale': 'en-gb',
                'room_number': 1,
                'units': 'metric',
                'include_adjacency': 'true'
            }
            
            headers = {
                'X-RapidAPI-Key': self.api_key,
                'X-RapidAPI-Host': 'booking-com.p.rapidapi.com'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_hotels(data.get('result', [])[:limit])
                else:
                    logger.error(f"Booking API error: {response.status}")
                    return self._get_fallback_hotels(city_name, limit)
                    
        except Exception as e:
            logger.error(f"Hotel search error: {e}")
            return self._get_fallback_hotels(city_name, limit)
    
    async def _get_destination_id(self, city_name: str) -> Optional[str]:
        """Get destination ID for a city."""
        try:
            url = f"{self.base_url}/hotels/locations"
            params = {
                'name': city_name,
                'locale': 'en-gb'
            }
            
            headers = {
                'X-RapidAPI-Key': self.api_key,
                'X-RapidAPI-Host': 'booking-com.p.rapidapi.com'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('result', [])
                    if results:
                        return results[0].get('dest_id')
                return None
                
        except Exception as e:
            logger.error(f"Destination ID lookup error: {e}")
            return None
    
    def _format_hotels(self, results: List[Dict]) -> List[Dict]:
        """Format Booking.com hotel data."""
        formatted = []
        for hotel in results:
            try:
                formatted.append({
                    'name': hotel.get('hotel_name', 'Unknown Hotel'),
                    'rating': hotel.get('review_score', 0) / 2,  # Convert from 10-point to 5-point scale
                    'review_count': hotel.get('review_nr', 0),
                    'price_per_night': hotel.get('min_total_price', 0),
                    'currency': hotel.get('currencycode', 'EUR'),
                    'address': hotel.get('address', ''),
                    'distance_to_center': hotel.get('distance', 0),
                    'amenities': self._extract_amenities(hotel.get('hotel_facilities', [])),
                    'photo': hotel.get('main_photo_url', ''),
                    'url': hotel.get('url', ''),
                    'stars': hotel.get('class', 0),
                    'description': hotel.get('hotel_description', '')[:200] + '...' if hotel.get('hotel_description') else ''
                })
            except Exception as e:
                logger.error(f"Error formatting hotel: {e}")
                continue
        return formatted
    
    def _extract_amenities(self, facilities: List[Dict]) -> List[str]:
        """Extract key amenities from hotel facilities."""
        if not facilities:
            return ['WiFi', 'Parking']
        
        amenity_names = []
        for facility in facilities[:5]:  # Top 5 amenities
            name = facility.get('name', '')
            if name:
                amenity_names.append(name)
        
        return amenity_names or ['WiFi', 'Parking']
    
    def _get_fallback_hotels(self, city_name: str, limit: int) -> List[Dict]:
        """Fallback hotel data when API is unavailable."""
        hotels = [
            {
                'name': f'Grand Hotel {city_name}',
                'rating': 4.5,
                'review_count': 1250,
                'price_per_night': 150,
                'currency': 'EUR',
                'address': f'City Center, {city_name}',
                'distance_to_center': 0.5,
                'amenities': ['WiFi', 'Parking', 'Restaurant', 'Spa', 'Room Service'],
                'photo': '',
                'url': '',
                'stars': 4,
                'description': f'Luxury hotel in the heart of {city_name} with exceptional service and amenities.'
            },
            {
                'name': f'Boutique Hotel {city_name}',
                'rating': 4.3,
                'review_count': 890,
                'price_per_night': 120,
                'currency': 'EUR',
                'address': f'Historic District, {city_name}',
                'distance_to_center': 0.8,
                'amenities': ['WiFi', 'Breakfast', 'Concierge', 'Bar'],
                'photo': '',
                'url': '',
                'stars': 4,
                'description': f'Charming boutique hotel with unique character in historic {city_name}.'
            },
            {
                'name': f'Hotel Central {city_name}',
                'rating': 4.1,
                'review_count': 650,
                'price_per_night': 90,
                'currency': 'EUR',
                'address': f'Main Street, {city_name}',
                'distance_to_center': 0.3,
                'amenities': ['WiFi', 'Parking', 'Restaurant'],
                'photo': '',
                'url': '',
                'stars': 3,
                'description': f'Comfortable and convenient hotel perfectly located in {city_name}.'
            },
            {
                'name': f'Budget Inn {city_name}',
                'rating': 3.8,
                'review_count': 420,
                'price_per_night': 65,
                'currency': 'EUR',
                'address': f'Near Train Station, {city_name}',
                'distance_to_center': 1.2,
                'amenities': ['WiFi', 'Breakfast'],
                'photo': '',
                'url': '',
                'stars': 3,
                'description': f'Clean and affordable accommodation with easy transport links in {city_name}.'
            }
        ]
        return hotels[:limit]
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
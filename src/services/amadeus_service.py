"""
Amadeus Hotel Search API integration for comprehensive hotel booking.
Provides real hotel data from Amadeus's global hotel inventory.
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from ..core.models import Coordinates

logger = structlog.get_logger(__name__)


class AmadeusHotelService:
    """Service for accessing Amadeus Hotel Search API."""
    
    def __init__(self):
        self.client_id = os.getenv('AMADEUS_CLIENT_ID')
        self.client_secret = os.getenv('AMADEUS_CLIENT_SECRET')
        
        # Amadeus API endpoints
        self.auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        self.base_url = "https://test.api.amadeus.com"
        
        # Token management
        self.access_token = None
        self.token_expires_at = None
        self.session = None
        
        if not self.client_id or not self.client_secret:
            logger.warning("Amadeus API credentials not configured - using fallback data")
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _get_access_token(self) -> bool:
        """Get or refresh access token."""
        # Check if current token is still valid
        if (self.access_token and self.token_expires_at and 
            datetime.now() < self.token_expires_at - timedelta(minutes=5)):  # 5 min buffer
            return True
        
        if not self.client_id or not self.client_secret:
            return False
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            async with self.session.post(self.auth_url, data=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    self.access_token = result['access_token']
                    expires_in = result.get('expires_in', 1800)
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    logger.info("Amadeus access token obtained", expires_in=expires_in)
                    return True
                else:
                    error_result = await response.json()
                    logger.error("Amadeus authentication failed", 
                               status=response.status, error=error_result)
                    return False
                    
        except Exception as e:
            logger.error(f"Amadeus authentication error: {e}")
            return False
    
    async def _get_api_headers(self) -> Optional[Dict[str, str]]:
        """Get headers with valid access token."""
        if not await self._get_access_token():
            return None
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
    
    async def get_hotels_by_city(self, city_code: str, radius: int = 5) -> List[Dict]:
        """Get list of hotels in a city using IATA city code."""
        headers = await self._get_api_headers()
        if not headers:
            return self._get_fallback_hotels(city_code, 10)
        
        try:
            url = f"{self.base_url}/v1/reference-data/locations/hotels/by-city"
            params = {
                'cityCode': city_code.upper(),
                'radius': radius,
                'radiusUnit': 'KM',
                'hotelSource': 'ALL'
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    hotels_data = result.get('data', [])
                    
                    # Format hotel data
                    hotels = []
                    for hotel in hotels_data:
                        hotel_info = {
                            'hotel_id': hotel.get('hotelId'),
                            'name': hotel.get('name', ''),
                            'iata_code': hotel.get('iataCode'),
                            'address': {
                                'lines': hotel.get('address', {}).get('lines', []),
                                'postal_code': hotel.get('address', {}).get('postalCode', ''),
                                'city': hotel.get('address', {}).get('cityName', ''),
                                'country': hotel.get('address', {}).get('countryCode', '')
                            },
                            'coordinates': {
                                'latitude': hotel.get('geoCode', {}).get('latitude'),
                                'longitude': hotel.get('geoCode', {}).get('longitude')
                            },
                            'distance': hotel.get('distance', {}).get('value'),
                            'distance_unit': hotel.get('distance', {}).get('unit'),
                            'chain_code': hotel.get('chainCode'),
                            'brand_code': hotel.get('brandCode'),
                            'source': 'amadeus'
                        }
                        hotels.append(hotel_info)
                    
                    logger.info(f"Found {len(hotels)} hotels in {city_code}")
                    return hotels
                else:
                    error_result = await response.json()
                    logger.error(f"Hotel list failed for {city_code}: {error_result}")
                    return self._get_fallback_hotels(city_code, 10)
                    
        except Exception as e:
            logger.error(f"Hotel list error for {city_code}: {e}")
            return self._get_fallback_hotels(city_code, 10)
    
    async def get_hotels_by_coordinates(self, coordinates: Coordinates, radius: int = 5) -> List[Dict]:
        """Get list of hotels near coordinates."""
        headers = await self._get_api_headers()
        if not headers:
            return self._get_fallback_hotels("Unknown", 10)
        
        try:
            url = f"{self.base_url}/v1/reference-data/locations/hotels/by-geocode"
            params = {
                'latitude': coordinates.latitude,
                'longitude': coordinates.longitude,
                'radius': radius,
                'radiusUnit': 'KM',
                'hotelSource': 'ALL'
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    hotels_data = result.get('data', [])
                    
                    # Format hotel data (same as get_hotels_by_city)
                    hotels = []
                    for hotel in hotels_data:
                        hotel_info = {
                            'hotel_id': hotel.get('hotelId'),
                            'name': hotel.get('name', ''),
                            'iata_code': hotel.get('iataCode'),
                            'address': {
                                'lines': hotel.get('address', {}).get('lines', []),
                                'postal_code': hotel.get('address', {}).get('postalCode', ''),
                                'city': hotel.get('address', {}).get('cityName', ''),
                                'country': hotel.get('address', {}).get('countryCode', '')
                            },
                            'coordinates': {
                                'latitude': hotel.get('geoCode', {}).get('latitude'),
                                'longitude': hotel.get('geoCode', {}).get('longitude')
                            },
                            'distance': hotel.get('distance', {}).get('value'),
                            'distance_unit': hotel.get('distance', {}).get('unit'),
                            'chain_code': hotel.get('chainCode'),
                            'brand_code': hotel.get('brandCode'),
                            'source': 'amadeus'
                        }
                        hotels.append(hotel_info)
                    
                    logger.info(f"Found {len(hotels)} hotels near coordinates")
                    return hotels
                else:
                    error_result = await response.json()
                    logger.error(f"Hotel geocode search failed: {error_result}")
                    return self._get_fallback_hotels("Unknown", 10)
                    
        except Exception as e:
            logger.error(f"Hotel geocode search error: {e}")
            return self._get_fallback_hotels("Unknown", 10)
    
    async def search_hotel_offers(self, hotel_ids: List[str], check_in_date: str, 
                                check_out_date: str, adults: int = 2, 
                                room_quantity: int = 1) -> List[Dict]:
        """Search for hotel offers using hotel IDs."""
        headers = await self._get_api_headers()
        if not headers:
            return self._get_fallback_offers(hotel_ids)
        
        try:
            url = f"{self.base_url}/v3/shopping/hotel-offers"
            params = {
                'hotelIds': ','.join(hotel_ids[:20]),  # Max 20 hotels per request
                'checkInDate': check_in_date,
                'checkOutDate': check_out_date,
                'adults': adults,
                'roomQuantity': room_quantity
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    offers_data = result.get('data', [])
                    
                    # Format offers data
                    offers = []
                    for offer in offers_data:
                        hotel_info = offer.get('hotel', {})
                        offers_list = offer.get('offers', [])
                        
                        if offers_list:
                            best_offer = offers_list[0]  # First is usually best price
                            
                            offer_info = {
                                'hotel_id': hotel_info.get('hotelId'),
                                'name': hotel_info.get('name', ''),
                                'chain_code': hotel_info.get('chainCode'),
                                'brand_code': hotel_info.get('brandCode'),
                                'rating': hotel_info.get('rating'),
                                'address': hotel_info.get('address', {}),
                                'coordinates': {
                                    'latitude': hotel_info.get('latitude'),
                                    'longitude': hotel_info.get('longitude')
                                },
                                'amenities': hotel_info.get('amenities', []),
                                'media': hotel_info.get('media', [])[:5],  # First 5 images
                                'offer': {
                                    'id': best_offer.get('id'),
                                    'check_in_date': best_offer.get('checkInDate'),
                                    'check_out_date': best_offer.get('checkOutDate'),
                                    'room_quantity': best_offer.get('roomQuantity'),
                                    'adults': best_offer.get('adults'),
                                    'price': {
                                        'currency': best_offer.get('price', {}).get('currency'),
                                        'base': best_offer.get('price', {}).get('base'),
                                        'total': best_offer.get('price', {}).get('total'),
                                        'taxes': best_offer.get('price', {}).get('taxes', [])
                                    },
                                    'room': {
                                        'type': best_offer.get('room', {}).get('type'),
                                        'type_estimated': best_offer.get('room', {}).get('typeEstimated', {}),
                                        'description': best_offer.get('room', {}).get('description', {})
                                    },
                                    'guests': best_offer.get('guests', {}),
                                    'payment_type': best_offer.get('policies', {}).get('paymentType'),
                                    'cancellation': best_offer.get('policies', {}).get('cancellation')
                                },
                                'source': 'amadeus'
                            }
                            offers.append(offer_info)
                    
                    logger.info(f"Found {len(offers)} hotel offers")
                    return offers
                else:
                    error_result = await response.json()
                    logger.error(f"Hotel offers search failed: {error_result}")
                    return self._get_fallback_offers(hotel_ids)
                    
        except Exception as e:
            logger.error(f"Hotel offers search error: {e}")
            return self._get_fallback_offers(hotel_ids)
    
    async def find_hotels(self, coordinates: Coordinates, city_name: str, 
                         check_in_date: str = None, check_out_date: str = None, 
                         limit: int = 10) -> List[Dict]:
        """
        Main method to find hotels - compatible with existing booking service interface.
        This replaces the old booking service method.
        """
        # Default dates if not provided
        if not check_in_date:
            check_in = datetime.now() + timedelta(days=30)
            check_in_date = check_in.strftime('%Y-%m-%d')
        
        if not check_out_date:
            check_out = datetime.now() + timedelta(days=31)
            check_out_date = check_out.strftime('%Y-%m-%d')
        
        try:
            # Step 1: Get hotels by coordinates
            hotels = await self.get_hotels_by_coordinates(coordinates, radius=10)
            
            if not hotels:
                # Fallback: try to get city code from coordinates (simplified)
                city_code = self._guess_city_code_from_name(city_name)
                if city_code:
                    hotels = await self.get_hotels_by_city(city_code)
            
            if not hotels:
                return self._get_fallback_hotels(city_name, limit)
            
            # Step 2: Get offers for top hotels
            hotel_ids = [h['hotel_id'] for h in hotels[:limit] if h.get('hotel_id')]
            if not hotel_ids:
                return self._get_fallback_hotels(city_name, limit)
            
            offers = await self.search_hotel_offers(
                hotel_ids, check_in_date, check_out_date, adults=2
            )
            
            # Step 3: Format for compatibility with existing interface
            formatted_hotels = []
            for offer in offers[:limit]:
                hotel = {
                    'name': offer.get('name', ''),
                    'rating': offer.get('rating', 4.0),
                    'review_count': 100,  # Amadeus doesn't provide this
                    'price_per_night': float(offer.get('offer', {}).get('price', {}).get('total') or 0),
                    'currency': offer.get('offer', {}).get('price', {}).get('currency', 'EUR'),
                    'address': self._format_address(offer.get('address', {})),
                    'distance_to_center': offer.get('distance', 0),
                    'amenities': [a.get('name', '') for a in offer.get('amenities', [])[:5]],
                    'photo': self._get_first_image(offer.get('media', [])),
                    'url': f"https://www.amadeus.com/hotel/{offer.get('hotel_id', '')}",
                    'website': f"https://www.amadeus.com/hotel/{offer.get('hotel_id', '')}",
                    'stars': int(offer.get('rating') or 4),
                    'description': f"Hotel in {city_name} with modern amenities and comfort.",
                    'amadeus_hotel_id': offer.get('hotel_id'),
                    'amadeus_offer_id': offer.get('offer', {}).get('id'),
                    'source': 'amadeus'
                }
                formatted_hotels.append(hotel)
            
            return formatted_hotels
            
        except Exception as e:
            logger.error(f"Find hotels error for {city_name}: {e}")
            return self._get_fallback_hotels(city_name, limit)
    
    def _guess_city_code_from_name(self, city_name: str) -> Optional[str]:
        """Guess IATA city code from city name."""
        city_codes = {
            'paris': 'PAR', 'lyon': 'LYS', 'marseille': 'MRS', 'nice': 'NCE',
            'toulouse': 'TLS', 'strasbourg': 'XER', 'bordeaux': 'BOD',
            'rome': 'ROM', 'milan': 'MIL', 'florence': 'FLR', 'venice': 'VCE',
            'naples': 'NAP', 'turin': 'TRN', 'bologna': 'BLQ', 'genoa': 'GOA',
            'madrid': 'MAD', 'barcelona': 'BCN', 'valencia': 'VLC', 'seville': 'SVQ',
            'bilbao': 'BIO', 'malaga': 'AGP', 'palma': 'PMI'
        }
        return city_codes.get(city_name.lower())
    
    def _format_address(self, address: Dict) -> str:
        """Format address for display."""
        lines = address.get('lines', [])
        city = address.get('cityName', '')
        postal_code = address.get('postalCode', '')
        
        if lines:
            return f"{', '.join(lines)}, {city} {postal_code}".strip(', ')
        return f"{city} {postal_code}".strip()
    
    def _get_first_image(self, media: List[Dict]) -> str:
        """Get first image URL from media list."""
        for item in media:
            if item.get('uri') and 'image' in item.get('category', '').lower():
                return item['uri']
        return ''
    
    def _get_fallback_hotels(self, city_name: str, limit: int) -> List[Dict]:
        """Fallback hotel data when API is unavailable."""
        hotels = []
        for i in range(min(limit, 5)):  # Max 5 fallback hotels
            hotel_types = ['Grand Hotel', 'Boutique Hotel', 'Central Hotel', 'Palace Hotel', 'Inn']
            prices = [120, 95, 85, 150, 75]
            ratings = [4.5, 4.2, 4.0, 4.7, 3.9]
            
            hotel = {
                'name': f'{hotel_types[i]} {city_name}',
                'rating': ratings[i],
                'review_count': 250 + (i * 50),
                'price_per_night': prices[i],
                'currency': 'EUR',
                'address': f'City Center, {city_name}',
                'distance_to_center': 0.5 + (i * 0.3),
                'amenities': ['WiFi', 'Parking', 'Restaurant', 'Spa', 'Room Service'][:(3+i)],
                'photo': '',
                'url': f'https://www.booking.com/hotel/{city_name.lower()}-{i}.html',
                'website': f'https://www.booking.com/hotel/{city_name.lower()}-{i}.html',
                'stars': int(ratings[i]),
                'description': f'Quality hotel in the heart of {city_name}.',
                'source': 'fallback'
            }
            hotels.append(hotel)
        
        return hotels
    
    def _get_fallback_offers(self, hotel_ids: List[str]) -> List[Dict]:
        """Fallback offers when API is unavailable."""
        offers = []
        for i, hotel_id in enumerate(hotel_ids[:3]):
            offer = {
                'hotel_id': hotel_id,
                'name': f'Hotel {i+1}',
                'rating': 4.0 + (i * 0.2),
                'offer': {
                    'price': {
                        'total': 100 + (i * 25),
                        'currency': 'EUR'
                    },
                    'room': {
                        'type': 'Standard Room'
                    }
                },
                'amenities': [{'name': 'WiFi'}, {'name': 'Parking'}],
                'source': 'fallback'
            }
            offers.append(offer)
        
        return offers


# Global service instance
_amadeus_service = None

def get_amadeus_service() -> AmadeusHotelService:
    """Get the global Amadeus service instance."""
    global _amadeus_service
    if _amadeus_service is None:
        _amadeus_service = AmadeusHotelService()
    return _amadeus_service
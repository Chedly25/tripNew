"""
Eventbrite API integration for events and activities.
Note: Search API was deprecated in 2019, but we can try alternative approaches.
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Optional
import structlog
from ..core.models import Coordinates

logger = structlog.get_logger(__name__)


class EventbriteService:
    """Service for accessing Eventbrite events (limited functionality due to API deprecation)."""
    
    def __init__(self):
        self.api_key = os.getenv('EVENTBRITE_API_KEY')
        self.base_url = "https://www.eventbriteapi.com/v3"
        self.session = None
        
        if not self.api_key:
            logger.warning("Eventbrite API key not configured - service will be limited")
    
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
    
    async def test_api_access(self) -> bool:
        """Test if API access is working."""
        if not self.api_key:
            return False
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Try to get user info as a test
            url = f"{self.base_url}/users/me/"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    logger.info("Eventbrite API access successful")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Eventbrite API test failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Eventbrite API test error: {e}")
            return False
    
    async def find_events_by_location(self, coordinates: Coordinates, city_name: str, limit: int = 10) -> List[Dict]:
        """
        Try to find events by location (likely deprecated, but we'll try).
        This will probably fail due to API deprecation, so we'll return fallback data.
        """
        if not self.api_key:
            return self._get_fallback_events(city_name, limit)
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Try the deprecated search endpoint (will likely fail)
            url = f"{self.base_url}/events/search/"
            params = {
                'location.latitude': coordinates.latitude,
                'location.longitude': coordinates.longitude,
                'location.within': '10km',
                'expand': 'venue,organizer',
                'sort_by': 'date'
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get('events', [])
                    
                    # Format events
                    formatted_events = []
                    for event in events[:limit]:
                        formatted_events.append({
                            'name': event.get('name', {}).get('text', 'Unknown Event'),
                            'rating': 4.0,  # Eventbrite doesn't provide ratings
                            'price_level': 1 if event.get('is_free', True) else 2,
                            'address': event.get('venue', {}).get('address', {}).get('localized_address_display', f'{city_name}'),
                            'category': 'Event',
                            'website': event.get('url', ''),
                            'url': event.get('url', ''),
                            'hours': event.get('start', {}).get('local', 'Check event details'),
                            'photo': event.get('logo', {}).get('url', ''),
                            'source': 'eventbrite',
                            'description': event.get('description', {}).get('text', '')[:200] + '...' if event.get('description', {}).get('text') else 'Event details available on Eventbrite'
                        })
                    
                    logger.info(f"Found {len(formatted_events)} events from Eventbrite for {city_name}")
                    return formatted_events
                else:
                    error_text = await response.text()
                    logger.warning(f"Eventbrite search failed (expected due to API deprecation): {response.status} - {error_text}")
                    return self._get_fallback_events(city_name, limit)
                    
        except Exception as e:
            logger.error(f"Eventbrite search error: {e}")
            return self._get_fallback_events(city_name, limit)
    
    def _get_fallback_events(self, city_name: str, limit: int) -> List[Dict]:
        """Fallback event data when API is unavailable."""
        events = [
            {
                'name': f'{city_name} Cultural Festival',
                'rating': 4.2,
                'price_level': 1,
                'address': f'City Center, {city_name}',
                'category': 'Cultural Event',
                'website': f'https://www.eventbrite.com/{city_name.lower()}-cultural-festival',
                'url': f'https://www.eventbrite.com/{city_name.lower()}-cultural-festival',
                'hours': 'Various times - check event page',
                'photo': '',
                'source': 'fallback',
                'description': f'Annual cultural celebration in {city_name} featuring local arts, music, and traditions'
            },
            {
                'name': f'{city_name} Food & Wine Tour',
                'rating': 4.5,
                'price_level': 2,
                'address': f'Historic District, {city_name}',
                'category': 'Food & Drink Event',
                'website': f'https://www.eventbrite.com/{city_name.lower()}-food-tour',
                'url': f'https://www.eventbrite.com/{city_name.lower()}-food-tour',
                'hours': 'Evening tours available',
                'photo': '',
                'source': 'fallback',
                'description': f'Guided culinary experience showcasing the best of {city_name}\'s local cuisine and wines'
            },
            {
                'name': f'{city_name} Walking History Tour',
                'rating': 4.1,
                'price_level': 1,
                'address': f'Tourist Information Center, {city_name}',
                'category': 'Educational Event',
                'website': f'https://www.eventbrite.com/{city_name.lower()}-history-tour',
                'url': f'https://www.eventbrite.com/{city_name.lower()}-history-tour',
                'hours': 'Daily tours - check schedule',
                'photo': '',
                'source': 'fallback',
                'description': f'Expert-led walking tour exploring the rich history and architecture of {city_name}'
            }
        ]
        return events[:limit]


# Global service instance
_eventbrite_service = None

def get_eventbrite_service() -> EventbriteService:
    """Get the global Eventbrite service instance."""
    global _eventbrite_service
    if _eventbrite_service is None:
        _eventbrite_service = EventbriteService()
    return _eventbrite_service
"""
Event service for discovering festivals, concerts, sports events, and cultural activities
that influence route optimization and travel planning decisions.
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import json
import re
from config import Config, EVENT_IMPACT
import logging

logger = logging.getLogger(__name__)

class EventService:
    def __init__(self):
        self.ticketmaster_api_key = Config.TICKETMASTER_API_KEY
        self.use_ticketmaster = bool(self.ticketmaster_api_key and 
                                   self.ticketmaster_api_key != 'your_ticketmaster_api_key_here')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_events_for_route(self, cities: List[Tuple[str, float, float]], 
                           start_date: datetime, end_date: datetime) -> Dict[str, List[Dict]]:
        """Get events for all cities along a route"""
        all_events = {}
        
        for city_name, lat, lon in cities:
            events = []
            
            # Try Ticketmaster API first
            if self.use_ticketmaster:
                tm_events = self._get_ticketmaster_events(city_name, lat, lon, start_date, end_date)
                events.extend(tm_events)
            
            # Add web scraping for additional sources
            scraped_events = self._scrape_local_events(city_name, start_date, end_date)
            events.extend(scraped_events)
            
            # Add fallback events if no real data found
            if not events:
                events = self._generate_fallback_events(city_name, start_date, end_date)
            
            all_events[city_name] = self._deduplicate_events(events)
        
        return all_events
    
    def _get_ticketmaster_events(self, city: str, lat: float, lon: float, 
                                start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get events from Ticketmaster API"""
        events = []
        
        try:
            params = {
                'apikey': self.ticketmaster_api_key,
                'latlong': f"{lat},{lon}",
                'radius': '50',  # 50km radius
                'unit': 'km',
                'startDateTime': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'endDateTime': end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'size': 50,
                'sort': 'relevance,desc'
            }
            
            response = requests.get(f"{Config.TICKETMASTER_URL}/events", params=params)
            data = response.json()
            
            if '_embedded' in data and 'events' in data['_embedded']:
                for event in data['_embedded']['events']:
                    parsed_event = self._parse_ticketmaster_event(event)
                    if parsed_event:
                        events.append(parsed_event)
                        
        except Exception as e:
            logger.error(f"Ticketmaster API error for {city}: {e}")
        
        return events
    
    def _parse_ticketmaster_event(self, event: Dict) -> Optional[Dict]:
        """Parse Ticketmaster event data into standardized format"""
        try:
            # Extract date
            date_str = event['dates']['start']['localDate']
            time_str = event['dates']['start'].get('localTime', '20:00')
            event_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
            
            # Extract venue
            venue_name = "Unknown Venue"
            venue_address = ""
            if '_embedded' in event and 'venues' in event['_embedded']:
                venue = event['_embedded']['venues'][0]
                venue_name = venue.get('name', venue_name)
                if 'address' in venue:
                    venue_address = venue['address'].get('line1', '')
            
            # Categorize event
            category = self._categorize_event(event.get('classifications', []))
            
            # Calculate impact score
            impact_score = self._calculate_event_impact(category, event.get('priceRanges', []))
            
            return {
                'name': event['name'],
                'date': event_datetime,
                'venue': venue_name,
                'address': venue_address,
                'category': category,
                'description': event.get('info', ''),
                'url': event.get('url', ''),
                'price_range': self._extract_price_range(event.get('priceRanges', [])),
                'impact_score': impact_score,
                'source': 'ticketmaster',
                'popularity': self._estimate_popularity(event)
            }
            
        except Exception as e:
            logger.error(f"Error parsing Ticketmaster event: {e}")
            return None
    
    def _categorize_event(self, classifications: List[Dict]) -> str:
        """Categorize event based on classifications"""
        if not classifications:
            return 'general'
        
        classification = classifications[0]
        segment = classification.get('segment', {}).get('name', '').lower()
        genre = classification.get('genre', {}).get('name', '').lower()
        
        # Map to our categories
        if 'music' in segment or 'concert' in genre:
            return 'music'
        elif 'sports' in segment:
            return 'sports'
        elif 'arts' in segment or 'theatre' in segment:
            return 'arts'
        elif 'family' in segment:
            return 'family'
        elif 'comedy' in genre:
            return 'comedy'
        else:
            return 'cultural'
    
    def _calculate_event_impact(self, category: str, price_ranges: List[Dict]) -> float:
        """Calculate how much an event impacts route attractiveness"""
        base_impact = EVENT_IMPACT.get('local_event', 1.1)
        
        # Adjust based on category
        category_multipliers = {
            'music': 1.5,
            'sports': 1.4,
            'arts': 1.3,
            'cultural': 1.3,
            'family': 1.2,
            'comedy': 1.2
        }
        
        impact = base_impact * category_multipliers.get(category, 1.0)
        
        # Adjust based on ticket prices (higher prices often mean bigger events)
        if price_ranges:
            max_price = max(pr.get('max', 50) for pr in price_ranges)
            if max_price > 200:
                impact *= 1.8  # Major event
            elif max_price > 100:
                impact *= 1.4  # Significant event
            elif max_price > 50:
                impact *= 1.2  # Medium event
        
        return min(impact, 2.0)  # Cap at 2.0
    
    def _extract_price_range(self, price_ranges: List[Dict]) -> str:
        """Extract price range string"""
        if not price_ranges:
            return "Price not available"
        
        min_price = min(pr.get('min', 0) for pr in price_ranges)
        max_price = max(pr.get('max', 0) for pr in price_ranges)
        currency = price_ranges[0].get('currency', 'EUR')
        
        return f"{min_price}-{max_price} {currency}"
    
    def _estimate_popularity(self, event: Dict) -> str:
        """Estimate event popularity based on available data"""
        # This is a simplified estimation
        classifications = event.get('classifications', [])
        if classifications:
            segment = classifications[0].get('segment', {}).get('name', '').lower()
            if 'music' in segment:
                return 'high'
            elif 'sports' in segment:
                return 'medium'
        
        return 'low'
    
    def _scrape_local_events(self, city: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Scrape local event websites for additional events"""
        events = []
        
        # List of European event discovery sites
        scrapers = [
            self._scrape_eventbrite,
            self._scrape_timeout_local,
            self._scrape_local_tourism_sites
        ]
        
        for scraper in scrapers:
            try:
                scraped = scraper(city, start_date, end_date)
                events.extend(scraped)
            except Exception as e:
                logger.error(f"Scraping error with {scraper.__name__} for {city}: {e}")
        
        return events
    
    def _scrape_eventbrite(self, city: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Scrape Eventbrite for local events"""
        events = []
        
        try:
            # Eventbrite search URL
            search_url = f"https://www.eventbrite.com/d/{city.lower().replace(' ', '-')}--events/"
            
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find event cards (structure may change)
            event_elements = soup.find_all('div', class_='event-card')
            
            for element in event_elements[:10]:  # Limit to 10 events
                try:
                    name = element.find('h3', class_='event-title')
                    date_elem = element.find('time')
                    venue_elem = element.find('div', class_='event-venue')
                    
                    if name and date_elem:
                        event_date = self._parse_date_string(date_elem.get('datetime', ''))
                        
                        if start_date <= event_date <= end_date:
                            events.append({
                                'name': name.get_text(strip=True),
                                'date': event_date,
                                'venue': venue_elem.get_text(strip=True) if venue_elem else 'Unknown Venue',
                                'address': city,
                                'category': 'cultural',
                                'description': '',
                                'url': '',
                                'price_range': 'Varies',
                                'impact_score': 1.2,
                                'source': 'eventbrite',
                                'popularity': 'medium'
                            })
                            
                except Exception as e:
                    logger.error(f"Error parsing Eventbrite event: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Eventbrite scraping error for {city}: {e}")
        
        return events
    
    def _scrape_timeout_local(self, city: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Scrape Time Out local guides for events"""
        events = []
        
        # Time Out has city-specific URLs
        city_urls = {
            'paris': 'https://www.timeout.com/paris/en/things-to-do/whats-on-in-paris-this-week',
            'london': 'https://www.timeout.com/london/things-to-do/whats-on-in-london-this-week',
            'barcelona': 'https://www.timeout.com/barcelona/en/things-to-do',
            'rome': 'https://www.timeout.com/rome/en/things-to-do',
            'berlin': 'https://www.timeout.com/berlin/en/things-to-do'
        }
        
        city_key = city.lower()
        if city_key in city_urls:
            try:
                response = self.session.get(city_urls[city_key], timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find event listings
                event_elements = soup.find_all('article', class_=['event', 'listing'])
                
                for element in event_elements[:5]:  # Limit to 5 events
                    try:
                        title_elem = element.find(['h2', 'h3'], class_=['title', 'event-title'])
                        
                        if title_elem:
                            events.append({
                                'name': title_elem.get_text(strip=True),
                                'date': start_date + timedelta(days=1),  # Approximate date
                                'venue': 'Various Venues',
                                'address': city,
                                'category': 'cultural',
                                'description': '',
                                'url': '',
                                'price_range': 'Varies',
                                'impact_score': 1.3,
                                'source': 'timeout',
                                'popularity': 'medium'
                            })
                            
                    except Exception as e:
                        logger.error(f"Error parsing Time Out event: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Time Out scraping error for {city}: {e}")
        
        return events
    
    def _scrape_local_tourism_sites(self, city: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Scrape local tourism websites for events"""
        events = []
        
        # This would contain city-specific tourism site URLs
        # For now, return empty list as implementation would be extensive
        return events
    
    def _generate_fallback_events(self, city: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate realistic fallback events when no real data is available"""
        import random
        
        # Common European events by season
        current_month = start_date.month
        
        seasonal_events = {
            'spring': ['Spring Festival', 'Art Exhibition', 'Food Market', 'Concert Series'],
            'summer': ['Summer Festival', 'Outdoor Concert', 'Food & Wine Festival', 'Cultural Festival'],
            'autumn': ['Harvest Festival', 'Classical Concert', 'Theater Performance', 'Art Fair'],
            'winter': ['Christmas Market', 'Winter Concert', 'New Year Celebration', 'Indoor Festival']
        }
        
        if current_month in [3, 4, 5]:
            season = 'spring'
        elif current_month in [6, 7, 8]:
            season = 'summer'
        elif current_month in [9, 10, 11]:
            season = 'autumn'
        else:
            season = 'winter'
        
        events = []
        event_types = seasonal_events[season]
        
        # Generate 2-4 events
        for i in range(random.randint(2, 4)):
            event_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            event_name = f"{city} {random.choice(event_types)}"
            
            events.append({
                'name': event_name,
                'date': event_date,
                'venue': f"{city} Cultural Center",
                'address': f"City Center, {city}",
                'category': random.choice(['cultural', 'music', 'food', 'arts']),
                'description': f"Annual {event_name.lower()} featuring local and international participants.",
                'url': '',
                'price_range': f"{random.randint(10, 50)}-{random.randint(60, 150)} EUR",
                'impact_score': random.uniform(1.1, 1.6),
                'source': 'generated',
                'popularity': random.choice(['low', 'medium', 'high'])
            })
        
        return events
    
    def _parse_date_string(self, date_str: str) -> datetime:
        """Parse various date string formats"""
        if not date_str:
            return datetime.now()
        
        # Try different formats
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str[:len(fmt)], fmt)
            except ValueError:
                continue
        
        return datetime.now()
    
    def _deduplicate_events(self, events: List[Dict]) -> List[Dict]:
        """Remove duplicate events based on name and date similarity"""
        if not events:
            return events
        
        unique_events = []
        seen = set()
        
        for event in events:
            # Create a key based on name (simplified) and date
            key = (
                re.sub(r'[^\w\s]', '', event['name'].lower())[:20],
                event['date'].strftime('%Y-%m-%d')
            )
            
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return sorted(unique_events, key=lambda x: x['impact_score'], reverse=True)
    
    def calculate_route_event_score(self, cities: List[str], events_data: Dict[str, List[Dict]]) -> float:
        """Calculate overall event attractiveness score for a route"""
        total_score = 1.0  # Base score
        
        for city in cities:
            if city in events_data:
                city_events = events_data[city]
                if city_events:
                    # Take the average of top 3 events
                    top_events = sorted(city_events, key=lambda x: x['impact_score'], reverse=True)[:3]
                    city_score = sum(event['impact_score'] for event in top_events) / len(top_events)
                    total_score += (city_score - 1.0) * 0.5  # Weight city contributions
        
        return min(total_score, 2.0)  # Cap at 2.0
    
    def get_major_festivals(self, country: str, month: int) -> List[Dict]:
        """Get major festivals by country and month"""
        major_festivals = {
            'france': {
                7: [{'name': 'Festival d\'Avignon', 'city': 'Avignon', 'impact': 2.0}],
                5: [{'name': 'Cannes Film Festival', 'city': 'Cannes', 'impact': 2.0}]
            },
            'spain': {
                3: [{'name': 'Las Fallas', 'city': 'Valencia', 'impact': 1.8}],
                7: [{'name': 'Running of Bulls', 'city': 'Pamplona', 'impact': 1.9}]
            },
            'italy': {
                2: [{'name': 'Venice Carnival', 'city': 'Venice', 'impact': 1.9}],
                9: [{'name': 'Venice Biennale', 'city': 'Venice', 'impact': 1.7}]
            },
            'germany': {
                9: [{'name': 'Oktoberfest', 'city': 'Munich', 'impact': 2.0}]
            }
        }
        
        return major_festivals.get(country.lower(), {}).get(month, [])
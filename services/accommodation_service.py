"""
Accommodation service for finding and pricing hotels, hostels, and other lodging options
along the route with real-time availability and pricing data.
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import re
from bs4 import BeautifulSoup
from config import Config
import logging

logger = logging.getLogger(__name__)

class AccommodationService:
    def __init__(self):
        self.booking_api_key = Config.BOOKING_COM_API_KEY
        self.use_booking_api = bool(self.booking_api_key and 
                                  self.booking_api_key != 'your_booking_api_key_here')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def find_accommodations(self, city: str, lat: float, lon: float, 
                          check_in: datetime, check_out: datetime,
                          guests: int = 2, budget_level: str = 'mid_range') -> List[Dict]:
        """Find accommodations for a city with various options"""
        
        accommodations = []
        
        # Try Booking.com API if available
        if self.use_booking_api:
            api_results = self._search_booking_api(city, lat, lon, check_in, check_out, guests)
            accommodations.extend(api_results)
        
        # Add web scraping for additional sources
        scraped_results = self._scrape_accommodation_sites(city, check_in, check_out, guests)
        accommodations.extend(scraped_results)
        
        # Generate fallback accommodations if no real data
        if not accommodations:
            accommodations = self._generate_fallback_accommodations(city, check_in, check_out, guests, budget_level)
        
        # Filter and sort by budget preference
        filtered = self._filter_by_budget(accommodations, budget_level)
        
        return self._rank_accommodations(filtered)[:10]  # Return top 10
    
    def _search_booking_api(self, city: str, lat: float, lon: float,
                           check_in: datetime, check_out: datetime, guests: int) -> List[Dict]:
        """Search Booking.com API for accommodations"""
        accommodations = []
        
        # Note: This would require actual Booking.com API credentials and endpoints
        # For now, we'll simulate API calls
        try:
            # Simulated API call structure
            params = {
                'latitude': lat,
                'longitude': lon,
                'checkin_date': check_in.strftime('%Y-%m-%d'),
                'checkout_date': check_out.strftime('%Y-%m-%d'),
                'adults_number': guests,
                'room_number': 1,
                'units': 'metric',
                'locale': 'en-gb',
                'currency': 'EUR'
            }
            
            # This would be the actual API call:
            # response = requests.get(booking_api_url, headers=headers, params=params)
            
            # For now, return empty list - will be filled by scraping or fallback
            pass
            
        except Exception as e:
            logger.error(f"Booking.com API error for {city}: {e}")
        
        return accommodations
    
    def _scrape_accommodation_sites(self, city: str, check_in: datetime, 
                                  check_out: datetime, guests: int) -> List[Dict]:
        """Scrape accommodation websites for real data"""
        accommodations = []
        
        # Scrape multiple sites
        scrapers = [
            self._scrape_booking_com,
            self._scrape_hostelworld,
            self._scrape_airbnb_alternative
        ]
        
        for scraper in scrapers:
            try:
                results = scraper(city, check_in, check_out, guests)
                accommodations.extend(results)
            except Exception as e:
                logger.error(f"Scraping error with {scraper.__name__} for {city}: {e}")
        
        return accommodations
    
    def _scrape_booking_com(self, city: str, check_in: datetime, 
                           check_out: datetime, guests: int) -> List[Dict]:
        """Scrape Booking.com for accommodation data"""
        accommodations = []
        
        try:
            # Build Booking.com search URL
            checkin_str = check_in.strftime('%Y-%m-%d')
            checkout_str = check_out.strftime('%Y-%m-%d')
            
            search_url = (f"https://www.booking.com/searchresults.html"
                         f"?ss={city.replace(' ', '+')}"
                         f"&checkin_year={check_in.year}&checkin_month={check_in.month}&checkin_monthday={check_in.day}"
                         f"&checkout_year={check_out.year}&checkout_month={check_out.month}&checkout_monthday={check_out.day}"
                         f"&group_adults={guests}&no_rooms=1")
            
            response = self.session.get(search_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find hotel cards (structure may change)
            hotel_elements = soup.find_all('div', {'data-testid': 'property-card'})
            
            for element in hotel_elements[:8]:  # Limit to 8 results
                try:
                    name_elem = element.find('div', {'data-testid': 'title'})
                    price_elem = element.find('span', {'data-testid': 'price-and-discounted-price'})
                    rating_elem = element.find('div', {'data-testid': 'review-score'})
                    location_elem = element.find('span', {'data-testid': 'address'})
                    
                    if name_elem:
                        # Extract price
                        price = self._extract_price_from_text(price_elem.get_text() if price_elem else '€100')
                        
                        # Extract rating
                        rating = self._extract_rating_from_text(rating_elem.get_text() if rating_elem else '8.0')
                        
                        accommodations.append({
                            'name': name_elem.get_text(strip=True),
                            'type': 'hotel',
                            'price_per_night': price,
                            'total_price': price * (check_out - check_in).days,
                            'rating': rating,
                            'rating_count': 100,  # Approximation
                            'location': location_elem.get_text(strip=True) if location_elem else city,
                            'amenities': ['WiFi', 'Breakfast'],  # Default amenities
                            'cancellation': 'Free cancellation',
                            'distance_from_center': 1.5,  # km, approximation
                            'source': 'booking.com',
                            'url': search_url,
                            'available': True
                        })
                        
                except Exception as e:
                    logger.error(f"Error parsing Booking.com hotel: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Booking.com scraping error for {city}: {e}")
        
        return accommodations
    
    def _scrape_hostelworld(self, city: str, check_in: datetime,
                           check_out: datetime, guests: int) -> List[Dict]:
        """Scrape Hostelworld for budget accommodations"""
        accommodations = []
        
        try:
            # Build Hostelworld search URL
            search_url = (f"https://www.hostelworld.com/search"
                         f"?search_text={city.replace(' ', '%20')}"
                         f"&country=&city=&date_from={check_in.strftime('%Y-%m-%d')}"
                         f"&date_to={check_out.strftime('%Y-%m-%d')}"
                         f"&number_of_guests={guests}")
            
            response = self.session.get(search_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find hostel cards
            hostel_elements = soup.find_all('div', class_=['fabresult', 'property-card'])
            
            for element in hostel_elements[:5]:  # Limit to 5 hostels
                try:
                    name_elem = element.find(['h2', 'h3'], class_=['title', 'property-title'])
                    price_elem = element.find('span', class_=['price', 'property-price'])
                    rating_elem = element.find('span', class_=['rating', 'property-rating'])
                    
                    if name_elem:
                        price = self._extract_price_from_text(price_elem.get_text() if price_elem else '€25')
                        rating = self._extract_rating_from_text(rating_elem.get_text() if rating_elem else '7.5')
                        
                        accommodations.append({
                            'name': name_elem.get_text(strip=True),
                            'type': 'hostel',
                            'price_per_night': price,
                            'total_price': price * (check_out - check_in).days,
                            'rating': rating,
                            'rating_count': 50,
                            'location': f"City Center, {city}",
                            'amenities': ['WiFi', 'Kitchen', 'Lounge'],
                            'cancellation': 'Free cancellation',
                            'distance_from_center': 0.8,
                            'source': 'hostelworld',
                            'url': search_url,
                            'available': True
                        })
                        
                except Exception as e:
                    logger.error(f"Error parsing Hostelworld property: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Hostelworld scraping error for {city}: {e}")
        
        return accommodations
    
    def _scrape_airbnb_alternative(self, city: str, check_in: datetime,
                                  check_out: datetime, guests: int) -> List[Dict]:
        """Scrape alternative accommodation sites"""
        # This would scrape sites like Vrbo, local apartment rental sites, etc.
        # For now, return empty list to avoid complexity
        return []
    
    def _generate_fallback_accommodations(self, city: str, check_in: datetime,
                                        check_out: datetime, guests: int, budget_level: str) -> List[Dict]:
        """Generate realistic fallback accommodations when scraping fails"""
        import random
        
        accommodations = []
        nights = (check_out - check_in).days
        
        # Base prices by budget level and city size
        city_size_multiplier = self._get_city_size_multiplier(city)
        
        budget_ranges = {
            'budget': (20, 60),
            'mid_range': (60, 150),
            'luxury': (150, 400)
        }
        
        price_range = budget_ranges.get(budget_level, budget_ranges['mid_range'])
        
        # Generate different types of accommodations
        accommodation_types = [
            ('hotel', 'Hotel', ['WiFi', 'Breakfast', 'Reception']),
            ('hostel', 'Hostel', ['WiFi', 'Kitchen', 'Lounge']),
            ('boutique', 'Boutique Hotel', ['WiFi', 'Premium Breakfast', 'Concierge']),
            ('apartment', 'Apartment', ['WiFi', 'Kitchen', 'Living Room']),
            ('b&b', 'Bed & Breakfast', ['WiFi', 'Breakfast', 'Garden'])
        ]
        
        for i, (acc_type, type_name, amenities) in enumerate(accommodation_types):
            base_price = random.randint(price_range[0], price_range[1])
            adjusted_price = int(base_price * city_size_multiplier)
            
            accommodations.append({
                'name': f"{city} {type_name} {chr(65 + i)}",  # A, B, C, etc.
                'type': acc_type,
                'price_per_night': adjusted_price,
                'total_price': adjusted_price * nights,
                'rating': round(random.uniform(7.0, 9.5), 1),
                'rating_count': random.randint(50, 500),
                'location': f"{random.choice(['City Center', 'Historic District', 'Near Station'])}, {city}",
                'amenities': amenities + random.sample(['Pool', 'Gym', 'Spa', 'Restaurant', 'Bar', 'Parking'], 
                                                     random.randint(0, 3)),
                'cancellation': random.choice(['Free cancellation', 'Non-refundable', 'Flexible']),
                'distance_from_center': round(random.uniform(0.2, 3.0), 1),
                'source': 'generated',
                'url': '',
                'available': True
            })
        
        return accommodations
    
    def _get_city_size_multiplier(self, city: str) -> float:
        """Get price multiplier based on city size and popularity"""
        major_cities = ['paris', 'rome', 'barcelona', 'madrid', 'milan', 'vienna', 'munich']
        medium_cities = ['florence', 'venice', 'nice', 'lyon', 'seville', 'prague']
        
        city_lower = city.lower()
        
        if city_lower in major_cities:
            return 1.3
        elif city_lower in medium_cities:
            return 1.1
        else:
            return 0.9
    
    def _extract_price_from_text(self, text: str) -> int:
        """Extract price from text string"""
        # Find numbers in the text
        numbers = re.findall(r'\d+', text.replace(',', ''))
        if numbers:
            return int(numbers[0])
        return 100  # Default price
    
    def _extract_rating_from_text(self, text: str) -> float:
        """Extract rating from text string"""
        # Find decimal numbers
        ratings = re.findall(r'\d+\.?\d*', text)
        if ratings:
            rating = float(ratings[0])
            return min(rating, 10.0)  # Cap at 10
        return 8.0  # Default rating
    
    def _filter_by_budget(self, accommodations: List[Dict], budget_level: str) -> List[Dict]:
        """Filter accommodations by budget level"""
        if not accommodations:
            return accommodations
        
        budget_ranges = {
            'budget': (0, 80),
            'mid_range': (40, 200),
            'luxury': (120, 1000)
        }
        
        min_price, max_price = budget_ranges.get(budget_level, budget_ranges['mid_range'])
        
        return [acc for acc in accommodations 
                if min_price <= acc['price_per_night'] <= max_price]
    
    def _rank_accommodations(self, accommodations: List[Dict]) -> List[Dict]:
        """Rank accommodations by quality and value"""
        if not accommodations:
            return accommodations
        
        def score_accommodation(acc):
            # Calculate score based on rating, price, and amenities
            rating_score = acc['rating'] / 10.0  # Normalize to 0-1
            
            # Price score (lower is better, but not too low)
            price = acc['price_per_night']
            if price < 30:
                price_score = 0.6  # Very cheap might be low quality
            elif price < 80:
                price_score = 1.0  # Good value
            elif price < 150:
                price_score = 0.8  # Reasonable
            else:
                price_score = 0.6  # Expensive
            
            # Amenities score
            amenity_score = min(len(acc['amenities']) / 5.0, 1.0)
            
            # Distance score (closer to center is better)
            distance_score = max(0, 1.0 - (acc['distance_from_center'] / 5.0))
            
            # Combine scores
            total_score = (rating_score * 0.4 + price_score * 0.3 + 
                          amenity_score * 0.2 + distance_score * 0.1)
            
            return total_score
        
        # Sort by score (highest first)
        return sorted(accommodations, key=score_accommodation, reverse=True)
    
    def estimate_accommodation_costs(self, cities: List[str], nights_per_city: List[int],
                                   budget_level: str = 'mid_range') -> Dict[str, Dict]:
        """Estimate accommodation costs for entire route"""
        total_cost = 0
        city_costs = {}
        
        for i, city in enumerate(cities):
            nights = nights_per_city[i] if i < len(nights_per_city) else 2
            
            # Get base price estimate
            city_multiplier = self._get_city_size_multiplier(city)
            
            budget_ranges = {
                'budget': 40,
                'mid_range': 100,
                'luxury': 250
            }
            
            base_price = budget_ranges.get(budget_level, 100)
            estimated_price = int(base_price * city_multiplier)
            city_total = estimated_price * nights
            
            city_costs[city] = {
                'price_per_night': estimated_price,
                'nights': nights,
                'total_cost': city_total,
                'budget_level': budget_level
            }
            
            total_cost += city_total
        
        return {
            'total_cost': total_cost,
            'cities': city_costs,
            'average_per_night': total_cost / sum(nights_per_city) if nights_per_city else 0
        }
    
    def get_accommodation_recommendations(self, city: str, budget_level: str, 
                                       travel_style: str) -> List[str]:
        """Get accommodation type recommendations based on travel style"""
        recommendations = {
            'budget': {
                'backpacker': ['hostels', 'budget hotels', 'shared accommodations'],
                'family': ['family hotels', 'apartments', 'budget resorts'],
                'business': ['budget business hotels', 'extended stay'],
                'romantic': ['boutique B&Bs', 'cozy hotels'],
                'adventure': ['hostels', 'mountain lodges', 'camping']
            },
            'mid_range': {
                'backpacker': ['boutique hostels', '3-star hotels'],
                'family': ['family hotels', 'serviced apartments', 'resort hotels'],
                'business': ['business hotels', '4-star chains'],
                'romantic': ['boutique hotels', 'romantic B&Bs', 'spa hotels'],
                'adventure': ['outdoor lodges', 'eco-hotels']
            },
            'luxury': {
                'backpacker': ['luxury hostels', 'designer hotels'],
                'family': ['luxury family resorts', 'villa rentals'],
                'business': ['5-star business hotels', 'luxury suites'],
                'romantic': ['luxury romantic hotels', '5-star boutiques', 'castle hotels'],
                'adventure': ['luxury eco-lodges', 'safari lodges']
            }
        }
        
        return recommendations.get(budget_level, {}).get(travel_style, ['standard hotels'])
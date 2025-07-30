#!/usr/bin/env python3
"""
Geographic Router - Real route generation based on actual geography
Creates logical intermediate cities based on start/end points and route focus
"""

import math
import random
from typing import Dict, List, Tuple
from comprehensive_cities_database import COMPREHENSIVE_CITIES_DB

class GeographicRouter:
    """Generate geographically logical routes between European cities."""
    
    def __init__(self):
        # Use comprehensive European cities database
        self.cities_db = COMPREHENSIVE_CITIES_DB.copy()
        
        # Add alias mappings for common city name variations
        self.city_aliases = {
            'barcelone': 'barcelona',
            'barcellona': 'barcelona', 
            'venise': 'venice',
            'venezia': 'venice',
            'firenze': 'florence',
            'florencia': 'florence',
            'roma': 'rome',
            'milano': 'milan',
            'napoli': 'naples',
            'torino': 'turin',
            'genova': 'genoa',
            'bologna': 'bologna',
            'parigi': 'paris',
            'lione': 'lyon',
            'marsiglia': 'marseille',
            'nizza': 'nice',
            'tolosa': 'toulouse',
            'bordeaux': 'bordeaux',
            'lilla': 'lille',
            'strasburgo': 'strasbourg',
            'monaco': 'monaco',
            'montecarlo': 'monte-carlo',
            'siviglia': 'seville',
            'granada': 'granada',
            'valencia': 'valencia',
            'malaga': 'malaga',
            'toledo': 'toledo',
            'segovia': 'segovia',
            'avila': 'avila',
            'salamanca': 'salamanca',
            'santiago': 'santiago-de-compostela',
            'bilbao': 'bilbao',
            'san-sebastian': 'san-sebastian',
            'pamplona': 'pamplona',
            'saragozza': 'zaragoza',
            'zurigo': 'zurich',
            'ginevra': 'geneva',
            'berna': 'bern',
            'basilea': 'basel',
            'losanna': 'lausanne',
            'lucerna': 'lucerne',
            'vienna': 'vienna',
            'salisburgo': 'salzburg',
            'innsbruck': 'innsbruck',
            'praga': 'prague',
            'budapest': 'budapest',
            'amsterdam': 'amsterdam',
            'bruxelles': 'brussels',
            'londra': 'london',
            'lisbona': 'lisbon',
            'porto': 'porto',
            'copenaghen': 'copenhagen',
            'stoccolma': 'stockholm',
            'berlino': 'berlin',
            'monaco-di-baviera': 'munich',
            'colonia': 'cologne',
            'francoforte': 'frankfurt',
            'amburgo': 'hamburg',
            'dresda': 'dresden',
            'heidelberg': 'heidelberg',
            'norimberga': 'nuremberg'
        }
        
        # Focus-specific city preferences
        self.focus_preferences = {
            'speed': ['major'],
            'scenery': ['scenery', 'adventure', 'hidden_gems'],
            'culture': ['cultural', 'major'],
            'culinary': ['culinary', 'cultural'],
            'hidden_gems': ['hidden_gems', 'cultural'],
            'budget': ['budget', 'cultural'],
            'adventure': ['adventure', 'scenery'],
            'wellness': ['wellness', 'hidden_gems']
        }
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def normalize_city_name(self, city_name: str) -> str:
        """Normalize city name for lookup."""
        normalized = city_name.lower().strip().replace(' ', '-')
        
        # Check for aliases first
        if normalized in self.city_aliases:
            return self.city_aliases[normalized]
        
        return normalized
    
    def get_city_info(self, city_name: str) -> Dict:
        """Get city information from database."""
        normalized_name = self.normalize_city_name(city_name)
        return self.cities_db.get(normalized_name, {
            'lat': 45.0, 'lon': 8.0, 'country': 'Europe', 
            'population': 100000, 'type': ['cultural'], 'region': 'Unknown'
        })
    
    def find_intermediate_cities(self, start_city: str, end_city: str, focus: str, count: int = 3, strategy_seed: int = 0) -> List[Dict]:
        """Find geographically logical intermediate cities."""
        start_info = self.get_city_info(start_city)
        end_info = self.get_city_info(end_city)
        
        start_lat, start_lon = start_info['lat'], start_info['lon']
        end_lat, end_lon = end_info['lat'], end_info['lon']
        
        # Get preferred city types for this focus
        preferred_types = self.focus_preferences.get(focus, ['cultural'])
        
        # Use strategy seed to create variation within same focus
        random.seed(hash(f"{start_city}{end_city}{focus}{strategy_seed}") % 2**32)
        
        # Find cities that are roughly between start and end
        candidates = []
        total_distance = self.calculate_distance(start_lat, start_lon, end_lat, end_lon)
        
        for city_name, city_info in self.cities_db.items():
            # Skip start and end cities
            if (self.normalize_city_name(city_name) == self.normalize_city_name(start_city) or 
                self.normalize_city_name(city_name) == self.normalize_city_name(end_city)):
                continue
            
            city_lat, city_lon = city_info['lat'], city_info['lon']
            
            # Calculate distances
            dist_from_start = self.calculate_distance(start_lat, start_lon, city_lat, city_lon)
            dist_from_end = self.calculate_distance(city_lat, city_lon, end_lat, end_lon)
            total_via_city = dist_from_start + dist_from_end
            
            # Check if city is roughly on the route (not too much detour)
            detour_factor = total_via_city / total_distance if total_distance > 0 else 2
            
            if detour_factor <= 1.5:  # Allow up to 50% detour
                # Calculate preference score
                preference_score = 0
                for city_type in city_info['type']:
                    if city_type in preferred_types:
                        preference_score += 3  # Higher weight for preferred types
                    else:
                        preference_score += 1
                
                # Add distance-based scoring (prefer cities that create good spacing)
                distance_score = 1 / (detour_factor * 0.5 + 0.5)  # Favor direct routes
                
                # Add strategy variation factor with larger range
                strategy_variation = random.uniform(0.5, 1.5)  # 100% variation range
                
                # Add population bonus for variety
                population_factor = min(city_info['population'] / 100000, 2.0)  # Cap at 2x
                
                candidates.append({
                    'name': city_name.replace('-', ' ').title(),
                    'country': city_info['country'],
                    'population': city_info['population'],
                    'region': city_info.get('region', 'Unknown'),
                    'lat': city_lat,
                    'lon': city_lon,
                    'types': city_info['type'],
                    'distance_from_start': dist_from_start,
                    'distance_from_end': dist_from_end,
                    'detour_factor': detour_factor,
                    'preference_score': preference_score,
                    'total_score': preference_score * distance_score * strategy_variation * population_factor,
                    'reason': self._generate_reason(city_info['type'], focus)
                })
        
        # Sort by total score and select best candidates
        candidates.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Select cities ensuring good geographic distribution and variety
        selected = []
        used_countries = set()
        used_regions = set()
        
        for candidate in candidates[:count * 5]:  # Consider more candidates for better variety
            # Check if this city provides good spacing and variety
            if not selected:
                selected.append(candidate)
                used_countries.add(candidate['country'])
                used_regions.add(candidate['region'])
            else:
                # Ensure minimum distance between selected cities
                min_dist_to_selected = min(
                    self.calculate_distance(candidate['lat'], candidate['lon'], 
                                          sel['lat'], sel['lon']) 
                    for sel in selected
                )
                
                # Favor cities from different countries/regions for variety
                country_bonus = 1.5 if candidate['country'] not in used_countries else 1.0
                region_bonus = 1.3 if candidate['region'] not in used_regions else 1.0
                variety_bonus = country_bonus * region_bonus
                
                # Adjusted minimum distance based on total trip length
                min_required_distance = max(50, total_distance * 0.1)  # At least 50km or 10% of total
                
                if (min_dist_to_selected > min_required_distance and 
                    (len(selected) < count or variety_bonus > 1.2)):
                    selected.append(candidate)
                    used_countries.add(candidate['country'])
                    used_regions.add(candidate['region'])
                    if len(selected) >= count:
                        break
        
        # If we don't have enough diverse cities, fill with best remaining
        while len(selected) < count and len(candidates) > len(selected):
            for candidate in candidates:
                if candidate not in selected:
                    selected.append(candidate)
                    break
        
        return selected[:count]
    
    def _generate_reason(self, city_types: List[str], focus: str) -> str:
        """Generate a reason why this city fits the route focus."""
        reasons = {
            'speed': {
                'major': 'Major transport hub with excellent highway connections',
                'cultural': 'Strategic stopover on main route with quick access',
                'default': 'Efficient highway junction point for fast travel'
            },
            'scenery': {
                'scenery': 'Breathtaking mountain and landscape views',
                'adventure': 'Gateway to spectacular natural scenery',
                'hidden_gems': 'Stunning hidden valley with panoramic views',
                'cultural': 'Historic sites with beautiful architectural backdrops',
                'default': 'Beautiful scenic route destination with photo opportunities'
            },
            'culture': {
                'cultural': 'Rich historical heritage and world-class museums',
                'major': 'Major cultural center with iconic attractions',
                'hidden_gems': 'Authentic cultural experiences off beaten path',
                'default': 'Important cultural and historical site worth exploring'
            },
            'culinary': {
                'culinary': 'Renowned regional cuisine and local specialties',
                'cultural': 'Traditional cooking methods and historic food markets',
                'major': 'Gastronomic capital with excellent restaurants',
                'hidden_gems': 'Secret local food spots known only to locals',
                'default': 'Authentic local food experiences and wine tastings'
            },
            'hidden_gems': {
                'hidden_gems': 'Authentic local experiences away from tourist crowds',
                'cultural': 'Lesser-known cultural treasures and secret sites',
                'scenery': 'Secret scenic spots known only to locals',
                'default': 'Genuine local atmosphere and undiscovered traditions'
            },
            'budget': {
                'budget': 'Excellent value accommodations and activities',
                'cultural': 'Great cultural sites without high entrance costs',
                'major': 'Major city with budget-friendly options and free attractions',
                'default': 'Affordable dining and accommodation options available'
            },
            'adventure': {
                'adventure': 'Outdoor activities and sports opportunities',
                'scenery': 'Base for hiking and outdoor adventures',
                'major': 'Urban adventures and activity centers',
                'cultural': 'Historic adventure trails and outdoor cultural sites',
                'default': 'Great for active travelers and outdoor sports'
            },
            'wellness': {
                'wellness': 'Renowned spa treatments and relaxation facilities',
                'hidden_gems': 'Peaceful retreat away from busy tourist areas',
                'scenery': 'Natural healing environment with therapeutic views',
                'cultural': 'Historic wellness traditions and thermal baths',
                'default': 'Perfect for rest, rejuvenation and peaceful relaxation'
            }
        }
        
        focus_reasons = reasons.get(focus, {})
        
        # Find the best matching reason
        for city_type in city_types:
            if city_type in focus_reasons:
                return focus_reasons[city_type]
        
        return focus_reasons.get('default', f'Perfect {focus} destination for this route')
    
    def generate_route_cities(self, start_city: str, end_city: str, focus: str, strategy_seed: int = 0) -> List[Dict]:
        """Generate complete list of intermediate cities for a route."""
        return self.find_intermediate_cities(start_city, end_city, focus, 3, strategy_seed)
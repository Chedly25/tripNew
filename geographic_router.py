#!/usr/bin/env python3
"""
Geographic Router - Real route generation based on actual geography
Creates logical intermediate cities based on start/end points and route focus
"""

import math
import random
from typing import Dict, List, Tuple

class GeographicRouter:
    """Generate geographically logical routes between European cities."""
    
    def __init__(self):
        # European cities with coordinates and characteristics
        self.cities_db = {
            # Major cities with coordinates (lat, lon)
            'paris': {'lat': 48.8566, 'lon': 2.3522, 'country': 'France', 'population': 2140526, 'type': ['major', 'cultural', 'culinary']},
            'london': {'lat': 51.5074, 'lon': -0.1278, 'country': 'UK', 'population': 8982000, 'type': ['major', 'cultural']},
            'berlin': {'lat': 52.5200, 'lon': 13.4050, 'country': 'Germany', 'population': 3669491, 'type': ['major', 'cultural', 'budget']},
            'rome': {'lat': 41.9028, 'lon': 12.4964, 'country': 'Italy', 'population': 2872800, 'type': ['major', 'cultural', 'culinary']},
            'madrid': {'lat': 40.4168, 'lon': -3.7038, 'country': 'Spain', 'population': 3223334, 'type': ['major', 'cultural']},
            'amsterdam': {'lat': 52.3676, 'lon': 4.9041, 'country': 'Netherlands', 'population': 821752, 'type': ['major', 'cultural']},
            'vienna': {'lat': 48.2082, 'lon': 16.3738, 'country': 'Austria', 'population': 1911191, 'type': ['major', 'cultural', 'wellness']},
            'barcelona': {'lat': 41.3851, 'lon': 2.1734, 'country': 'Spain', 'population': 1620343, 'type': ['major', 'cultural', 'culinary']},
            'munich': {'lat': 48.1351, 'lon': 11.5820, 'country': 'Germany', 'population': 1471508, 'type': ['major', 'cultural', 'culinary']},
            'milan': {'lat': 45.4642, 'lon': 9.1900, 'country': 'Italy', 'population': 1396059, 'type': ['major', 'cultural', 'culinary']},
            'venice': {'lat': 45.4408, 'lon': 12.3155, 'country': 'Italy', 'population': 261905, 'type': ['major', 'cultural', 'hidden_gems']},
            'florence': {'lat': 43.7696, 'lon': 11.2558, 'country': 'Italy', 'population': 382258, 'type': ['major', 'cultural', 'culinary']},
            'naples': {'lat': 40.8518, 'lon': 14.2681, 'country': 'Italy', 'population': 967069, 'type': ['major', 'culinary']},
            'zurich': {'lat': 47.3769, 'lon': 8.5417, 'country': 'Switzerland', 'population': 415367, 'type': ['major', 'wellness']},
            'geneva': {'lat': 46.2044, 'lon': 6.1432, 'country': 'Switzerland', 'population': 203856, 'type': ['major', 'wellness']},
            'prague': {'lat': 50.0755, 'lon': 14.4378, 'country': 'Czech Republic', 'population': 1318982, 'type': ['major', 'cultural', 'budget']},
            'budapest': {'lat': 47.4979, 'lon': 19.0402, 'country': 'Hungary', 'population': 1752286, 'type': ['major', 'cultural', 'wellness', 'budget']},
            'lisbon': {'lat': 38.7223, 'lon': -9.1393, 'country': 'Portugal', 'population': 544851, 'type': ['major', 'cultural']},
            'copenhagen': {'lat': 55.6761, 'lon': 12.5683, 'country': 'Denmark', 'population': 634265, 'type': ['major', 'cultural']},
            'stockholm': {'lat': 59.3293, 'lon': 18.0686, 'country': 'Sweden', 'population': 975551, 'type': ['major', 'cultural']},
            'brussels': {'lat': 50.8503, 'lon': 4.3517, 'country': 'Belgium', 'population': 179277, 'type': ['major', 'cultural', 'culinary']},
            
            # French cities
            'aix-en-provence': {'lat': 43.5297, 'lon': 5.4474, 'country': 'France', 'population': 143006, 'type': ['cultural', 'culinary']},
            'lyon': {'lat': 45.7640, 'lon': 4.8357, 'country': 'France', 'population': 515695, 'type': ['major', 'culinary', 'cultural']},
            'marseille': {'lat': 43.2965, 'lon': 5.3698, 'country': 'France', 'population': 861635, 'type': ['major', 'culinary']},
            'nice': {'lat': 43.7102, 'lon': 7.2620, 'country': 'France', 'population': 342637, 'type': ['cultural', 'wellness']},
            'cannes': {'lat': 43.5528, 'lon': 7.0174, 'country': 'France', 'population': 74152, 'type': ['cultural', 'wellness']},
            'monaco': {'lat': 43.7384, 'lon': 7.4246, 'country': 'Monaco', 'population': 39242, 'type': ['wellness', 'hidden_gems']},
            'strasbourg': {'lat': 48.5734, 'lon': 7.7521, 'country': 'France', 'population': 280966, 'type': ['cultural', 'culinary']},
            'bordeaux': {'lat': 44.8378, 'lon': -0.5792, 'country': 'France', 'population': 257804, 'type': ['culinary', 'cultural']},
            'toulouse': {'lat': 43.6047, 'lon': 1.4442, 'country': 'France', 'population': 479553, 'type': ['cultural', 'adventure']},
            'nantes': {'lat': 47.2184, 'lon': -1.5536, 'country': 'France', 'population': 309346, 'type': ['cultural', 'budget']},
            'montpellier': {'lat': 43.6110, 'lon': 3.8767, 'country': 'France', 'population': 285121, 'type': ['cultural', 'budget']},
            
            # German cities
            'cologne': {'lat': 50.9375, 'lon': 6.9603, 'country': 'Germany', 'population': 1085664, 'type': ['major', 'cultural']},
            'frankfurt': {'lat': 50.1109, 'lon': 8.6821, 'country': 'Germany', 'population': 753056, 'type': ['major', 'cultural']},
            'hamburg': {'lat': 53.5511, 'lon': 9.9937, 'country': 'Germany', 'population': 1945532, 'type': ['major', 'cultural']},
            'dresden': {'lat': 51.0504, 'lon': 13.7373, 'country': 'Germany', 'population': 554649, 'type': ['cultural', 'budget']},
            'heidelberg': {'lat': 49.3988, 'lon': 8.6724, 'country': 'Germany', 'population': 159914, 'type': ['cultural', 'hidden_gems']},
            'nuremberg': {'lat': 49.4521, 'lon': 11.0767, 'country': 'Germany', 'population': 518365, 'type': ['cultural', 'budget']},
            
            # Italian cities
            'genoa': {'lat': 44.4056, 'lon': 8.9463, 'country': 'Italy', 'population': 580223, 'type': ['cultural', 'culinary']},
            'turin': {'lat': 45.0703, 'lon': 7.6869, 'country': 'Italy', 'population': 870952, 'type': ['cultural', 'culinary']},
            'bologna': {'lat': 44.4949, 'lon': 11.3426, 'country': 'Italy', 'population': 390636, 'type': ['cultural', 'culinary']},
            'verona': {'lat': 45.4384, 'lon': 10.9916, 'country': 'Italy', 'population': 259608, 'type': ['cultural', 'culinary']},
            'padua': {'lat': 45.4064, 'lon': 11.8768, 'country': 'Italy', 'population': 214198, 'type': ['cultural', 'budget']},
            'pisa': {'lat': 43.7228, 'lon': 10.4017, 'country': 'Italy', 'population': 91104, 'type': ['cultural', 'budget']},
            'siena': {'lat': 43.3188, 'lon': 11.3307, 'country': 'Italy', 'population': 53901, 'type': ['cultural', 'hidden_gems']},
            'parma': {'lat': 44.8015, 'lon': 10.3279, 'country': 'Italy', 'population': 195687, 'type': ['culinary', 'hidden_gems']},
            'modena': {'lat': 44.6473, 'lon': 10.9252, 'country': 'Italy', 'population': 185273, 'type': ['culinary', 'hidden_gems']},
            'ravenna': {'lat': 44.4173, 'lon': 12.1993, 'country': 'Italy', 'population': 159115, 'type': ['cultural', 'hidden_gems']},
            
            # Swiss cities
            'bern': {'lat': 46.9481, 'lon': 7.4474, 'country': 'Switzerland', 'population': 133883, 'type': ['cultural', 'wellness']},
            'basel': {'lat': 47.5596, 'lon': 7.5886, 'country': 'Switzerland', 'population': 175131, 'type': ['cultural', 'wellness']},
            'lausanne': {'lat': 46.5197, 'lon': 6.6323, 'country': 'Switzerland', 'population': 139111, 'type': ['wellness', 'cultural']},
            'lucerne': {'lat': 47.0502, 'lon': 8.3093, 'country': 'Switzerland', 'population': 82620, 'type': ['wellness', 'scenery']},
            'interlaken': {'lat': 46.6863, 'lon': 7.8632, 'country': 'Switzerland', 'population': 5749, 'type': ['adventure', 'scenery']},
            'zermatt': {'lat': 46.0207, 'lon': 7.7491, 'country': 'Switzerland', 'population': 5800, 'type': ['adventure', 'scenery']},
            'st-moritz': {'lat': 46.4908, 'lon': 9.8355, 'country': 'Switzerland', 'population': 5067, 'type': ['wellness', 'adventure']},
            
            # Austrian cities
            'salzburg': {'lat': 47.8095, 'lon': 13.0550, 'country': 'Austria', 'population': 155021, 'type': ['cultural', 'scenery']},
            'innsbruck': {'lat': 47.2692, 'lon': 11.4041, 'country': 'Austria', 'population': 132236, 'type': ['adventure', 'scenery']},
            'graz': {'lat': 47.0707, 'lon': 15.4395, 'country': 'Austria', 'population': 291072, 'type': ['cultural', 'budget']},
            'hallstatt': {'lat': 47.5622, 'lon': 13.6493, 'country': 'Austria', 'population': 778, 'type': ['hidden_gems', 'scenery']},
            
            # Alpine and mountain cities
            'chamonix': {'lat': 45.9237, 'lon': 6.8694, 'country': 'France', 'population': 8906, 'type': ['adventure', 'scenery']},
            'annecy': {'lat': 45.8992, 'lon': 6.1294, 'country': 'France', 'population': 128199, 'type': ['hidden_gems', 'scenery']},
            'grenoble': {'lat': 45.1885, 'lon': 5.7245, 'country': 'France', 'population': 160649, 'type': ['adventure', 'budget']},
            'chambery': {'lat': 45.5646, 'lon': 5.9178, 'country': 'France', 'population': 59490, 'type': ['scenery', 'hidden_gems']},
            
            # Eastern European
            'krakow': {'lat': 50.0647, 'lon': 19.9450, 'country': 'Poland', 'population': 779115, 'type': ['cultural', 'budget']},
            'warsaw': {'lat': 52.2297, 'lon': 21.0122, 'country': 'Poland', 'population': 1790658, 'type': ['major', 'cultural', 'budget']},
            'ljubljana': {'lat': 46.0569, 'lon': 14.5058, 'country': 'Slovenia', 'population': 294464, 'type': ['cultural', 'budget', 'hidden_gems']},
            'bled': {'lat': 46.3683, 'lon': 14.1148, 'country': 'Slovenia', 'population': 5051, 'type': ['hidden_gems', 'scenery']},
            'bratislava': {'lat': 48.1486, 'lon': 17.1077, 'country': 'Slovakia', 'population': 432864, 'type': ['cultural', 'budget']},
            
            # Spa and wellness cities
            'baden-baden': {'lat': 48.7606, 'lon': 8.2413, 'country': 'Germany', 'population': 55449, 'type': ['wellness', 'hidden_gems']},
            'karlovy-vary': {'lat': 50.2329, 'lon': 12.8716, 'country': 'Czech Republic', 'population': 48686, 'type': ['wellness', 'hidden_gems']},
            'marienbad': {'lat': 49.9646, 'lon': 12.7016, 'country': 'Czech Republic', 'population': 12235, 'type': ['wellness', 'hidden_gems']},
            'vichy': {'lat': 46.1277, 'lon': 3.4256, 'country': 'France', 'population': 25279, 'type': ['wellness', 'hidden_gems']},
            
            # Coastal cities
            'santander': {'lat': 43.4623, 'lon': -3.8099, 'country': 'Spain', 'population': 172044, 'type': ['cultural', 'scenery']},
            'san-sebastian': {'lat': 43.3183, 'lon': -1.9812, 'country': 'Spain', 'population': 186665, 'type': ['culinary', 'cultural']},
            'bilbao': {'lat': 43.2627, 'lon': -2.9253, 'country': 'Spain', 'population': 345821, 'type': ['cultural', 'culinary']},
            
            # Hidden gems
            'rothenburg': {'lat': 49.3755, 'lon': 10.1763, 'country': 'Germany', 'population': 11072, 'type': ['hidden_gems', 'cultural']},
            'cesky-krumlov': {'lat': 48.8127, 'lon': 14.3175, 'country': 'Czech Republic', 'population': 13056, 'type': ['hidden_gems', 'cultural']},
            'sintra': {'lat': 38.7970, 'lon': -9.3897, 'country': 'Portugal', 'population': 377835, 'type': ['hidden_gems', 'cultural']},
            'colmar': {'lat': 48.0776, 'lon': 7.3583, 'country': 'France', 'population': 69105, 'type': ['hidden_gems', 'cultural']},
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
        return city_name.lower().strip().replace(' ', '-')
    
    def get_city_info(self, city_name: str) -> Dict:
        """Get city information from database."""
        normalized_name = self.normalize_city_name(city_name)
        return self.cities_db.get(normalized_name, {
            'lat': 45.0, 'lon': 8.0, 'country': 'Europe', 
            'population': 100000, 'type': ['cultural']
        })
    
    def find_intermediate_cities(self, start_city: str, end_city: str, focus: str, count: int = 3) -> List[Dict]:
        """Find geographically logical intermediate cities."""
        start_info = self.get_city_info(start_city)
        end_info = self.get_city_info(end_city)
        
        start_lat, start_lon = start_info['lat'], start_info['lon']
        end_lat, end_lon = end_info['lat'], end_info['lon']
        
        # Get preferred city types for this focus
        preferred_types = self.focus_preferences.get(focus, ['cultural'])
        
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
                        preference_score += 2
                    else:
                        preference_score += 1
                
                # Add distance-based scoring (prefer cities that create good spacing)
                distance_score = 1 / (detour_factor * 0.5 + 0.5)  # Favor direct routes
                
                candidates.append({
                    'name': city_name.replace('-', ' ').title(),
                    'country': city_info['country'],
                    'population': city_info['population'],
                    'lat': city_lat,
                    'lon': city_lon,
                    'types': city_info['type'],
                    'distance_from_start': dist_from_start,
                    'distance_from_end': dist_from_end,
                    'detour_factor': detour_factor,
                    'preference_score': preference_score,
                    'total_score': preference_score * distance_score,
                    'reason': self._generate_reason(city_info['type'], focus)
                })
        
        # Sort by total score and select best candidates
        candidates.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Select cities ensuring good geographic distribution
        selected = []
        for candidate in candidates[:count * 3]:  # Consider more candidates
            # Check if this city provides good spacing
            if not selected:
                selected.append(candidate)
            else:
                # Ensure minimum distance between selected cities
                min_dist_to_selected = min(
                    self.calculate_distance(candidate['lat'], candidate['lon'], 
                                          sel['lat'], sel['lon']) 
                    for sel in selected
                )
                
                if min_dist_to_selected > 100:  # At least 100km apart
                    selected.append(candidate)
                    if len(selected) >= count:
                        break
        
        # If we don't have enough well-spaced cities, fill with best remaining
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
                'cultural': 'Strategic stopover on main route',
                'default': 'Efficient highway junction point'
            },
            'scenery': {
                'scenery': 'Breathtaking mountain and landscape views',
                'adventure': 'Gateway to spectacular natural scenery',
                'hidden_gems': 'Stunning hidden valley with panoramic views',
                'default': 'Beautiful scenic route destination'
            },
            'culture': {
                'cultural': 'Rich historical heritage and museums',
                'major': 'Major cultural center with world-class attractions',
                'hidden_gems': 'Authentic cultural experiences off beaten path',
                'default': 'Important cultural and historical site'
            },
            'culinary': {
                'culinary': 'Renowned regional cuisine and local specialties',
                'cultural': 'Traditional cooking methods and local markets',
                'major': 'Gastronomic capital with excellent restaurants',
                'default': 'Authentic local food experiences'
            },
            'hidden_gems': {
                'hidden_gems': 'Authentic local experiences away from crowds',
                'cultural': 'Lesser-known cultural treasures',
                'scenery': 'Secret scenic spots known only to locals',
                'default': 'Genuine local atmosphere and traditions'
            },
            'budget': {
                'budget': 'Excellent value accommodations and activities',
                'cultural': 'Great cultural sites without high costs',
                'major': 'Major city with budget-friendly options',
                'default': 'Affordable dining and accommodation options'
            },
            'adventure': {
                'adventure': 'Outdoor activities and sports opportunities',
                'scenery': 'Base for hiking and outdoor adventures',
                'major': 'Urban adventures and activity centers',
                'default': 'Great for active travelers and sports'
            },
            'wellness': {
                'wellness': 'Renowned spa treatments and relaxation',
                'hidden_gems': 'Peaceful retreat away from busy areas',
                'scenery': 'Natural healing environment',
                'default': 'Perfect for rest and rejuvenation'
            }
        }
        
        focus_reasons = reasons.get(focus, {})
        
        # Find the best matching reason
        for city_type in city_types:
            if city_type in focus_reasons:
                return focus_reasons[city_type]
        
        return focus_reasons.get('default', 'Perfect stop for this route focus')
    
    def generate_route_cities(self, start_city: str, end_city: str, focus: str) -> List[Dict]:
        """Generate complete list of intermediate cities for a route."""
        return self.find_intermediate_cities(start_city, end_city, focus, 3)
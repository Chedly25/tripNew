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
        """Find geographically logical intermediate cities with proper route progression."""
        start_info = self.get_city_info(start_city)
        end_info = self.get_city_info(end_city)
        
        start_lat, start_lon = start_info['lat'], start_info['lon']
        end_lat, end_lon = end_info['lat'], end_info['lon']
        
        # Get preferred city types for this focus
        preferred_types = self.focus_preferences.get(focus, ['cultural'])
        
        # Use strategy seed to create variation within same focus
        random.seed(hash(f"{start_city}{end_city}{focus}{strategy_seed}") % 2**32)
        
        # Find cities using improved geographic logic
        route_cities = self._find_route_progression(
            start_lat, start_lon, end_lat, end_lon, 
            start_city, end_city, preferred_types, count, strategy_seed, focus
        )
        
        return route_cities
    
    def _find_route_progression(self, start_lat: float, start_lon: float, 
                               end_lat: float, end_lon: float, 
                               start_city: str, end_city: str,
                               preferred_types: List[str], count: int, strategy_seed: int, focus: str) -> List[Dict]:
        """Find cities that form a logical geographic progression."""
        
        # Calculate total distance and bearing
        total_distance = self.calculate_distance(start_lat, start_lon, end_lat, end_lon)
        main_bearing = self._calculate_bearing(start_lat, start_lon, end_lat, end_lon)
        
        # Create segments along the route
        segments = []
        for i in range(1, count + 1):
            progress = i / (count + 1)  # Evenly space segments
            
            # Calculate intermediate point along the great circle route
            intermediate_lat, intermediate_lon = self._interpolate_route_point(
                start_lat, start_lon, end_lat, end_lon, progress
            )
            
            segments.append({
                'target_lat': intermediate_lat,
                'target_lon': intermediate_lon,
                'progress': progress,
                'min_distance_from_start': total_distance * progress * 0.4,  # Must be at least 40% of progress
                'max_distance_from_start': total_distance * progress * 1.6,  # Must be at most 160% of progress
                'search_radius': max(50, total_distance * 0.15)  # Search within radius
            })
        
        selected_cities = []
        used_city_names = {self.normalize_city_name(start_city), self.normalize_city_name(end_city)}
        
        # Find best city for each segment
        for segment_idx, segment in enumerate(segments):
            best_candidates = []
            
            for city_name, city_info in self.cities_db.items():
                normalized_name = self.normalize_city_name(city_name)
                
                # Skip already used cities
                if normalized_name in used_city_names:
                    continue
                
                city_lat, city_lon = city_info['lat'], city_info['lon']
                
                # Calculate distances
                dist_from_start = self.calculate_distance(start_lat, start_lon, city_lat, city_lon)
                dist_from_end = self.calculate_distance(city_lat, city_lon, end_lat, end_lon)
                dist_from_target = self.calculate_distance(
                    segment['target_lat'], segment['target_lon'], city_lat, city_lon
                )
                
                # Check if city is in reasonable position for this segment
                if (dist_from_start < segment['min_distance_from_start'] or 
                    dist_from_start > segment['max_distance_from_start'] or
                    dist_from_target > segment['search_radius']):
                    continue
                
                # Check route logic: city should be closer to end than to start for later segments
                route_progress = dist_from_start / (dist_from_start + dist_from_end)
                expected_progress = segment['progress']
                progress_penalty = abs(route_progress - expected_progress)
                
                if progress_penalty > 0.3:  # Too far from expected route position
                    continue
                
                # Calculate bearing consistency
                bearing_to_city = self._calculate_bearing(start_lat, start_lon, city_lat, city_lon)
                bearing_from_city = self._calculate_bearing(city_lat, city_lon, end_lat, end_lon)
                
                # Penalize cities that create sharp direction changes
                bearing_consistency = self._calculate_bearing_consistency(
                    main_bearing, bearing_to_city, bearing_from_city
                )
                
                # Skip cities that create too much backtracking
                if bearing_consistency < 0.3:
                    continue
                
                # Calculate preference score
                preference_score = 0
                for city_type in city_info['type']:
                    if city_type in preferred_types:
                        preference_score += 3
                    else:
                        preference_score += 1
                
                # Calculate final score
                distance_score = 1.0 / (1.0 + dist_from_target / 50.0)  # Closer to target is better
                progress_score = 1.0 - progress_penalty  # Better route progression
                population_score = min(city_info['population'] / 100000, 2.0)
                
                # Add controlled randomization based on strategy seed
                random_factor = random.uniform(0.7, 1.3)
                
                total_score = (preference_score * distance_score * progress_score * 
                              bearing_consistency * population_score * random_factor)
                
                best_candidates.append({
                    'name': city_name.replace('-', ' ').title(),
                    'country': city_info['country'],
                    'population': city_info['population'],
                    'region': city_info.get('region', 'Unknown'),
                    'lat': city_lat,
                    'lon': city_lon,
                    'types': city_info['type'],
                    'distance_from_start': dist_from_start,
                    'distance_from_end': dist_from_end,
                    'distance_from_target': dist_from_target,
                    'route_progress': route_progress,
                    'bearing_consistency': bearing_consistency,
                    'total_score': total_score,
                    'reason': self._generate_reason(city_info['type'], focus),
                    'normalized_name': normalized_name
                })
            
            # Sort candidates by score and select the best one that doesn't conflict
            best_candidates.sort(key=lambda x: x['total_score'], reverse=True)
            
            # Select best candidate that maintains good spacing
            for candidate in best_candidates:
                # Check minimum distance from already selected cities
                min_distance_ok = True
                if selected_cities:
                    min_dist = min(
                        self.calculate_distance(candidate['lat'], candidate['lon'], 
                                              city['lat'], city['lon'])
                        for city in selected_cities
                    )
                    if min_dist < max(30, total_distance * 0.08):  # Minimum 30km or 8% of total
                        min_distance_ok = False
                
                if min_distance_ok:
                    selected_cities.append(candidate)
                    used_city_names.add(candidate['normalized_name'])
                    break
        
        # Sort selected cities by distance from start to ensure proper order
        selected_cities.sort(key=lambda x: x['distance_from_start'])
        
        return selected_cities
    
    def _interpolate_route_point(self, lat1: float, lon1: float, lat2: float, lon2: float, progress: float) -> tuple:
        """Calculate intermediate point along great circle route."""
        import math
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Calculate distance
        d = math.acos(math.sin(lat1_rad) * math.sin(lat2_rad) + 
                     math.cos(lat1_rad) * math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad))
        
        if d == 0:
            return lat1, lon1
        
        # Calculate intermediate point
        a = math.sin((1 - progress) * d) / math.sin(d)
        b = math.sin(progress * d) / math.sin(d)
        
        x = a * math.cos(lat1_rad) * math.cos(lon1_rad) + b * math.cos(lat2_rad) * math.cos(lon2_rad)
        y = a * math.cos(lat1_rad) * math.sin(lon1_rad) + b * math.cos(lat2_rad) * math.sin(lon2_rad)
        z = a * math.sin(lat1_rad) + b * math.sin(lat2_rad)
        
        lat_result = math.atan2(z, math.sqrt(x*x + y*y))
        lon_result = math.atan2(y, x)
        
        return math.degrees(lat_result), math.degrees(lon_result)
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing between two points."""
        import math
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(delta_lon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon_rad))
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        return (bearing_deg + 360) % 360
    
    def _calculate_bearing_consistency(self, main_bearing: float, bearing1: float, bearing2: float) -> float:
        """Calculate how consistent bearings are with the main route direction."""
        
        def angle_difference(a1, a2):
            diff = abs(a1 - a2)
            return min(diff, 360 - diff)
        
        # Calculate how much each bearing deviates from main bearing
        dev1 = angle_difference(main_bearing, bearing1)
        dev2 = angle_difference(main_bearing, bearing2)
        
        # Good consistency means small deviations
        consistency1 = max(0, 1 - dev1 / 90)  # Normalize to 0-1
        consistency2 = max(0, 1 - dev2 / 90)
        
        return (consistency1 + consistency2) / 2
    
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
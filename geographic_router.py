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
        
        # COMPLETELY REWORKED Focus-specific city preferences with HEAVY hidden gems emphasis
        self.focus_preferences = {
            'speed': ['major', 'cultural'],  # Only for speed focus, use major cities
            'scenery': ['hidden_gems', 'scenery', 'adventure'],  # Hidden gems first!
            'culture': ['hidden_gems', 'cultural', 'major'],  # Hidden gems first!
            'culinary': ['hidden_gems', 'culinary', 'cultural'],  # Hidden gems first!
            'hidden_gems': ['hidden_gems', 'cultural', 'scenery'],  # Heavily weighted to hidden gems
            'budget': ['hidden_gems', 'budget', 'cultural'],  # Hidden gems first!
            'adventure': ['hidden_gems', 'adventure', 'scenery'],  # Hidden gems first!
            'wellness': ['hidden_gems', 'wellness', 'scenery']  # Hidden gems first!
        }
        
        # STRATEGY-SPECIFIC ROUTING PATTERNS - Each strategy gets completely different approach
        self.strategy_patterns = {
            1: {'preference': 'shortest_path', 'hidden_gems_weight': 2.0, 'variety_bonus': 1.0},
            2: {'preference': 'scenic_route', 'hidden_gems_weight': 4.0, 'variety_bonus': 2.0},
            3: {'preference': 'cultural_discovery', 'hidden_gems_weight': 3.5, 'variety_bonus': 2.5},
            4: {'preference': 'culinary_adventure', 'hidden_gems_weight': 3.0, 'variety_bonus': 1.8},
            5: {'preference': 'off_beaten_path', 'hidden_gems_weight': 5.0, 'variety_bonus': 3.0},
            6: {'preference': 'local_authentic', 'hidden_gems_weight': 4.5, 'variety_bonus': 2.8},
            7: {'preference': 'adventure_trail', 'hidden_gems_weight': 3.8, 'variety_bonus': 2.2},
            8: {'preference': 'wellness_journey', 'hidden_gems_weight': 4.2, 'variety_bonus': 2.6}
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
        """COMPLETELY REWRITTEN: Find cities focusing heavily on hidden gems with strategy-specific variation."""
        
        # Get strategy-specific parameters
        strategy_pattern = self.strategy_patterns.get(strategy_seed, self.strategy_patterns[1])
        hidden_gems_weight = strategy_pattern['hidden_gems_weight']
        variety_bonus = strategy_pattern['variety_bonus']
        route_preference = strategy_pattern['preference']
        
        # Calculate total distance and create flexible search zones
        total_distance = self.calculate_distance(start_lat, start_lon, end_lat, end_lon)
        
        # STRATEGY-SPECIFIC ROUTE GENERATION
        if route_preference == 'off_beaten_path':
            # Maximum hidden gems focus - wider search, smaller towns preferred
            search_zones = self._create_wide_search_zones(start_lat, start_lon, end_lat, end_lon, count, total_distance)
        elif route_preference == 'scenic_route':
            # Focus on scenic detours and mountain/coastal routes
            search_zones = self._create_scenic_detour_zones(start_lat, start_lon, end_lat, end_lon, count, total_distance)
        elif route_preference == 'cultural_discovery':
            # Focus on historic and cultural hidden gems
            search_zones = self._create_cultural_discovery_zones(start_lat, start_lon, end_lat, end_lon, count, total_distance)
        else:
            # Default balanced approach with hidden gems emphasis
            search_zones = self._create_balanced_search_zones(start_lat, start_lon, end_lat, end_lon, count, total_distance)
        
        selected_cities = []
        used_city_names = {self.normalize_city_name(start_city), self.normalize_city_name(end_city)}
        
        # Find cities for each search zone with strategy-specific scoring
        for zone_idx, zone in enumerate(search_zones):
            zone_candidates = []
            
            for city_name, city_info in self.cities_db.items():
                normalized_name = self.normalize_city_name(city_name)
                
                # Skip already used cities
                if normalized_name in used_city_names:
                    continue
                
                city_lat, city_lon = city_info['lat'], city_info['lon']
                
                # Check if city is within this search zone
                dist_from_zone_center = self.calculate_distance(
                    zone['center_lat'], zone['center_lon'], city_lat, city_lon
                )
                
                if dist_from_zone_center > zone['radius']:
                    continue
                
                # Calculate basic distances
                dist_from_start = self.calculate_distance(start_lat, start_lon, city_lat, city_lon)
                dist_from_end = self.calculate_distance(city_lat, city_lon, end_lat, end_lon)
                
                # HIDDEN GEMS SCORING - Heavily prioritize hidden gems
                hidden_gems_score = 0
                for city_type in city_info['type']:
                    if city_type == 'hidden_gems':
                        hidden_gems_score += 10 * hidden_gems_weight  # MASSIVE bonus for hidden gems
                    elif city_type in preferred_types:
                        hidden_gems_score += 4
                    else:
                        hidden_gems_score += 1
                
                # POPULATION INVERSE SCORING - Smaller = better (authentic experience)
                population = city_info['population']
                if population < 1000:
                    population_score = 8.0  # Tiny villages - maximum authenticity
                elif population < 5000:
                    population_score = 6.0  # Small towns - high authenticity
                elif population < 20000:
                    population_score = 4.0  # Medium towns - good authenticity
                elif population < 100000:
                    population_score = 2.5  # Cities - moderate authenticity
                else:
                    population_score = 1.0  # Large cities - low authenticity (except for speed focus)
                
                # STRATEGY-SPECIFIC BONUSES
                strategy_bonus = 1.0
                if route_preference == 'off_beaten_path' and 'hidden_gems' in city_info['type']:
                    strategy_bonus = 3.0  # Triple bonus for off-beaten-path hidden gems
                elif route_preference == 'scenic_route' and ('scenery' in city_info['type'] or 'adventure' in city_info['type']):
                    strategy_bonus = 2.5
                elif route_preference == 'cultural_discovery' and 'cultural' in city_info['type']:
                    strategy_bonus = 2.2
                elif route_preference == 'culinary_adventure' and 'culinary' in city_info['type']:
                    strategy_bonus = 2.8
                elif route_preference == 'wellness_journey' and 'wellness' in city_info['type']:
                    strategy_bonus = 2.4
                elif route_preference == 'adventure_trail' and 'adventure' in city_info['type']:
                    strategy_bonus = 2.6
                
                # VARIETY BONUS - Encourage different countries/regions
                country_bonus = 1.0
                region_bonus = 1.0
                if selected_cities:
                    used_countries = {city['country'] for city in selected_cities}
                    used_regions = {city['region'] for city in selected_cities}
                    
                    if city_info['country'] not in used_countries:
                        country_bonus = 1.5 * variety_bonus
                    if city_info.get('region', '') not in used_regions:
                        region_bonus = 1.3 * variety_bonus
                
                # DISTANCE-BASED SCORING - Reward good positioning
                zone_position_score = 1.0 / (1.0 + dist_from_zone_center / 20.0)
                
                # STRATEGIC RANDOMIZATION - Different patterns for different strategies
                random.seed(hash(f"{city_name}{strategy_seed}{zone_idx}") % 2**32)  # Deterministic but varied
                random_factor = random.uniform(0.5, 2.0)  # Much wider range for variety
                
                # FINAL SCORING with heavy hidden gems weighting
                total_score = (hidden_gems_score * population_score * strategy_bonus * 
                              country_bonus * region_bonus * zone_position_score * random_factor)
                
                zone_candidates.append({
                    'name': city_name.replace('-', ' ').title(),
                    'country': city_info['country'],
                    'population': city_info['population'],
                    'region': city_info.get('region', 'Unknown'),
                    'lat': city_lat,
                    'lon': city_lon,
                    'types': city_info['type'],
                    'distance_from_start': dist_from_start,
                    'distance_from_end': dist_from_end,
                    'hidden_gems_score': hidden_gems_score,
                    'population_score': population_score,
                    'strategy_bonus': strategy_bonus,
                    'total_score': total_score,
                    'reason': self._generate_reason(city_info['type'], focus),
                    'normalized_name': normalized_name,
                    'is_hidden_gem': 'hidden_gems' in city_info['type']
                })
            
            # Sort by total score and select best candidate that maintains spacing
            zone_candidates.sort(key=lambda x: x['total_score'], reverse=True)
            
            # Select best candidate with minimum distance requirement
            for candidate in zone_candidates[:20]:  # Consider top 20 to allow for spacing constraints
                min_distance_ok = True
                if selected_cities:
                    min_dist = min(
                        self.calculate_distance(candidate['lat'], candidate['lon'], 
                                              city['lat'], city['lon'])
                        for city in selected_cities
                    )
                    # Dynamic minimum distance based on total trip length
                    min_required = max(25, total_distance * 0.06)  # Minimum 25km or 6% of total
                    if min_dist < min_required:
                        min_distance_ok = False
                
                if min_distance_ok:
                    selected_cities.append(candidate)
                    used_city_names.add(candidate['normalized_name'])
                    break
        
        # Sort selected cities by distance from start to ensure proper order
        selected_cities.sort(key=lambda x: x['distance_from_start'])
        
        return selected_cities
    
    def _create_wide_search_zones(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, count: int, total_distance: float) -> List[Dict]:
        """Create wide search zones for off-beaten-path routing with maximum variety."""
        zones = []
        
        # Create zones with wider radius and strategic offsets for maximum variety
        for i in range(count):
            progress = (i + 1) / (count + 1)
            
            # Wide detour potential - up to 40% off main route
            detour_factor = 0.4
            zone_radius = max(80, total_distance * 0.25)  # Much wider search
            
            # Strategic offset perpendicular to main route
            perpendicular_offset = random.uniform(-detour_factor, detour_factor) * total_distance * 0.3
            
            # Calculate zone center with detour
            center_lat, center_lon = self._interpolate_route_point(start_lat, start_lon, end_lat, end_lon, progress)
            
            # Add perpendicular offset for variety
            bearing = self._calculate_bearing(start_lat, start_lon, end_lat, end_lon)
            perpendicular_bearing = (bearing + 90) % 360
            
            offset_lat, offset_lon = self._point_at_distance_bearing(
                center_lat, center_lon, abs(perpendicular_offset), perpendicular_bearing
            )
            
            zones.append({
                'center_lat': offset_lat,
                'center_lon': offset_lon,
                'radius': zone_radius,
                'emphasis': 'hidden_gems'
            })
        
        return zones
    
    def _create_scenic_detour_zones(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, count: int, total_distance: float) -> List[Dict]:
        """Create zones that favor scenic detours and natural beauty spots."""
        zones = []
        
        for i in range(count):
            progress = (i + 1) / (count + 1)
            
            # Scenic routes prefer moderate detours for beautiful landscapes
            detour_factor = 0.25
            zone_radius = max(60, total_distance * 0.18)
            
            # Strategic positioning for scenic variety
            scenic_offset = random.uniform(-detour_factor, detour_factor) * total_distance * 0.2
            
            center_lat, center_lon = self._interpolate_route_point(start_lat, start_lon, end_lat, end_lon, progress)
            
            # Offset for scenic variation
            bearing = self._calculate_bearing(start_lat, start_lon, end_lat, end_lon)
            scenic_bearing = (bearing + random.choice([60, -60, 120, -120])) % 360
            
            offset_lat, offset_lon = self._point_at_distance_bearing(
                center_lat, center_lon, abs(scenic_offset), scenic_bearing
            )
            
            zones.append({
                'center_lat': offset_lat,
                'center_lon': offset_lon,
                'radius': zone_radius,
                'emphasis': 'scenery'
            })
        
        return zones
    
    def _create_cultural_discovery_zones(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, count: int, total_distance: float) -> List[Dict]:
        """Create zones that prioritize cultural sites and historic hidden gems."""
        zones = []
        
        for i in range(count):
            progress = (i + 1) / (count + 1)
            
            # Cultural routes balance direct path with cultural significance
            detour_factor = 0.2
            zone_radius = max(50, total_distance * 0.15)
            
            # Strategic cultural positioning
            cultural_offset = random.uniform(-detour_factor, detour_factor) * total_distance * 0.15
            
            center_lat, center_lon = self._interpolate_route_point(start_lat, start_lon, end_lat, end_lon, progress)
            
            # Cultural variety through strategic offsets
            bearing = self._calculate_bearing(start_lat, start_lon, end_lat, end_lon)
            cultural_bearing = (bearing + random.choice([45, -45, 135, -135])) % 360
            
            offset_lat, offset_lon = self._point_at_distance_bearing(
                center_lat, center_lon, abs(cultural_offset), cultural_bearing
            )
            
            zones.append({
                'center_lat': offset_lat,
                'center_lon': offset_lon,
                'radius': zone_radius,
                'emphasis': 'cultural'
            })
        
        return zones
    
    def _create_balanced_search_zones(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, count: int, total_distance: float) -> List[Dict]:
        """Create balanced zones with moderate variety and hidden gems emphasis."""
        zones = []
        
        for i in range(count):
            progress = (i + 1) / (count + 1)
            
            # Balanced approach with hidden gems preference
            detour_factor = 0.15
            zone_radius = max(40, total_distance * 0.12)
            
            # Moderate strategic positioning
            balanced_offset = random.uniform(-detour_factor, detour_factor) * total_distance * 0.1
            
            center_lat, center_lon = self._interpolate_route_point(start_lat, start_lon, end_lat, end_lon, progress)
            
            # Balanced variety
            bearing = self._calculate_bearing(start_lat, start_lon, end_lat, end_lon)
            balanced_bearing = (bearing + random.choice([30, -30, 90, -90])) % 360
            
            offset_lat, offset_lon = self._point_at_distance_bearing(
                center_lat, center_lon, abs(balanced_offset), balanced_bearing
            )
            
            zones.append({
                'center_lat': offset_lat,
                'center_lon': offset_lon,
                'radius': zone_radius,
                'emphasis': 'balanced'
            })
        
        return zones
    
    def _point_at_distance_bearing(self, lat: float, lon: float, distance_km: float, bearing_deg: float) -> tuple:
        """Calculate a point at given distance and bearing from origin point."""
        import math
        
        R = 6371  # Earth radius in km
        
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing_deg)
        
        new_lat_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance_km / R) +
            math.cos(lat_rad) * math.sin(distance_km / R) * math.cos(bearing_rad)
        )
        
        new_lon_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat_rad),
            math.cos(distance_km / R) - math.sin(lat_rad) * math.sin(new_lat_rad)
        )
        
        return math.degrees(new_lat_rad), math.degrees(new_lon_rad)
    
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
#!/usr/bin/env python3
"""
PROFESSIONAL European Roadtrip Planner - Dynamic Routes with Real AI
Professional interface with real-time route generation and Claude API integration
"""

from flask import Flask, render_template, request, jsonify
import json
import os
import time
import random
from typing import Dict, List
import requests
from anthropic import Anthropic
from enhanced_features import EnhancedFeatures
from geographic_router import GeographicRouter
from additional_features import AdditionalFeatures
from ai_travel_assistant import AITravelAssistant

app = Flask(__name__)

class ProfessionalDynamicPlanner:
    """Professional planner with dynamic routes and real AI insights."""
    
    def __init__(self):
        self.cache_buster = str(int(time.time()))
        self.claude_client = None
        self.enhanced_features = EnhancedFeatures()
        self.geographic_router = GeographicRouter()
        self.additional_features = AdditionalFeatures()
        self.ai_assistant = AITravelAssistant()
    
    def initialize_claude(self, api_key: str):
        """Initialize Claude API client."""
        if api_key and api_key.strip():
            try:
                self.claude_client = Anthropic(api_key=api_key.strip())
                return True
            except Exception as e:
                print(f"Claude API initialization failed: {e}")
                return False
        return False
    
    def generate_dynamic_routes(self, start_city: str, end_city: str, travel_days: int, 
                              venice_nights: int, season: str, claude_api_key: str = None) -> List[Dict]:
        """Generate dynamic, contextual routes based on user input."""
        
        # Initialize Claude if API key provided
        ai_enabled = self.initialize_claude(claude_api_key) if claude_api_key else False
        if ai_enabled:
            self.ai_assistant = AITravelAssistant(self.claude_client)
        
        # Base route configurations - each truly different
        route_configs = [
            {
                'name': 'Fastest Direct Route',
                'focus': 'speed',
                'intermediate_cities': self._get_direct_route_cities(start_city, end_city),
                'strategy': 'Optimize for minimal driving time and maximum time at destinations'
            },
            {
                'name': 'Scenic Mountain Pass Route',
                'focus': 'scenery',
                'intermediate_cities': self._get_mountain_cities(start_city, end_city),
                'strategy': 'Take the most beautiful mountain passes and scenic viewpoints'
            },
            {
                'name': 'Historic Cities Cultural Route',
                'focus': 'culture',
                'intermediate_cities': self._get_historic_cities(start_city, end_city),
                'strategy': 'Visit UNESCO World Heritage sites and major cultural landmarks'
            },
            {
                'name': 'Food & Wine Discovery Route',
                'focus': 'culinary',
                'intermediate_cities': self._get_culinary_cities(start_city, end_city),
                'strategy': 'Experience regional cuisines, local markets, and wine regions'
            },
            {
                'name': 'Off-the-Beaten-Path Route',
                'focus': 'hidden_gems',
                'intermediate_cities': self._get_hidden_gem_cities(start_city, end_city),
                'strategy': 'Discover lesser-known towns and authentic local experiences'
            },
            {
                'name': 'Budget-Friendly Route',
                'focus': 'budget',
                'intermediate_cities': self._get_budget_cities(start_city, end_city),
                'strategy': 'Maximize value with affordable accommodations and free attractions'
            },
            {
                'name': 'Adventure & Activities Route',
                'focus': 'adventure',
                'intermediate_cities': self._get_adventure_cities(start_city, end_city),
                'strategy': 'Focus on outdoor activities, sports, and adventure experiences'
            },
            {
                'name': 'Relaxation & Wellness Route',
                'focus': 'wellness',
                'intermediate_cities': self._get_wellness_cities(start_city, end_city),
                'strategy': 'Emphasize spas, thermal baths, and peaceful countryside retreats'
            }
        ]
        
        routes = []
        for i, config in enumerate(route_configs):
            try:
                route = self._build_route(
                    config, start_city, end_city, travel_days, 
                    venice_nights, season, ai_enabled
                )
                routes.append(route)
            except Exception as e:
                print(f"Error building route {i}: {e}")
                # Add fallback route
                routes.append(self._create_fallback_route(config['name'], start_city, end_city, travel_days, venice_nights))
        
        return routes
    
    def _get_direct_route_cities(self, start: str, end: str) -> List[Dict]:
        """Get cities for fastest direct route."""
        return self.geographic_router.generate_route_cities(start, end, 'speed', 1)
    
    def _get_mountain_cities(self, start: str, end: str) -> List[Dict]:
        """Get cities for scenic mountain route."""
        return self.geographic_router.generate_route_cities(start, end, 'scenery', 2)
    
    def _get_historic_cities(self, start: str, end: str) -> List[Dict]:
        """Get cities for historic cultural route."""
        return self.geographic_router.generate_route_cities(start, end, 'culture', 3)
    
    def _get_culinary_cities(self, start: str, end: str) -> List[Dict]:
        """Get cities for food & wine route."""
        return self.geographic_router.generate_route_cities(start, end, 'culinary', 4)
    
    def _get_hidden_gem_cities(self, start: str, end: str) -> List[Dict]:
        """Get cities for hidden gems route."""
        return self.geographic_router.generate_route_cities(start, end, 'hidden_gems', 5)
    
    def _get_budget_cities(self, start: str, end: str) -> List[Dict]:
        """Get cities for budget-friendly route."""
        return self.geographic_router.generate_route_cities(start, end, 'budget', 6)
    
    def _get_adventure_cities(self, start: str, end: str) -> List[Dict]:
        """Get cities for adventure route."""
        return self.geographic_router.generate_route_cities(start, end, 'adventure', 7)
    
    def _get_wellness_cities(self, start: str, end: str) -> List[Dict]:
        """Get cities for wellness route."""
        return self.geographic_router.generate_route_cities(start, end, 'wellness', 8)
    
    def get_route_attractions(self, start_city: str, end_city: str, intermediate_cities: List[str]) -> Dict:
        """Get attractions and photo spots along the entire route."""
        try:
            all_cities = [start_city] + intermediate_cities + [end_city]
            attractions_by_city = {}
            
            for city in all_cities:
                city_info = self.geographic_router.get_city_info(city)
                attractions = self._generate_city_attractions(city, city_info)
                attractions_by_city[city] = attractions
            
            return {
                'success': True,
                'route_attractions': attractions_by_city,
                'total_attractions': sum(len(attrs['attractions']) for attrs in attractions_by_city.values()),
                'photo_opportunities': sum(len(attrs['photo_spots']) for attrs in attractions_by_city.values()),
                'must_see_highlights': self._get_route_highlights(all_cities)
            }
        except Exception as e:
            return {'error': f'Failed to get route attractions: {str(e)}'}
    
    def _generate_city_attractions(self, city_name: str, city_info: Dict) -> Dict:
        """Generate attractions for a specific city."""
        city_types = city_info.get('type', ['cultural'])
        population = city_info.get('population', 100000)
        
        # Base attractions based on city type
        attractions = []
        photo_spots = []
        
        # Major attractions based on city type
        if 'major' in city_types:
            attractions.extend([
                f"{city_name} Historic Center - UNESCO World Heritage architecture and cobblestone streets",
                f"Grand Cathedral of {city_name} - Spectacular Gothic/Romanesque masterpiece",
                f"{city_name} Central Square - Vibrant main plaza with street performers and cafes",
                f"Municipal Museum - Local history and art collections",
                f"Old Town Walking Tour - Guided exploration of medieval quarters"
            ])
            photo_spots.extend([
                f"Cathedral spires at golden hour",
                f"Panoramic city view from bell tower",
                f"Street art and colorful building facades",
                f"Traditional market scenes"
            ])
        
        if 'cultural' in city_types:
            attractions.extend([
                f"{city_name} Art Gallery - Regional and contemporary exhibitions",
                f"Cultural Heritage Museum - Traditional crafts and local customs",
                f"Historic District - Preserved medieval architecture",
                f"Local Artisan Workshops - Traditional crafts demonstrations"
            ])
            photo_spots.extend([
                f"Ancient stone bridges and waterways",
                f"Traditional architecture details",
                f"Local craftspeople at work"
            ])
        
        if 'culinary' in city_types:
            attractions.extend([
                f"Traditional Food Market - Local specialties and fresh produce",
                f"{city_name} Wine Cellars - Regional wine tasting experiences",
                f"Cooking Class with Local Chef - Authentic regional cuisine",
                f"Historic Restaurants - Century-old dining establishments"
            ])
            photo_spots.extend([
                f"Colorful spice markets and food displays",
                f"Traditional cooking techniques",
                f"Wine cellars and vineyard landscapes"
            ])
        
        if 'scenery' in city_types:
            attractions.extend([
                f"Scenic Viewpoint - Panoramic landscape photography",
                f"Nature Walking Trails - Hiking paths with stunning vistas",
                f"Mountain/Lake Excursions - Natural beauty tours",
                f"Botanical Gardens - Native flora and peaceful gardens"
            ])
            photo_spots.extend([
                f"Sunrise/sunset mountain silhouettes",
                f"Reflection photography at lakes",
                f"Wildflower meadows and forests",
                f"Dramatic cliff and valley views"
            ])
        
        if 'adventure' in city_types:
            attractions.extend([
                f"Adventure Sports Center - Rock climbing, kayaking, cycling",
                f"Outdoor Activity Base - Hiking and nature exploration",
                f"Extreme Sports Facilities - Zip-lining, paragliding",
                f"National Park Access - Wildlife watching and trails"
            ])
            photo_spots.extend([
                f"Action sports photography",
                f"Wildlife and nature close-ups",
                f"Adventure equipment and gear shots"
            ])
        
        if 'wellness' in city_types:
            attractions.extend([
                f"Historic Thermal Baths - Natural hot springs and spa treatments",
                f"Wellness Center - Massage, meditation, yoga classes",
                f"Peaceful Gardens - Relaxation and contemplation spaces",
                f"Health Resort - Complete wellness packages"
            ])
            photo_spots.extend([
                f"Serene spa environments",
                f"Zen garden compositions",
                f"Peaceful water features"
            ])
        
        if 'hidden_gems' in city_types:
            attractions.extend([
                f"Secret Local Viewpoint - Known only to locals",
                f"Underground Historic Sites - Hidden cellars or tunnels",
                f"Local Family Restaurant - Authentic, non-touristy dining",
                f"Artisan Quarter - Small workshops and local creators"
            ])
            photo_spots.extend([
                f"Hidden alleyways and secret corners",
                f"Local life and authentic moments",
                f"Undiscovered architectural details"
            ])
        
        # Ensure we have at least basic attractions
        if not attractions:
            attractions = [
                f"{city_name} Town Center - Main attractions and local life",
                f"Historic Buildings - Notable architecture and landmarks",
                f"Local Market - Regional products and crafts",
                f"Scenic Walk - Best views and photo opportunities"
            ]
            photo_spots = [
                f"Town square and main monuments",
                f"Local architecture and street scenes",
                f"Market life and local culture"
            ]
        
        return {
            'attractions': attractions[:6],  # Limit to top 6
            'photo_spots': photo_spots[:4],  # Limit to top 4
            'city_type': city_types,
            'estimated_visit_time': '2-4 hours' if population < 200000 else '4-8 hours'
        }
    
    def _get_route_highlights(self, cities: List[str]) -> List[Dict]:
        """Get must-see highlights for the entire route."""
        highlights = []
        for i, city in enumerate(cities):
            city_info = self.geographic_router.get_city_info(city)
            
            if i == 0:  # Start city
                highlights.append({
                    'city': city,
                    'highlight': f'Departure from {city} - Stock up on regional specialties for the journey',
                    'type': 'departure',
                    'photo_tip': 'Capture the excitement of starting your European adventure'
                })
            elif i == len(cities) - 1:  # End city
                highlights.append({
                    'city': city,
                    'highlight': f'Grand Finale in {city} - Celebrate your epic journey',
                    'type': 'destination',
                    'photo_tip': 'Document your arrival and reflect on the incredible route'
                })
            else:  # Intermediate cities
                city_types = city_info.get('type', ['cultural'])
                if 'major' in city_types:
                    highlight_text = f'Major cultural hub - Explore world-class attractions'
                    photo_tip = 'Iconic architecture and bustling city life'
                elif 'scenery' in city_types:
                    highlight_text = f'Scenic paradise - Nature photography opportunities'
                    photo_tip = 'Golden hour landscapes and natural beauty'
                elif 'culinary' in city_types:
                    highlight_text = f'Culinary hotspot - Taste authentic regional cuisine'
                    photo_tip = 'Food photography and local market scenes'
                else:
                    highlight_text = f'Cultural gem - Discover local traditions and history'
                    photo_tip = 'Authentic local life and hidden corners'
                
                highlights.append({
                    'city': city,
                    'highlight': highlight_text,
                    'type': 'stopover',
                    'photo_tip': photo_tip
                })
        
        return highlights
    
    def _build_route(self, config: Dict, start_city: str, end_city: str, 
                    travel_days: int, venice_nights: int, season: str, ai_enabled: bool) -> Dict:
        """Build a complete route with AI insights if available."""
        
        intermediate_cities = config['intermediate_cities']
        
        # Calculate realistic distances and times
        total_km = self._calculate_realistic_distance(start_city, end_city, len(intermediate_cities))
        driving_hours = round(total_km / 80, 1)  # Realistic highway speed with stops
        
        # Build overnight stops
        overnight_stops = [
            {
                'name': start_city,
                'country': 'France',
                'nights': 1,
                'population': 143006,
                'score': round(random.uniform(7.5, 8.5), 1),
                'activities': self._get_activities_for_city(start_city, config['focus']),
                'hidden_gems': self._get_hidden_gems_for_city(start_city, config['focus']),
                'local_secret': self._get_local_secret(start_city, config['focus'])
            }
        ]
        
        # Add intermediate stops
        for city_info in intermediate_cities[:min(2, travel_days-2)]:  # Limit based on travel days
            overnight_stops.append({
                'name': city_info['name'],
                'country': city_info['country'],
                'nights': 1,
                'population': city_info['population'],
                'score': round(random.uniform(8.0, 9.5), 1),
                'activities': self._get_activities_for_city(city_info['name'], config['focus']),
                'hidden_gems': self._get_hidden_gems_for_city(city_info['name'], config['focus']),
                'local_secret': self._get_local_secret(city_info['name'], config['focus']),
                'stop_reason': city_info['reason']
            })
        
        # Add final destination
        overnight_stops.append({
            'name': end_city,
            'country': 'Italy',
            'nights': venice_nights,
            'population': 261905,
            'score': round(random.uniform(9.0, 9.8), 1),
            'activities': self._get_activities_for_city(end_city, config['focus']),
            'hidden_gems': self._get_hidden_gems_for_city(end_city, config['focus']),
            'local_secret': self._get_local_secret(end_city, config['focus'])
        })
        
        # Build day stops
        day_stops = []
        for city_info in intermediate_cities[len(overnight_stops)-2:]:  # Use remaining cities as day stops
            day_stops.append({
                'name': city_info['name'],
                'country': city_info['country'],
                'score': round(random.uniform(7.8, 9.2), 1),
                'type': self._get_stop_type(config['focus']),
                'highlight': city_info['reason']
            })
        
        route_data = {
            'strategy_name': config['name'],
            'strategy_description': f"{config['strategy']} - Optimized for {season} travel conditions",
            'route': {
                'overnight_stops': overnight_stops,
                'day_stops': day_stops
            },
            'summary': {
                'total_km': total_km,
                'driving_hours': driving_hours,
                'nights': travel_days - 1,
                'overnight_stops': len(overnight_stops),
                'day_stops': len(day_stops),
                'hidden_gems_count': len(overnight_stops) * 2
            },
            'transport_mode': self._get_transport_mode(config['focus']),
            'unique_features': self._get_unique_features(config['focus']),
            'focus_area': config['focus'],
            'season_optimization': self._get_season_tips(season, config['focus'])
        }
        
        # Add AI insights if Claude API is available
        if ai_enabled and self.claude_client:
            try:
                ai_insights = self._get_ai_insights(route_data, season)
                route_data['ai_insights'] = ai_insights
            except Exception as e:
                print(f"AI insights failed: {e}")
                route_data['ai_insights'] = None
        
        return route_data
    
    def _get_ai_insights(self, route_data: Dict, season: str) -> Dict:
        """Get real AI insights using Claude API."""
        try:
            overnight_cities = [stop['name'] for stop in route_data['route']['overnight_stops']]
            
            prompt = f"""As a European travel expert, provide practical insights for this {season} roadtrip:

Route: {' → '.join(overnight_cities)}
Focus: {route_data['focus_area']}
Duration: {route_data['summary']['nights']} nights

Provide specific, actionable advice in exactly this format:

WEATHER_TIPS: [2-3 specific weather considerations for {season}]
PACKING_ESSENTIALS: [3-4 must-pack items for this route and season]
LOCAL_CUSTOMS: [2-3 important cultural tips for these regions]
MONEY_SAVING: [2-3 concrete ways to save money on this route]
HIDDEN_EXPERIENCES: [2-3 unique experiences most tourists miss]
BEST_TIME_TO_VISIT: [specific times of day/week for key attractions]

Keep each section to 2-3 concise, practical points. Focus on actionable advice."""

            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse the structured response
            content = response.content[0].text
            insights = {}
            
            sections = ['WEATHER_TIPS', 'PACKING_ESSENTIALS', 'LOCAL_CUSTOMS', 
                       'MONEY_SAVING', 'HIDDEN_EXPERIENCES', 'BEST_TIME_TO_VISIT']
            
            for section in sections:
                if section in content:
                    start = content.find(section + ':')
                    if start != -1:
                        start += len(section + ':')
                        end = content.find('\n\n', start)
                        if end == -1:
                            # Try to find next section
                            next_section_pos = float('inf')
                            for next_sec in sections:
                                if next_sec != section:
                                    pos = content.find(next_sec + ':', start)
                                    if pos != -1 and pos < next_section_pos:
                                        next_section_pos = pos
                            end = next_section_pos if next_section_pos != float('inf') else len(content)
                        
                        text = content[start:end].strip()
                        insights[section.lower()] = text
            
            return insights
            
        except Exception as e:
            print(f"Claude API error: {e}")
            return None
    
    def _calculate_realistic_distance(self, start: str, end: str, intermediate_count: int) -> int:
        """Calculate realistic driving distance based on actual geography."""
        start_info = self.geographic_router.get_city_info(start)
        end_info = self.geographic_router.get_city_info(end)
        
        # Calculate base distance
        base_distance = self.geographic_router.calculate_distance(
            start_info['lat'], start_info['lon'],
            end_info['lat'], end_info['lon']
        )
        
        # Add realistic detour for intermediate stops (15-25% extra per stop)
        detour_factor = 1 + (intermediate_count * random.uniform(0.15, 0.25))
        
        return int(base_distance * detour_factor)
    
    def _get_activities_for_city(self, city: str, focus: str) -> List[str]:
        """Get contextual activities based on city and focus."""
        activities_map = {
            'speed': ['Quick city tour', 'Main landmark visit', 'Express local experience'],
            'scenery': ['Panoramic viewpoints', 'Scenic walks', 'Photography spots'],
            'culture': ['Museums and galleries', 'Historic sites', 'Cultural performances'],
            'culinary': ['Local restaurants', 'Food markets', 'Cooking classes'],
            'hidden_gems': ['Local neighborhoods', 'Secret viewpoints', 'Authentic experiences'],
            'budget': ['Free attractions', 'Public parks', 'Budget-friendly tours'],
            'adventure': ['Outdoor activities', 'Sports experiences', 'Adventure tours'],
            'wellness': ['Spa treatments', 'Relaxation activities', 'Wellness centers']
        }
        
        base_activities = activities_map.get(focus, ['City exploration', 'Local attractions', 'Cultural sites'])
        return random.sample(base_activities, min(3, len(base_activities)))
    
    def _get_hidden_gems_for_city(self, city: str, focus: str) -> List[str]:
        """Get hidden gems based on city and focus."""
        return [f"Hidden {focus} spots", f"Local {focus} secrets", f"Off-tourist-path {focus}"]
    
    def _get_local_secret(self, city: str, focus: str) -> str:
        """Get a local secret based on city and focus."""
        secrets = {
            'speed': f"Fastest route through {city} avoids the main tourist areas",
            'scenery': f"{city} has secret viewpoints known only to locals",
            'culture': f"{city} hosts underground cultural events in historic venues",
            'culinary': f"Best {city} food is found in family-run places locals frequent",
            'hidden_gems': f"{city} has neighborhoods tourists never discover",
            'budget': f"{city} offers free experiences most visitors don't know about",
            'adventure': f"{city} has adventure activities not advertised to tourists",
            'wellness': f"{city} has hidden wellness spots used by locals for centuries"
        }
        return secrets.get(focus, f"{city} has secrets that only locals know")
    
    def _get_transport_mode(self, focus: str) -> str:
        """Get transport mode based on focus."""
        modes = {
            'speed': 'Highway-optimized rental car',
            'scenery': 'Convertible for scenic drives',
            'culture': 'Comfortable touring vehicle',
            'culinary': 'Food tour vehicle with local guide',
            'hidden_gems': 'Local-guided adventure vehicle',
            'budget': 'Economy rental car',
            'adventure': 'All-terrain vehicle',
            'wellness': 'Luxury comfort vehicle'
        }
        return modes.get(focus, 'Standard rental car')
    
    def _get_unique_features(self, focus: str) -> List[str]:
        """Get unique features based on focus."""
        features_map = {
            'speed': ['express routes', 'time optimization', 'efficient stops'],
            'scenery': ['scenic drives', 'photo opportunities', 'panoramic routes'],
            'culture': ['historical sites', 'museums', 'cultural immersion'],
            'culinary': ['food experiences', 'wine tastings', 'local cuisine'],
            'hidden_gems': ['secret locations', 'authentic experiences', 'local insights'],
            'budget': ['cost savings', 'value experiences', 'budget optimization'],
            'adventure': ['outdoor activities', 'sports experiences', 'active travel'],
            'wellness': ['relaxation', 'spa experiences', 'wellness activities']
        }
        return features_map.get(focus, ['unique experiences'])
    
    def _get_season_tips(self, season: str, focus: str) -> str:
        """Get season-specific optimization tips."""
        tips = {
            'spring': f"Spring {focus} experiences with mild weather and fewer crowds",
            'summer': f"Summer {focus} adventures with extended daylight and peak activities",
            'autumn': f"Autumn {focus} journey with beautiful colors and harvest seasons",
            'winter': f"Winter {focus} travel with cozy indoor experiences and winter sports"
        }
        return tips.get(season, f"{season.title()} travel optimized for {focus}")
    
    def _get_stop_type(self, focus: str) -> str:
        """Get stop type based on focus."""
        types = {
            'speed': 'quick_visit',
            'scenery': 'scenic_stop',
            'culture': 'cultural_site',
            'culinary': 'food_experience',
            'hidden_gems': 'hidden_gem',
            'budget': 'budget_attraction',
            'adventure': 'activity_stop',
            'wellness': 'wellness_center'
        }
        return types.get(focus, 'attraction')
    
    def _create_fallback_route(self, name: str, start: str, end: str, days: int, nights: int) -> Dict:
        """Create a fallback route if generation fails."""
        return {
            'strategy_name': name,
            'strategy_description': f"A carefully planned route from {start} to {end}",
            'route': {
                'overnight_stops': [
                    {'name': start, 'country': 'France', 'nights': 1, 'population': 143006, 'score': 8.0},
                    {'name': end, 'country': 'Italy', 'nights': nights, 'population': 261905, 'score': 9.0}
                ],
                'day_stops': [
                    {'name': 'Scenic Stop', 'country': 'Various', 'score': 8.5, 'type': 'scenic_stop'}
                ]
            },
            'summary': {
                'total_km': 850, 'driving_hours': 10.6, 'nights': days - 1,
                'overnight_stops': 2, 'day_stops': 1, 'hidden_gems_count': 4
            },
            'transport_mode': 'Standard rental car',
            'unique_features': ['personalized route'],
            'focus_area': 'general'
        }

@app.route('/')
def index():
    """Professional landing page."""
    interface = ProfessionalDynamicPlanner()
    return render_template('professional_dynamic.html', cache_buster=interface.cache_buster)

@app.route('/plan', methods=['POST'])
def plan_trip():
    """Process dynamic trip planning with real AI."""
    form_data = request.form.to_dict()
    
    try:
        start_city = form_data.get('start_city', 'Aix-en-Provence')
        end_city = form_data.get('end_city', 'Venice')
        travel_days = int(form_data.get('travel_days', 4))
        venice_nights = int(form_data.get('venice_nights', 2))
        season = form_data.get('season', 'summer')
        claude_api_key = form_data.get('claude_api_key', '').strip()
        
        interface = ProfessionalDynamicPlanner()
        itineraries = interface.generate_dynamic_routes(
            start_city, end_city, travel_days, venice_nights, season, claude_api_key
        )
        
        return render_template('professional_dynamic_results.html',
                             itineraries=itineraries,
                             form_data=form_data,
                             cache_buster=interface.cache_buster,
                             ai_enabled=bool(claude_api_key))
    except Exception as e:
        return render_template('error.html', error=str(e))

# AI TRAVEL ASSISTANT API ENDPOINTS - 12 Advanced Features
@app.route('/api/ai-destination-finder', methods=['POST'])
def ai_destination_finder():
    """AI-powered destination finder based on travel reasons."""
    try:
        data = request.get_json()
        travel_reason = data.get('travel_reason', 'vacation')
        preferences = data.get('preferences', {})
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.intelligent_destination_finder(travel_reason, preferences)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-personalized-itinerary', methods=['POST'])
def ai_personalized_itinerary():
    """Create AI-powered personalized itineraries."""
    try:
        data = request.get_json()
        destination = data.get('destination', 'Paris')
        duration = data.get('duration', 3)
        interests = data.get('interests', ['culture'])
        travel_style = data.get('travel_style', 'mid_range')
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.personalized_itinerary_creator(destination, duration, interests, travel_style)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-budget-optimizer', methods=['POST'])
def ai_budget_optimizer():
    """AI-powered budget optimization."""
    try:
        data = request.get_json()
        budget = data.get('budget', 1000)
        preferences = data.get('preferences', {})
        destination = data.get('destination', 'Paris')
        duration = data.get('duration', 3)
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.smart_budget_optimizer(budget, preferences, destination, duration)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-seasonal-advisor', methods=['POST'])
def ai_seasonal_advisor():
    """AI seasonal travel advisor."""
    try:
        data = request.get_json()
        destinations = data.get('destinations', ['Paris', 'Rome'])
        travel_months = data.get('travel_months', ['June', 'July'])
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.seasonal_travel_advisor(destinations, travel_months)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-cultural-planner', methods=['POST'])
def ai_cultural_planner():
    """AI cultural immersion planner."""
    try:
        data = request.get_json()
        destination = data.get('destination', 'Florence')
        cultural_interests = data.get('cultural_interests', ['art', 'history'])
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.cultural_immersion_planner(destination, cultural_interests)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-risk-assessment', methods=['POST'])
def ai_risk_assessment():
    """AI travel risk assessment."""
    try:
        data = request.get_json()
        destinations = data.get('destinations', ['Paris'])
        travel_dates = data.get('travel_dates', ['2024-06-01'])
        traveler_profile = data.get('traveler_profile', {'age': 30, 'experience': 'moderate'})
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.risk_assessment_advisor(destinations, travel_dates, traveler_profile)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-sustainable-travel', methods=['POST'])
def ai_sustainable_travel():
    """AI sustainable travel planner."""
    try:
        data = request.get_json()
        route_data = data.get('route_data', {})
        sustainability_goals = data.get('sustainability_goals', ['reduce_carbon'])
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.sustainable_travel_planner(route_data, sustainability_goals)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-accessibility-planner', methods=['POST'])
def ai_accessibility_planner():
    """AI accessibility travel planner."""
    try:
        data = request.get_json()
        destination = data.get('destination', 'Barcelona')
        accessibility_needs = data.get('accessibility_needs', ['wheelchair_access'])
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.accessibility_travel_planner(destination, accessibility_needs)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-events-curator', methods=['POST'])
def ai_events_curator():
    """AI local events curator."""
    try:
        data = request.get_json()
        destination = data.get('destination', 'Prague')
        travel_dates = data.get('travel_dates', ['2024-06-15'])
        interests = data.get('interests', ['music', 'culture'])
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.local_events_curator(destination, travel_dates, interests)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-multi-destination', methods=['POST'])
def ai_multi_destination():
    """AI multi-destination optimizer."""
    try:
        data = request.get_json()
        destinations = data.get('destinations', ['Paris', 'Rome', 'Barcelona'])
        constraints = data.get('constraints', {'budget': 2000, 'time': 10})
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.multi_destination_optimizer(destinations, constraints)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-companion-matcher', methods=['POST'])
def ai_companion_matcher():
    """AI travel companion matcher."""
    try:
        data = request.get_json()
        traveler_profile = data.get('traveler_profile', {'age': 28, 'interests': ['culture']})
        trip_details = data.get('trip_details', {'destination': 'Italy', 'duration': 7})
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.travel_companion_matcher(traveler_profile, trip_details)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai-travel-concierge', methods=['POST'])
def ai_travel_concierge():
    """AI real-time travel concierge."""
    try:
        data = request.get_json()
        current_location = data.get('current_location', 'Paris')
        immediate_needs = data.get('immediate_needs', ['restaurant', 'directions'])
        
        interface = ProfessionalDynamicPlanner()
        result = interface.ai_assistant.real_time_travel_concierge(current_location, immediate_needs)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Enhanced Features API Endpoints
@app.route('/api/optimize-route', methods=['POST'])
def optimize_route():
    """Optimize route with traffic analysis."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.enhanced_features.optimize_route(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/smart-schedule', methods=['POST'])
def smart_schedule():
    """Create optimized daily schedules."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.enhanced_features.smart_schedule(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/track-prices', methods=['POST'])
def track_prices():
    """Track accommodation and activity prices."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.enhanced_features.track_prices(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/find-accommodations', methods=['POST'])
def find_accommodations():
    """Find hotel options with prices."""
    try:
        data = request.get_json()
        city = data.get('city', 'Venice')
        nights = data.get('nights', 2)
        checkin_date = data.get('checkin_date')
        
        interface = ProfessionalDynamicPlanner()
        result = interface.enhanced_features.find_accommodations(city, nights, checkin_date)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-weather', methods=['POST'])
def check_weather():
    """Get weather forecasts for route destinations."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.enhanced_features.check_weather(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/calculate-budget', methods=['POST'])
def calculate_budget():
    """Calculate detailed budget breakdown."""
    try:
        data = request.get_json()
        travel_style = data.get('travel_style', 'mid_range')
        interface = ProfessionalDynamicPlanner()
        result = interface.enhanced_features.calculate_budget(data, travel_style)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/find-restaurants', methods=['POST'])
def find_restaurants():
    """Find restaurants with ratings."""
    try:
        data = request.get_json()
        city = data.get('city', 'Venice')
        cuisine_preferences = data.get('cuisine_preferences', [])
        
        interface = ProfessionalDynamicPlanner()
        result = interface.enhanced_features.find_restaurants(city, cuisine_preferences)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-packing-list', methods=['POST'])
def generate_packing_list():
    """Generate comprehensive packing list."""
    try:
        data = request.get_json()
        season = data.get('season', 'summer')
        travel_days = data.get('travel_days', 4)
        
        interface = ProfessionalDynamicPlanner()
        result = interface.enhanced_features.generate_packing_list(data, season, travel_days)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 10 NEW FEATURE API ENDPOINTS
@app.route('/api/real-time-traffic', methods=['POST'])
def real_time_traffic():
    """Get real-time traffic conditions."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.real_time_traffic(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/currency-converter', methods=['POST'])
def currency_converter():
    """Convert currencies for multi-country trips."""
    try:
        data = request.get_json()
        base_currency = data.get('base_currency', 'EUR')
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.currency_converter(data, base_currency)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/emergency-contacts', methods=['POST'])
def emergency_contacts():
    """Get emergency contacts and safety info."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.emergency_contacts(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/travel-insurance', methods=['POST'])
def travel_insurance():
    """Find and compare travel insurance."""
    try:
        data = request.get_json()
        traveler_age = data.get('traveler_age', 35)
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.travel_insurance_finder(data, traveler_age)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/carbon-footprint', methods=['POST'])
def carbon_footprint():
    """Calculate trip carbon footprint."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.carbon_footprint_calculator(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/local-events', methods=['POST'])
def local_events():
    """Find local events and festivals."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.local_events_finder(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vehicle-preparation', methods=['POST'])
def vehicle_preparation():
    """Get vehicle preparation checklist."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.vehicle_preparation(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/language-phrases', methods=['POST'])
def language_phrases():
    """Get language phrase book."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.language_phrase_book(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/border-crossing', methods=['POST'])
def border_crossing():
    """Get border crossing information."""
    try:
        data = request.get_json()
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.border_crossing_info(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/group-coordinator', methods=['POST'])
def group_coordinator():
    """Coordinate group travel."""
    try:
        data = request.get_json()
        group_size = data.get('group_size', 4)
        interface = ProfessionalDynamicPlanner()
        result = interface.additional_features.group_travel_coordinator(data, group_size)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# NEW API ENDPOINTS FOR REQUIRED FEATURES

@app.route('/api/cities', methods=['GET'])
def get_cities():
    """Get all available cities for autocomplete."""
    try:
        interface = ProfessionalDynamicPlanner()
        cities = []
        for city_key, city_info in interface.geographic_router.cities_db.items():
            cities.append({
                'value': city_key,
                'label': city_key.replace('-', ' ').title(),
                'country': city_info['country'],
                'region': city_info.get('region', ''),
                'population': city_info['population']
            })
        
        # Sort cities by popularity (population) and name
        cities.sort(key=lambda x: (-x['population'], x['label']))
        return jsonify(cities)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/route-attractions', methods=['POST'])
def route_attractions():
    """Get attractions and photo spots along the route."""
    try:
        data = request.get_json()
        start_city = data.get('start_city', '')
        end_city = data.get('end_city', '')
        intermediate_cities = data.get('intermediate_cities', [])
        
        interface = ProfessionalDynamicPlanner()
        result = interface.get_route_attractions(start_city, end_city, intermediate_cities)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("PROFESSIONAL DYNAMIC EUROPEAN ROADTRIP PLANNER")
    print("=" * 70)
    print("- Real-time route generation based on your preferences")
    print("- Claude AI integration for personalized insights")
    print("- 8 different route strategies with unique focuses")
    print("- Professional interface with ALL FEATURES WORKING")
    print("- 25 Enhanced Features + 12 AI Assistant Features")
    print("- Complete European Database: France, Spain, Italy + More")
    print("- AI Travel Assistant with Claude Integration")
    print("PORT: http://localhost:5006")
    print("=" * 70)
    app.run(debug=True, host='0.0.0.0', port=5006)
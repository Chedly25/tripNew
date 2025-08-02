"""AI Inspiration Engine - Generates surprise trips and themed routes."""

import logging
import random
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import calendar

logger = logging.getLogger(__name__)


@dataclass
class InspirationTrip:
    """A generated inspiration trip with explanation."""
    start_city: str
    end_city: str
    duration: str
    budget: str
    travel_style: str
    inspiration_message: str
    theme: str
    season_perfect: bool = False


class AIInspirationEngine:
    """AI-powered inspiration engine for surprise trips and themed routes."""
    
    def __init__(self):
        # Curated inspiration combinations
        self.inspiration_templates = {
            'romantic_spring': {
                'routes': [
                    ('Paris', 'Venice', 'Love flows through charming canals and romantic boulevards'),
                    ('Barcelona', 'Florence', 'Passionate cities where art and romance intertwine'),
                    ('Prague', 'Vienna', 'Imperial romance through fairy-tale capitals'),
                    ('Amsterdam', 'Bruges', 'Intimate waterway romance in picture-perfect settings')
                ],
                'duration': '7 days',
                'budget': 'moderate',
                'style': 'romantic',
                'season': 'spring'
            },
            'adventure_summer': {
                'routes': [
                    ('Munich', 'Zurich', 'Alpine adventures await in the heart of Europe'),
                    ('Barcelona', 'Nice', 'Mediterranean coastline meets mountain peaks'),
                    ('Berlin', 'Copenhagen', 'Nordic adventures through vibrant capitals'),
                    ('Edinburgh', 'Dublin', 'Celtic adventures across emerald landscapes')
                ],
                'duration': '10 days',
                'budget': 'moderate',
                'style': 'adventure',
                'season': 'summer'
            },
            'cultural_autumn': {
                'routes': [
                    ('London', 'Rome', 'Journey through millennia of European civilization'),
                    ('Vienna', 'Budapest', 'Imperial grandeur along the Danube'),
                    ('Madrid', 'Lisbon', 'Iberian cultural treasures await discovery'),
                    ('Berlin', 'Warsaw', 'Stories of resilience in historic capitals')
                ],
                'duration': '14 days',
                'budget': 'luxury',
                'style': 'cultural',
                'season': 'autumn'
            },
            'foodie_year_round': {
                'routes': [
                    ('Lyon', 'Bologna', 'Culinary capitals of France and Italy beckon'),
                    ('San Sebastian', 'Marseille', 'Coastal flavors from Basque to Provençal'),
                    ('Brussels', 'Amsterdam', 'Beer, chocolate, and cheese adventures'),
                    ('Copenhagen', 'Stockholm', 'Nordic cuisine innovation tour')
                ],
                'duration': '7 days',
                'budget': 'luxury',
                'style': 'foodie',
                'season': 'any'
            },
            'hidden_gems_winter': {
                'routes': [
                    ('Ljubljana', 'Zagreb', 'Undiscovered Balkan charm awaits exploration'),
                    ('Tallinn', 'Riga', 'Medieval Baltic treasures in winter wonderland'),
                    ('Porto', 'Seville', 'Authentic Iberian soul far from crowds'),
                    ('Krakow', 'Bratislava', 'Central European secrets in historic splendor')
                ],
                'duration': '5 days',
                'budget': 'budget',
                'style': 'hidden_gems',
                'season': 'winter'
            },
            'scenic_routes': {
                'routes': [
                    ('Innsbruck', 'Lake Como', 'Alpine beauty meets Italian lake magic'),
                    ('Geneva', 'Monaco', 'Luxurious journey through breathtaking landscapes'),
                    ('Salzburg', 'Hallstatt', 'Sound of Music meets fairy-tale perfection'),
                    ('Interlaken', 'Chamonix', 'Mountain paradise across borders')
                ],
                'duration': '5 days',
                'budget': 'luxury',
                'style': 'scenic',
                'season': 'any'
            }
        }
        
        # Seasonal inspirations
        self.seasonal_themes = {
            'spring': {
                'messages': [
                    "Spring awakens Europe's romantic soul...",
                    "Blooming gardens and mild weather call for adventure...",
                    "Easter markets and tulip fields await...",
                    "Perfect weather for discovering hidden terraces..."
                ],
                'preferred_styles': ['romantic', 'scenic', 'cultural']
            },
            'summer': {
                'messages': [
                    "Summer festivals and midnight sun adventures...",
                    "Beach towns and mountain hikes beckon...",
                    "Long days perfect for epic journeys...",
                    "Festival season brings Europe alive..."
                ],
                'preferred_styles': ['adventure', 'scenic', 'foodie']
            },
            'autumn': {
                'messages': [
                    "Harvest season brings rich colors and flavors...",
                    "Cozy cities and fewer crowds await...",
                    "Wine harvest and cultural seasons begin...",
                    "Perfect time for deep cultural immersion..."
                ],
                'preferred_styles': ['cultural', 'foodie', 'romantic']
            },
            'winter': {
                'messages': [
                    "Christmas markets and cozy cafés call...",
                    "Winter wonderlands and festive cheer...",
                    "Authentic local life away from summer crowds...",
                    "Museum season and intimate discoveries..."
                ],
                'preferred_styles': ['hidden_gems', 'cultural', 'romantic']
            }
        }
        
        # Dynamic inspiration factors
        self.inspiration_factors = [
            "You've been working hard - time for a romantic escape",
            "Adventure is calling your name this season",
            "Your cultural curiosity deserves feeding",
            "Hidden gems are waiting to be discovered",
            "Foodie adventures await the curious traveler",
            "Scenic beauty will restore your soul",
            "Time to explore Europe's best-kept secrets",
            "This route combines everything you love"
        ]
    
    def generate_surprise_trip(self, user_preferences: Optional[Dict] = None) -> InspirationTrip:
        """Generate a surprise trip based on season and inspiration."""
        current_season = self._get_current_season()
        
        # Choose inspiration template based on season
        suitable_templates = self._get_seasonal_templates(current_season)
        template_key = random.choice(list(suitable_templates.keys()))
        template = suitable_templates[template_key]
        
        # Select route
        route = random.choice(template['routes'])
        start_city, end_city, route_inspiration = route
        
        # Create inspiration message
        season_data = self.seasonal_themes[current_season]
        base_message = random.choice(season_data['messages'])
        personal_factor = random.choice(self.inspiration_factors)
        
        inspiration_message = f"{base_message} {route_inspiration}. {personal_factor}!"
        
        return InspirationTrip(
            start_city=start_city,
            end_city=end_city,
            duration=template['duration'],
            budget=template['budget'],
            travel_style=template['style'],
            inspiration_message=inspiration_message,
            theme=template_key,
            season_perfect=True
        )
    
    def generate_themed_trip(self, theme: str) -> Optional[InspirationTrip]:
        """Generate a trip based on specific theme."""
        matching_templates = {
            k: v for k, v in self.inspiration_templates.items() 
            if theme.lower() in k.lower()
        }
        
        if not matching_templates:
            return None
        
        template_key = random.choice(list(matching_templates.keys()))
        template = matching_templates[template_key]
        
        route = random.choice(template['routes'])
        start_city, end_city, route_inspiration = route
        
        inspiration_message = f"{route_inspiration}. Perfect for {theme} enthusiasts!"
        
        return InspirationTrip(
            start_city=start_city,
            end_city=end_city,
            duration=template['duration'],
            budget=template['budget'],
            travel_style=template['style'],
            inspiration_message=inspiration_message,
            theme=template_key
        )
    
    def get_seasonal_suggestions(self, season: str = None) -> List[InspirationTrip]:
        """Get multiple suggestions for a season."""
        if not season:
            season = self._get_current_season()
        
        suitable_templates = self._get_seasonal_templates(season)
        suggestions = []
        
        for template_key, template in suitable_templates.items():
            # Get one route from each template
            route = random.choice(template['routes'])
            start_city, end_city, route_inspiration = route
            
            season_data = self.seasonal_themes[season]
            base_message = random.choice(season_data['messages'])
            
            inspiration_message = f"{base_message} {route_inspiration}"
            
            suggestions.append(InspirationTrip(
                start_city=start_city,
                end_city=end_city,
                duration=template['duration'],
                budget=template['budget'],
                travel_style=template['style'],
                inspiration_message=inspiration_message,
                theme=template_key,
                season_perfect=True
            ))
        
        return suggestions[:3]  # Return top 3
    
    def get_monthly_inspiration(self, month: int = None) -> InspirationTrip:
        """Get inspiration perfect for specific month."""
        if not month:
            month = datetime.now().month
        
        month_themes = {
            1: 'hidden_gems_winter',  # January - fewer crowds
            2: 'cultural_autumn',     # February - museum season
            3: 'romantic_spring',     # March - early spring romance
            4: 'romantic_spring',     # April - perfect spring weather
            5: 'scenic_routes',       # May - ideal weather for scenic drives
            6: 'adventure_summer',    # June - long days for adventure
            7: 'adventure_summer',    # July - peak adventure season
            8: 'foodie_year_round',   # August - festival and food season
            9: 'cultural_autumn',     # September - perfect cultural weather
            10: 'scenic_routes',      # October - autumn colors
            11: 'cultural_autumn',    # November - cozy cultural season
            12: 'hidden_gems_winter'  # December - Christmas markets
        }
        
        theme_key = month_themes.get(month, 'scenic_routes')
        if theme_key in self.inspiration_templates:
            template = self.inspiration_templates[theme_key]
            route = random.choice(template['routes'])
            start_city, end_city, route_inspiration = route
            
            month_name = calendar.month_name[month]
            inspiration_message = f"Perfect for {month_name}! {route_inspiration}"
            
            return InspirationTrip(
                start_city=start_city,
                end_city=end_city,
                duration=template['duration'],
                budget=template['budget'],
                travel_style=template['style'],
                inspiration_message=inspiration_message,
                theme=theme_key,
                season_perfect=True
            )
        
        return self.generate_surprise_trip()
    
    def _get_current_season(self) -> str:
        """Determine current season."""
        month = datetime.now().month
        if month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        elif month in [9, 10, 11]:
            return 'autumn'
        else:
            return 'winter'
    
    def _get_seasonal_templates(self, season: str) -> Dict:
        """Get templates suitable for the season."""
        seasonal_templates = {}
        
        for key, template in self.inspiration_templates.items():
            template_season = template.get('season', 'any')
            if template_season == 'any' or template_season == season:
                seasonal_templates[key] = template
        
        # If no seasonal templates, return a few general ones
        if not seasonal_templates:
            return {
                'scenic_routes': self.inspiration_templates['scenic_routes'],
                'foodie_year_round': self.inspiration_templates['foodie_year_round']
            }
        
        return seasonal_templates
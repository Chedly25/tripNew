"""AI Dream Trip Builder - Converts natural language to trip parameters."""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DreamTripParams:
    """Parsed trip parameters from natural language."""
    start_city: Optional[str] = None
    end_city: Optional[str] = None
    duration: Optional[str] = None
    budget: Optional[str] = None
    travel_style: Optional[str] = None
    interests: List[str] = None
    group_type: Optional[str] = None
    season: Optional[str] = None
    confidence: float = 0.0
    extracted_intent: str = ""


class AIDreamTripBuilder:
    """AI-powered natural language to trip parameters converter."""
    
    def __init__(self):
        # City name patterns
        self.european_cities = {
            # Major cities
            'paris', 'london', 'rome', 'barcelona', 'amsterdam', 'berlin', 'vienna', 'madrid',
            'prague', 'budapest', 'florence', 'venice', 'milan', 'munich', 'zurich', 'geneva',
            'copenhagen', 'stockholm', 'oslo', 'helsinki', 'dublin', 'edinburgh', 'brussels',
            'lisbon', 'porto', 'athens', 'santorini', 'dubrovnik', 'split', 'nice', 'monaco',
            
            # Hidden gems
            'ljubljana', 'bratislava', 'tallinn', 'riga', 'vilnius', 'krakow', 'warsaw',
            'ghent', 'bruges', 'bologna', 'verona', 'salzburg', 'hallstatt', 'interlaken',
            'chamonix', 'annecy', 'colmar', 'strasbourg', 'lyon', 'marseille', 'bordeaux'
        }
        
        # Duration patterns
        self.duration_patterns = {
            r'(\d+)\s*days?': lambda m: f"{m.group(1)} days",
            r'(\d+)\s*weeks?': lambda m: f"{int(m.group(1)) * 7} days",
            r'week': "7 days",
            r'weekend': "3 days",
            r'long weekend': "4 days",
            r'short trip': "5 days",
            r'quick trip': "3 days"
        }
        
        # Budget patterns
        self.budget_patterns = {
            r'(\d+)\s*(?:euros?|€)': self._parse_budget_amount,
            r'budget': 'budget',
            r'cheap': 'budget',
            r'affordable': 'budget',
            r'luxury': 'luxury',
            r'expensive': 'luxury',
            r'splurge': 'luxury',
            r'moderate': 'moderate',
            r'mid.?range': 'moderate'
        }
        
        # Travel style patterns
        self.style_patterns = {
            'romantic': ['romantic', 'honeymoon', 'love', 'couple', 'anniversary', 'intimate'],
            'cultural': ['culture', 'museum', 'history', 'art', 'heritage', 'historical'],
            'adventure': ['adventure', 'hiking', 'outdoor', 'active', 'sports', 'mountain'],
            'foodie': ['food', 'cuisine', 'restaurant', 'culinary', 'wine', 'gastronomy'],
            'scenic': ['scenic', 'beautiful', 'views', 'landscapes', 'nature', 'photography'],
            'hidden_gems': ['hidden', 'secret', 'off.beaten', 'undiscovered', 'authentic', 'local']
        }
        
        # Group type patterns
        self.group_patterns = {
            'solo': ['solo', 'alone', 'by myself', 'individual'],
            'couple': ['couple', 'two', 'partner', 'boyfriend', 'girlfriend', 'husband', 'wife'],
            'family': ['family', 'kids', 'children', 'parents'],
            'friends': ['friends', 'group', 'gang', 'crew']
        }
        
        # Season patterns
        self.season_patterns = {
            'spring': ['spring', 'march', 'april', 'may'],
            'summer': ['summer', 'june', 'july', 'august'],
            'autumn': ['autumn', 'fall', 'september', 'october', 'november'],
            'winter': ['winter', 'december', 'january', 'february']
        }
        
        # Interest keywords
        self.interest_keywords = {
            'culture': ['museum', 'gallery', 'cathedral', 'church', 'palace', 'castle'],
            'food': ['restaurant', 'café', 'market', 'wine', 'beer', 'chocolate'],
            'nature': ['park', 'garden', 'lake', 'mountain', 'beach', 'forest'],
            'nightlife': ['bar', 'club', 'nightlife', 'party', 'entertainment'],
            'shopping': ['shopping', 'boutique', 'market', 'souvenir'],
            'architecture': ['architecture', 'building', 'tower', 'bridge']
        }
    
    def parse_dream_trip(self, text: str) -> DreamTripParams:
        """Parse natural language into trip parameters."""
        try:
            text_lower = text.lower()
            params = DreamTripParams()
            confidence_factors = []
            
            # Extract cities
            start, end = self._extract_cities(text_lower)
            if start:
                params.start_city = start
                confidence_factors.append(0.3)
            if end:
                params.end_city = end
                confidence_factors.append(0.3)
            
            # Extract duration
            duration = self._extract_duration(text_lower)
            if duration:
                params.duration = duration
                confidence_factors.append(0.2)
            
            # Extract budget
            budget = self._extract_budget(text_lower)
            if budget:
                params.budget = budget
                confidence_factors.append(0.1)
            
            # Extract travel style
            style = self._extract_travel_style(text_lower)
            if style:
                params.travel_style = style
                confidence_factors.append(0.2)
            
            # Extract group type
            group = self._extract_group_type(text_lower)
            if group:
                params.group_type = group
                confidence_factors.append(0.1)
            
            # Extract season
            season = self._extract_season(text_lower)
            if season:
                params.season = season
                confidence_factors.append(0.1)
            
            # Extract interests
            interests = self._extract_interests(text_lower)
            if interests:
                params.interests = interests
                confidence_factors.append(0.1)
            
            # Calculate confidence
            params.confidence = min(1.0, sum(confidence_factors))
            
            # Extract intent
            params.extracted_intent = self._extract_intent(text_lower, params)
            
            return params
            
        except Exception as e:
            logger.error(f"Dream trip parsing failed: {e}")
            return DreamTripParams()
    
    def enhance_with_suggestions(self, params: DreamTripParams) -> DreamTripParams:
        """Enhance incomplete parameters with intelligent suggestions."""
        # If no cities specified, suggest based on style/interests
        if not params.start_city and not params.end_city:
            start, end = self._suggest_cities_by_style(params.travel_style, params.interests)
            params.start_city = start
            params.end_city = end
        elif params.start_city and not params.end_city:
            params.end_city = self._suggest_end_city(params.start_city, params.travel_style)
        elif params.end_city and not params.start_city:
            params.start_city = self._suggest_start_city(params.end_city, params.travel_style)
        
        # Suggest duration if not specified
        if not params.duration:
            params.duration = self._suggest_duration(params.travel_style, params.group_type)
        
        # Suggest budget if not specified
        if not params.budget:
            params.budget = self._suggest_budget(params.travel_style)
        
        # Suggest travel style if not specified
        if not params.travel_style:
            params.travel_style = self._suggest_travel_style(params.interests)
        
        return params
    
    def _extract_cities(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract start and end cities from text."""
        # Look for "from X to Y" pattern
        from_to_pattern = r'from\s+(\w+)\s+to\s+(\w+)'
        match = re.search(from_to_pattern, text)
        if match:
            start = match.group(1).title()
            end = match.group(2).title()
            if start.lower() in self.european_cities and end.lower() in self.european_cities:
                return start, end
        
        # Look for "X to Y" pattern
        to_pattern = r'(\w+)\s+to\s+(\w+)'
        match = re.search(to_pattern, text)
        if match:
            start = match.group(1).title()
            end = match.group(2).title()
            if start.lower() in self.european_cities and end.lower() in self.european_cities:
                return start, end
        
        # Look for individual cities mentioned
        mentioned_cities = []
        for city in self.european_cities:
            if city in text:
                mentioned_cities.append(city.title())
        
        if len(mentioned_cities) >= 2:
            return mentioned_cities[0], mentioned_cities[1]
        elif len(mentioned_cities) == 1:
            return mentioned_cities[0], None
        
        return None, None
    
    def _extract_duration(self, text: str) -> Optional[str]:
        """Extract duration from text."""
        for pattern, replacement in self.duration_patterns.items():
            match = re.search(pattern, text)
            if match:
                if callable(replacement):
                    return replacement(match)
                else:
                    return replacement
        return None
    
    def _extract_budget(self, text: str) -> Optional[str]:
        """Extract budget from text."""
        for pattern, replacement in self.budget_patterns.items():
            if re.search(pattern, text):
                if callable(replacement):
                    return replacement(text)
                else:
                    return replacement
        return None
    
    def _parse_budget_amount(self, text: str) -> str:
        """Parse specific budget amounts."""
        amounts = re.findall(r'(\d+)', text)
        if amounts:
            amount = int(amounts[0])
            if amount < 1000:
                return 'budget'
            elif amount < 3000:
                return 'moderate'
            else:
                return 'luxury'
        return 'moderate'
    
    def _extract_travel_style(self, text: str) -> Optional[str]:
        """Extract travel style from text."""
        style_scores = {}
        
        for style, keywords in self.style_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                style_scores[style] = score
        
        if style_scores:
            return max(style_scores, key=style_scores.get)
        return None
    
    def _extract_group_type(self, text: str) -> Optional[str]:
        """Extract group type from text."""
        for group_type, keywords in self.group_patterns.items():
            if any(keyword in text for keyword in keywords):
                return group_type
        return None
    
    def _extract_season(self, text: str) -> Optional[str]:
        """Extract season from text."""
        for season, keywords in self.season_patterns.items():
            if any(keyword in text for keyword in keywords):
                return season
        return None
    
    def _extract_interests(self, text: str) -> List[str]:
        """Extract interests from text."""
        interests = []
        for interest, keywords in self.interest_keywords.items():
            if any(keyword in text for keyword in keywords):
                interests.append(interest)
        return interests
    
    def _extract_intent(self, text: str, params: DreamTripParams) -> str:
        """Extract the overall intent/theme of the trip."""
        intent_phrases = {
            'honeymoon': 'romantic getaway for newlyweds',
            'anniversary': 'celebrating a special milestone',
            'birthday': 'birthday celebration trip',
            'graduation': 'graduation celebration',
            'retirement': 'retirement adventure',
            'bucket list': 'once-in-a-lifetime experience',
            'surprise': 'surprise trip planning',
            'first time': 'first European adventure',
            'backpacking': 'budget backpacking adventure',
            'luxury': 'luxury travel experience'
        }
        
        for phrase, intent in intent_phrases.items():
            if phrase in text:
                return intent
        
        # Generate intent based on extracted parameters
        if params.travel_style and params.group_type:
            return f"{params.travel_style} trip for {params.group_type}"
        elif params.travel_style:
            return f"{params.travel_style} European adventure"
        
        return "European travel experience"
    
    def _suggest_cities_by_style(self, style: str, interests: List[str]) -> Tuple[str, str]:
        """Suggest cities based on travel style and interests."""
        style_suggestions = {
            'romantic': ('Paris', 'Venice'),
            'cultural': ('Rome', 'Florence'),
            'adventure': ('Interlaken', 'Chamonix'),
            'foodie': ('Lyon', 'Bologna'),
            'scenic': ('Hallstatt', 'Santorini'),
            'hidden_gems': ('Ljubljana', 'Porto')
        }
        
        if style in style_suggestions:
            return style_suggestions[style]
        
        # Default suggestions
        return ('Barcelona', 'Prague')
    
    def _suggest_end_city(self, start_city: str, style: str) -> str:
        """Suggest end city based on start city and style."""
        suggestions = {
            'Paris': {'romantic': 'Venice', 'cultural': 'Rome', 'adventure': 'Interlaken'},
            'London': {'romantic': 'Paris', 'cultural': 'Amsterdam', 'adventure': 'Edinburgh'},
            'Barcelona': {'romantic': 'Nice', 'cultural': 'Madrid', 'adventure': 'Andorra'},
            'Rome': {'romantic': 'Florence', 'cultural': 'Athens', 'adventure': 'Sicily'}
        }
        
        if start_city in suggestions and style in suggestions[start_city]:
            return suggestions[start_city][style]
        
        # Default based on style
        style_defaults = {
            'romantic': 'Venice',
            'cultural': 'Rome',
            'adventure': 'Interlaken',
            'foodie': 'Bologna',
            'scenic': 'Hallstatt'
        }
        
        return style_defaults.get(style, 'Prague')
    
    def _suggest_start_city(self, end_city: str, style: str) -> str:
        """Suggest start city based on end city and style."""
        # Reverse the logic from end city suggestions
        return 'Paris'  # Default popular starting point
    
    def _suggest_duration(self, style: str, group_type: str) -> str:
        """Suggest duration based on style and group."""
        duration_suggestions = {
            'romantic': '7 days',
            'cultural': '10 days',
            'adventure': '14 days',
            'foodie': '7 days',
            'scenic': '5 days',
            'hidden_gems': '10 days'
        }
        
        base_duration = duration_suggestions.get(style, '7 days')
        
        # Adjust for group type
        if group_type == 'family':
            return '7 days'  # Shorter for families
        elif group_type == 'solo':
            return '10 days'  # Longer for solo travelers
        
        return base_duration
    
    def _suggest_budget(self, style: str) -> str:
        """Suggest budget based on travel style."""
        budget_suggestions = {
            'romantic': 'luxury',
            'cultural': 'moderate',
            'adventure': 'budget',
            'foodie': 'luxury',
            'scenic': 'moderate',
            'hidden_gems': 'budget'
        }
        
        return budget_suggestions.get(style, 'moderate')
    
    def _suggest_travel_style(self, interests: List[str]) -> str:
        """Suggest travel style based on interests."""
        if not interests:
            return 'scenic'
        
        interest_style_map = {
            'culture': 'cultural',
            'food': 'foodie',
            'nature': 'scenic',
            'nightlife': 'adventure',
            'architecture': 'cultural'
        }
        
        # Find the most relevant style
        for interest in interests:
            if interest in interest_style_map:
                return interest_style_map[interest]
        
        return 'scenic'
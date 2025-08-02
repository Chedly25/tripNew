"""AI City Discovery Service - Smart ranking and discovery of European cities."""

import logging
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredCity:
    """A discovered city with AI scoring and metadata."""
    name: str
    country: str
    description: str
    ai_score: float  # 0-100
    tags: List[str]
    population: int
    coordinates: Tuple[float, float]
    hidden_gem_score: float
    uniqueness_score: float
    accessibility_score: float
    reasons: List[str]


class AICityDiscovery:
    """AI-powered city discovery and ranking system."""
    
    def __init__(self, city_service):
        self.city_service = city_service
        
        # City scoring criteria
        self.scoring_weights = {
            'hidden_gem': 0.3,
            'uniqueness': 0.25,
            'accessibility': 0.2,
            'cultural_richness': 0.15,
            'natural_beauty': 0.1
        }
        
        # Predefined city characteristics for enhanced scoring
        self.city_characteristics = {
            'romantic': ['venice', 'paris', 'prague', 'bruges', 'verona', 'florence', 'santorini', 'hallstatt'],
            'cultural': ['rome', 'athens', 'florence', 'vienna', 'budapest', 'prague', 'barcelona', 'madrid'],
            'foodie': ['lyon', 'bologna', 'san sebastian', 'naples', 'marseille', 'brussels', 'copenhagen'],
            'adventure': ['interlaken', 'chamonix', 'innsbruck', 'zakopane', 'brasov', 'lillehammer'],
            'coastal': ['nice', 'barcelona', 'dubrovnik', 'santorini', 'porto', 'valencia', 'lisbon'],
            'mountain': ['interlaken', 'innsbruck', 'chamonix', 'zermatt', 'hallstatt', 'brasov'],
            'hidden_gems': ['ljubljana', 'tallinn', 'riga', 'bratislava', 'porto', 'ghent', 'bruges']
        }
        
        # Enhanced city descriptions
        self.enhanced_descriptions = {
            'ljubljana': "Slovenia's charming capital combines fairy-tale architecture with vibrant cultural scene",
            'tallinn': "Medieval Baltic gem with perfectly preserved old town and cutting-edge digital culture",
            'riga': "Art Nouveau architectural wonderland with vibrant nightlife and rich cultural heritage",
            'bratislava': "Danube riverside beauty with imperial history and emerging culinary scene",
            'porto': "Portugal's soulful northern capital famous for port wine and stunning azulejo tiles",
            'ghent': "Belgium's best-kept secret with medieval grandeur and youthful university energy",
            'bruges': "Medieval time capsule with romantic canals and world-class chocolate",
            'venice': "Floating masterpiece of art, romance, and timeless Italian elegance",
            'florence': "Renaissance birthplace where every street corner reveals artistic treasures",
            'vienna': "Imperial elegance meets coffeehouse culture in Austria's sophisticated capital",
            'prague': "Bohemian fairy-tale city with stunning architecture and rich cultural traditions",
            'barcelona': "Gaudí's modernist playground meets Mediterranean beach culture",
            'lyon': "France's gastronomic capital hidden between Paris and the French Riviera",
            'bologna': "Italy's culinary heart with medieval towers and vibrant university atmosphere"
        }
    
    def discover_cities(self, query: str = "", filter_type: str = "all", limit: int = 12) -> List[DiscoveredCity]:
        """Discover cities based on query and filters."""
        try:
            # Get comprehensive city database
            all_cities = self.city_service._get_comprehensive_city_database()
            
            # Apply filters
            filtered_cities = self._apply_filters(all_cities, filter_type)
            
            # Score cities based on query and characteristics
            scored_cities = []
            for city in filtered_cities[:50]:  # Limit for performance
                discovered_city = self._score_city(city, query, filter_type)
                if discovered_city:
                    scored_cities.append(discovered_city)
            
            # Sort by AI score
            scored_cities.sort(key=lambda x: x.ai_score, reverse=True)
            
            return scored_cities[:limit]
            
        except Exception as e:
            logger.error(f"City discovery failed: {e}")
            return self._get_fallback_cities(limit)
    
    def find_similar_cities(self, reference_city: str, exclude_popular: bool = True) -> List[DiscoveredCity]:
        """Find cities similar to a reference city."""
        try:
            all_cities = self.city_service._get_comprehensive_city_database()
            reference_city_lower = reference_city.lower()
            
            # Find reference city characteristics
            ref_characteristics = []
            for category, cities in self.city_characteristics.items():
                if any(ref_city in reference_city_lower for ref_city in cities):
                    ref_characteristics.append(category)
            
            if not ref_characteristics:
                ref_characteristics = ['cultural']  # Default
            
            similar_cities = []
            for city in all_cities:
                if city.name.lower() == reference_city_lower:
                    continue  # Skip the reference city itself
                
                similarity_score = self._calculate_similarity(city, ref_characteristics)
                if similarity_score > 0.3:  # Threshold for similarity
                    discovered_city = self._score_city(city, f"similar to {reference_city}", ref_characteristics[0])
                    if discovered_city:
                        discovered_city.ai_score = similarity_score * 100
                        similar_cities.append(discovered_city)
            
            similar_cities.sort(key=lambda x: x.ai_score, reverse=True)
            return similar_cities[:8]
            
        except Exception as e:
            logger.error(f"Similar city search failed: {e}")
            return []
    
    def get_hidden_gems(self, region: str = "all", max_population: int = 200000) -> List[DiscoveredCity]:
        """Find hidden gem cities with low tourist saturation."""
        try:
            all_cities = self.city_service._get_comprehensive_city_database()
            
            hidden_gems = []
            for city in all_cities:
                # Filter by population (smaller cities are more likely to be hidden gems)
                if hasattr(city, 'population') and city.population > max_population:
                    continue
                
                # Calculate hidden gem score
                hidden_gem_score = self._calculate_hidden_gem_score(city)
                if hidden_gem_score > 0.6:
                    discovered_city = self._score_city(city, "hidden gems", "hidden_gems")
                    if discovered_city:
                        discovered_city.hidden_gem_score = hidden_gem_score
                        discovered_city.ai_score = hidden_gem_score * 100
                        hidden_gems.append(discovered_city)
            
            hidden_gems.sort(key=lambda x: x.hidden_gem_score, reverse=True)
            return hidden_gems[:10]
            
        except Exception as e:
            logger.error(f"Hidden gems discovery failed: {e}")
            return []
    
    def _apply_filters(self, cities: List, filter_type: str) -> List:
        """Apply category filters to city list."""
        if filter_type == "all":
            return cities
        
        if filter_type in self.city_characteristics:
            filter_cities = self.city_characteristics[filter_type]
            return [city for city in cities 
                   if any(filter_city in city.name.lower() for filter_city in filter_cities)]
        
        return cities
    
    def _score_city(self, city, query: str, filter_type: str) -> Optional[DiscoveredCity]:
        """Score a city based on query and characteristics."""
        try:
            # Base scoring
            hidden_gem_score = self._calculate_hidden_gem_score(city)
            uniqueness_score = self._calculate_uniqueness_score(city)
            accessibility_score = self._calculate_accessibility_score(city)
            
            # Query relevance scoring
            query_score = self._calculate_query_relevance(city, query)
            
            # Category matching
            category_score = self._calculate_category_score(city, filter_type)
            
            # Weighted final score
            ai_score = (
                hidden_gem_score * self.scoring_weights['hidden_gem'] +
                uniqueness_score * self.scoring_weights['uniqueness'] +
                accessibility_score * self.scoring_weights['accessibility'] +
                query_score * 0.3 +
                category_score * 0.2
            ) * 100
            
            # Generate tags
            tags = self._generate_tags(city, filter_type)
            
            # Generate description
            description = self._generate_description(city)
            
            # Generate reasons
            reasons = self._generate_reasons(city, ai_score, hidden_gem_score, uniqueness_score)
            
            return DiscoveredCity(
                name=city.name,
                country=getattr(city, 'country', 'Europe'),
                description=description,
                ai_score=min(100, max(0, ai_score)),
                tags=tags,
                population=getattr(city, 'population', 100000),
                coordinates=(getattr(city.coordinates, 'latitude', 0), 
                           getattr(city.coordinates, 'longitude', 0)),
                hidden_gem_score=hidden_gem_score,
                uniqueness_score=uniqueness_score,
                accessibility_score=accessibility_score,
                reasons=reasons
            )
            
        except Exception as e:
            logger.error(f"City scoring failed for {city.name}: {e}")
            return None
    
    def _calculate_hidden_gem_score(self, city) -> float:
        """Calculate how much of a hidden gem this city is."""
        score = 0.5  # Base score
        
        # Smaller cities are more likely to be hidden gems
        population = getattr(city, 'population', 100000)
        if population < 50000:
            score += 0.3
        elif population < 150000:
            score += 0.2
        elif population < 500000:
            score += 0.1
        
        # Cities not in major tourist lists
        major_cities = ['paris', 'london', 'rome', 'barcelona', 'amsterdam', 'berlin', 'vienna', 'madrid']
        if not any(major in city.name.lower() for major in major_cities):
            score += 0.2
        
        # Specific hidden gem cities get bonus
        if any(gem in city.name.lower() for gem in self.city_characteristics.get('hidden_gems', [])):
            score += 0.3
        
        return min(1.0, score)
    
    def _calculate_uniqueness_score(self, city) -> float:
        """Calculate how unique/special this city is."""
        score = 0.4  # Base score
        
        city_lower = city.name.lower()
        
        # Special characteristics
        unique_features = {
            'canals': ['venice', 'bruges', 'amsterdam', 'ghent'],
            'medieval': ['tallinn', 'riga', 'bruges', 'carcassonne'],
            'islands': ['santorini', 'mykonos', 'malta'],
            'mountains': ['interlaken', 'chamonix', 'innsbruck', 'zermatt'],
            'thermal_baths': ['budapest', 'baden-baden', 'reykjavik'],
            'art_nouveau': ['riga', 'brussels', 'nancy'],
            'wine_regions': ['porto', 'bordeaux', 'reims', 'rioja']
        }
        
        for feature, cities in unique_features.items():
            if any(special in city_lower for special in cities):
                score += 0.15
        
        return min(1.0, score)
    
    def _calculate_accessibility_score(self, city) -> float:
        """Calculate how accessible the city is for travelers."""
        score = 0.5  # Base score
        
        # Capital cities are generally more accessible
        capitals = ['paris', 'london', 'rome', 'madrid', 'berlin', 'vienna', 'amsterdam', 'brussels']
        if any(capital in city.name.lower() for capital in capitals):
            score += 0.3
        
        # Well-connected cities
        connected_cities = ['zurich', 'munich', 'milan', 'barcelona', 'prague', 'budapest']
        if any(connected in city.name.lower() for connected in connected_cities):
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_query_relevance(self, city, query: str) -> float:
        """Calculate how relevant the city is to the search query."""
        if not query:
            return 0.5
        
        query_lower = query.lower()
        city_name_lower = city.name.lower()
        
        # Direct name match
        if city_name_lower in query_lower or query_lower in city_name_lower:
            return 1.0
        
        # Characteristic matching
        score = 0.0
        for category, cities in self.city_characteristics.items():
            if category in query_lower:
                if any(city_match in city_name_lower for city_match in cities):
                    score += 0.8
        
        # Keyword matching
        keywords = {
            'romantic': ['romantic', 'love', 'couple', 'honeymoon'],
            'cultural': ['culture', 'museum', 'history', 'art', 'heritage'],
            'foodie': ['food', 'cuisine', 'restaurant', 'culinary', 'wine'],
            'adventure': ['adventure', 'outdoor', 'hiking', 'mountain', 'sport'],
            'hidden': ['hidden', 'secret', 'undiscovered', 'off-beaten'],
            'coastal': ['beach', 'sea', 'coast', 'ocean', 'island'],
            'less_crowded': ['quiet', 'peaceful', 'less crowded', 'authentic']
        }
        
        for category, words in keywords.items():
            if any(word in query_lower for word in words):
                if category in self.city_characteristics:
                    if any(city_match in city_name_lower 
                          for city_match in self.city_characteristics[category]):
                        score += 0.6
        
        return min(1.0, score)
    
    def _calculate_category_score(self, city, filter_type: str) -> float:
        """Calculate how well the city matches the selected category."""
        if filter_type == "all":
            return 0.5
        
        city_lower = city.name.lower()
        
        if filter_type in self.city_characteristics:
            category_cities = self.city_characteristics[filter_type]
            if any(cat_city in city_lower for cat_city in category_cities):
                return 1.0
        
        return 0.2
    
    def _calculate_similarity(self, city, reference_characteristics: List[str]) -> float:
        """Calculate similarity to reference city characteristics."""
        score = 0.0
        city_lower = city.name.lower()
        
        for characteristic in reference_characteristics:
            if characteristic in self.city_characteristics:
                if any(char_city in city_lower 
                      for char_city in self.city_characteristics[characteristic]):
                    score += 1.0 / len(reference_characteristics)
        
        return score
    
    def _generate_tags(self, city, filter_type: str) -> List[str]:
        """Generate relevant tags for the city."""
        tags = []
        city_lower = city.name.lower()
        
        # Add category tags
        for category, cities in self.city_characteristics.items():
            if any(cat_city in city_lower for cat_city in cities):
                tags.append(category.replace('_', ' ').title())
        
        # Add size tag
        population = getattr(city, 'population', 100000)
        if population < 100000:
            tags.append('Small Town')
        elif population < 500000:
            tags.append('Medium City')
        else:
            tags.append('Large City')
        
        # Add country tag
        country = getattr(city, 'country', 'Europe')
        tags.append(country)
        
        return tags[:5]  # Limit to 5 tags
    
    def _generate_description(self, city) -> str:
        """Generate an appealing description for the city."""
        city_lower = city.name.lower()
        
        # Use enhanced descriptions if available
        if city_lower in self.enhanced_descriptions:
            return self.enhanced_descriptions[city_lower]
        
        # Generate based on characteristics
        descriptions = []
        
        # Check characteristics
        if any(cat_city in city_lower for cat_city in self.city_characteristics.get('romantic', [])):
            descriptions.append("romantic atmosphere")
        if any(cat_city in city_lower for cat_city in self.city_characteristics.get('cultural', [])):
            descriptions.append("rich cultural heritage")
        if any(cat_city in city_lower for cat_city in self.city_characteristics.get('foodie', [])):
            descriptions.append("exceptional culinary scene")
        if any(cat_city in city_lower for cat_city in self.city_characteristics.get('hidden_gems', [])):
            descriptions.append("authentic local charm")
        
        if descriptions:
            return f"Discover {city.name}'s {' and '.join(descriptions)} in this captivating European destination."
        
        return f"Experience the unique charm and character of {city.name}, a distinctive European destination."
    
    def _generate_reasons(self, city, ai_score: float, hidden_gem_score: float, uniqueness_score: float) -> List[str]:
        """Generate reasons why this city is recommended."""
        reasons = []
        
        if ai_score > 80:
            reasons.append("Perfect match for your preferences")
        elif ai_score > 60:
            reasons.append("Excellent fit for your travel style")
        
        if hidden_gem_score > 0.7:
            reasons.append("Authentic experience away from crowds")
        
        if uniqueness_score > 0.7:
            reasons.append("Unique features you won't find elsewhere")
        
        city_lower = city.name.lower()
        
        # Add specific reasons based on characteristics
        if any(cat_city in city_lower for cat_city in self.city_characteristics.get('romantic', [])):
            reasons.append("Perfect for romantic getaways")
        if any(cat_city in city_lower for cat_city in self.city_characteristics.get('foodie', [])):
            reasons.append("Outstanding culinary experiences")
        if any(cat_city in city_lower for cat_city in self.city_characteristics.get('cultural', [])):
            reasons.append("Rich history and cultural attractions")
        
        return reasons[:3]  # Limit to 3 reasons
    
    def _get_fallback_cities(self, limit: int) -> List[DiscoveredCity]:
        """Return fallback cities when discovery fails."""
        fallback_data = [
            ("Ljubljana", "Slovenia", "Slovenia's charming capital with fairy-tale architecture", 85),
            ("Porto", "Portugal", "Portugal's soulful northern gem famous for port wine", 82),
            ("Bruges", "Belgium", "Medieval time capsule with romantic canals", 80),
            ("Tallinn", "Estonia", "Medieval Baltic treasure with digital innovation", 78),
            ("Ghent", "Belgium", "Belgium's best-kept secret with university energy", 75),
        ]
        
        cities = []
        for name, country, desc, score in fallback_data[:limit]:
            cities.append(DiscoveredCity(
                name=name,
                country=country,
                description=desc,
                ai_score=score,
                tags=["Hidden Gem", "Cultural", country],
                population=150000,
                coordinates=(50.0, 4.0),
                hidden_gem_score=0.8,
                uniqueness_score=0.7,
                accessibility_score=0.6,
                reasons=["Authentic experience", "Unique character", "Perfect for exploration"]
            ))
        
        return cities
"""
Claude AI integration for travel assistance, personalization, and intelligent features.
"""
import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

class ClaudeAIService:
    """Service for integrating Claude AI into travel planning and assistance."""
    
    def __init__(self):
        self.api_key = os.getenv('CLAUDE_API_KEY')
        self.base_url = "https://api.anthropic.com/v1"
        self.model = "claude-3-sonnet-20240229"
        self.session = None
        
        if not self.api_key:
            logger.warning("Claude API key not configured - AI features will be limited")
    
    async def _make_request(self, messages: List[Dict], max_tokens: int = 1000, 
                           system_prompt: str = None) -> Optional[str]:
        """Make a request to Claude API."""
        if not self.api_key:
            return None
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': self.api_key,
                'anthropic-version': '2023-06-01'
            }
            
            payload = {
                'model': self.model,
                'max_tokens': max_tokens,
                'messages': messages
            }
            
            if system_prompt:
                payload['system'] = system_prompt
            
            async with self.session.post(f"{self.base_url}/messages", 
                                       headers=headers, 
                                       json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['content'][0]['text'] if data.get('content') else None
                else:
                    logger.error(f"Claude API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Claude API request failed: {e}")
            return None
    
    def _make_request_sync(self, messages: List[Dict], max_tokens: int = 1000, 
                          system_prompt: str = None) -> Optional[str]:
        """Make a synchronous request to Claude API."""
        if not self.api_key:
            return None
        
        try:
            import requests
            
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': self.api_key,
                'anthropic-version': '2023-06-01'
            }
            
            payload = {
                'model': self.model,
                'max_tokens': max_tokens,
                'messages': messages
            }
            
            if system_prompt:
                payload['system'] = system_prompt
            
            response = requests.post(f"{self.base_url}/messages", 
                                   headers=headers, 
                                   json=payload,
                                   timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data['content'][0]['text'] if data.get('content') else None
            else:
                logger.error(f"Claude API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Claude API sync request failed: {e}")
            return None
    
    async def travel_chat_assistant(self, user_message: str, chat_history: List[Dict] = None, 
                                  user_context: Dict = None) -> str:
        """AI travel assistant for general travel questions and advice."""
        system_prompt = """You are an expert European travel assistant specializing in road trips and travel planning. 
        You help users plan amazing road trips across Europe, provide travel advice, suggest destinations, 
        and answer questions about European travel, culture, food, and attractions.
        
        Keep your responses helpful, informative, and engaging. Always consider practical aspects like 
        driving distances, costs, weather, and seasonal considerations. Be specific with recommendations 
        and provide actionable advice.
        
        If asked about the Road Trip Planner app, explain that it's a comprehensive tool for planning 
        European road trips with AI-powered route suggestions, real hotel bookings, restaurant recommendations, 
        and detailed itineraries."""
        
        # Build conversation context
        messages = []
        
        # Add chat history if available
        if chat_history:
            for msg in chat_history[-10:]:  # Last 10 messages for context
                messages.append({
                    'role': msg.get('message_type', 'user'),
                    'content': msg.get('message_content', '')
                })
        
        # Add current user message
        messages.append({
            'role': 'user',
            'content': user_message
        })
        
        response = await self._make_request(messages, max_tokens=1500, system_prompt=system_prompt)
        return response or "I'm sorry, I'm having trouble connecting to my AI assistant right now. Please try again later."
    
    async def analyze_travel_preferences(self, user_data: Dict) -> Dict:
        """Analyze user travel preferences and suggest personalized recommendations."""
        system_prompt = """You are an AI travel analyst. Analyze the user's travel history and preferences 
        to provide personalized insights and recommendations for future trips.
        
        Based on the provided data, identify patterns in their travel behavior, preferred destinations, 
        route types, spending habits, and suggest improvements or new experiences they might enjoy.
        
        Return your analysis as a JSON object with these keys:
        - travel_personality: A brief description of their travel style
        - preferred_experiences: List of experiences they seem to enjoy
        - budget_insights: Analysis of their spending patterns
        - recommendations: Specific suggestions for future trips
        - new_destinations: Suggested new places to explore
        - optimal_trip_length: Recommended trip duration based on their history"""
        
        user_prompt = f"""Analyze this user's travel data and provide personalized insights:
        
        Travel History:
        - Total trips: {user_data.get('total_trips', 0)}
        - Total distance traveled: {user_data.get('total_distance', 0)} km
        - Favorite route type: {user_data.get('favorite_route_type', 'unknown')}
        - Cities visited: {user_data.get('cities_visited', [])}
        - Average trip cost: €{user_data.get('average_cost', 0)}
        - Most recent trips: {user_data.get('recent_trips', [])}
        
        Please provide a comprehensive analysis and recommendations."""
        
        messages = [{'role': 'user', 'content': user_prompt}]
        
        response = await self._make_request(messages, max_tokens=2000, system_prompt=system_prompt)
        
        if response:
            try:
                # Try to parse as JSON
                return json.loads(response)
            except json.JSONDecodeError:
                # If not valid JSON, return structured fallback
                return {
                    'travel_personality': 'Adventure Seeker',
                    'preferred_experiences': ['Cultural sites', 'Scenic routes', 'Local cuisine'],
                    'budget_insights': 'Balanced spending on experiences and comfort',
                    'recommendations': [response],
                    'new_destinations': ['Prague', 'Swiss Alps', 'Portuguese Coast'],
                    'optimal_trip_length': '5-7 days'
                }
        
        return self._get_fallback_analysis()
    
    async def generate_smart_itinerary(self, route_data: Dict, user_preferences: Dict = None, 
                                     days: int = 5) -> Dict:
        """Generate a detailed day-by-day itinerary using AI."""
        system_prompt = """You are an expert travel itinerary planner. Create detailed, practical 
        day-by-day itineraries for European road trips. Include specific activities, timing, 
        restaurant suggestions, cultural insights, and practical tips.
        
        Return a JSON object with this structure:
        {
            "itinerary": [
                {
                    "day": 1,
                    "location": "City Name",
                    "theme": "Arrival & Exploration",
                    "morning": { "activity": "", "description": "", "duration": "", "tips": "" },
                    "afternoon": { "activity": "", "description": "", "duration": "", "tips": "" },
                    "evening": { "activity": "", "description": "", "duration": "", "tips": "" },
                    "restaurants": [{"name": "", "cuisine": "", "price_range": "", "why_special": ""}],
                    "driving_info": {"distance": "", "duration": "", "route_notes": ""}
                }
            ],
            "travel_tips": [],
            "cultural_insights": [],
            "budget_breakdown": {"daily_average": "", "total_estimate": ""}
        }"""
        
        cities = [route_data.get('start_city', {}).get('name', 'Start')] + \
                [city.get('name', '') if isinstance(city, dict) else str(city) 
                 for city in route_data.get('intermediate_cities', [])] + \
                [route_data.get('end_city', {}).get('name', 'End')]
        
        route_type = route_data.get('route_type', 'scenic')
        total_distance = route_data.get('total_distance_km', 0)
        
        user_prompt = f"""Create a detailed {days}-day itinerary for a {route_type} road trip:
        
        Route: {' → '.join(cities)}
        Total Distance: {total_distance} km
        Route Type: {route_type}
        User Preferences: {user_preferences or 'Standard European road trip experience'}
        
        Focus on the {route_type} aspects and create memorable experiences for each day.
        Include practical driving information, local specialties, and cultural highlights."""
        
        messages = [{'role': 'user', 'content': user_prompt}]
        
        response = await self._make_request(messages, max_tokens=3000, system_prompt=system_prompt)
        
        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI itinerary response as JSON")
                return self._create_fallback_itinerary(cities, days, route_type)
        
        return self._create_fallback_itinerary(cities, days, route_type)
    
    async def optimize_route_for_weather(self, route_data: Dict, weather_data: Dict) -> Dict:
        """Optimize route suggestions based on weather conditions."""
        system_prompt = """You are a weather-aware travel optimizer. Analyze the route and weather 
        conditions to suggest optimizations, alternative activities, and timing adjustments.
        
        Provide practical advice for handling different weather conditions during the trip."""
        
        user_prompt = f"""Optimize this route based on weather conditions:
        
        Route: {route_data.get('start_city', {}).get('name')} to {route_data.get('end_city', {}).get('name')}
        Cities: {[city.get('name', '') if isinstance(city, dict) else str(city) for city in route_data.get('intermediate_cities', [])]}
        Route Type: {route_data.get('route_type', 'scenic')}
        
        Weather Forecast: {weather_data}
        
        Suggest optimizations, indoor alternatives, and timing adjustments."""
        
        messages = [{'role': 'user', 'content': user_prompt}]
        
        response = await self._make_request(messages, max_tokens=1500, system_prompt=system_prompt)
        
        return {
            'optimizations': response or "Weather optimization unavailable",
            'indoor_alternatives': [],
            'timing_suggestions': []
        }
    
    def analyze_photo_for_destinations(self, image_data: str = None, photo_description: str = None) -> List[Dict]:
        """Analyze photo or photo descriptions to suggest similar destinations."""
        
        if image_data:
            # Use Claude's vision capabilities for actual image analysis
            system_prompt = """You are an expert travel destination recommendation AI with visual analysis capabilities. 
            Analyze the uploaded image and suggest 3-5 similar European destinations that match what you see in the photo.
            
            Look for:
            - Architectural styles (Gothic, Renaissance, Medieval, Modern, etc.)
            - Natural features (mountains, lakes, coastlines, forests, etc.)
            - Urban vs rural settings
            - Cultural elements and atmosphere
            - Historical periods and influences
            
            Return a JSON array with this exact structure:
            [
                {
                    "destination": "City/Location Name",
                    "country": "Country",
                    "similarity_reasons": ["specific reason based on what you see in the image"],
                    "best_time_to_visit": "Season/Months",
                    "highlights": ["attraction1", "attraction2", "attraction3"],
                    "image_match_confidence": "high/medium/low"
                }
            ]"""
            
            try:
                # Create message with image for Claude's vision API
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",  # Will be updated based on actual image type
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": "Analyze this travel destination image and suggest similar European destinations I could visit. Focus on architectural style, natural features, and overall atmosphere."
                            }
                        ]
                    }
                ]
                
                response = self._make_request_sync(messages, max_tokens=1500, system_prompt=system_prompt)
                
                try:
                    destinations = json.loads(response) if response else []
                    return destinations if isinstance(destinations, list) else []
                except json.JSONDecodeError:
                    # If JSON parsing fails, return the response as a simple text suggestion
                    return [{"destination": "AI Analysis", "country": "Europe", "description": response or "Unable to analyze image"}]
                    
            except Exception as e:
                logger.error(f"Image analysis failed: {e}")
                return [{"destination": "Analysis Error", "country": "Europe", "description": "Unable to analyze the uploaded image. Please try again with a clearer photo."}]
        
        elif photo_description:
            # Fallback to text-based analysis
            system_prompt = """You are a destination recommendation AI. Based on photo descriptions, 
            suggest similar European destinations that match the aesthetic, atmosphere, or features 
            described in the image.
            
            Return a JSON array of destinations with this structure:
            [
                {
                    "destination": "City/Location Name",
                    "country": "Country",
                    "similarity_reasons": ["reason1", "reason2"],
                    "best_time_to_visit": "Season/Months",
                    "highlights": ["attraction1", "attraction2"],
                    "driving_distance_from_major_cities": {"Paris": "500km", "Munich": "300km"}
                }
            ]"""
        
            user_prompt = f"""Based on this photo description, suggest similar European destinations for a road trip:
            
            Photo Description: {photo_description}
            
            Find places with similar landscapes, architecture, atmosphere, or cultural features."""
            
            messages = [{'role': 'user', 'content': user_prompt}]
            
            try:
                response = self._make_request_sync(messages, max_tokens=2000, system_prompt=system_prompt)
                
                if response:
                    try:
                        return json.loads(response)
                    except json.JSONDecodeError:
                        return [{"destination": "AI Analysis", "country": "Europe", "description": response}]
            except Exception as e:
                logger.error(f"Text-based photo analysis failed: {e}")
        
        return [
            {
                "destination": "Photo Analysis Unavailable",
                "country": "Europe",
                "similarity_reasons": ["Service temporarily unavailable"],
                "best_time_to_visit": "Spring to Fall",
                "highlights": ["Please try again later"],
                "description": "Photo analysis service is currently unavailable"
            }
        ]
    
    async def generate_travel_insights(self, user_analytics: Dict) -> Dict:
        """Generate travel insights and statistics."""
        system_prompt = """You are a travel analytics expert. Analyze user travel data to provide 
        interesting insights, achievements, comparisons, and gamification elements.
        
        Create engaging travel statistics and milestone celebrations."""
        
        user_prompt = f"""Generate travel insights for this user:
        
        Analytics: {user_analytics}
        
        Create interesting statistics, achievements unlocked, comparisons to average travelers, 
        and milestone celebrations. Make it engaging and motivational."""
        
        messages = [{'role': 'user', 'content': user_prompt}]
        
        response = await self._make_request(messages, max_tokens=1500, system_prompt=system_prompt)
        
        return {
            'insights': response or "Your travel journey is unique and amazing!",
            'achievements': ['Explorer', 'Road Trip Enthusiast'],
            'next_milestones': ['Visit 10 countries', 'Complete 25 trips']
        }
    
    def _get_fallback_analysis(self) -> Dict:
        """Fallback analysis when AI is unavailable."""
        return {
            'travel_personality': 'Adventurous Explorer',
            'preferred_experiences': ['Cultural discovery', 'Scenic beauty', 'Local cuisine'],
            'budget_insights': 'Balanced approach to travel spending',
            'recommendations': ['Try a different route type', 'Explore off-season destinations'],
            'new_destinations': ['Czech Republic', 'Slovenia', 'Portuguese Douro Valley'],
            'optimal_trip_length': '5-7 days'
        }
    
    def _create_fallback_itinerary(self, cities: List[str], days: int, route_type: str) -> Dict:
        """Create fallback itinerary when AI is unavailable."""
        itinerary = []
        for day in range(1, days + 1):
            city_index = min(day - 1, len(cities) - 1)
            city = cities[city_index] if cities else f"Day {day} Location"
            
            itinerary.append({
                'day': day,
                'location': city,
                'theme': f"Explore {city}",
                'morning': {
                    'activity': f"Morning in {city}",
                    'description': f"Discover the highlights of {city}",
                    'duration': '3 hours',
                    'tips': 'Start early to avoid crowds'
                },
                'afternoon': {
                    'activity': f"Afternoon activities",
                    'description': f"Enjoy local culture and attractions",
                    'duration': '4 hours',
                    'tips': 'Perfect time for sightseeing'
                },
                'evening': {
                    'activity': f"Evening dining",
                    'description': f"Experience local cuisine",
                    'duration': '2 hours',
                    'tips': 'Try regional specialties'
                },
                'restaurants': [
                    {
                        'name': f"Local Restaurant in {city}",
                        'cuisine': 'Regional',
                        'price_range': '€€',
                        'why_special': 'Authentic local experience'
                    }
                ],
                'driving_info': {
                    'distance': '50-100 km' if day < days else '0 km',
                    'duration': '1-2 hours' if day < days else 'Final destination',
                    'route_notes': 'Scenic route recommended'
                }
            })
        
        return {
            'itinerary': itinerary,
            'travel_tips': ['Pack light', 'Check weather', 'Have backup plans'],
            'cultural_insights': ['Learn basic local phrases', 'Respect local customs'],
            'budget_breakdown': {
                'daily_average': '€100-150',
                'total_estimate': f'€{days * 125}'
            }
        }
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()

# Global service instance
_claude_service = None

def get_claude_service() -> ClaudeAIService:
    """Get global Claude AI service instance."""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeAIService()
    return _claude_service
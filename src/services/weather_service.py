"""
Weather service for real-time weather data and travel optimization.
"""
import os
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from ..core.models import Coordinates

logger = structlog.get_logger(__name__)

class WeatherService:
    """Service for weather data and travel weather optimization."""
    
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHER_API_KEY')  # Free OpenWeatherMap API
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.session = None
        
        if not self.api_key:
            logger.warning("Weather API key not configured - using fallback data")
    
    async def get_current_weather(self, coordinates: Coordinates, city_name: str) -> Dict:
        """Get current weather for a location."""
        if not self.api_key:
            return self._get_fallback_weather(city_name)
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/weather"
            params = {
                'lat': coordinates.latitude,
                'lon': coordinates.longitude,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_current_weather(data, city_name)
                else:
                    logger.warning(f"Weather API error: {response.status}")
                    return self._get_fallback_weather(city_name)
                    
        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
            return self._get_fallback_weather(city_name)
    
    async def get_weather_forecast(self, coordinates: Coordinates, city_name: str, days: int = 5) -> Dict:
        """Get weather forecast for a location."""
        if not self.api_key:
            return self._get_fallback_forecast(city_name, days)
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/forecast"
            params = {
                'lat': coordinates.latitude,
                'lon': coordinates.longitude,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': days * 8  # 8 forecasts per day (3-hour intervals)
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_forecast(data, city_name)
                else:
                    logger.warning(f"Weather forecast API error: {response.status}")
                    return self._get_fallback_forecast(city_name, days)
                    
        except Exception as e:
            logger.error(f"Weather forecast error: {e}")
            return self._get_fallback_forecast(city_name, days)
    
    async def get_route_weather(self, route_cities: List[Dict]) -> Dict:
        """Get weather data for all cities in a route."""
        weather_data = {}
        
        for city in route_cities:
            city_name = city.get('name', '')
            coordinates = city.get('coordinates', [])
            
            if city_name and coordinates:
                try:
                    from ..core.models import Coordinates
                    city_coords = Coordinates(latitude=coordinates[0], longitude=coordinates[1])
                    
                    # Get both current weather and forecast
                    current = await self.get_current_weather(city_coords, city_name)
                    forecast = await self.get_weather_forecast(city_coords, city_name)
                    
                    weather_data[city_name] = {
                        'current': current,
                        'forecast': forecast
                    }
                    
                except Exception as e:
                    logger.warning(f"Weather fetch failed for {city_name}: {e}")
                    weather_data[city_name] = {
                        'current': self._get_fallback_weather(city_name),
                        'forecast': self._get_fallback_forecast(city_name, 5)
                    }
        
        return weather_data
    
    def analyze_travel_conditions(self, weather_data: Dict) -> Dict:
        """Analyze weather conditions for travel optimization."""
        analysis = {
            'overall_conditions': 'good',
            'alerts': [],
            'recommendations': [],
            'best_travel_days': [],
            'weather_warnings': []
        }
        
        poor_weather_count = 0
        total_cities = len(weather_data)
        
        for city_name, city_weather in weather_data.items():
            current = city_weather.get('current', {})
            forecast = city_weather.get('forecast', {})
            
            # Check current conditions
            temp = current.get('temperature', 20)
            condition = current.get('condition', '').lower()
            humidity = current.get('humidity', 50)
            wind_speed = current.get('wind_speed', 5)
            
            # Analyze conditions for driving
            if 'rain' in condition or 'storm' in condition:
                analysis['alerts'].append(f"Rain expected in {city_name} - pack waterproof gear")
                poor_weather_count += 1
            
            if 'snow' in condition:
                analysis['alerts'].append(f"Snow conditions in {city_name} - check tire requirements")
                analysis['weather_warnings'].append(f"Winter driving conditions in {city_name}")
                poor_weather_count += 1
            
            if wind_speed > 20:
                analysis['alerts'].append(f"Strong winds in {city_name} - drive carefully")
            
            if temp < 0:
                analysis['recommendations'].append(f"Pack warm clothing for {city_name} (freezing temperatures)")
            elif temp > 35:
                analysis['recommendations'].append(f"Stay hydrated in {city_name} (very hot weather)")
            
            # Analyze forecast for best travel days
            daily_forecasts = forecast.get('daily', [])
            for i, day_forecast in enumerate(daily_forecasts[:5]):
                day_condition = day_forecast.get('condition', '').lower()
                day_temp = day_forecast.get('temperature', 20)
                
                if ('clear' in day_condition or 'sunny' in day_condition) and 15 <= day_temp <= 25:
                    date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
                    analysis['best_travel_days'].append({
                        'date': date,
                        'city': city_name,
                        'condition': day_condition,
                        'temperature': day_temp
                    })
        
        # Overall assessment
        if poor_weather_count == 0:
            analysis['overall_conditions'] = 'excellent'
        elif poor_weather_count / total_cities < 0.3:
            analysis['overall_conditions'] = 'good'
        elif poor_weather_count / total_cities < 0.6:
            analysis['overall_conditions'] = 'fair'
        else:
            analysis['overall_conditions'] = 'poor'
        
        # General recommendations
        if analysis['overall_conditions'] in ['poor', 'fair']:
            analysis['recommendations'].append("Consider postponing trip or choosing alternative indoor activities")
        
        if len(analysis['best_travel_days']) > 0:
            analysis['recommendations'].append("Plan outdoor activities during the clearest days")
        
        return analysis
    
    def get_seasonal_recommendations(self, month: int, route_type: str) -> List[str]:
        """Get seasonal travel recommendations."""
        recommendations = []
        
        # Spring (March-May)
        if 3 <= month <= 5:
            recommendations.extend([
                "Perfect time for scenic routes with blooming landscapes",
                "Pack layers - weather can be unpredictable",
                "Popular destinations may have fewer crowds"
            ])
            if route_type == 'scenic':
                recommendations.append("Cherry blossoms and spring flowers make this ideal for scenic routes")
        
        # Summer (June-August)
        elif 6 <= month <= 8:
            recommendations.extend([
                "Peak travel season - book accommodations early",
                "Perfect weather for outdoor activities and adventure routes",
                "Stay hydrated and use sun protection"
            ])
            if route_type == 'adventure':
                recommendations.append("Ideal season for hiking and outdoor adventures")
        
        # Autumn (September-November)
        elif 9 <= month <= 11:
            recommendations.extend([
                "Beautiful fall foliage for scenic routes",
                "Comfortable temperatures for driving",
                "Harvest season - great for culinary tours"
            ])
            if route_type == 'culinary':
                recommendations.append("Harvest season offers the best local produce and wines")
        
        # Winter (December-February)
        else:
            recommendations.extend([
                "Check winter driving requirements",
                "Some mountain passes may be closed",
                "Perfect for cultural and indoor activities"
            ])
            if route_type == 'cultural':
                recommendations.append("Winter is ideal for museums, galleries, and cultural sites")
        
        return recommendations
    
    def _format_current_weather(self, data: Dict, city_name: str) -> Dict:
        """Format current weather data from API response."""
        return {
            'city': city_name,
            'temperature': data['main']['temp'],
            'feels_like': data['main']['feels_like'],
            'humidity': data['main']['humidity'],
            'pressure': data['main']['pressure'],
            'condition': data['weather'][0]['description'],
            'condition_icon': data['weather'][0]['icon'],
            'wind_speed': data['wind']['speed'],
            'wind_direction': data['wind'].get('deg', 0),
            'visibility': data.get('visibility', 10000) / 1000,  # Convert to km
            'uv_index': data.get('uvi', 5),  # Fallback value
            'timestamp': datetime.now().isoformat()
        }
    
    def _format_forecast(self, data: Dict, city_name: str) -> Dict:
        """Format forecast data from API response."""
        forecasts = data['list']
        daily_forecasts = []
        
        # Group forecasts by day
        current_day = None
        day_data = []
        
        for forecast in forecasts:
            forecast_date = datetime.fromtimestamp(forecast['dt']).date()
            
            if current_day != forecast_date:
                if day_data:
                    daily_forecasts.append(self._aggregate_daily_forecast(day_data, current_day))
                current_day = forecast_date
                day_data = []
            
            day_data.append(forecast)
        
        # Add the last day
        if day_data:
            daily_forecasts.append(self._aggregate_daily_forecast(day_data, current_day))
        
        return {
            'city': city_name,
            'daily': daily_forecasts[:5],  # 5-day forecast
            'hourly': [self._format_hourly_forecast(f) for f in forecasts[:24]]  # 24-hour forecast
        }
    
    def _aggregate_daily_forecast(self, day_data: List[Dict], date) -> Dict:
        """Aggregate hourly forecasts into daily forecast."""
        temps = [d['main']['temp'] for d in day_data]
        conditions = [d['weather'][0]['description'] for d in day_data]
        
        # Find most common condition
        condition_counts = {}
        for condition in conditions:
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
        
        most_common_condition = max(condition_counts, key=condition_counts.get)
        
        return {
            'date': date.isoformat(),
            'temperature': sum(temps) / len(temps),
            'min_temperature': min(temps),
            'max_temperature': max(temps),
            'condition': most_common_condition,
            'humidity': sum(d['main']['humidity'] for d in day_data) / len(day_data),
            'wind_speed': sum(d['wind']['speed'] for d in day_data) / len(day_data),
            'precipitation_chance': max(d.get('pop', 0) for d in day_data) * 100
        }
    
    def _format_hourly_forecast(self, forecast: Dict) -> Dict:
        """Format hourly forecast data."""
        return {
            'time': datetime.fromtimestamp(forecast['dt']).isoformat(),
            'temperature': forecast['main']['temp'],
            'condition': forecast['weather'][0]['description'],
            'condition_icon': forecast['weather'][0]['icon'],
            'humidity': forecast['main']['humidity'],
            'wind_speed': forecast['wind']['speed'],
            'precipitation_chance': forecast.get('pop', 0) * 100
        }
    
    def _get_fallback_weather(self, city_name: str) -> Dict:
        """Fallback when weather API is unavailable - returns minimal data indicating unavailable service."""
        logger.warning(f"Weather service unavailable for {city_name}. Returning minimal fallback data.")
        return {
            'city': city_name,
            'temperature': None,
            'feels_like': None,
            'humidity': None,
            'pressure': None,
            'condition': 'Weather data unavailable',
            'condition_icon': '',
            'wind_speed': None,
            'wind_direction': None,
            'visibility': None,
            'uv_index': None,
            'timestamp': datetime.now().isoformat(),
            'error': 'Weather service unavailable'
        }
    
    def _get_fallback_forecast(self, city_name: str, days: int) -> Dict:
        """Fallback when forecast API is unavailable - returns minimal data indicating unavailable service."""
        logger.warning(f"Weather forecast service unavailable for {city_name}. Returning minimal fallback data.")
        daily_forecasts = []
        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            daily_forecasts.append({
                'date': date.date().isoformat(),
                'temperature': None,
                'min_temperature': None,
                'max_temperature': None,
                'condition': 'Weather data unavailable',
                'humidity': None,
                'wind_speed': None,
                'precipitation_chance': None,
                'error': 'Weather service unavailable'
            })
        
        return {
            'city': city_name,
            'daily': daily_forecasts,
            'hourly': [],
            'error': 'Weather service unavailable'
        }
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()

# Global service instance
_weather_service = None

def get_weather_service() -> WeatherService:
    """Get global weather service instance."""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
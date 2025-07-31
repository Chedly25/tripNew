"""
Weather service for route optimization based on weather conditions
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from config import Config, WEATHER_SCORES
import logging

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.api_key = Config.OPENWEATHER_API_KEY
        self.base_url = Config.OPENWEATHER_URL
        self.use_api = bool(self.api_key and self.api_key != 'your_openweather_api_key_here')
    
    def get_weather_forecast(self, lat: float, lon: float, days: int = 5) -> Optional[Dict]:
        """Get weather forecast for a location"""
        if self.use_api:
            return self._get_weather_api(lat, lon, days)
        else:
            return self._get_weather_fallback(lat, lon, days)
    
    def _get_weather_api(self, lat: float, lon: float, days: int = 5) -> Optional[Dict]:
        """Get weather data from OpenWeatherMap API"""
        try:
            # Get current weather
            current_params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            current_response = requests.get(f"{self.base_url}/weather", params=current_params)
            current_data = current_response.json()
            
            # Get forecast
            forecast_params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            forecast_response = requests.get(f"{self.base_url}/forecast", params=forecast_params)
            forecast_data = forecast_response.json()
            
            if current_response.status_code == 200 and forecast_response.status_code == 200:
                return self._process_weather_data(current_data, forecast_data, days)
                
        except Exception as e:
            logger.error(f"Weather API error for {lat}, {lon}: {e}")
        
        return None
    
    def _get_weather_fallback(self, lat: float, lon: float, days: int = 5) -> Dict:
        """Generate fallback weather data"""
        # Generate realistic weather data based on season and location
        import random
        from datetime import datetime
        
        current_month = datetime.now().month
        
        # Determine season
        if current_month in [12, 1, 2]:
            season = 'winter'
            temp_range = (2, 12)
            rain_chance = 0.4
        elif current_month in [3, 4, 5]:
            season = 'spring'
            temp_range = (8, 18)
            rain_chance = 0.3
        elif current_month in [6, 7, 8]:
            season = 'summer'
            temp_range = (18, 28)
            rain_chance = 0.2
        else:
            season = 'autumn'
            temp_range = (10, 20)
            rain_chance = 0.35
        
        # Adjust for latitude (northern = colder)
        if lat > 50:  # Northern Europe
            temp_range = (temp_range[0] - 3, temp_range[1] - 3)
        elif lat < 40:  # Southern Europe
            temp_range = (temp_range[0] + 5, temp_range[1] + 5)
        
        forecast = []
        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            
            # Generate weather conditions
            rain_today = random.random() < rain_chance
            if rain_today:
                condition = random.choice(['rain', 'shower_rain'])
                temp_today = random.randint(temp_range[0], temp_range[0] + 8)
            else:
                condition = random.choice(['clear', 'few_clouds', 'scattered_clouds'])
                temp_today = random.randint(temp_range[0] + 3, temp_range[1])
            
            forecast.append({
                'date': date.strftime('%Y-%m-%d'),
                'temperature': temp_today,
                'condition': condition,
                'description': condition.replace('_', ' ').title(),
                'humidity': random.randint(40, 80),
                'wind_speed': random.randint(5, 25),
                'score': WEATHER_SCORES.get(condition, 0.7)
            })
        
        return {
            'current': forecast[0],
            'forecast': forecast,
            'location': f"Lat: {lat:.2f}, Lon: {lon:.2f}",
            'source': 'fallback'
        }
    
    def _process_weather_data(self, current_data: Dict, forecast_data: Dict, days: int) -> Dict:
        """Process raw weather data into standardized format"""
        current = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'temperature': round(current_data['main']['temp']),
            'condition': self._normalize_condition(current_data['weather'][0]['main'].lower()),
            'description': current_data['weather'][0]['description'],
            'humidity': current_data['main']['humidity'],
            'wind_speed': round(current_data['wind']['speed'] * 3.6),  # Convert m/s to km/h
            'score': WEATHER_SCORES.get(self._normalize_condition(current_data['weather'][0]['main'].lower()), 0.7)
        }
        
        forecast = [current]
        
        # Process forecast data (3-hour intervals, group by day)
        daily_forecasts = {}
        for item in forecast_data['list'][:days * 8]:  # 8 forecasts per day (3-hour intervals)
            date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
            
            if date not in daily_forecasts:
                daily_forecasts[date] = []
            
            daily_forecasts[date].append({
                'temperature': round(item['main']['temp']),
                'condition': self._normalize_condition(item['weather'][0]['main'].lower()),
                'description': item['weather'][0]['description'],
                'humidity': item['main']['humidity'],
                'wind_speed': round(item['wind']['speed'] * 3.6)
            })
        
        # Average daily values
        for date, forecasts in daily_forecasts.items():
            if date != current['date']:  # Skip current day
                avg_temp = sum(f['temperature'] for f in forecasts) // len(forecasts)
                most_common_condition = max(set(f['condition'] for f in forecasts), 
                                          key=[f['condition'] for f in forecasts].count)
                avg_humidity = sum(f['humidity'] for f in forecasts) // len(forecasts)
                avg_wind = sum(f['wind_speed'] for f in forecasts) // len(forecasts)
                
                forecast.append({
                    'date': date,
                    'temperature': avg_temp,
                    'condition': most_common_condition,
                    'description': most_common_condition.replace('_', ' ').title(),
                    'humidity': avg_humidity,
                    'wind_speed': avg_wind,
                    'score': WEATHER_SCORES.get(most_common_condition, 0.7)
                })
        
        return {
            'current': current,
            'forecast': forecast[:days],
            'location': f"{current_data['name']}, {current_data['sys']['country']}",
            'source': 'openweathermap'
        }
    
    def _normalize_condition(self, condition: str) -> str:
        """Normalize weather condition to our scoring system"""
        condition_map = {
            'clear': 'clear',
            'clouds': 'few_clouds',
            'rain': 'rain',
            'drizzle': 'shower_rain',
            'thunderstorm': 'thunderstorm',
            'snow': 'snow',
            'mist': 'mist',
            'fog': 'mist',
            'haze': 'mist'
        }
        return condition_map.get(condition, 'few_clouds')
    
    def get_route_weather_score(self, route_coordinates: List[Tuple[float, float]], 
                               travel_dates: List[datetime]) -> float:
        """Calculate weather score for an entire route"""
        if not route_coordinates or not travel_dates:
            return 0.7  # Default neutral score
        
        total_score = 0
        valid_scores = 0
        
        # Sample weather at key points along the route
        sample_points = route_coordinates[::max(1, len(route_coordinates) // 5)]  # Sample up to 5 points
        
        for i, coords in enumerate(sample_points):
            if i < len(travel_dates):
                weather = self.get_weather_forecast(coords[0], coords[1], 1)
                if weather and weather['forecast']:
                    # Find weather for the travel date
                    travel_date = travel_dates[i].strftime('%Y-%m-%d')
                    for forecast in weather['forecast']:
                        if forecast['date'] == travel_date:
                            total_score += forecast['score']
                            valid_scores += 1
                            break
        
        return total_score / valid_scores if valid_scores > 0 else 0.7
    
    def get_weather_alerts(self, lat: float, lon: float) -> List[Dict]:
        """Get weather alerts for a location"""
        if not self.use_api:
            return []
        
        try:
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key
            }
            
            response = requests.get(f"{self.base_url}/onecall", params=params)
            data = response.json()
            
            alerts = []
            if 'alerts' in data:
                for alert in data['alerts']:
                    alerts.append({
                        'event': alert['event'],
                        'description': alert['description'],
                        'start': datetime.fromtimestamp(alert['start']),
                        'end': datetime.fromtimestamp(alert['end']),
                        'severity': self._categorize_alert_severity(alert['event'])
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Weather alerts error for {lat}, {lon}: {e}")
            return []
    
    def _categorize_alert_severity(self, event: str) -> str:
        """Categorize weather alert severity"""
        high_severity = ['thunderstorm', 'snow', 'ice', 'wind', 'flood']
        medium_severity = ['rain', 'fog', 'heat']
        
        event_lower = event.lower()
        
        for keyword in high_severity:
            if keyword in event_lower:
                return 'high'
        
        for keyword in medium_severity:
            if keyword in event_lower:
                return 'medium'
        
        return 'low'
    
    def should_avoid_route_due_to_weather(self, weather_score: float, alerts: List[Dict]) -> bool:
        """Determine if a route should be avoided due to weather"""
        # Avoid if weather score is very low
        if weather_score < 0.3:
            return True
        
        # Avoid if there are high severity alerts
        for alert in alerts:
            if alert['severity'] == 'high':
                return True
        
        return False
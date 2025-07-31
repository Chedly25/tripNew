"""
Database layer for caching API results and storing user preferences
"""
import sqlite3
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "roadtrip_planner.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # API Cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS api_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cache_key TEXT UNIQUE,
                        data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        service_type TEXT
                    )
                ''')
                
                # Routes table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS routes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        route_id TEXT UNIQUE,
                        user_id TEXT,
                        route_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_favorite BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                # User preferences table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT UNIQUE,
                        preferences TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Weather cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS weather_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        location_key TEXT,
                        forecast_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                ''')
                
                # Events cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS events_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        city TEXT,
                        date_range TEXT,
                        events_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                ''')
                
                # City coordinates cache
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS city_coordinates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        city_name TEXT UNIQUE,
                        latitude REAL,
                        longitude REAL,
                        country TEXT,
                        formatted_address TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def cache_api_result(self, cache_key: str, data: Any, service_type: str, 
                        cache_hours: int = 6) -> bool:
        """Cache API result with expiration"""
        try:
            expires_at = datetime.now() + timedelta(hours=cache_hours)
            data_json = json.dumps(data, default=str)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO api_cache 
                    (cache_key, data, expires_at, service_type)
                    VALUES (?, ?, ?, ?)
                ''', (cache_key, data_json, expires_at, service_type))
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            return False
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached API result if not expired"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT data, expires_at FROM api_cache 
                    WHERE cache_key = ? AND expires_at > ?
                ''', (cache_key, datetime.now()))
                
                result = cursor.fetchone()
                if result:
                    data_json, expires_at = result
                    return json.loads(data_json)
                    
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        
        return None
    
    def cache_weather_data(self, lat: float, lon: float, forecast_data: Dict, 
                          cache_hours: int = 3) -> bool:
        """Cache weather forecast data"""
        try:
            location_key = f"{lat:.4f},{lon:.4f}"
            expires_at = datetime.now() + timedelta(hours=cache_hours)
            data_json = json.dumps(forecast_data, default=str)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO weather_cache 
                    (location_key, forecast_data, expires_at)
                    VALUES (?, ?, ?)
                ''', (location_key, data_json, expires_at))
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Weather cache error: {e}")
            return False
    
    def get_cached_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """Get cached weather data"""
        try:
            location_key = f"{lat:.4f},{lon:.4f}"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT forecast_data FROM weather_cache 
                    WHERE location_key = ? AND expires_at > ?
                ''', (location_key, datetime.now()))
                
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                    
        except Exception as e:
            logger.error(f"Weather cache retrieval error: {e}")
        
        return None
    
    def cache_events_data(self, city: str, start_date: datetime, end_date: datetime,
                         events_data: List[Dict], cache_hours: int = 12) -> bool:
        """Cache events data for a city and date range"""
        try:
            date_range = f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
            expires_at = datetime.now() + timedelta(hours=cache_hours)
            data_json = json.dumps(events_data, default=str)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO events_cache 
                    (city, date_range, events_data, expires_at)
                    VALUES (?, ?, ?, ?)
                ''', (city.lower(), date_range, data_json, expires_at))
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Events cache error: {e}")
            return False
    
    def get_cached_events(self, city: str, start_date: datetime, 
                         end_date: datetime) -> Optional[List[Dict]]:
        """Get cached events data"""
        try:
            date_range = f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT events_data FROM events_cache 
                    WHERE city = ? AND date_range = ? AND expires_at > ?
                ''', (city.lower(), date_range, datetime.now()))
                
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                    
        except Exception as e:
            logger.error(f"Events cache retrieval error: {e}")
        
        return None
    
    def cache_city_coordinates(self, city_name: str, lat: float, lon: float,
                              country: str = "", formatted_address: str = "") -> bool:
        """Cache city coordinates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO city_coordinates 
                    (city_name, latitude, longitude, country, formatted_address)
                    VALUES (?, ?, ?, ?, ?)
                ''', (city_name.lower(), lat, lon, country, formatted_address))
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"City coordinates cache error: {e}")
            return False
    
    def get_city_coordinates(self, city_name: str) -> Optional[Dict]:
        """Get cached city coordinates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT latitude, longitude, country, formatted_address 
                    FROM city_coordinates WHERE city_name = ?
                ''', (city_name.lower(),))
                
                result = cursor.fetchone()
                if result:
                    lat, lon, country, formatted_address = result
                    return {
                        'lat': lat,
                        'lon': lon,
                        'country': country,
                        'formatted_address': formatted_address
                    }
                    
        except Exception as e:
            logger.error(f"City coordinates retrieval error: {e}")
        
        return None
    
    def save_route(self, route_id: str, route_data: Dict, user_id: str = "anonymous") -> bool:
        """Save a generated route"""
        try:
            data_json = json.dumps(route_data, default=str)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO routes 
                    (route_id, user_id, route_data)
                    VALUES (?, ?, ?)
                ''', (route_id, user_id, data_json))
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Route save error: {e}")
            return False
    
    def get_saved_routes(self, user_id: str = "anonymous") -> List[Dict]:
        """Get all saved routes for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT route_id, route_data, created_at, is_favorite 
                    FROM routes WHERE user_id = ? 
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                results = cursor.fetchall()
                routes = []
                
                for route_id, route_data, created_at, is_favorite in results:
                    route = json.loads(route_data)
                    route['route_id'] = route_id
                    route['created_at'] = created_at
                    route['is_favorite'] = bool(is_favorite)
                    routes.append(route)
                
                return routes
                
        except Exception as e:
            logger.error(f"Routes retrieval error: {e}")
            return []
    
    def mark_route_favorite(self, route_id: str, is_favorite: bool = True) -> bool:
        """Mark/unmark a route as favorite"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE routes SET is_favorite = ? WHERE route_id = ?
                ''', (is_favorite, route_id))
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Route favorite update error: {e}")
            return False
    
    def save_user_preferences(self, user_id: str, preferences: Dict) -> bool:
        """Save user preferences"""
        try:
            prefs_json = json.dumps(preferences)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_preferences 
                    (user_id, preferences)
                    VALUES (?, ?)
                ''', (user_id, prefs_json))
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"User preferences save error: {e}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """Get user preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT preferences FROM user_preferences WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                    
        except Exception as e:
            logger.error(f"User preferences retrieval error: {e}")
        
        return None
    
    def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clean up API cache
                cursor.execute('DELETE FROM api_cache WHERE expires_at < ?', (datetime.now(),))
                api_cleaned = cursor.rowcount
                
                # Clean up weather cache
                cursor.execute('DELETE FROM weather_cache WHERE expires_at < ?', (datetime.now(),))
                weather_cleaned = cursor.rowcount
                
                # Clean up events cache
                cursor.execute('DELETE FROM events_cache WHERE expires_at < ?', (datetime.now(),))
                events_cleaned = cursor.rowcount
                
                conn.commit()
                
                total_cleaned = api_cleaned + weather_cleaned + events_cleaned
                logger.info(f"Cleaned up {total_cleaned} expired cache entries")
                
                return total_cleaned
                
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # API cache stats
                cursor.execute('SELECT COUNT(*) FROM api_cache WHERE expires_at > ?', (datetime.now(),))
                stats['active_api_cache'] = cursor.fetchone()[0]
                
                # Weather cache stats
                cursor.execute('SELECT COUNT(*) FROM weather_cache WHERE expires_at > ?', (datetime.now(),))
                stats['active_weather_cache'] = cursor.fetchone()[0]
                
                # Events cache stats
                cursor.execute('SELECT COUNT(*) FROM events_cache WHERE expires_at > ?', (datetime.now(),))
                stats['active_events_cache'] = cursor.fetchone()[0]
                
                # Routes stats
                cursor.execute('SELECT COUNT(*) FROM routes')
                stats['total_routes'] = cursor.fetchone()[0]
                
                # City coordinates stats
                cursor.execute('SELECT COUNT(*) FROM city_coordinates')
                stats['cached_cities'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}

# Global database instance
db_manager = None

def get_db():
    """Get global database instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
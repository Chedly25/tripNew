"""
Database models and configuration for the road trip application.
Supports user accounts, trip saving, favorites, and advanced features.
"""
import os
import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import hashlib
import secrets
import json
import structlog

logger = structlog.get_logger(__name__)

class Database:
    """Main database handler for the application."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'roadtrip.db')
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database with all required tables."""
        with self.get_connection() as conn:
            # Users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    salt TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    profile_image TEXT,
                    travel_preferences TEXT, -- JSON
                    oauth_provider TEXT, -- 'google', 'facebook', etc.
                    oauth_id TEXT, -- OAuth provider user ID
                    profile_picture TEXT, -- OAuth profile picture URL
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    email_verified BOOLEAN DEFAULT 0
                )
            ''')
            
            # Add OAuth columns to existing users table if they don't exist
            try:
                conn.execute('ALTER TABLE users ADD COLUMN oauth_provider TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                conn.execute('ALTER TABLE users ADD COLUMN oauth_id TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                conn.execute('ALTER TABLE users ADD COLUMN profile_picture TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # User sessions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Saved trips table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS saved_trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    trip_name TEXT NOT NULL,
                    trip_data TEXT NOT NULL, -- JSON
                    route_type TEXT NOT NULL,
                    start_city TEXT NOT NULL,
                    end_city TEXT NOT NULL,
                    intermediate_cities TEXT, -- JSON
                    total_distance REAL,
                    total_duration REAL,
                    estimated_cost REAL,
                    is_favorite BOOLEAN DEFAULT 0,
                    is_public BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Trip reviews and ratings
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trip_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    trip_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    review_text TEXT,
                    photos TEXT, -- JSON array of photo URLs
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id)
                )
            ''')
            
            # User travel analytics
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    total_trips INTEGER DEFAULT 0,
                    total_distance REAL DEFAULT 0,
                    total_duration REAL DEFAULT 0,
                    favorite_route_type TEXT,
                    countries_visited TEXT, -- JSON array
                    cities_visited TEXT, -- JSON array
                    carbon_footprint REAL DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # AI chat history
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ai_chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id TEXT NOT NULL,
                    message_type TEXT NOT NULL, -- 'user' or 'assistant'
                    message_content TEXT NOT NULL,
                    context_data TEXT, -- JSON for additional context
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Travel alerts and notifications
            conn.execute('''
                CREATE TABLE IF NOT EXISTS travel_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    alert_type TEXT NOT NULL, -- 'weather', 'traffic', 'safety', etc.
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    trip_id INTEGER,
                    is_read BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id)
                )
            ''')
            
            # Collaborative trip planning
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trip_collaborators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT DEFAULT 'viewer', -- 'owner', 'editor', 'viewer'
                    invited_by INTEGER,
                    invitation_status TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'declined'
                    invitation_token TEXT UNIQUE,
                    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    joined_at TIMESTAMP,
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (invited_by) REFERENCES users (id)
                )
            ''')
            
            # Trip votes and suggestions
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trip_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    suggestion_type TEXT NOT NULL, -- 'destination', 'activity', 'restaurant', 'hotel', etc.
                    suggestion_data TEXT NOT NULL, -- JSON
                    votes INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'proposed', -- 'proposed', 'accepted', 'rejected'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Offline trip downloads
            conn.execute('''
                CREATE TABLE IF NOT EXISTS offline_trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    trip_id INTEGER NOT NULL,
                    download_data TEXT NOT NULL, -- JSON with all trip data
                    version INTEGER DEFAULT 1,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_synced TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id)
                )
            ''')
            
            # Budget tracking and expenses
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trip_expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    expense_category TEXT NOT NULL, -- 'transport', 'accommodation', 'food', 'activities', etc.
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'EUR',
                    paid_by INTEGER NOT NULL,
                    split_with TEXT, -- JSON array of user_ids
                    receipt_url TEXT,
                    expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (paid_by) REFERENCES users (id)
                )
            ''')
            
            # Travel journal entries
            conn.execute('''
                CREATE TABLE IF NOT EXISTS travel_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    entry_type TEXT DEFAULT 'text', -- 'text', 'photo', 'video', 'location'
                    title TEXT,
                    content TEXT,
                    media_urls TEXT, -- JSON array
                    location_data TEXT, -- JSON with coordinates, place name
                    weather_data TEXT, -- JSON snapshot
                    mood TEXT, -- user's mood/rating
                    is_private BOOLEAN DEFAULT 0,
                    entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Packing lists
            conn.execute('''
                CREATE TABLE IF NOT EXISTS packing_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    list_name TEXT DEFAULT 'My Packing List',
                    items TEXT NOT NULL, -- JSON array of {item, quantity, packed, category}
                    weather_considered TEXT, -- JSON weather data used
                    activities_considered TEXT, -- JSON activities data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Local transportation cache
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transportation_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city_name TEXT NOT NULL,
                    transport_type TEXT NOT NULL, -- 'public_transit', 'parking', 'bike_share', etc.
                    data TEXT NOT NULL, -- JSON
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')
            
            # Emergency contacts
            conn.execute('''
                CREATE TABLE IF NOT EXISTS emergency_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    country TEXT NOT NULL,
                    service_type TEXT NOT NULL, -- 'police', 'medical', 'embassy', 'roadside', etc.
                    service_name TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    address TEXT,
                    coordinates TEXT, -- JSON
                    languages TEXT, -- JSON array
                    notes TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Local experiences marketplace
            conn.execute('''
                CREATE TABLE IF NOT EXISTS local_experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    host_user_id INTEGER,
                    city TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL, -- 'tour', 'cooking', 'adventure', 'cultural', etc.
                    price REAL NOT NULL,
                    currency TEXT DEFAULT 'EUR',
                    duration_hours REAL,
                    max_participants INTEGER,
                    languages TEXT, -- JSON array
                    included_items TEXT, -- JSON array
                    photos TEXT, -- JSON array
                    rating REAL DEFAULT 0,
                    review_count INTEGER DEFAULT 0,
                    is_verified BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (host_user_id) REFERENCES users (id)
                )
            ''')
            
            # Experience bookings
            conn.execute('''
                CREATE TABLE IF NOT EXISTS experience_bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experience_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    trip_id INTEGER,
                    booking_date DATE NOT NULL,
                    participants INTEGER DEFAULT 1,
                    total_price REAL NOT NULL,
                    status TEXT DEFAULT 'pending', -- 'pending', 'confirmed', 'cancelled'
                    payment_status TEXT DEFAULT 'pending',
                    special_requests TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (experience_id) REFERENCES local_experiences (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id)
                )
            ''')
            
            # Itinerary optimization preferences
            conn.execute('''
                CREATE TABLE IF NOT EXISTS optimization_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    trip_id INTEGER,
                    energy_pattern TEXT DEFAULT 'moderate', -- 'morning_person', 'night_owl', 'moderate'
                    pace_preference TEXT DEFAULT 'relaxed', -- 'packed', 'relaxed', 'balanced'
                    break_frequency TEXT DEFAULT 'regular', -- 'minimal', 'regular', 'frequent'
                    meal_times TEXT, -- JSON with preferred times
                    avoid_rush_hours BOOLEAN DEFAULT 1,
                    max_walking_distance REAL DEFAULT 2.0, -- km
                    accessibility_needs TEXT, -- JSON
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (trip_id) REFERENCES saved_trips (id)
                )
            ''')
            
            # User emergency contacts (personal contacts)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_emergency_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT,
                    relationship TEXT,
                    is_primary BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
        
        logger.info("Database initialized successfully")

class UserManager:
    """Handles user authentication and management."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                           password.encode('utf-8'), 
                                           salt.encode('utf-8'), 
                                           100000)
        return password_hash.hex(), salt
    
    def verify_password(self, password: str, hash_hex: str, salt: str) -> bool:
        """Verify password against hash."""
        password_hash, _ = self.hash_password(password, salt)
        return password_hash == hash_hex
    
    def create_user(self, email: str, username: str, password: str = None, 
                   first_name: str = None, last_name: str = None,
                   oauth_provider: str = None, oauth_id: str = None,
                   profile_picture: str = None) -> Optional[int]:
        """Create a new user account."""
        try:
            # Hash password only for regular users (not OAuth)
            if password:
                password_hash, salt = self.hash_password(password)
            else:
                password_hash, salt = None, None
            
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO users (email, username, password_hash, salt, first_name, last_name,
                                     oauth_provider, oauth_id, profile_picture)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (email, username, password_hash, salt, first_name, last_name,
                      oauth_provider, oauth_id, profile_picture))
                
                user_id = cursor.lastrowid
                
                # Initialize user analytics
                conn.execute('''
                    INSERT INTO user_analytics (user_id) VALUES (?)
                ''', (user_id,))
                
                conn.commit()
                logger.info(f"User created successfully: {username}")
                return user_id
                
        except sqlite3.IntegrityError as e:
            logger.error(f"User creation failed: {e}")
            return None
    
    def authenticate_user(self, login: str, password: str) -> Optional[Dict]:
        """Authenticate user by email or username."""
        with self.db.get_connection() as conn:
            user = conn.execute('''
                SELECT * FROM users 
                WHERE (email = ? OR username = ?) AND is_active = 1
            ''', (login, login)).fetchone()
            
            if user and self.verify_password(password, user['password_hash'], user['salt']):
                # Update last login
                conn.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
                ''', (user['id'],))
                conn.commit()
                
                return dict(user)
        
        return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        with self.db.get_connection() as conn:
            user = conn.execute('''
                SELECT * FROM users WHERE email = ? AND is_active = 1
            ''', (email,)).fetchone()
            
            return dict(user) if user else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username."""
        with self.db.get_connection() as conn:
            user = conn.execute('''
                SELECT * FROM users WHERE username = ? AND is_active = 1
            ''', (username,)).fetchone()
            
            return dict(user) if user else None
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp."""
        with self.db.get_connection() as conn:
            conn.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user_id,))
            conn.commit()
    
    def create_session(self, user_id: int) -> str:
        """Create a new user session."""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=30)  # 30 day sessions
        
        with self.db.get_connection() as conn:
            conn.execute('''
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at))
            conn.commit()
        
        return session_token
    
    def get_user_by_session(self, session_token: str) -> Optional[Dict]:
        """Get user by session token."""
        with self.db.get_connection() as conn:
            result = conn.execute('''
                SELECT u.*, s.expires_at 
                FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = ? AND s.is_active = 1 AND s.expires_at > CURRENT_TIMESTAMP
            ''', (session_token,)).fetchone()
            
            return dict(result) if result else None
    
    def logout_user(self, session_token: str):
        """Logout user by deactivating session."""
        with self.db.get_connection() as conn:
            conn.execute('''
                UPDATE user_sessions SET is_active = 0 WHERE session_token = ?
            ''', (session_token,))
            conn.commit()

class TripManager:
    """Handles trip saving, favorites, and management."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def save_trip(self, user_id: int, trip_name: str, trip_data: Dict, 
                  is_favorite: bool = False, is_public: bool = False) -> int:
        """Save a trip for a user."""
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO saved_trips (
                    user_id, trip_name, trip_data, route_type, start_city, end_city,
                    intermediate_cities, total_distance, total_duration, estimated_cost,
                    is_favorite, is_public
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, trip_name, json.dumps(trip_data),
                trip_data.get('route_type', ''), 
                trip_data.get('start_city', {}).get('name', ''),
                trip_data.get('end_city', {}).get('name', ''),
                json.dumps(trip_data.get('intermediate_cities', [])),
                trip_data.get('total_distance_km', 0),
                trip_data.get('total_duration_hours', 0),
                trip_data.get('estimated_cost', {}).get('total_estimate', 0),
                is_favorite, is_public
            ))
            
            trip_id = cursor.lastrowid
            conn.commit()
            
            # Update user analytics
            self._update_user_analytics(user_id, trip_data)
            
            return trip_id
    
    def get_user_trips(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get all trips for a user."""
        with self.db.get_connection() as conn:
            trips = conn.execute('''
                SELECT * FROM saved_trips 
                WHERE user_id = ? 
                ORDER BY updated_at DESC 
                LIMIT ?
            ''', (user_id, limit)).fetchall()
            
            return [dict(trip) for trip in trips]
    
    def get_favorite_trips(self, user_id: int) -> List[Dict]:
        """Get favorite trips for a user."""
        with self.db.get_connection() as conn:
            trips = conn.execute('''
                SELECT * FROM saved_trips 
                WHERE user_id = ? AND is_favorite = 1 
                ORDER BY updated_at DESC
            ''', (user_id,)).fetchall()
            
            return [dict(trip) for trip in trips]
    
    def toggle_favorite(self, user_id: int, trip_id: int) -> bool:
        """Toggle favorite status of a trip."""
        with self.db.get_connection() as conn:
            # First check if trip belongs to user
            trip = conn.execute('''
                SELECT is_favorite FROM saved_trips WHERE id = ? AND user_id = ?
            ''', (trip_id, user_id)).fetchone()
            
            if trip:
                new_status = not bool(trip['is_favorite'])
                conn.execute('''
                    UPDATE saved_trips SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ? AND user_id = ?
                ''', (new_status, trip_id, user_id))
                conn.commit()
                return new_status
        
        return False
    
    def delete_trip(self, user_id: int, trip_id: int) -> bool:
        """Delete a trip."""
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                DELETE FROM saved_trips WHERE id = ? AND user_id = ?
            ''', (trip_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def _update_user_analytics(self, user_id: int, trip_data: Dict):
        """Update user analytics when a trip is saved."""
        with self.db.get_connection() as conn:
            # Get current analytics
            analytics = conn.execute('''
                SELECT * FROM user_analytics WHERE user_id = ?
            ''', (user_id,)).fetchone()
            
            if analytics:
                new_total_trips = analytics['total_trips'] + 1
                new_total_distance = analytics['total_distance'] + trip_data.get('total_distance_km', 0)
                new_total_duration = analytics['total_duration'] + trip_data.get('total_duration_hours', 0)
                
                # Calculate carbon footprint (rough estimate: 0.2kg CO2 per km)
                new_carbon = analytics['carbon_footprint'] + (trip_data.get('total_distance_km', 0) * 0.2)
                
                # Update cities and countries visited
                cities_visited = json.loads(analytics['cities_visited'] or '[]')
                intermediate_cities = trip_data.get('intermediate_cities', [])
                
                for city in intermediate_cities:
                    city_name = city.get('name') if isinstance(city, dict) else str(city)
                    if city_name and city_name not in cities_visited:
                        cities_visited.append(city_name)
                
                conn.execute('''
                    UPDATE user_analytics SET
                        total_trips = ?, total_distance = ?, total_duration = ?,
                        cities_visited = ?, carbon_footprint = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (new_total_trips, new_total_distance, new_total_duration,
                      json.dumps(cities_visited), new_carbon, user_id))
                conn.commit()

# Global database instance
_db_instance = None

def get_database() -> Database:
    """Get global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

def get_user_manager() -> UserManager:
    """Get user manager instance."""
    return UserManager(get_database())

def get_trip_manager() -> TripManager:
    """Get trip manager instance."""
    return TripManager(get_database())
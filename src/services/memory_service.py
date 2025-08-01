"""
Advanced memory and session management service for persistent user experience.
Handles session state, trip history, form data, and user preferences.
"""
import os
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from ..core.database import get_database

logger = structlog.get_logger(__name__)

class MemoryService:
    """Comprehensive memory management for user sessions and trip data."""
    
    def __init__(self):
        self.db = get_database()
    
    def save_session_state(self, user_id: Optional[int], session_id: str, state_data: Dict[str, Any]) -> bool:
        """Save current session state (form data, selections, page state)."""
        try:
            with self.db.get_connection() as conn:
                # Create session_states table if it doesn't exist
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS session_states (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        session_id TEXT NOT NULL,
                        state_key TEXT NOT NULL,
                        state_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        UNIQUE(session_id, state_key)
                    )
                ''')
                
                # Set expiration (30 days for logged users, 1 day for anonymous)
                expires_at = datetime.now() + timedelta(days=30 if user_id else 1)
                
                # Save or update session state
                conn.execute('''
                    INSERT OR REPLACE INTO session_states 
                    (user_id, session_id, state_key, state_data, updated_at, expires_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ''', (user_id, session_id, 'main_state', json.dumps(state_data), expires_at))
                
                conn.commit()
                logger.info("Session state saved", session_id=session_id, user_id=user_id)
                return True
                
        except Exception as e:
            logger.error("Failed to save session state", error=str(e))
            return False
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session state data."""
        try:
            with self.db.get_connection() as conn:
                result = conn.execute('''
                    SELECT state_data FROM session_states 
                    WHERE session_id = ? AND state_key = 'main_state' 
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                ''', (session_id,)).fetchone()
                
                if result:
                    return json.loads(result['state_data'])
                return None
                
        except Exception as e:
            logger.error("Failed to get session state", error=str(e))
            return None
    
    def save_trip_preparation(self, user_id: Optional[int], session_id: str, prep_data: Dict[str, Any]) -> str:
        """Save trip preparation data with unique ID."""
        try:
            prep_id = str(uuid.uuid4())
            
            with self.db.get_connection() as conn:
                # Create trip_preparations table if it doesn't exist
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS trip_preparations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        prep_id TEXT UNIQUE NOT NULL,
                        user_id INTEGER,
                        session_id TEXT NOT NULL,
                        prep_name TEXT,
                        prep_data TEXT NOT NULL,
                        status TEXT DEFAULT 'draft',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Generate preparation name
                prep_name = self._generate_prep_name(prep_data)
                
                conn.execute('''
                    INSERT INTO trip_preparations 
                    (prep_id, user_id, session_id, prep_name, prep_data, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (prep_id, user_id, session_id, prep_name, json.dumps(prep_data), 'draft'))
                
                conn.commit()
                logger.info("Trip preparation saved", prep_id=prep_id, user_id=user_id)
                return prep_id
                
        except Exception as e:
            logger.error("Failed to save trip preparation", error=str(e))
            return None
    
    def get_trip_preparations(self, user_id: Optional[int], session_id: str) -> List[Dict[str, Any]]:
        """Get all trip preparations for user/session."""
        try:
            with self.db.get_connection() as conn:
                if user_id:
                    # Get all preparations for logged-in user
                    results = conn.execute('''
                        SELECT * FROM trip_preparations 
                        WHERE user_id = ? 
                        ORDER BY updated_at DESC
                    ''', (user_id,)).fetchall()
                else:
                    # Get preparations for current session only
                    results = conn.execute('''
                        SELECT * FROM trip_preparations 
                        WHERE session_id = ? AND user_id IS NULL
                        ORDER BY updated_at DESC
                    ''', (session_id,)).fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error("Failed to get trip preparations", error=str(e))
            return []
    
    def update_trip_preparation(self, prep_id: str, prep_data: Dict[str, Any]) -> bool:
        """Update existing trip preparation."""
        try:
            with self.db.get_connection() as conn:
                prep_name = self._generate_prep_name(prep_data)
                
                conn.execute('''
                    UPDATE trip_preparations 
                    SET prep_data = ?, prep_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE prep_id = ?
                ''', (json.dumps(prep_data), prep_name, prep_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error("Failed to update trip preparation", error=str(e))
            return False
    
    def save_search_history(self, user_id: Optional[int], session_id: str, search_data: Dict[str, Any]) -> bool:
        """Save search query and results to history."""
        try:
            with self.db.get_connection() as conn:
                # Create search_history table if it doesn't exist
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS search_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        session_id TEXT NOT NULL,
                        search_query TEXT NOT NULL,
                        search_results TEXT,
                        search_type TEXT DEFAULT 'trip_planning',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                search_query = f"{search_data.get('start_location', '')} → {search_data.get('end_location', '')}"
                
                conn.execute('''
                    INSERT INTO search_history 
                    (user_id, session_id, search_query, search_results, search_type)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, session_id, search_query, 
                      json.dumps(search_data), 'trip_planning'))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error("Failed to save search history", error=str(e))
            return False
    
    def get_search_history(self, user_id: Optional[int], session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get search history for user/session."""
        try:
            with self.db.get_connection() as conn:
                if user_id:
                    results = conn.execute('''
                        SELECT * FROM search_history 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (user_id, limit)).fetchall()
                else:
                    results = conn.execute('''
                        SELECT * FROM search_history 
                        WHERE session_id = ? AND user_id IS NULL
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (session_id, limit)).fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error("Failed to get search history", error=str(e))
            return []
    
    def save_page_state(self, session_id: str, page_url: str, page_data: Dict[str, Any]) -> bool:
        """Save specific page state (scroll position, form data, etc.)."""
        try:
            with self.db.get_connection() as conn:
                # Create page_states table if it doesn't exist
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS page_states (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        page_url TEXT NOT NULL,
                        page_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(session_id, page_url)
                    )
                ''')
                
                conn.execute('''
                    INSERT OR REPLACE INTO page_states 
                    (session_id, page_url, page_data, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (session_id, page_url, json.dumps(page_data)))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error("Failed to save page state", error=str(e))
            return False
    
    def get_page_state(self, session_id: str, page_url: str) -> Optional[Dict[str, Any]]:
        """Get specific page state."""
        try:
            with self.db.get_connection() as conn:
                result = conn.execute('''
                    SELECT page_data FROM page_states 
                    WHERE session_id = ? AND page_url = ?
                ''', (session_id, page_url)).fetchone()
                
                if result:
                    return json.loads(result['page_data'])
                return None
                
        except Exception as e:
            logger.error("Failed to get page state", error=str(e))
            return None
    
    def cleanup_expired_data(self) -> bool:
        """Clean up expired session data."""
        try:
            with self.db.get_connection() as conn:
                # Clean expired session states
                conn.execute('''
                    DELETE FROM session_states 
                    WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
                ''')
                
                # Clean old anonymous trip preparations (older than 7 days)
                week_ago = datetime.now() - timedelta(days=7)
                conn.execute('''
                    DELETE FROM trip_preparations 
                    WHERE user_id IS NULL AND created_at < ?
                ''', (week_ago,))
                
                # Clean old page states (older than 3 days)
                three_days_ago = datetime.now() - timedelta(days=3)
                conn.execute('''
                    DELETE FROM page_states 
                    WHERE updated_at < ?
                ''', (three_days_ago,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error("Failed to cleanup expired data", error=str(e))
            return False
    
    def _generate_prep_name(self, prep_data: Dict[str, Any]) -> str:
        """Generate a human-readable name for trip preparation."""
        start = prep_data.get('start_location', 'Unknown')
        end = prep_data.get('end_location', 'Unknown')
        route_types = prep_data.get('route_types', [])
        
        if route_types:
            types_str = ', '.join(route_types[:2])
            return f"{start} → {end} ({types_str})"
        else:
            return f"{start} → {end}"

# Global memory service instance
_memory_service = None

def get_memory_service() -> MemoryService:
    """Get global memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
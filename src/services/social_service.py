"""
Social features service for trip sharing, reviews, and community features.
"""
import os
import json
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime
import structlog
from ..core.database import get_database

logger = structlog.get_logger(__name__)

class SocialService:
    """Service for social features like trip sharing and reviews."""
    
    def __init__(self):
        self.db = get_database()
    
    def share_trip(self, user_id: int, trip_id: int, share_type: str = 'public', 
                   message: str = '') -> Dict:
        """Share a trip with the community."""
        try:
            with self.db.get_connection() as conn:
                # Check if trip belongs to user
                trip = conn.execute('''
                    SELECT * FROM saved_trips WHERE id = ? AND user_id = ?
                ''', (trip_id, user_id)).fetchone()
                
                if not trip:
                    return {'success': False, 'error': 'Trip not found'}
                
                # Update trip sharing status
                conn.execute('''
                    UPDATE saved_trips 
                    SET is_public = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ? AND user_id = ?
                ''', (share_type == 'public', trip_id, user_id))
                
                # Create share record
                share_id = str(uuid.uuid4())
                conn.execute('''
                    INSERT INTO trip_shares (share_id, user_id, trip_id, share_type, message, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (share_id, user_id, trip_id, share_type, message))
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS trip_shares (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        share_id TEXT UNIQUE NOT NULL,
                        user_id INTEGER NOT NULL,
                        trip_id INTEGER NOT NULL,
                        share_type TEXT NOT NULL,
                        message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (trip_id) REFERENCES saved_trips (id)
                    )
                ''')
                
                conn.commit()
                
                return {
                    'success': True,
                    'share_id': share_id,
                    'share_url': f"/shared-trip/{share_id}",
                    'message': 'Trip shared successfully!'
                }
                
        except Exception as e:
            logger.error(f"Trip sharing failed: {e}")
            return {'success': False, 'error': 'Failed to share trip'}
    
    def get_shared_trip(self, share_id: str) -> Optional[Dict]:
        """Get a shared trip by share ID."""
        try:
            with self.db.get_connection() as conn:
                result = conn.execute('''
                    SELECT ts.*, st.*, u.username, u.first_name, u.last_name
                    FROM trip_shares ts
                    JOIN saved_trips st ON ts.trip_id = st.id
                    JOIN users u ON ts.user_id = u.id
                    WHERE ts.share_id = ? AND st.is_public = 1
                ''', (share_id,)).fetchone()
                
                if result:
                    trip_data = dict(result)
                    
                    # Parse JSON fields
                    trip_data['trip_data'] = json.loads(trip_data['trip_data'])
                    trip_data['intermediate_cities'] = json.loads(trip_data['intermediate_cities'] or '[]')
                    
                    return trip_data
                
        except Exception as e:
            logger.error(f"Failed to get shared trip: {e}")
        
        return None
    
    def get_public_trips(self, limit: int = 20, route_type: str = None) -> List[Dict]:
        """Get public trips from the community."""
        try:
            with self.db.get_connection() as conn:
                query = '''
                    SELECT st.*, u.username, u.first_name, u.last_name,
                           COUNT(tr.id) as review_count,
                           AVG(tr.rating) as avg_rating
                    FROM saved_trips st
                    JOIN users u ON st.user_id = u.id
                    LEFT JOIN trip_reviews tr ON st.id = tr.trip_id
                    WHERE st.is_public = 1
                '''
                
                params = []
                
                if route_type:
                    query += ' AND st.route_type = ?'
                    params.append(route_type)
                
                query += '''
                    GROUP BY st.id
                    ORDER BY st.created_at DESC, avg_rating DESC
                    LIMIT ?
                '''
                params.append(limit)
                
                trips = conn.execute(query, params).fetchall()
                
                result = []
                for trip in trips:
                    trip_dict = dict(trip)
                    trip_dict['trip_data'] = json.loads(trip_dict['trip_data'])
                    trip_dict['intermediate_cities'] = json.loads(trip_dict['intermediate_cities'] or '[]')
                    result.append(trip_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get public trips: {e}")
            return []
    
    def add_trip_review(self, user_id: int, trip_id: int, rating: int, 
                       review_text: str = '', photos: List[str] = None) -> Dict:
        """Add a review for a shared trip."""
        try:
            if not 1 <= rating <= 5:
                return {'success': False, 'error': 'Rating must be between 1 and 5'}
            
            with self.db.get_connection() as conn:
                # Check if trip is public
                trip = conn.execute('''
                    SELECT id FROM saved_trips WHERE id = ? AND is_public = 1
                ''', (trip_id,)).fetchone()
                
                if not trip:
                    return {'success': False, 'error': 'Trip not found or not public'}
                
                # Check if user already reviewed this trip
                existing = conn.execute('''
                    SELECT id FROM trip_reviews WHERE user_id = ? AND trip_id = ?
                ''', (user_id, trip_id)).fetchone()
                
                if existing:
                    return {'success': False, 'error': 'You have already reviewed this trip'}
                
                # Add review
                conn.execute('''
                    INSERT INTO trip_reviews (user_id, trip_id, rating, review_text, photos, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, trip_id, rating, review_text, json.dumps(photos or [])))
                
                conn.commit()
                
                return {'success': True, 'message': 'Review added successfully!'}
                
        except Exception as e:
            logger.error(f"Failed to add review: {e}")
            return {'success': False, 'error': 'Failed to add review'}
    
    def get_trip_reviews(self, trip_id: int) -> List[Dict]:
        """Get reviews for a trip."""
        try:
            with self.db.get_connection() as conn:
                reviews = conn.execute('''
                    SELECT tr.*, u.username, u.first_name, u.last_name
                    FROM trip_reviews tr
                    JOIN users u ON tr.user_id = u.id
                    WHERE tr.trip_id = ?
                    ORDER BY tr.created_at DESC
                ''', (trip_id,)).fetchall()
                
                result = []
                for review in reviews:
                    review_dict = dict(review)
                    review_dict['photos'] = json.loads(review_dict['photos'] or '[]')
                    result.append(review_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get reviews: {e}")
            return []
    
    def get_user_social_stats(self, user_id: int) -> Dict:
        """Get social statistics for a user."""
        try:
            with self.db.get_connection() as conn:
                # Get trip sharing stats
                shared_trips = conn.execute('''
                    SELECT COUNT(*) as count FROM saved_trips WHERE user_id = ? AND is_public = 1
                ''', (user_id,)).fetchone()['count']
                
                # Get reviews given
                reviews_given = conn.execute('''
                    SELECT COUNT(*) as count FROM trip_reviews WHERE user_id = ?
                ''', (user_id,)).fetchone()['count']
                
                # Get reviews received (for their shared trips)
                reviews_received = conn.execute('''
                    SELECT COUNT(*) as count FROM trip_reviews tr
                    JOIN saved_trips st ON tr.trip_id = st.id
                    WHERE st.user_id = ?
                ''', (user_id,)).fetchone()['count']
                
                # Get average rating received
                avg_rating = conn.execute('''
                    SELECT AVG(tr.rating) as avg_rating FROM trip_reviews tr
                    JOIN saved_trips st ON tr.trip_id = st.id
                    WHERE st.user_id = ?
                ''', (user_id,)).fetchone()['avg_rating'] or 0
                
                return {
                    'shared_trips': shared_trips,
                    'reviews_given': reviews_given,
                    'reviews_received': reviews_received,
                    'average_rating': round(avg_rating, 1) if avg_rating else 0,
                    'community_level': self._calculate_community_level(shared_trips, reviews_given, avg_rating)
                }
                
        except Exception as e:
            logger.error(f"Failed to get social stats: {e}")
            return {
                'shared_trips': 0,
                'reviews_given': 0,
                'reviews_received': 0,
                'average_rating': 0,
                'community_level': 'Beginner'
            }
    
    def _calculate_community_level(self, shared_trips: int, reviews_given: int, avg_rating: float) -> str:
        """Calculate user's community level based on activity."""
        score = shared_trips * 10 + reviews_given * 5 + (avg_rating * 10)
        
        if score >= 200:
            return 'Travel Expert'
        elif score >= 100:
            return 'Adventure Guide'
        elif score >= 50:
            return 'Explorer'
        elif score >= 20:
            return 'Traveler'
        else:
            return 'Beginner'
    
    def generate_social_insights(self, user_id: int) -> Dict:
        """Generate social insights for a user."""
        stats = self.get_user_social_stats(user_id)
        
        insights = {
            'community_contribution': f"You've shared {stats['shared_trips']} trips and written {stats['reviews_given']} reviews",
            'reputation': f"Your shared trips have an average rating of {stats['average_rating']}/5",
            'community_level': stats['community_level'],
            'next_goal': self._get_next_social_goal(stats),
            'achievements': self._get_social_achievements(stats)
        }
        
        return insights
    
    def _get_next_social_goal(self, stats: Dict) -> str:
        """Get the next social goal for the user."""
        if stats['shared_trips'] == 0:
            return "Share your first trip with the community!"
        elif stats['reviews_given'] < 5:
            return "Write more reviews to help fellow travelers"
        elif stats['shared_trips'] < 5:
            return "Share more trips to become an Adventure Guide"
        else:
            return "Keep being an amazing community member!"
    
    def _get_social_achievements(self, stats: Dict) -> List[str]:
        """Get social achievements for the user."""
        achievements = []
        
        if stats['shared_trips'] >= 1:
            achievements.append("Trip Sharer")
        if stats['shared_trips'] >= 5:
            achievements.append("Community Contributor")
        if stats['reviews_given'] >= 5:
            achievements.append("Helpful Reviewer")
        if stats['average_rating'] >= 4.5 and stats['reviews_received'] >= 3:
            achievements.append("Highly Rated Planner")
        if stats['community_level'] == 'Travel Expert':
            achievements.append("Travel Expert")
        
        return achievements

# Global service instance
_social_service = None

def get_social_service() -> SocialService:
    """Get global social service instance."""
    global _social_service
    if _social_service is None:
        _social_service = SocialService()
    return _social_service
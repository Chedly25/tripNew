"""
Local experience marketplace service.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import json
import structlog
from src.core.database import get_database
from src.core.exceptions import ValidationError, ServiceError

logger = structlog.get_logger(__name__)


class MarketplaceService:
    """Handles local experience marketplace functionality."""
    
    def __init__(self):
        self.db = get_database()
    
    def create_experience(self, host_user_id: int, experience_data: Dict[str, Any]) -> int:
        """Create a new local experience."""
        try:
            # Validate required fields
            required_fields = ['city', 'title', 'description', 'category', 'price']
            for field in required_fields:
                if field not in experience_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Handle JSON fields
            languages = experience_data.get('languages', ['English'])
            included_items = experience_data.get('included_items', [])
            photos = experience_data.get('photos', [])
            
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO local_experiences (
                        host_user_id, city, title, description, category,
                        price, currency, duration_hours, max_participants,
                        languages, included_items, photos, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    host_user_id,
                    experience_data['city'],
                    experience_data['title'],
                    experience_data['description'],
                    experience_data['category'],
                    experience_data['price'],
                    experience_data.get('currency', 'EUR'),
                    experience_data.get('duration_hours'),
                    experience_data.get('max_participants'),
                    json.dumps(languages),
                    json.dumps(included_items),
                    json.dumps(photos),
                    True
                ))
                
                experience_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Experience created", experience_id=experience_id, host_id=host_user_id)
                return experience_id
                
        except Exception as e:
            logger.error(f"Failed to create experience: {e}")
            raise ServiceError(f"Failed to create experience: {str(e)}")
    
    def search_experiences(self, city: str = None, category: str = None, 
                          max_price: float = None, language: str = None,
                          date_filter: date = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for experiences with filters."""
        try:
            query = '''
                SELECT e.*, u.username as host_name, u.profile_picture as host_picture
                FROM local_experiences e
                JOIN users u ON e.host_user_id = u.id
                WHERE e.is_active = 1
            '''
            params = []
            
            if city:
                query += ' AND LOWER(e.city) LIKE LOWER(?)'
                params.append(f'%{city}%')
            
            if category:
                query += ' AND e.category = ?'
                params.append(category)
            
            if max_price:
                query += ' AND e.price <= ?'
                params.append(max_price)
            
            if language:
                query += ' AND e.languages LIKE ?'
                params.append(f'%{language}%')
            
            query += ' ORDER BY e.rating DESC, e.created_at DESC LIMIT ?'
            params.append(limit)
            
            with self.db.get_connection() as conn:
                experiences = conn.execute(query, params).fetchall()
                
                result = []
                for exp in experiences:
                    exp_dict = dict(exp)
                    # Parse JSON fields
                    for field in ['languages', 'included_items', 'photos']:
                        if exp_dict.get(field):
                            exp_dict[field] = json.loads(exp_dict[field])
                    
                    # Add booking availability if date provided
                    if date_filter:
                        exp_dict['available_on_date'] = self._check_availability(
                            exp_dict['id'], date_filter
                        )
                    
                    result.append(exp_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to search experiences: {e}")
            raise ServiceError(f"Failed to search experiences: {str(e)}")
    
    def get_experience(self, experience_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific experience with details."""
        try:
            with self.db.get_connection() as conn:
                experience = conn.execute('''
                    SELECT e.*, u.username as host_name, u.profile_picture as host_picture,
                           u.created_at as host_member_since
                    FROM local_experiences e
                    JOIN users u ON e.host_user_id = u.id
                    WHERE e.id = ? AND e.is_active = 1
                ''', (experience_id,)).fetchone()
                
                if not experience:
                    return None
                
                exp_dict = dict(experience)
                
                # Parse JSON fields
                for field in ['languages', 'included_items', 'photos']:
                    if exp_dict.get(field):
                        exp_dict[field] = json.loads(exp_dict[field])
                
                # Get recent reviews
                exp_dict['recent_reviews'] = self._get_experience_reviews(experience_id, limit=5)
                
                # Get host's other experiences
                exp_dict['host_other_experiences'] = self._get_host_other_experiences(
                    exp_dict['host_user_id'], experience_id, limit=3
                )
                
                return exp_dict
                
        except Exception as e:
            logger.error(f"Failed to get experience: {e}")
            raise ServiceError(f"Failed to get experience: {str(e)}")
    
    def book_experience(self, experience_id: int, user_id: int, 
                       booking_data: Dict[str, Any]) -> int:
        """Book an experience."""
        try:
            # Validate booking data
            required_fields = ['booking_date', 'participants']
            for field in required_fields:
                if field not in booking_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Get experience details
            experience = self.get_experience(experience_id)
            if not experience:
                raise ValidationError("Experience not found")
            
            # Check availability
            booking_date = datetime.strptime(booking_data['booking_date'], '%Y-%m-%d').date()
            if not self._check_availability(experience_id, booking_date):
                raise ValidationError("Experience not available on selected date")
            
            # Calculate total price
            participants = booking_data['participants']
            if participants > experience.get('max_participants', float('inf')):
                raise ValidationError("Too many participants for this experience")
            
            total_price = experience['price'] * participants
            
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO experience_bookings (
                        experience_id, user_id, trip_id, booking_date,
                        participants, total_price, special_requests
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    experience_id,
                    user_id,
                    booking_data.get('trip_id'),
                    booking_date,
                    participants,
                    total_price,
                    booking_data.get('special_requests', '')
                ))
                
                booking_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Experience booked", booking_id=booking_id, experience_id=experience_id)
                return booking_id
                
        except Exception as e:
            logger.error(f"Failed to book experience: {e}")
            raise ServiceError(f"Failed to book experience: {str(e)}")
    
    def get_user_bookings(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get user's experience bookings."""
        try:
            query = '''
                SELECT b.*, e.title, e.city, e.category, e.duration_hours,
                       u.username as host_name, u.profile_picture as host_picture
                FROM experience_bookings b
                JOIN local_experiences e ON b.experience_id = e.id
                JOIN users u ON e.host_user_id = u.id
                WHERE b.user_id = ?
            '''
            params = [user_id]
            
            if status:
                query += ' AND b.status = ?'
                params.append(status)
            
            query += ' ORDER BY b.booking_date DESC'
            
            with self.db.get_connection() as conn:
                bookings = conn.execute(query, params).fetchall()
                return [dict(booking) for booking in bookings]
                
        except Exception as e:
            logger.error(f"Failed to get user bookings: {e}")
            raise ServiceError(f"Failed to get user bookings: {str(e)}")
    
    def get_host_bookings(self, host_user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get bookings for experiences hosted by a user."""
        try:
            query = '''
                SELECT b.*, e.title, e.city, e.category,
                       u.username as guest_name, u.profile_picture as guest_picture
                FROM experience_bookings b
                JOIN local_experiences e ON b.experience_id = e.id
                JOIN users u ON b.user_id = u.id
                WHERE e.host_user_id = ?
            '''
            params = [host_user_id]
            
            if status:
                query += ' AND b.status = ?'
                params.append(status)
            
            query += ' ORDER BY b.booking_date DESC'
            
            with self.db.get_connection() as conn:
                bookings = conn.execute(query, params).fetchall()
                return [dict(booking) for booking in bookings]
                
        except Exception as e:
            logger.error(f"Failed to get host bookings: {e}")
            raise ServiceError(f"Failed to get host bookings: {str(e)}")
    
    def update_booking_status(self, booking_id: int, host_user_id: int, 
                             new_status: str) -> bool:
        """Update booking status (host action)."""
        try:
            valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed']
            if new_status not in valid_statuses:
                raise ValidationError(f"Invalid status: {new_status}")
            
            with self.db.get_connection() as conn:
                # Verify host owns this experience
                result = conn.execute('''
                    SELECT b.id FROM experience_bookings b
                    JOIN local_experiences e ON b.experience_id = e.id
                    WHERE b.id = ? AND e.host_user_id = ?
                ''', (booking_id, host_user_id)).fetchone()
                
                if not result:
                    return False
                
                cursor = conn.execute('''
                    UPDATE experience_bookings
                    SET status = ?
                    WHERE id = ?
                ''', (new_status, booking_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                return success
                
        except Exception as e:
            logger.error(f"Failed to update booking status: {e}")
            raise ServiceError(f"Failed to update booking status: {str(e)}")
    
    def add_experience_review(self, booking_id: int, user_id: int, 
                             review_data: Dict[str, Any]) -> int:
        """Add a review for an experience after completion."""
        try:
            # Validate review data
            if 'rating' not in review_data or not (1 <= review_data['rating'] <= 5):
                raise ValidationError("Rating must be between 1 and 5")
            
            # Verify user booked this experience and it's completed
            with self.db.get_connection() as conn:
                booking = conn.execute('''
                    SELECT * FROM experience_bookings
                    WHERE id = ? AND user_id = ? AND status = 'completed'
                ''', (booking_id, user_id)).fetchone()
                
                if not booking:
                    raise ValidationError("Booking not found or not completed")
                
                # Add review to trip_reviews table (reusing existing structure)
                cursor = conn.execute('''
                    INSERT INTO trip_reviews (user_id, trip_id, rating, review_text, photos)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    booking['experience_id'],  # Using experience_id as trip_id
                    review_data['rating'],
                    review_data.get('review_text', ''),
                    json.dumps(review_data.get('photos', []))
                ))
                
                review_id = cursor.lastrowid
                
                # Update experience rating
                self._update_experience_rating(booking['experience_id'])
                
                conn.commit()
                return review_id
                
        except Exception as e:
            logger.error(f"Failed to add experience review: {e}")
            raise ServiceError(f"Failed to add experience review: {str(e)}")
    
    def get_categories(self) -> List[str]:
        """Get available experience categories."""
        return [
            'tour',
            'cooking',
            'adventure',
            'cultural',
            'nature',
            'photography',
            'sports',
            'arts_crafts',
            'food_drink',
            'history',
            'music',
            'wellness',
            'family',
            'unique'
        ]
    
    def _check_availability(self, experience_id: int, booking_date: date) -> bool:
        """Check if experience is available on a specific date."""
        try:
            with self.db.get_connection() as conn:
                # Get experience details
                experience = conn.execute('''
                    SELECT max_participants FROM local_experiences
                    WHERE id = ? AND is_active = 1
                ''', (experience_id,)).fetchone()
                
                if not experience:
                    return False
                
                # Check existing bookings for that date
                existing_bookings = conn.execute('''
                    SELECT SUM(participants) as total_booked
                    FROM experience_bookings
                    WHERE experience_id = ? AND booking_date = ? 
                    AND status IN ('pending', 'confirmed')
                ''', (experience_id, booking_date)).fetchone()
                
                total_booked = existing_bookings['total_booked'] or 0
                max_participants = experience['max_participants'] or float('inf')
                
                return total_booked < max_participants
                
        except Exception as e:
            logger.error(f"Failed to check availability: {e}")
            return False
    
    def _get_experience_reviews(self, experience_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get reviews for an experience."""
        try:
            with self.db.get_connection() as conn:
                reviews = conn.execute('''
                    SELECT r.*, u.username, u.profile_picture
                    FROM trip_reviews r
                    JOIN users u ON r.user_id = u.id
                    WHERE r.trip_id = ?
                    ORDER BY r.created_at DESC
                    LIMIT ?
                ''', (experience_id, limit)).fetchall()
                
                result = []
                for review in reviews:
                    review_dict = dict(review)
                    if review_dict.get('photos'):
                        review_dict['photos'] = json.loads(review_dict['photos'])
                    result.append(review_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get experience reviews: {e}")
            return []
    
    def _get_host_other_experiences(self, host_user_id: int, exclude_id: int, 
                                   limit: int = 5) -> List[Dict[str, Any]]:
        """Get other experiences by the same host."""
        try:
            with self.db.get_connection() as conn:
                experiences = conn.execute('''
                    SELECT id, title, city, category, price, currency, rating
                    FROM local_experiences
                    WHERE host_user_id = ? AND id != ? AND is_active = 1
                    ORDER BY rating DESC, created_at DESC
                    LIMIT ?
                ''', (host_user_id, exclude_id, limit)).fetchall()
                
                return [dict(exp) for exp in experiences]
                
        except Exception as e:
            logger.error(f"Failed to get host other experiences: {e}")
            return []
    
    def _update_experience_rating(self, experience_id: int):
        """Update experience rating based on reviews."""
        try:
            with self.db.get_connection() as conn:
                # Calculate average rating
                result = conn.execute('''
                    SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
                    FROM trip_reviews
                    WHERE trip_id = ?
                ''', (experience_id,)).fetchone()
                
                avg_rating = result['avg_rating'] or 0
                review_count = result['review_count'] or 0
                
                # Update experience
                conn.execute('''
                    UPDATE local_experiences
                    SET rating = ?, review_count = ?
                    WHERE id = ?
                ''', (round(avg_rating, 1), review_count, experience_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update experience rating: {e}")
    
    def get_popular_experiences(self, city: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular experiences based on bookings and ratings."""
        try:
            query = '''
                SELECT e.*, u.username as host_name, u.profile_picture as host_picture,
                       COUNT(b.id) as booking_count
                FROM local_experiences e
                JOIN users u ON e.host_user_id = u.id
                LEFT JOIN experience_bookings b ON e.id = b.experience_id
                WHERE e.is_active = 1
            '''
            params = []
            
            if city:
                query += ' AND LOWER(e.city) LIKE LOWER(?)'
                params.append(f'%{city}%')
            
            query += '''
                GROUP BY e.id
                ORDER BY e.rating DESC, booking_count DESC, e.created_at DESC
                LIMIT ?
            '''
            params.append(limit)
            
            with self.db.get_connection() as conn:
                experiences = conn.execute(query, params).fetchall()
                
                result = []
                for exp in experiences:
                    exp_dict = dict(exp)
                    # Parse JSON fields
                    for field in ['languages', 'included_items', 'photos']:
                        if exp_dict.get(field):
                            exp_dict[field] = json.loads(exp_dict[field])
                    result.append(exp_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get popular experiences: {e}")
            raise ServiceError(f"Failed to get popular experiences: {str(e)}")
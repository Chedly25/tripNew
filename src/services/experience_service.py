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


class ExperienceService:
    """Handles local experience marketplace features."""
    
    def __init__(self):
        self.db = get_database()
    
    def create_experience(self, host_user_id: int, experience_data: Dict[str, Any]) -> int:
        """Create a new local experience listing."""
        try:
            # Validate required fields
            required_fields = ['city', 'title', 'description', 'category', 'price']
            for field in required_fields:
                if field not in experience_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Validate category
            valid_categories = ['tour', 'cooking', 'adventure', 'cultural', 'workshop', 'outdoor', 'nightlife', 'wellness']
            if experience_data['category'] not in valid_categories:
                raise ValidationError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
            
            # Prepare JSON fields
            languages = experience_data.get('languages', ['English'])
            included_items = experience_data.get('included_items', [])
            photos = experience_data.get('photos', [])
            
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO local_experiences (
                        host_user_id, city, title, description, category,
                        price, currency, duration_hours, max_participants,
                        languages, included_items, photos
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    host_user_id,
                    experience_data['city'],
                    experience_data['title'],
                    experience_data['description'],
                    experience_data['category'],
                    experience_data['price'],
                    experience_data.get('currency', 'EUR'),
                    experience_data.get('duration_hours', 2.0),
                    experience_data.get('max_participants', 10),
                    json.dumps(languages),
                    json.dumps(included_items),
                    json.dumps(photos)
                ))
                
                experience_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Experience created", experience_id=experience_id, city=experience_data['city'])
                return experience_id
                
        except Exception as e:
            logger.error(f"Failed to create experience: {e}")
            raise ServiceError(f"Failed to create experience: {str(e)}")
    
    def get_experiences_by_city(self, city: str, category: str = None, 
                               max_price: float = None) -> List[Dict[str, Any]]:
        """Get all experiences in a specific city."""
        try:
            query = '''
                SELECT e.*, u.username as host_name, u.profile_picture as host_picture
                FROM local_experiences e
                LEFT JOIN users u ON e.host_user_id = u.id
                WHERE e.city = ? AND e.is_active = 1
            '''
            params = [city]
            
            if category:
                query += ' AND e.category = ?'
                params.append(category)
            
            if max_price:
                query += ' AND e.price <= ?'
                params.append(max_price)
            
            query += ' ORDER BY e.rating DESC, e.review_count DESC'
            
            with self.db.get_connection() as conn:
                experiences = conn.execute(query, params).fetchall()
                
                result = []
                for experience in experiences:
                    exp_dict = dict(experience)
                    # Parse JSON fields
                    for field in ['languages', 'included_items', 'photos']:
                        if exp_dict.get(field):
                            exp_dict[field] = json.loads(exp_dict[field])
                    result.append(exp_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get experiences: {e}")
            raise ServiceError(f"Failed to get experiences: {str(e)}")
    
    def get_experience(self, experience_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific experience by ID."""
        try:
            with self.db.get_connection() as conn:
                experience = conn.execute('''
                    SELECT e.*, u.username as host_name, u.profile_picture as host_picture,
                           u.email as host_email
                    FROM local_experiences e
                    LEFT JOIN users u ON e.host_user_id = u.id
                    WHERE e.id = ? AND e.is_active = 1
                ''', (experience_id,)).fetchone()
                
                if experience:
                    exp_dict = dict(experience)
                    # Parse JSON fields
                    for field in ['languages', 'included_items', 'photos']:
                        if exp_dict.get(field):
                            exp_dict[field] = json.loads(exp_dict[field])
                    
                    # Get recent reviews
                    exp_dict['recent_reviews'] = self._get_experience_reviews(experience_id, limit=5)
                    
                    return exp_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get experience: {e}")
            raise ServiceError(f"Failed to get experience: {str(e)}")
    
    def book_experience(self, experience_id: int, user_id: int, 
                       booking_data: Dict[str, Any]) -> int:
        """Book an experience."""
        try:
            # Validate required fields
            required_fields = ['booking_date', 'participants']
            for field in required_fields:
                if field not in booking_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Get experience details
            experience = self.get_experience(experience_id)
            if not experience:
                raise ValidationError("Experience not found")
            
            # Validate participants count
            participants = booking_data['participants']
            if participants > experience['max_participants']:
                raise ValidationError(f"Too many participants. Maximum: {experience['max_participants']}")
            
            # Calculate total price
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
                    booking_data['booking_date'],
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
        """Get all bookings for a user."""
        try:
            query = '''
                SELECT b.*, e.title, e.city, e.category, e.duration_hours,
                       u.username as host_name
                FROM experience_bookings b
                JOIN local_experiences e ON b.experience_id = e.id
                LEFT JOIN users u ON e.host_user_id = u.id
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
    
    def update_booking_status(self, booking_id: int, host_user_id: int, 
                             new_status: str) -> bool:
        """Update booking status (host only)."""
        try:
            valid_statuses = ['pending', 'confirmed', 'cancelled']
            if new_status not in valid_statuses:
                raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            
            with self.db.get_connection() as conn:
                # Verify host owns the experience
                cursor = conn.execute('''
                    UPDATE experience_bookings 
                    SET status = ?
                    WHERE id = ? AND experience_id IN (
                        SELECT id FROM local_experiences WHERE host_user_id = ?
                    )
                ''', (new_status, booking_id, host_user_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                return success
                
        except Exception as e:
            logger.error(f"Failed to update booking status: {e}")
            raise ServiceError(f"Failed to update booking status: {str(e)}")
    
    def add_review(self, booking_id: int, user_id: int, review_data: Dict[str, Any]) -> bool:
        """Add a review for a completed experience."""
        try:
            # Validate required fields
            required_fields = ['rating']
            for field in required_fields:
                if field not in review_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            rating = review_data['rating']
            if not (1 <= rating <= 5):
                raise ValidationError("Rating must be between 1 and 5")
            
            with self.db.get_connection() as conn:
                # Verify booking exists and belongs to user
                booking = conn.execute('''
                    SELECT b.experience_id, b.status
                    FROM experience_bookings b
                    WHERE b.id = ? AND b.user_id = ?
                ''', (booking_id, user_id)).fetchone()
                
                if not booking:
                    raise ValidationError("Booking not found")
                
                if booking['status'] != 'confirmed':
                    raise ValidationError("Can only review confirmed experiences")
                
                experience_id = booking['experience_id']
                
                # Add review to trip_reviews table (reusing existing structure)
                conn.execute('''
                    INSERT INTO trip_reviews (
                        user_id, trip_id, rating, review_text, photos
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    experience_id,  # Using experience_id as trip_id
                    rating,
                    review_data.get('review_text', ''),
                    json.dumps(review_data.get('photos', []))
                ))
                
                # Update experience rating
                self._update_experience_rating(experience_id)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to add review: {e}")
            raise ServiceError(f"Failed to add review: {str(e)}")
    
    def _update_experience_rating(self, experience_id: int):
        """Update experience average rating and review count."""
        try:
            with self.db.get_connection() as conn:
                # Calculate new rating
                result = conn.execute('''
                    SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
                    FROM trip_reviews
                    WHERE trip_id = ?
                ''', (experience_id,)).fetchone()
                
                if result['review_count'] > 0:
                    conn.execute('''
                        UPDATE local_experiences
                        SET rating = ?, review_count = ?
                        WHERE id = ?
                    ''', (
                        round(result['avg_rating'], 1),
                        result['review_count'],
                        experience_id
                    ))
                
        except Exception as e:
            logger.error(f"Failed to update experience rating: {e}")
    
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
    
    def search_experiences(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search experiences with various filters."""
        try:
            query = '''
                SELECT e.*, u.username as host_name, u.profile_picture as host_picture
                FROM local_experiences e
                LEFT JOIN users u ON e.host_user_id = u.id
                WHERE e.is_active = 1
            '''
            params = []
            
            # Add filters
            if search_params.get('city'):
                query += ' AND e.city LIKE ?'
                params.append(f"%{search_params['city']}%")
            
            if search_params.get('category'):
                query += ' AND e.category = ?'
                params.append(search_params['category'])
            
            if search_params.get('max_price'):
                query += ' AND e.price <= ?'
                params.append(search_params['max_price'])
            
            if search_params.get('min_rating'):
                query += ' AND e.rating >= ?'
                params.append(search_params['min_rating'])
            
            if search_params.get('max_duration'):
                query += ' AND e.duration_hours <= ?'
                params.append(search_params['max_duration'])
            
            if search_params.get('language'):
                query += ' AND e.languages LIKE ?'
                params.append(f'%"{search_params["language"]}"%')
            
            if search_params.get('search_term'):
                query += ' AND (e.title LIKE ? OR e.description LIKE ?)'
                term = f"%{search_params['search_term']}%"
                params.extend([term, term])
            
            # Add sorting
            sort_by = search_params.get('sort_by', 'rating')
            if sort_by == 'price_low':
                query += ' ORDER BY e.price ASC'
            elif sort_by == 'price_high':
                query += ' ORDER BY e.price DESC'
            elif sort_by == 'newest':
                query += ' ORDER BY e.created_at DESC'
            else:
                query += ' ORDER BY e.rating DESC, e.review_count DESC'
            
            # Add limit
            limit = search_params.get('limit', 50)
            query += f' LIMIT {limit}'
            
            with self.db.get_connection() as conn:
                experiences = conn.execute(query, params).fetchall()
                
                result = []
                for experience in experiences:
                    exp_dict = dict(experience)
                    # Parse JSON fields
                    for field in ['languages', 'included_items', 'photos']:
                        if exp_dict.get(field):
                            exp_dict[field] = json.loads(exp_dict[field])
                    result.append(exp_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to search experiences: {e}")
            raise ServiceError(f"Failed to search experiences: {str(e)}")
    
    def get_host_experiences(self, host_user_id: int) -> List[Dict[str, Any]]:
        """Get all experiences hosted by a user."""
        try:
            with self.db.get_connection() as conn:
                experiences = conn.execute('''
                    SELECT e.*, COUNT(b.id) as booking_count
                    FROM local_experiences e
                    LEFT JOIN experience_bookings b ON e.id = b.experience_id
                    WHERE e.host_user_id = ?
                    GROUP BY e.id
                    ORDER BY e.created_at DESC
                ''', (host_user_id,)).fetchall()
                
                result = []
                for experience in experiences:
                    exp_dict = dict(experience)
                    # Parse JSON fields
                    for field in ['languages', 'included_items', 'photos']:
                        if exp_dict.get(field):
                            exp_dict[field] = json.loads(exp_dict[field])
                    result.append(exp_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get host experiences: {e}")
            raise ServiceError(f"Failed to get host experiences: {str(e)}")
    
    def get_categories(self) -> List[str]:
        """Get all available experience categories."""
        return ['tour', 'cooking', 'adventure', 'cultural', 'workshop', 'outdoor', 'nightlife', 'wellness']
    
    def cancel_booking(self, booking_id: int, user_id: int) -> bool:
        """Cancel a booking (user can cancel their own bookings)."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    UPDATE experience_bookings 
                    SET status = 'cancelled'
                    WHERE id = ? AND user_id = ? AND status = 'pending'
                ''', (booking_id, user_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                return success
                
        except Exception as e:
            logger.error(f"Failed to cancel booking: {e}")
            raise ServiceError(f"Failed to cancel booking: {str(e)}")
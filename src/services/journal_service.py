"""
Travel journal service for creating and managing trip diaries.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import structlog
from ..core.database import get_database
from ..core.exceptions import ValidationError, ServiceError

logger = structlog.get_logger(__name__)


class JournalService:
    """Handles travel journal entries and trip diaries."""
    
    def __init__(self):
        self.db = get_database()
    
    def create_entry(self, trip_id: int, user_id: int, entry_data: Dict[str, Any]) -> int:
        """Create a new journal entry."""
        try:
            # Validate entry type
            valid_types = ['text', 'photo', 'video', 'location']
            entry_type = entry_data.get('entry_type', 'text')
            if entry_type not in valid_types:
                raise ValidationError(f"Invalid entry type: {entry_type}")
            
            # Prepare media URLs if provided
            media_urls = entry_data.get('media_urls', [])
            if media_urls and not isinstance(media_urls, list):
                raise ValidationError("media_urls must be a list")
            
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO travel_journal (
                        trip_id, user_id, entry_type, title, content,
                        media_urls, location_data, weather_data, mood,
                        is_private, entry_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trip_id,
                    user_id,
                    entry_type,
                    entry_data.get('title', ''),
                    entry_data.get('content', ''),
                    json.dumps(media_urls) if media_urls else None,
                    json.dumps(entry_data.get('location_data')) if entry_data.get('location_data') else None,
                    json.dumps(entry_data.get('weather_data')) if entry_data.get('weather_data') else None,
                    entry_data.get('mood'),
                    entry_data.get('is_private', False),
                    entry_data.get('entry_date', datetime.now())
                ))
                
                entry_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Journal entry created", entry_id=entry_id, trip_id=trip_id)
                return entry_id
                
        except Exception as e:
            logger.error(f"Failed to create journal entry: {e}")
            raise ServiceError(f"Failed to create journal entry: {str(e)}")
    
    def get_trip_journal(self, trip_id: int, user_id: Optional[int] = None, 
                        include_private: bool = False) -> List[Dict[str, Any]]:
        """Get all journal entries for a trip."""
        try:
            query = '''
                SELECT j.*, u.username, u.profile_picture
                FROM travel_journal j
                JOIN users u ON j.user_id = u.id
                WHERE j.trip_id = ?
            '''
            params = [trip_id]
            
            # Filter by privacy unless viewing own entries
            if not include_private:
                query += ' AND (j.is_private = 0 OR j.user_id = ?)'
                params.append(user_id or -1)
            
            query += ' ORDER BY j.entry_date DESC'
            
            with self.db.get_connection() as conn:
                entries = conn.execute(query, params).fetchall()
                
                result = []
                for entry in entries:
                    entry_dict = dict(entry)
                    # Parse JSON fields
                    for field in ['media_urls', 'location_data', 'weather_data']:
                        if entry_dict.get(field):
                            entry_dict[field] = json.loads(entry_dict[field])
                    result.append(entry_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get journal entries: {e}")
            raise ServiceError(f"Failed to get journal entries: {str(e)}")
    
    def get_entry(self, entry_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific journal entry."""
        try:
            with self.db.get_connection() as conn:
                entry = conn.execute('''
                    SELECT j.*, u.username, u.profile_picture
                    FROM travel_journal j
                    JOIN users u ON j.user_id = u.id
                    WHERE j.id = ? AND (j.is_private = 0 OR j.user_id = ?)
                ''', (entry_id, user_id)).fetchone()
                
                if entry:
                    entry_dict = dict(entry)
                    # Parse JSON fields
                    for field in ['media_urls', 'location_data', 'weather_data']:
                        if entry_dict.get(field):
                            entry_dict[field] = json.loads(entry_dict[field])
                    return entry_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get journal entry: {e}")
            raise ServiceError(f"Failed to get journal entry: {str(e)}")
    
    def update_entry(self, entry_id: int, user_id: int, update_data: Dict[str, Any]) -> bool:
        """Update a journal entry."""
        try:
            allowed_fields = ['title', 'content', 'mood', 'is_private']
            update_fields = []
            update_values = []
            
            for field in allowed_fields:
                if field in update_data:
                    update_fields.append(f"{field} = ?")
                    update_values.append(update_data[field])
            
            # Handle JSON fields
            if 'media_urls' in update_data:
                update_fields.append("media_urls = ?")
                update_values.append(json.dumps(update_data['media_urls']))
            
            if not update_fields:
                return False
            
            update_values.extend([entry_id, user_id])
            
            with self.db.get_connection() as conn:
                cursor = conn.execute(f'''
                    UPDATE travel_journal 
                    SET {', '.join(update_fields)}
                    WHERE id = ? AND user_id = ?
                ''', update_values)
                
                success = cursor.rowcount > 0
                conn.commit()
                return success
                
        except Exception as e:
            logger.error(f"Failed to update journal entry: {e}")
            raise ServiceError(f"Failed to update journal entry: {str(e)}")
    
    def delete_entry(self, entry_id: int, user_id: int) -> bool:
        """Delete a journal entry."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    DELETE FROM travel_journal 
                    WHERE id = ? AND user_id = ?
                ''', (entry_id, user_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                return success
                
        except Exception as e:
            logger.error(f"Failed to delete journal entry: {e}")
            raise ServiceError(f"Failed to delete journal entry: {str(e)}")
    
    def generate_trip_diary(self, trip_id: int) -> Dict[str, Any]:
        """Generate a complete trip diary with all entries and metadata."""
        try:
            # Get trip details
            with self.db.get_connection() as conn:
                trip = conn.execute('''
                    SELECT * FROM saved_trips WHERE id = ?
                ''', (trip_id,)).fetchone()
                
                if not trip:
                    raise ValidationError(f"Trip {trip_id} not found")
                
                trip_data = json.loads(trip['trip_data'])
            
            # Get all journal entries
            entries = self.get_trip_journal(trip_id, include_private=False)
            
            # Get expense summary
            expenses = self._get_trip_expense_summary(trip_id)
            
            # Organize entries by date
            entries_by_date = {}
            for entry in entries:
                date = entry['entry_date'].split('T')[0] if 'T' in entry['entry_date'] else entry['entry_date'].split(' ')[0]
                if date not in entries_by_date:
                    entries_by_date[date] = []
                entries_by_date[date].append(entry)
            
            # Create diary structure
            diary = {
                'trip_name': trip['trip_name'],
                'route_type': trip['route_type'],
                'start_city': trip['start_city'],
                'end_city': trip['end_city'],
                'total_distance': trip['total_distance'],
                'total_duration': trip['total_duration'],
                'created_at': trip['created_at'],
                'entries_by_date': entries_by_date,
                'total_entries': len(entries),
                'expense_summary': expenses,
                'participants': self._get_trip_participants(trip_id),
                'media_count': self._count_media(entries)
            }
            
            return diary
            
        except Exception as e:
            logger.error(f"Failed to generate trip diary: {e}")
            raise ServiceError(f"Failed to generate trip diary: {str(e)}")
    
    def _get_trip_expense_summary(self, trip_id: int) -> Dict[str, Any]:
        """Get expense summary for diary."""
        try:
            with self.db.get_connection() as conn:
                result = conn.execute('''
                    SELECT 
                        COUNT(*) as expense_count,
                        SUM(amount) as total_spent,
                        MIN(expense_date) as first_expense,
                        MAX(expense_date) as last_expense
                    FROM trip_expenses
                    WHERE trip_id = ?
                ''', (trip_id,)).fetchone()
                
                return {
                    'expense_count': result['expense_count'] or 0,
                    'total_spent': result['total_spent'] or 0,
                    'first_expense': result['first_expense'],
                    'last_expense': result['last_expense']
                }
        except:
            return {'expense_count': 0, 'total_spent': 0}
    
    def _get_trip_participants(self, trip_id: int) -> List[Dict[str, Any]]:
        """Get all participants who have journal entries."""
        try:
            with self.db.get_connection() as conn:
                participants = conn.execute('''
                    SELECT DISTINCT u.id, u.username, u.profile_picture, COUNT(j.id) as entry_count
                    FROM travel_journal j
                    JOIN users u ON j.user_id = u.id
                    WHERE j.trip_id = ?
                    GROUP BY u.id
                ''', (trip_id,)).fetchall()
                
                return [dict(p) for p in participants]
        except:
            return []
    
    def _count_media(self, entries: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count media types in entries."""
        counts = {'photos': 0, 'videos': 0, 'locations': 0}
        
        for entry in entries:
            if entry['entry_type'] == 'photo':
                counts['photos'] += len(entry.get('media_urls', []))
            elif entry['entry_type'] == 'video':
                counts['videos'] += len(entry.get('media_urls', []))
            elif entry['entry_type'] == 'location':
                counts['locations'] += 1
        
        return counts
    
    def search_entries(self, trip_id: int, search_term: str) -> List[Dict[str, Any]]:
        """Search journal entries by content or title."""
        try:
            with self.db.get_connection() as conn:
                entries = conn.execute('''
                    SELECT j.*, u.username, u.profile_picture
                    FROM travel_journal j
                    JOIN users u ON j.user_id = u.id
                    WHERE j.trip_id = ? AND j.is_private = 0
                    AND (j.title LIKE ? OR j.content LIKE ?)
                    ORDER BY j.entry_date DESC
                ''', (trip_id, f'%{search_term}%', f'%{search_term}%')).fetchall()
                
                result = []
                for entry in entries:
                    entry_dict = dict(entry)
                    # Parse JSON fields
                    for field in ['media_urls', 'location_data', 'weather_data']:
                        if entry_dict.get(field):
                            entry_dict[field] = json.loads(entry_dict[field])
                    result.append(entry_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to search journal entries: {e}")
            raise ServiceError(f"Failed to search journal entries: {str(e)}")
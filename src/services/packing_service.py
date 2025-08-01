"""
Smart packing assistant service with weather integration.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import structlog
from ..core.database import get_database
from ..core.exceptions import ValidationError, ServiceError

logger = structlog.get_logger(__name__)


class PackingService:
    """Handles packing list generation and management."""
    
    def __init__(self):
        self.db = get_database()
        self.base_items = self._load_base_items()
    
    def _load_base_items(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load base packing items by category."""
        return {
            'essentials': [
                {'item': 'Passport', 'quantity': 1, 'category': 'documents'},
                {'item': 'Driver\'s License', 'quantity': 1, 'category': 'documents'},
                {'item': 'Travel Insurance Documents', 'quantity': 1, 'category': 'documents'},
                {'item': 'Phone Charger', 'quantity': 1, 'category': 'electronics'},
                {'item': 'Wallet', 'quantity': 1, 'category': 'personal'},
                {'item': 'Medications', 'quantity': 1, 'category': 'health'},
                {'item': 'Toothbrush', 'quantity': 1, 'category': 'toiletries'},
                {'item': 'Toothpaste', 'quantity': 1, 'category': 'toiletries'},
            ],
            'warm_weather': [
                {'item': 'T-shirts', 'quantity': 3, 'category': 'clothing'},
                {'item': 'Shorts', 'quantity': 2, 'category': 'clothing'},
                {'item': 'Sunglasses', 'quantity': 1, 'category': 'accessories'},
                {'item': 'Sunscreen', 'quantity': 1, 'category': 'health'},
                {'item': 'Hat/Cap', 'quantity': 1, 'category': 'accessories'},
                {'item': 'Sandals', 'quantity': 1, 'category': 'footwear'},
                {'item': 'Swimsuit', 'quantity': 1, 'category': 'clothing'},
            ],
            'cold_weather': [
                {'item': 'Warm Jacket', 'quantity': 1, 'category': 'clothing'},
                {'item': 'Sweaters', 'quantity': 2, 'category': 'clothing'},
                {'item': 'Long Pants', 'quantity': 3, 'category': 'clothing'},
                {'item': 'Gloves', 'quantity': 1, 'category': 'accessories'},
                {'item': 'Scarf', 'quantity': 1, 'category': 'accessories'},
                {'item': 'Warm Hat', 'quantity': 1, 'category': 'accessories'},
                {'item': 'Thermal Underwear', 'quantity': 2, 'category': 'clothing'},
            ],
            'rainy_weather': [
                {'item': 'Rain Jacket', 'quantity': 1, 'category': 'clothing'},
                {'item': 'Umbrella', 'quantity': 1, 'category': 'accessories'},
                {'item': 'Waterproof Shoes', 'quantity': 1, 'category': 'footwear'},
                {'item': 'Plastic Bags', 'quantity': 3, 'category': 'misc'},
            ],
            'adventure': [
                {'item': 'Hiking Boots', 'quantity': 1, 'category': 'footwear'},
                {'item': 'Backpack', 'quantity': 1, 'category': 'bags'},
                {'item': 'Water Bottle', 'quantity': 1, 'category': 'accessories'},
                {'item': 'First Aid Kit', 'quantity': 1, 'category': 'health'},
                {'item': 'Flashlight', 'quantity': 1, 'category': 'tools'},
                {'item': 'Map/GPS', 'quantity': 1, 'category': 'navigation'},
            ],
            'city': [
                {'item': 'Comfortable Walking Shoes', 'quantity': 1, 'category': 'footwear'},
                {'item': 'City Map/Guide', 'quantity': 1, 'category': 'navigation'},
                {'item': 'Public Transport Card', 'quantity': 1, 'category': 'documents'},
                {'item': 'Small Day Bag', 'quantity': 1, 'category': 'bags'},
            ],
            'beach': [
                {'item': 'Beach Towel', 'quantity': 1, 'category': 'accessories'},
                {'item': 'Flip Flops', 'quantity': 1, 'category': 'footwear'},
                {'item': 'Beach Bag', 'quantity': 1, 'category': 'bags'},
                {'item': 'Snorkel Gear', 'quantity': 1, 'category': 'sports'},
            ]
        }
    
    def generate_packing_list(self, trip_id: int, user_id: int, trip_data: Dict[str, Any]) -> int:
        """Generate a smart packing list based on trip details and weather."""
        try:
            # Extract trip details
            duration_days = trip_data.get('total_duration_hours', 24) / 24
            route_type = trip_data.get('route_type', 'cultural')
            weather_data = trip_data.get('weather_data', {})
            activities = trip_data.get('activities', [])
            
            # Start with essentials
            packing_items = []
            for item in self.base_items['essentials']:
                packing_items.append({
                    **item,
                    'packed': False,
                    'custom': False
                })
            
            # Add weather-specific items
            if weather_data:
                avg_temp = weather_data.get('average_temperature', 20)
                precipitation = weather_data.get('precipitation_chance', 0)
                
                if avg_temp > 25:
                    for item in self.base_items['warm_weather']:
                        adjusted_item = item.copy()
                        # Adjust quantities based on trip duration
                        if item['category'] == 'clothing':
                            adjusted_item['quantity'] = max(1, int(item['quantity'] * (duration_days / 3)))
                        packing_items.append({
                            **adjusted_item,
                            'packed': False,
                            'custom': False
                        })
                elif avg_temp < 10:
                    for item in self.base_items['cold_weather']:
                        packing_items.append({
                            **item,
                            'packed': False,
                            'custom': False
                        })
                
                if precipitation > 30:
                    for item in self.base_items['rainy_weather']:
                        packing_items.append({
                            **item,
                            'packed': False,
                            'custom': False
                        })
            
            # Add activity-specific items
            if route_type in ['adventure', 'hidden_gems']:
                for item in self.base_items['adventure']:
                    packing_items.append({
                        **item,
                        'packed': False,
                        'custom': False
                    })
            
            if route_type in ['cultural', 'culinary']:
                for item in self.base_items['city']:
                    packing_items.append({
                        **item,
                        'packed': False,
                        'custom': False
                    })
            
            # Check for beach destinations
            if any('beach' in str(activity).lower() for activity in activities):
                for item in self.base_items['beach']:
                    packing_items.append({
                        **item,
                        'packed': False,
                        'custom': False
                    })
            
            # Remove duplicates
            unique_items = {}
            for item in packing_items:
                key = item['item']
                if key not in unique_items:
                    unique_items[key] = item
                else:
                    # Keep the one with higher quantity
                    if item['quantity'] > unique_items[key]['quantity']:
                        unique_items[key] = item
            
            packing_items = list(unique_items.values())
            
            # Save the packing list
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO packing_lists (
                        trip_id, user_id, list_name, items,
                        weather_considered, activities_considered
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    trip_id,
                    user_id,
                    f"Packing List for {trip_data.get('trip_name', 'Trip')}",
                    json.dumps(packing_items),
                    json.dumps(weather_data) if weather_data else None,
                    json.dumps(activities) if activities else None
                ))
                
                list_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Packing list generated", list_id=list_id, trip_id=trip_id)
                return list_id
                
        except Exception as e:
            logger.error(f"Failed to generate packing list: {e}")
            raise ServiceError(f"Failed to generate packing list: {str(e)}")
    
    def get_packing_list(self, list_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific packing list."""
        try:
            with self.db.get_connection() as conn:
                packing_list = conn.execute('''
                    SELECT * FROM packing_lists
                    WHERE id = ? AND user_id = ?
                ''', (list_id, user_id)).fetchone()
                
                if packing_list:
                    result = dict(packing_list)
                    result['items'] = json.loads(result['items'])
                    if result.get('weather_considered'):
                        result['weather_considered'] = json.loads(result['weather_considered'])
                    if result.get('activities_considered'):
                        result['activities_considered'] = json.loads(result['activities_considered'])
                    
                    # Calculate progress
                    items = result['items']
                    packed_count = sum(1 for item in items if item.get('packed', False))
                    result['progress'] = {
                        'packed': packed_count,
                        'total': len(items),
                        'percentage': (packed_count / len(items) * 100) if items else 0
                    }
                    
                    return result
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get packing list: {e}")
            raise ServiceError(f"Failed to get packing list: {str(e)}")
    
    def get_trip_packing_lists(self, trip_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Get all packing lists for a trip."""
        try:
            with self.db.get_connection() as conn:
                lists = conn.execute('''
                    SELECT * FROM packing_lists
                    WHERE trip_id = ? AND user_id = ?
                    ORDER BY created_at DESC
                ''', (trip_id, user_id)).fetchall()
                
                result = []
                for packing_list in lists:
                    list_dict = dict(packing_list)
                    items = json.loads(list_dict['items'])
                    packed_count = sum(1 for item in items if item.get('packed', False))
                    
                    list_dict['progress'] = {
                        'packed': packed_count,
                        'total': len(items),
                        'percentage': (packed_count / len(items) * 100) if items else 0
                    }
                    
                    result.append(list_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get packing lists: {e}")
            raise ServiceError(f"Failed to get packing lists: {str(e)}")
    
    def update_item_status(self, list_id: int, user_id: int, item_name: str, packed: bool) -> bool:
        """Update the packed status of an item."""
        try:
            packing_list = self.get_packing_list(list_id, user_id)
            if not packing_list:
                return False
            
            items = packing_list['items']
            updated = False
            
            for item in items:
                if item['item'] == item_name:
                    item['packed'] = packed
                    updated = True
                    break
            
            if updated:
                with self.db.get_connection() as conn:
                    conn.execute('''
                        UPDATE packing_lists
                        SET items = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND user_id = ?
                    ''', (json.dumps(items), list_id, user_id))
                    conn.commit()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update item status: {e}")
            raise ServiceError(f"Failed to update item status: {str(e)}")
    
    def add_custom_item(self, list_id: int, user_id: int, item_data: Dict[str, Any]) -> bool:
        """Add a custom item to the packing list."""
        try:
            packing_list = self.get_packing_list(list_id, user_id)
            if not packing_list:
                return False
            
            new_item = {
                'item': item_data['item'],
                'quantity': item_data.get('quantity', 1),
                'category': item_data.get('category', 'custom'),
                'packed': False,
                'custom': True
            }
            
            items = packing_list['items']
            items.append(new_item)
            
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE packing_lists
                    SET items = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (json.dumps(items), list_id, user_id))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to add custom item: {e}")
            raise ServiceError(f"Failed to add custom item: {str(e)}")
    
    def remove_item(self, list_id: int, user_id: int, item_name: str) -> bool:
        """Remove an item from the packing list."""
        try:
            packing_list = self.get_packing_list(list_id, user_id)
            if not packing_list:
                return False
            
            items = packing_list['items']
            items = [item for item in items if item['item'] != item_name]
            
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE packing_lists
                    SET items = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (json.dumps(items), list_id, user_id))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove item: {e}")
            raise ServiceError(f"Failed to remove item: {str(e)}")
    
    def get_categories(self) -> List[str]:
        """Get all available item categories."""
        return [
            'documents',
            'electronics', 
            'personal',
            'health',
            'toiletries',
            'clothing',
            'accessories',
            'footwear',
            'bags',
            'misc',
            'tools',
            'navigation',
            'sports',
            'custom'
        ]
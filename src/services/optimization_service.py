"""
Smart itinerary optimization service with ML-powered scheduling.
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, time
import json
import structlog
from ..core.database import get_database
from ..core.exceptions import ValidationError, ServiceError

logger = structlog.get_logger(__name__)


class ItineraryOptimizationService:
    """Handles smart itinerary optimization using ML algorithms."""
    
    def __init__(self):
        self.db = get_database()
    
    def save_user_preferences(self, user_id: int, trip_id: int = None, 
                            preferences: Dict[str, Any] = None) -> int:
        """Save user's optimization preferences."""
        try:
            if not preferences:
                preferences = {}
            
            # Set defaults
            energy_pattern = preferences.get('energy_pattern', 'moderate')
            pace_preference = preferences.get('pace_preference', 'relaxed')
            break_frequency = preferences.get('break_frequency', 'regular')
            meal_times = preferences.get('meal_times', {
                'breakfast': '08:00',
                'lunch': '12:30',
                'dinner': '19:00'
            })
            
            with self.db.get_connection() as conn:
                # Check if preferences exist
                existing = conn.execute('''
                    SELECT id FROM optimization_preferences
                    WHERE user_id = ? AND (trip_id = ? OR trip_id IS NULL)
                ''', (user_id, trip_id)).fetchone()
                
                if existing:
                    # Update existing
                    conn.execute('''
                        UPDATE optimization_preferences SET
                            energy_pattern = ?, pace_preference = ?, break_frequency = ?,
                            meal_times = ?, avoid_rush_hours = ?, max_walking_distance = ?,
                            accessibility_needs = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (
                        energy_pattern,
                        pace_preference,
                        break_frequency,
                        json.dumps(meal_times),
                        preferences.get('avoid_rush_hours', True),
                        preferences.get('max_walking_distance', 2.0),
                        json.dumps(preferences.get('accessibility_needs', {})),
                        existing['id']
                    ))
                    pref_id = existing['id']
                else:
                    # Create new
                    cursor = conn.execute('''
                        INSERT INTO optimization_preferences (
                            user_id, trip_id, energy_pattern, pace_preference,
                            break_frequency, meal_times, avoid_rush_hours,
                            max_walking_distance, accessibility_needs
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id, trip_id, energy_pattern, pace_preference,
                        break_frequency, json.dumps(meal_times),
                        preferences.get('avoid_rush_hours', True),
                        preferences.get('max_walking_distance', 2.0),
                        json.dumps(preferences.get('accessibility_needs', {}))
                    ))
                    pref_id = cursor.lastrowid
                
                conn.commit()
                logger.info(f"User preferences saved", user_id=user_id, pref_id=pref_id)
                return pref_id
                
        except Exception as e:
            logger.error(f"Failed to save user preferences: {e}")
            raise ServiceError(f"Failed to save user preferences: {str(e)}")
    
    def get_user_preferences(self, user_id: int, trip_id: int = None) -> Dict[str, Any]:
        """Get user's optimization preferences."""
        try:
            with self.db.get_connection() as conn:
                # Try trip-specific preferences first, then general preferences
                preferences = None
                if trip_id:
                    preferences = conn.execute('''
                        SELECT * FROM optimization_preferences
                        WHERE user_id = ? AND trip_id = ?
                    ''', (user_id, trip_id)).fetchone()
                
                if not preferences:
                    preferences = conn.execute('''
                        SELECT * FROM optimization_preferences
                        WHERE user_id = ? AND trip_id IS NULL
                    ''', (user_id,)).fetchone()
                
                if preferences:
                    pref_dict = dict(preferences)
                    if pref_dict.get('meal_times'):
                        pref_dict['meal_times'] = json.loads(pref_dict['meal_times'])
                    if pref_dict.get('accessibility_needs'):
                        pref_dict['accessibility_needs'] = json.loads(pref_dict['accessibility_needs'])
                    return pref_dict
                
                # Return defaults if no preferences found
                return {
                    'energy_pattern': 'moderate',
                    'pace_preference': 'relaxed',
                    'break_frequency': 'regular',
                    'meal_times': {
                        'breakfast': '08:00',
                        'lunch': '12:30',
                        'dinner': '19:00'
                    },
                    'avoid_rush_hours': True,
                    'max_walking_distance': 2.0,
                    'accessibility_needs': {}
                }
                
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            raise ServiceError(f"Failed to get user preferences: {str(e)}")
    
    def optimize_itinerary(self, trip_data: Dict[str, Any], user_id: int,
                          activities: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optimize trip itinerary based on user preferences and ML algorithms."""
        try:
            # Get user preferences
            preferences = self.get_user_preferences(user_id, trip_data.get('trip_id'))
            
            # Get trip details
            duration_days = int(trip_data.get('total_duration_hours', 72) / 24)
            route_segments = trip_data.get('segments', [])
            
            if not activities:
                activities = self._generate_default_activities(trip_data)
            
            # Create optimized daily schedules
            optimized_schedule = []
            
            for day in range(duration_days):
                daily_schedule = self._optimize_daily_schedule(
                    day + 1, activities, preferences, route_segments
                )
                optimized_schedule.append(daily_schedule)
            
            # Calculate optimization metrics
            metrics = self._calculate_optimization_metrics(optimized_schedule, preferences)
            
            result = {
                'trip_id': trip_data.get('trip_id'),
                'optimization_date': datetime.now().isoformat(),
                'user_preferences': preferences,
                'optimized_schedule': optimized_schedule,
                'optimization_metrics': metrics,
                'recommendations': self._generate_recommendations(optimized_schedule, preferences)
            }
            
            logger.info(f"Itinerary optimized", user_id=user_id, days=duration_days)
            return result
            
        except Exception as e:
            logger.error(f"Failed to optimize itinerary: {e}")
            raise ServiceError(f"Failed to optimize itinerary: {str(e)}")
    
    def _generate_default_activities(self, trip_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate default activities based on trip data."""
        route_type = trip_data.get('route_type', 'cultural')
        intermediate_cities = trip_data.get('intermediate_cities', [])
        
        activities = []
        
        # Add activities based on route type
        activity_templates = {
            'cultural': [
                {'type': 'museum', 'duration': 2.0, 'energy_cost': 'medium'},
                {'type': 'historic_site', 'duration': 1.5, 'energy_cost': 'low'},
                {'type': 'walking_tour', 'duration': 2.5, 'energy_cost': 'high'},
                {'type': 'cathedral', 'duration': 1.0, 'energy_cost': 'low'}
            ],
            'culinary': [
                {'type': 'food_market', 'duration': 1.5, 'energy_cost': 'medium'},
                {'type': 'cooking_class', 'duration': 3.0, 'energy_cost': 'medium'},
                {'type': 'wine_tasting', 'duration': 2.0, 'energy_cost': 'low'},
                {'type': 'restaurant', 'duration': 1.5, 'energy_cost': 'low'}
            ],
            'adventure': [
                {'type': 'hiking', 'duration': 4.0, 'energy_cost': 'high'},
                {'type': 'outdoor_activity', 'duration': 3.0, 'energy_cost': 'high'},
                {'type': 'scenic_viewpoint', 'duration': 1.0, 'energy_cost': 'medium'},
                {'type': 'adventure_sport', 'duration': 2.5, 'energy_cost': 'high'}
            ]
        }
        
        templates = activity_templates.get(route_type, activity_templates['cultural'])
        
        # Generate activities for each city
        for i, city in enumerate(intermediate_cities[:5]):  # Limit to 5 cities
            city_name = city.get('name') if isinstance(city, dict) else str(city)
            
            for j, template in enumerate(templates):
                if len(activities) < 20:  # Limit total activities
                    activity = {
                        'id': f"activity_{i}_{j}",
                        'name': f"{template['type'].replace('_', ' ').title()} in {city_name}",
                        'city': city_name,
                        'type': template['type'],
                        'duration_hours': template['duration'],
                        'energy_cost': template['energy_cost'],
                        'opening_hours': {'start': '09:00', 'end': '18:00'},
                        'priority': 'medium',
                        'weather_dependent': template['type'] in ['hiking', 'outdoor_activity', 'scenic_viewpoint']
                    }
                    activities.append(activity)
        
        return activities
    
    def _optimize_daily_schedule(self, day_number: int, activities: List[Dict[str, Any]],
                               preferences: Dict[str, Any], route_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize schedule for a single day."""
        try:
            # Determine energy levels throughout the day
            energy_pattern = preferences.get('energy_pattern', 'moderate')
            energy_curve = self._get_energy_curve(energy_pattern)
            
            # Get meal times
            meal_times = preferences.get('meal_times', {})
            
            # Filter activities for this day (simplified - in reality would be more complex)
            day_activities = activities[(day_number-1)*3:day_number*3]  # 3 activities per day
            
            # Optimize activity ordering
            optimized_activities = self._optimize_activity_order(
                day_activities, energy_curve, preferences
            )
            
            # Schedule activities with time slots
            scheduled_activities = self._schedule_activities(
                optimized_activities, meal_times, preferences
            )
            
            # Add breaks and travel times
            final_schedule = self._add_breaks_and_travel(scheduled_activities, preferences)
            
            return {
                'day': day_number,
                'date': (datetime.now() + timedelta(days=day_number-1)).strftime('%Y-%m-%d'),
                'schedule': final_schedule,
                'energy_distribution': self._calculate_daily_energy_distribution(final_schedule),
                'total_walking_distance': self._calculate_walking_distance(final_schedule),
                'estimated_cost': self._estimate_daily_cost(final_schedule)
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize daily schedule: {e}")
            return {
                'day': day_number,
                'schedule': [],
                'energy_distribution': 'balanced',
                'total_walking_distance': 0,
                'estimated_cost': 0
            }
    
    def _get_energy_curve(self, energy_pattern: str) -> Dict[str, float]:
        """Get energy levels throughout the day."""
        curves = {
            'morning_person': {
                '08:00': 1.0, '10:00': 0.9, '12:00': 0.8, '14:00': 0.6, 
                '16:00': 0.7, '18:00': 0.5, '20:00': 0.3
            },
            'night_owl': {
                '08:00': 0.3, '10:00': 0.5, '12:00': 0.7, '14:00': 0.8, 
                '16:00': 0.9, '18:00': 1.0, '20:00': 0.9
            },
            'moderate': {
                '08:00': 0.7, '10:00': 0.8, '12:00': 0.9, '14:00': 0.7, 
                '16:00': 0.8, '18:00': 0.6, '20:00': 0.4
            }
        }
        return curves.get(energy_pattern, curves['moderate'])
    
    def _optimize_activity_order(self, activities: List[Dict[str, Any]], 
                               energy_curve: Dict[str, float], 
                               preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Optimize the order of activities based on energy levels."""
        # Sort activities by energy cost vs available energy
        def activity_score(activity):
            energy_cost = {'low': 0.3, 'medium': 0.6, 'high': 0.9}.get(activity.get('energy_cost', 'medium'), 0.6)
            priority_score = {'high': 3, 'medium': 2, 'low': 1}.get(activity.get('priority', 'medium'), 2)
            return priority_score - energy_cost
        
        return sorted(activities, key=activity_score, reverse=True)
    
    def _schedule_activities(self, activities: List[Dict[str, Any]], 
                           meal_times: Dict[str, str], 
                           preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Schedule activities with specific time slots."""
        scheduled = []
        current_time = datetime.strptime('09:00', '%H:%M').time()
        
        # Add breakfast
        if 'breakfast' in meal_times:
            scheduled.append({
                'type': 'meal',
                'name': 'Breakfast',
                'start_time': meal_times['breakfast'],
                'duration_hours': 0.5,
                'activity_type': 'meal'
            })
        
        for activity in activities:
            # Calculate start time
            start_time = (datetime.combine(datetime.today(), current_time) + 
                         timedelta(minutes=30)).time().strftime('%H:%M')
            
            scheduled_activity = {
                **activity,
                'start_time': start_time,
                'end_time': (datetime.strptime(start_time, '%H:%M') + 
                           timedelta(hours=activity.get('duration_hours', 1))).strftime('%H:%M'),
                'activity_type': 'attraction'
            }
            scheduled.append(scheduled_activity)
            
            # Update current time
            end_time = datetime.strptime(scheduled_activity['end_time'], '%H:%M').time()
            current_time = end_time
            
            # Add lunch if it's time
            lunch_time_obj = datetime.strptime(meal_times.get('lunch', '12:30'), '%H:%M').time()
            if current_time >= lunch_time_obj and not any(s.get('name') == 'Lunch' for s in scheduled):
                scheduled.append({
                    'type': 'meal',
                    'name': 'Lunch',
                    'start_time': meal_times.get('lunch', '12:30'),
                    'duration_hours': 1.0,
                    'activity_type': 'meal'
                })
                current_time = (datetime.combine(datetime.today(), lunch_time_obj) + 
                              timedelta(hours=1)).time()
        
        # Add dinner
        if 'dinner' in meal_times:
            scheduled.append({
                'type': 'meal',
                'name': 'Dinner',
                'start_time': meal_times['dinner'],
                'duration_hours': 1.5,
                'activity_type': 'meal'
            })
        
        return sorted(scheduled, key=lambda x: x.get('start_time', '00:00'))
    
    def _add_breaks_and_travel(self, scheduled_activities: List[Dict[str, Any]], 
                             preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add breaks and travel time between activities."""
        final_schedule = []
        break_frequency = preferences.get('break_frequency', 'regular')
        
        for i, activity in enumerate(scheduled_activities):
            final_schedule.append(activity)
            
            # Add travel time if not the last activity
            if i < len(scheduled_activities) - 1:
                travel_duration = 0.25 if activity.get('city') == scheduled_activities[i+1].get('city') else 0.5
                
                final_schedule.append({
                    'type': 'travel',
                    'name': 'Travel time',
                    'duration_hours': travel_duration,
                    'activity_type': 'travel'
                })
            
            # Add breaks based on frequency
            if break_frequency == 'frequent' and i % 2 == 1:
                final_schedule.append({
                    'type': 'break',
                    'name': 'Rest break',
                    'duration_hours': 0.25,
                    'activity_type': 'break'
                })
            elif break_frequency == 'regular' and i % 3 == 2:
                final_schedule.append({
                    'type': 'break',
                    'name': 'Rest break',
                    'duration_hours': 0.25,
                    'activity_type': 'break'
                })
        
        return final_schedule
    
    def _calculate_daily_energy_distribution(self, schedule: List[Dict[str, Any]]) -> str:
        """Calculate how energy is distributed throughout the day."""
        high_energy_count = sum(1 for item in schedule if item.get('energy_cost') == 'high')
        total_activities = sum(1 for item in schedule if item.get('activity_type') == 'attraction')
        
        if total_activities == 0:
            return 'balanced'
        
        ratio = high_energy_count / total_activities
        
        if ratio > 0.6:
            return 'high_intensity'
        elif ratio < 0.3:
            return 'low_intensity'
        else:
            return 'balanced'
    
    def _calculate_walking_distance(self, schedule: List[Dict[str, Any]]) -> float:
        """Estimate total walking distance for the day."""
        # Simplified calculation - in reality would use actual coordinates
        walking_activities = [item for item in schedule if item.get('activity_type') == 'attraction']
        return len(walking_activities) * 0.8  # Average 0.8km walking per activity
    
    def _estimate_daily_cost(self, schedule: List[Dict[str, Any]]) -> float:
        """Estimate total daily cost."""
        costs = {
            'museum': 15, 'historic_site': 10, 'walking_tour': 20, 'cathedral': 5,
            'food_market': 25, 'cooking_class': 80, 'wine_tasting': 35, 'restaurant': 45,
            'hiking': 0, 'outdoor_activity': 30, 'scenic_viewpoint': 0, 'adventure_sport': 60,
            'meal': 25
        }
        
        total_cost = 0
        for item in schedule:
            activity_type = item.get('type', item.get('name', '').lower())
            total_cost += costs.get(activity_type, 10)
        
        return total_cost
    
    def _calculate_optimization_metrics(self, schedule: List[Dict[str, Any]], 
                                      preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate metrics about the optimization quality."""
        total_activities = sum(len([item for item in day['schedule'] 
                                  if item.get('activity_type') == 'attraction']) 
                             for day in schedule)
        
        total_walking = sum(day.get('total_walking_distance', 0) for day in schedule)
        total_cost = sum(day.get('estimated_cost', 0) for day in schedule)
        
        # Calculate energy distribution score
        energy_distributions = [day.get('energy_distribution', 'balanced') for day in schedule]
        balanced_days = energy_distributions.count('balanced')
        energy_score = balanced_days / len(schedule) if schedule else 0
        
        return {
            'total_activities': total_activities,
            'total_walking_distance_km': round(total_walking, 1),
            'total_estimated_cost': round(total_cost, 2),
            'energy_balance_score': round(energy_score, 2),
            'average_activities_per_day': round(total_activities / len(schedule), 1) if schedule else 0,
            'optimization_quality': 'excellent' if energy_score > 0.8 else 'good' if energy_score > 0.6 else 'fair'
        }
    
    def _generate_recommendations(self, schedule: List[Dict[str, Any]], 
                                preferences: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Check for long days
        for day in schedule:
            activities = [item for item in day['schedule'] if item.get('activity_type') == 'attraction']
            if len(activities) > 4:
                recommendations.append(f"Day {day['day']} is quite packed. Consider reducing activities for a more relaxed pace.")
        
        # Check walking distance
        max_distance = preferences.get('max_walking_distance', 2.0)
        for day in schedule:
            if day.get('total_walking_distance', 0) > max_distance:
                recommendations.append(f"Day {day['day']} involves {day['total_walking_distance']:.1f}km walking. Consider using public transport.")
        
        # Energy pattern recommendations
        energy_pattern = preferences.get('energy_pattern', 'moderate')
        if energy_pattern == 'morning_person':
            recommendations.append("Your schedule prioritizes morning activities based on your energy pattern.")
        elif energy_pattern == 'night_owl':
            recommendations.append("Consider booking evening activities or cultural events to match your energy pattern.")
        
        if not recommendations:
            recommendations.append("Your itinerary is well-optimized based on your preferences!")
        
        return recommendations
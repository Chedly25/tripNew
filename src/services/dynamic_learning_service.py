"""
Dynamic Learning Service

Basic learning system for improving intermediate city selection over time.
Learns from user behavior, feedback, and usage patterns.
"""
import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import structlog

from ..core.models import City, TripRequest

logger = structlog.get_logger(__name__)


@dataclass
class UserInteraction:
    """Record of user interaction with city recommendations."""
    user_id: Optional[str]
    session_id: str
    city_name: str
    action: str  # 'viewed', 'selected', 'rejected', 'saved', 'rated'
    route_type: str
    context: Dict[str, Any]
    timestamp: datetime
    rating: Optional[float] = None
    feedback: Optional[str] = None


@dataclass
class CityPopularity:
    """Popularity metrics for a city."""
    city_name: str
    total_views: int = 0
    total_selections: int = 0
    total_rejections: int = 0
    avg_rating: float = 0.0
    rating_count: int = 0
    last_updated: datetime = None
    
    @property
    def selection_rate(self) -> float:
        """Calculate selection rate."""
        total_interactions = self.total_views + self.total_selections + self.total_rejections
        return self.total_selections / total_interactions if total_interactions > 0 else 0.0
    
    @property
    def popularity_score(self) -> float:
        """Calculate overall popularity score."""
        base_score = self.selection_rate * 0.6
        rating_score = (self.avg_rating / 5.0) * 0.4 if self.avg_rating > 0 else 0.0
        return base_score + rating_score


@dataclass
class RouteTypeInsights:
    """Insights for a specific route type."""
    route_type: str
    preferred_city_types: Dict[str, float]  # City type -> preference score
    avg_cities_per_route: float
    seasonal_preferences: Dict[str, float]  # Season -> preference multiplier
    budget_preferences: Dict[str, float]   # Budget range -> preference


class DynamicLearningService:
    """Basic learning service for improving recommendations."""
    
    def __init__(self):
        self.data_file = "data/learning_data.json"
        self.interactions: List[UserInteraction] = []
        self.city_popularity: Dict[str, CityPopularity] = {}
        self.route_insights: Dict[str, RouteTypeInsights] = {}
        
        # Load existing data
        self._load_learning_data()
        
        # Initialize with basic insights
        self._initialize_route_insights()
    
    def record_interaction(self, interaction: UserInteraction):
        """Record a user interaction for learning."""
        
        self.interactions.append(interaction)
        
        # Update city popularity
        self._update_city_popularity(interaction)
        
        # Update route insights
        self._update_route_insights(interaction)
        
        # Periodically save data
        if len(self.interactions) % 10 == 0:
            self._save_learning_data()
        
        logger.info(f"Recorded interaction: {interaction.action} for {interaction.city_name}")
    
    def get_popularity_boost(self, city_name: str, route_type: str) -> float:
        """Get popularity boost for a city based on learning data."""
        
        city_key = city_name.lower()
        
        # Base popularity boost
        if city_key in self.city_popularity:
            popularity = self.city_popularity[city_key]
            base_boost = popularity.popularity_score * 0.2  # Max 20% boost
        else:
            base_boost = 0.0
        
        # Route-specific insights
        route_boost = 0.0
        if route_type in self.route_insights:
            insights = self.route_insights[route_type]
            # This would analyze city types that are popular for this route type
            # For now, simplified implementation
            route_boost = 0.05
        
        total_boost = min(base_boost + route_boost, 0.3)  # Cap at 30% boost
        
        return total_boost
    
    def get_route_recommendations(self, route_type: str, season: str = None) -> Dict[str, Any]:
        """Get learned recommendations for a route type."""
        
        if route_type not in self.route_insights:
            return {}
        
        insights = self.route_insights[route_type]
        
        recommendations = {
            'preferred_city_types': insights.preferred_city_types,
            'recommended_city_count': int(insights.avg_cities_per_route),
            'seasonal_adjustment': insights.seasonal_preferences.get(season, 1.0) if season else 1.0
        }
        
        return recommendations
    
    def get_trending_cities(self, route_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get currently trending cities based on recent interactions."""
        
        # Get recent interactions (last 30 days)
        recent_cutoff = datetime.now() - timedelta(days=30)
        recent_interactions = [
            i for i in self.interactions 
            if i.timestamp >= recent_cutoff
        ]
        
        # Filter by route type if specified
        if route_type:
            recent_interactions = [
                i for i in recent_interactions 
                if i.route_type == route_type
            ]
        
        # Count city mentions
        city_mentions = {}
        for interaction in recent_interactions:
            city_name = interaction.city_name.lower()
            if interaction.action in ['selected', 'saved', 'rated']:
                city_mentions[city_name] = city_mentions.get(city_name, 0) + 1
        
        # Sort by mentions and return top cities
        trending = sorted(
            city_mentions.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:limit]
        
        return [
            {
                'city_name': city_name,
                'mentions': count,
                'popularity_score': self.city_popularity.get(city_name, CityPopularity(city_name)).popularity_score
            }
            for city_name, count in trending
        ]
    
    def analyze_user_preferences(self, user_id: str = None) -> Dict[str, Any]:
        """Analyze preferences for a specific user or overall."""
        
        # Filter interactions by user if specified
        if user_id:
            user_interactions = [i for i in self.interactions if i.user_id == user_id]
        else:
            user_interactions = self.interactions
        
        if not user_interactions:
            return {}
        
        # Analyze preferences
        route_type_counts = {}
        city_type_preferences = {}
        avg_ratings = {}
        
        for interaction in user_interactions:
            # Route type preferences
            route_type = interaction.route_type
            if interaction.action in ['selected', 'saved']:
                route_type_counts[route_type] = route_type_counts.get(route_type, 0) + 1
            
            # City type preferences (would need city type data)
            # For now, simplified
            
            # Rating analysis
            if interaction.rating:
                if route_type not in avg_ratings:
                    avg_ratings[route_type] = []
                avg_ratings[route_type].append(interaction.rating)
        
        # Calculate averages
        for route_type in avg_ratings:
            avg_ratings[route_type] = sum(avg_ratings[route_type]) / len(avg_ratings[route_type])
        
        return {
            'preferred_route_types': route_type_counts,
            'average_ratings_by_route': avg_ratings,
            'total_interactions': len(user_interactions)
        }
    
    def get_personalized_adjustments(self, user_id: str, route_type: str) -> Dict[str, float]:
        """Get personalized scoring adjustments for a user."""
        
        user_prefs = self.analyze_user_preferences(user_id)
        
        adjustments = {
            'popularity_weight': 1.0,
            'novelty_weight': 1.0,
            'rating_weight': 1.0
        }
        
        # Adjust based on user's route type preferences
        route_counts = user_prefs.get('preferred_route_types', {})
        total_interactions = sum(route_counts.values()) if route_counts else 0
        
        if total_interactions > 5:  # Enough data for personalization
            route_preference = route_counts.get(route_type, 0) / total_interactions
            
            if route_preference > 0.5:
                # User likes this route type, boost popular choices
                adjustments['popularity_weight'] = 1.2
            elif route_preference < 0.2:
                # User doesn't usually choose this route type, suggest novelty
                adjustments['novelty_weight'] = 1.3
        
        return adjustments
    
    def _update_city_popularity(self, interaction: UserInteraction):
        """Update popularity metrics for a city."""
        
        city_key = interaction.city_name.lower()
        
        if city_key not in self.city_popularity:
            self.city_popularity[city_key] = CityPopularity(
                city_name=interaction.city_name,
                last_updated=datetime.now()
            )
        
        popularity = self.city_popularity[city_key]
        
        # Update metrics based on action
        if interaction.action == 'viewed':
            popularity.total_views += 1
        elif interaction.action == 'selected':
            popularity.total_selections += 1
        elif interaction.action == 'rejected':
            popularity.total_rejections += 1
        elif interaction.action == 'rated' and interaction.rating:
            # Update rating
            total_rating = popularity.avg_rating * popularity.rating_count
            popularity.rating_count += 1
            popularity.avg_rating = (total_rating + interaction.rating) / popularity.rating_count
        
        popularity.last_updated = datetime.now()
    
    def _update_route_insights(self, interaction: UserInteraction):
        """Update insights for route types."""
        
        route_type = interaction.route_type
        
        if route_type not in self.route_insights:
            return  # Will be handled by initialization
        
        insights = self.route_insights[route_type]
        
        # Update preferred city types based on selections
        if interaction.action == 'selected' and 'city_types' in interaction.context:
            city_types = interaction.context['city_types']
            for city_type in city_types:
                current_pref = insights.preferred_city_types.get(city_type, 0.5)
                # Slightly boost preference
                insights.preferred_city_types[city_type] = min(current_pref + 0.01, 1.0)
        
        # Update seasonal preferences
        if 'season' in interaction.context and interaction.action in ['selected', 'rated']:
            season = interaction.context['season']
            current_pref = insights.seasonal_preferences.get(season, 1.0)
            if interaction.action == 'rated' and interaction.rating:
                # Adjust based on rating
                adjustment = (interaction.rating - 3.0) * 0.02  # -0.04 to +0.04
                insights.seasonal_preferences[season] = max(0.5, min(1.5, current_pref + adjustment))
    
    def _initialize_route_insights(self):
        """Initialize basic route insights."""
        
        route_types = ['scenic', 'cultural', 'adventure', 'culinary', 'romantic', 'hidden_gems']
        
        for route_type in route_types:
            if route_type not in self.route_insights:
                self.route_insights[route_type] = RouteTypeInsights(
                    route_type=route_type,
                    preferred_city_types={
                        'cultural': 0.7 if route_type == 'cultural' else 0.5,
                        'scenic': 0.8 if route_type == 'scenic' else 0.5,
                        'adventure': 0.8 if route_type == 'adventure' else 0.4,
                        'culinary': 0.8 if route_type == 'culinary' else 0.5,
                        'romantic': 0.7 if route_type == 'romantic' else 0.5,
                        'historic': 0.8 if route_type == 'cultural' else 0.6,
                        'authentic': 0.9 if route_type == 'hidden_gems' else 0.6
                    },
                    avg_cities_per_route=4.0,
                    seasonal_preferences={
                        'spring': 1.0,
                        'summer': 1.1,
                        'autumn': 0.9,
                        'winter': 0.8
                    },
                    budget_preferences={
                        'budget': 1.0,
                        'mid-range': 1.1,
                        'luxury': 0.9
                    }
                )
    
    def _load_learning_data(self):
        """Load learning data from file."""
        
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                # Load interactions
                interactions_data = data.get('interactions', [])
                self.interactions = [
                    UserInteraction(
                        user_id=i.get('user_id'),
                        session_id=i['session_id'],
                        city_name=i['city_name'],
                        action=i['action'],
                        route_type=i['route_type'],
                        context=i.get('context', {}),
                        timestamp=datetime.fromisoformat(i['timestamp']),
                        rating=i.get('rating'),
                        feedback=i.get('feedback')
                    )
                    for i in interactions_data
                ]
                
                # Load city popularity
                popularity_data = data.get('city_popularity', {})
                self.city_popularity = {
                    city_name: CityPopularity(
                        city_name=p['city_name'],
                        total_views=p.get('total_views', 0),
                        total_selections=p.get('total_selections', 0),
                        total_rejections=p.get('total_rejections', 0),
                        avg_rating=p.get('avg_rating', 0.0),
                        rating_count=p.get('rating_count', 0),
                        last_updated=datetime.fromisoformat(p['last_updated']) if p.get('last_updated') else datetime.now()
                    )
                    for city_name, p in popularity_data.items()
                }
                
                logger.info(f"Loaded {len(self.interactions)} interactions and {len(self.city_popularity)} city popularity records")
                
        except Exception as e:
            logger.warning(f"Failed to load learning data: {e}")
    
    def _save_learning_data(self):
        """Save learning data to file."""
        
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            # Prepare data for saving
            data = {
                'interactions': [
                    {
                        'user_id': i.user_id,
                        'session_id': i.session_id,
                        'city_name': i.city_name,
                        'action': i.action,
                        'route_type': i.route_type,
                        'context': i.context,
                        'timestamp': i.timestamp.isoformat(),
                        'rating': i.rating,
                        'feedback': i.feedback
                    }
                    for i in self.interactions[-1000:]  # Keep last 1000 interactions
                ],
                'city_popularity': {
                    city_name: {
                        'city_name': p.city_name,
                        'total_views': p.total_views,
                        'total_selections': p.total_selections,
                        'total_rejections': p.total_rejections,
                        'avg_rating': p.avg_rating,
                        'rating_count': p.rating_count,
                        'last_updated': p.last_updated.isoformat() if p.last_updated else datetime.now().isoformat()
                    }
                    for city_name, p in self.city_popularity.items()
                },
                'last_saved': datetime.now().isoformat()
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info("Learning data saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save learning data: {e}")
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get statistics about the learning system."""
        
        return {
            'total_interactions': len(self.interactions),
            'unique_cities': len(self.city_popularity),
            'route_types_analyzed': len(self.route_insights),
            'most_popular_cities': [
                {
                    'name': city_name,
                    'popularity_score': popularity.popularity_score,
                    'selection_rate': popularity.selection_rate
                }
                for city_name, popularity in sorted(
                    self.city_popularity.items(),
                    key=lambda x: x[1].popularity_score,
                    reverse=True
                )[:10]
            ],
            'trending_cities': self.get_trending_cities(limit=5)
        }


# Global service instance
_dynamic_learning_service = None

def get_dynamic_learning_service() -> DynamicLearningService:
    """Get the global dynamic learning service instance."""
    global _dynamic_learning_service
    if _dynamic_learning_service is None:
        _dynamic_learning_service = DynamicLearningService()
    return _dynamic_learning_service
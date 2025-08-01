"""
Enhanced Flask application with AI features, user accounts, and advanced functionality.
"""
import os
import json
import asyncio
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.exceptions import BadRequest, InternalServerError
import structlog
from datetime import datetime, timedelta

# Import existing services
from ..infrastructure.config import SecureConfigurationService
from ..infrastructure.logging import configure_logging, SecurityLogger
from ..services.google_places_city_service import GooglePlacesCityService
from ..services.route_service import ProductionRouteService
from ..services.validation_service import ValidationService
from ..services.travel_planner import TravelPlannerServiceImpl
from ..services.booking_service import BookingService
from ..services.foursquare_service import FoursquareService

# Import new services and features
from ..core.database import get_database, get_user_manager, get_trip_manager
from ..web.auth_routes import auth_bp, login_required, get_current_user
from ..services.claude_ai_service import get_claude_service
from ..services.weather_service import get_weather_service
from ..services.social_service import get_social_service
from ..services.emergency_service import EmergencyService
from ..core.exceptions import TravelPlannerException, ValidationError

# Configure logging
configure_logging(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    json_logs=os.getenv('FLASK_ENV') == 'production'
)

logger = structlog.get_logger(__name__)
security_logger = SecurityLogger()

def create_enhanced_app() -> Flask:
    """Enhanced application factory with all new features."""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    # Security configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(32))
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    
    # Initialize database
    db = get_database()
    logger.info("Database initialized successfully")
    
    # Register authentication blueprint
    app.register_blueprint(auth_bp)
    
    # Initialize services
    config_service = SecureConfigurationService()
    city_service = GooglePlacesCityService()
    route_service = ProductionRouteService(config_service)
    validation_service = ValidationService()
    booking_service = BookingService()
    foursquare_service = FoursquareService()
    claude_service = get_claude_service()
    weather_service = get_weather_service()
    social_service = get_social_service()
    emergency_service = EmergencyService()
    
    travel_planner = TravelPlannerServiceImpl(
        city_service, route_service, validation_service
    )
    
    # Add user context to templates
    @app.context_processor
    def inject_user():
        """Inject current user into all templates."""
        user = get_current_user()
        return dict(current_user=user)
    
    @app.before_request
    def log_request():
        """Log all requests for security monitoring."""
        security_logger.logger.info(
            "http_request",
            method=request.method,
            path=request.path,
            remote_addr=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:100]
        )
    
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net cdnjs.cloudflare.com unpkg.com fonts.googleapis.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com unpkg.com fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com; "
            "img-src 'self' data: https: http: *.tile.openstreetmap.org *.googleapis.com; "
            "connect-src 'self' https: *.tile.openstreetmap.org api.openrouteservice.org api.anthropic.com; "
            "frame-src 'none'"
        )
        return response
    
    # Error handlers
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        logger.warning("Validation error", error=str(e))
        return jsonify({'error': str(e)}), 400
    
    @app.errorhandler(TravelPlannerException)
    def handle_travel_planner_error(e):
        logger.error("Travel planner error", error=str(e))
        return jsonify({'error': 'Service temporarily unavailable'}), 500
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        logger.error("Internal server error", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500
    
    # Main routes
    @app.route('/')
    def index():
        """Enhanced landing page with user context."""
        try:
            user = get_current_user()
            recent_trips = []
            if user:
                trip_manager = get_trip_manager()
                recent_trips = trip_manager.get_user_trips(user['id'], limit=3)
            
            return render_template('enhanced_main.html', recent_trips=recent_trips)
        except Exception as e:
            logger.error("Template rendering failed", error=str(e))
            return "Service temporarily unavailable", 500
    
    @app.route('/results')
    def results():
        """Enhanced results page with save functionality."""
        return render_template('travel_results_enhanced.html')
    
    @app.route('/trip-details')
    def trip_details():
        """Trip details page."""
        return render_template('trip_details.html')
    
    # Original API endpoints
    @app.route('/api/plan-trip', methods=['POST'])
    async def plan_trip():
        """Enhanced trip planning with user context."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            user = get_current_user()
            user_preferences = {}
            if user:
                # Get user travel preferences for personalization
                try:
                    preferences_json = user.get('travel_preferences', '{}')
                    user_preferences = json.loads(preferences_json) if preferences_json else {}
                except json.JSONDecodeError:
                    user_preferences = {}
            
            # Validate input
            result = validation_service.validate_travel_plan_request(data)
            if not result.success:
                return jsonify({'error': result.error_message}), 400
            
            # Plan the trip
            plan_result = await travel_planner.create_travel_plan(
                data['start_location'],
                data['end_location'],
                data.get('route_types', ['scenic', 'cultural'])
            )
            
            if not plan_result.success:
                return jsonify({'error': plan_result.error_message}), 500
            
            # Enhance with AI personalization if user is logged in and Claude is available
            if user and user_preferences:
                try:
                    # Get AI-enhanced route suggestions
                    for route in plan_result.data.get('routes', []):
                        ai_enhancements = await claude_service.analyze_travel_preferences({
                            'route_data': route,
                            'user_preferences': user_preferences,
                            'user_history': user
                        })
                        route['ai_suggestions'] = ai_enhancements
                except Exception as e:
                    logger.warning(f"AI enhancement failed: {e}")
            
            return jsonify(plan_result.data)
            
        except Exception as e:
            logger.error("Trip planning failed", error=str(e))
            return jsonify({'error': 'Trip planning service unavailable'}), 500
    
    @app.route('/api/trip-data', methods=['POST'])
    async def get_trip_data():
        """Enhanced trip data with real bookings."""
        try:
            data = request.get_json()
            cities = data.get('cities', [])
            
            if not cities:
                return jsonify({'error': 'Cities data required'}), 400
            
            # Fetch real data from multiple sources
            hotels_data = {}
            restaurants_data = {}
            activities_data = {}
            
            # Use asyncio to fetch data concurrently
            for city in cities:
                city_name = city.get('name', '')
                coordinates = city.get('coordinates', [])
                
                if city_name and coordinates:
                    try:
                        # Fetch hotels
                        from ..core.models import Coordinates
                        city_coords = Coordinates(latitude=coordinates[0], longitude=coordinates[1])
                        hotels = await booking_service.find_hotels(city_coords, city_name)
                        hotels_data[city_name] = hotels
                        
                        # Fetch restaurants and activities
                        restaurants = await foursquare_service.search_restaurants(city_coords, city_name)
                        activities = await foursquare_service.search_activities(city_coords, city_name)
                        
                        restaurants_data[city_name] = restaurants
                        activities_data[city_name] = activities
                        
                    except Exception as e:
                        logger.warning(f"Data fetch failed for {city_name}: {e}")
                        continue
            
            return jsonify({
                'success': True,
                'data': {
                    'hotels': hotels_data,
                    'restaurants': restaurants_data,
                    'activities': activities_data
                }
            })
            
        except Exception as e:
            logger.error("Trip data fetch failed", error=str(e))
            return jsonify({'error': 'Data fetch failed'}), 500
    
    @app.route('/api/travel/refresh-route', methods=['POST'])
    async def refresh_route():
        """Refresh a specific route type with new cities."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            original_request = data.get('request')
            route_type = data.get('route_type')
            exclude_cities = data.get('exclude_cities', [])
            
            if not original_request or not route_type:
                return jsonify({'error': 'Missing required parameters'}), 400
            
            # Create trip request from original data
            from ..core.models import TripRequest, Season
            trip_request = TripRequest(
                start_city=original_request.get('start_city'),
                end_city=original_request.get('end_city'),
                travel_days=original_request.get('travel_days', 7),
                interests=original_request.get('interests', []),
                season=Season(original_request.get('season', 'summer'))
            )
            
            # Get the specific route strategy
            route_strategies = travel_planner_service._initialize_route_strategies()
            strategy = None
            for s in route_strategies:
                if s['type'] == route_type:
                    strategy = s
                    break
            
            if not strategy:
                return jsonify({'error': f'Unknown route type: {route_type}'}), 400
            
            # Generate a new route for this specific type with randomization
            import random
            random.seed()  # Reset random seed for variety
            
            # Get start and end cities
            start_city = await city_service.get_city_by_name(trip_request.start_city)
            end_city = await city_service.get_city_by_name(trip_request.end_city)
            
            if not start_city or not end_city:
                return jsonify({'error': 'Invalid start or end city'}), 400
            
            # Use ML recommendation system for intelligent city selection
            from ..services.ml_recommendation_service import MLRecommendationService, TripPreference
            
            # Initialize ML service if not already available
            if not hasattr(app, 'ml_service'):
                app.ml_service = MLRecommendationService(city_service)
            
            # Create trip preferences from request
            trip_preferences = TripPreference(
                budget_range=original_request.get('budget_range', 'mid-range'),
                duration_days=trip_request.travel_days,
                travel_style=route_type,
                season=trip_request.season.value if hasattr(trip_request.season, 'value') else str(trip_request.season),
                group_size=original_request.get('group_size', 2),
                activity_preferences=trip_request.interests,
                previous_trips=exclude_cities  # Use excluded cities as "already seen"
            )
            
            # Get session ID for consistent randomization within session
            session_id = request.headers.get('X-Session-ID', str(hash(str(data))))
            
            # Use exploration factor based on refresh count or user preference
            exploration_factor = min(0.6, 0.2 + len(exclude_cities) * 0.1)  # More exploration with more refreshes
            
            # Get ML-powered recommendations
            ml_result = app.ml_service.get_smart_recommendations(
                preferences=trip_preferences,
                start_city=trip_request.start_city,
                end_city=trip_request.end_city,
                exploration_factor=exploration_factor,
                session_id=session_id
            )
            
            if not ml_result.success:
                logger.warning("ML recommendations failed, falling back to simple method")
                # Fallback to original method
                intermediate_cities = await travel_planner_service._find_intermediate_cities_async(
                    strategy, start_city, end_city, trip_request
                )
                filtered_cities = [c for c in intermediate_cities if c.name not in exclude_cities]
                max_cities = strategy.get('max_cities', 3)
                if len(filtered_cities) > max_cities:
                    filtered_cities = random.sample(filtered_cities, max_cities)
            else:
                # Use ML recommendations
                recommendations = ml_result.data['recommendations']
                max_cities = strategy.get('max_cities', 3)
                filtered_cities = [rec['city'] for rec in recommendations[:max_cities]]
                
                logger.info("ML recommendations applied", 
                           method=ml_result.data['algorithm_info']['method'],
                           exploration_factor=exploration_factor,
                           cities_selected=len(filtered_cities))
            
            # Generate the route
            all_cities = [start_city] + filtered_cities + [end_city]
            route_result = route_service.optimize_multi_city_route(all_cities)
            
            if not route_result.success:
                return jsonify({'error': 'Failed to generate route'}), 500
            
            route_data = route_result.data
            
            # Create enriched route data
            from ..core.models import TravelRoute, RouteType
            travel_route = TravelRoute(
                route_type=RouteType(strategy['type']),
                segments=route_data['segments'],
                total_distance_km=route_data['total_distance_km'],
                total_duration_hours=route_data['total_duration_hours'],
                intermediate_cities=filtered_cities,
                description=strategy['description']
            )
            
            # Enrich with itinerary
            enriched_route = await travel_planner_service._enrich_route_with_itinerary(
                travel_route, trip_request, strategy, start_city, end_city
            )
            
            return jsonify({
                'success': True,
                'data': enriched_route
            })
            
        except Exception as e:
            logger.error("Route refresh failed", error=str(e), exc_info=True)
            return jsonify({'error': f'Route refresh failed: {str(e)}'}), 500
    
    # AI Assistant Chat API
    @app.route('/api/ai-chat', methods=['POST'])
    async def ai_chat():
        """AI travel assistant chat endpoint."""
        try:
            data = request.get_json()
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return jsonify({'error': 'Message is required'}), 400
            
            user = get_current_user()
            chat_history = []
            user_context = {}
            
            if user:
                # Get recent chat history
                with get_database().get_connection() as conn:
                    history = conn.execute('''
                        SELECT message_type, message_content FROM ai_chat_history 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC 
                        LIMIT 20
                    ''', (user['id'],)).fetchall()
                    chat_history = [dict(row) for row in reversed(history)]
                
                user_context = {
                    'user_id': user['id'],
                    'username': user['username'],
                    'travel_preferences': user.get('travel_preferences', '{}')
                }
            
            # Get AI response
            response = await claude_service.travel_chat_assistant(
                user_message, chat_history, user_context
            )
            
            # Save chat history if user is logged in
            if user:
                session_id = session.get('session_id', 'anonymous')
                with get_database().get_connection() as conn:
                    # Save user message
                    conn.execute('''
                        INSERT INTO ai_chat_history (user_id, session_id, message_type, message_content)
                        VALUES (?, ?, ?, ?)
                    ''', (user['id'], session_id, 'user', user_message))
                    
                    # Save assistant response
                    conn.execute('''
                        INSERT INTO ai_chat_history (user_id, session_id, message_type, message_content)
                        VALUES (?, ?, ?, ?)
                    ''', (user['id'], session_id, 'assistant', response))
                    
                    conn.commit()
            
            return jsonify({
                'success': True,
                'response': response,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error("AI chat failed", error=str(e))
            return jsonify({'error': 'AI assistant temporarily unavailable'}), 500
    
    # Trip saving and management
    @app.route('/api/save-trip', methods=['POST'])
    @login_required
    async def save_trip():
        """Save a trip for the current user."""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            data = request.get_json()
            trip_data = data.get('trip_data')
            trip_name = data.get('trip_name', f"Trip to {trip_data.get('end_city', {}).get('name', 'Unknown')}")
            is_favorite = data.get('is_favorite', False)
            
            if not trip_data:
                return jsonify({'error': 'Trip data is required'}), 400
            
            trip_manager = get_trip_manager()
            trip_id = trip_manager.save_trip(user['id'], trip_name, trip_data, is_favorite)
            
            return jsonify({
                'success': True,
                'trip_id': trip_id,
                'message': 'Trip saved successfully!'
            })
            
        except Exception as e:
            logger.error("Trip saving failed", error=str(e))
            return jsonify({'error': 'Failed to save trip'}), 500
    
    # AI-powered features
    @app.route('/api/ai-itinerary', methods=['POST'])
    @login_required
    async def generate_ai_itinerary():
        """Generate detailed AI-powered itinerary."""
        try:
            user = get_current_user()
            data = request.get_json()
            route_data = data.get('route_data', {})
            days = data.get('days', 5)
            
            user_preferences = {}
            if user.get('travel_preferences'):
                try:
                    user_preferences = json.loads(user['travel_preferences'])
                except json.JSONDecodeError:
                    pass
            
            itinerary = await claude_service.generate_smart_itinerary(
                route_data, user_preferences, days
            )
            
            return jsonify({
                'success': True,
                'itinerary': itinerary
            })
            
        except Exception as e:
            logger.error("AI itinerary generation failed", error=str(e))
            return jsonify({'error': 'Itinerary generation failed'}), 500
    
    @app.route('/api/ai-photo-analysis', methods=['POST'])
    async def analyze_photo():
        """Analyze photo for destination suggestions."""
        try:
            data = request.get_json()
            photo_description = data.get('description', '')
            
            if not photo_description:
                return jsonify({'error': 'Photo description required'}), 400
            
            suggestions = await claude_service.analyze_photo_for_destinations(photo_description)
            
            return jsonify({
                'success': True,
                'destinations': suggestions
            })
            
        except Exception as e:
            logger.error("Photo analysis failed", error=str(e))
            return jsonify({'error': 'Photo analysis failed'}), 500
    
    @app.route('/api/travel-insights')
    @login_required
    async def get_travel_insights():
        """Get AI-powered travel insights for the user."""
        try:
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Get user analytics
            with get_database().get_connection() as conn:
                analytics = conn.execute('''
                    SELECT * FROM user_analytics WHERE user_id = ?
                ''', (user['id'],)).fetchone()
                
                if analytics:
                    analytics_dict = dict(analytics)
                    insights = await claude_service.generate_travel_insights(analytics_dict)
                    
                    return jsonify({
                        'success': True,
                        'insights': insights,
                        'analytics': analytics_dict
                    })
            
            return jsonify({'error': 'No travel data available'}), 404
            
        except Exception as e:
            logger.error("Travel insights failed", error=str(e))
            return jsonify({'error': 'Insights generation failed'}), 500
    
    # Chat interface page
    @app.route('/ai-assistant')
    def ai_assistant():
        """AI travel assistant chat interface."""
        return render_template('ai_assistant.html')
    
    # Analytics and insights page
    @app.route('/travel-insights')
    @login_required
    def travel_insights():
        """Travel insights and analytics page."""
        return render_template('travel_insights.html')
    
    # Weather API endpoints
    @app.route('/api/weather/current', methods=['POST'])
    async def get_current_weather():
        """Get current weather for a location."""
        try:
            data = request.get_json()
            coordinates = data.get('coordinates', [])
            city_name = data.get('city_name', '')
            
            if not coordinates or not city_name:
                return jsonify({'error': 'Coordinates and city name required'}), 400
            
            from ..core.models import Coordinates
            coords = Coordinates(latitude=coordinates[0], longitude=coordinates[1])
            weather = await weather_service.get_current_weather(coords, city_name)
            
            return jsonify({'success': True, 'weather': weather})
            
        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")
            return jsonify({'error': 'Weather service unavailable'}), 500
    
    @app.route('/api/weather/forecast', methods=['POST'])
    async def get_weather_forecast():
        """Get weather forecast for a location."""
        try:
            data = request.get_json()
            coordinates = data.get('coordinates', [])
            city_name = data.get('city_name', '')
            days = data.get('days', 5)
            
            from ..core.models import Coordinates
            coords = Coordinates(latitude=coordinates[0], longitude=coordinates[1])
            forecast = await weather_service.get_weather_forecast(coords, city_name, days)
            
            return jsonify({'success': True, 'forecast': forecast})
            
        except Exception as e:
            logger.error(f"Weather forecast failed: {e}")
            return jsonify({'error': 'Weather service unavailable'}), 500
    
    @app.route('/api/weather/route', methods=['POST'])
    async def get_route_weather():
        """Get weather for all cities in a route."""
        try:
            data = request.get_json()
            route_cities = data.get('cities', [])
            
            weather_data = await weather_service.get_route_weather(route_cities)
            analysis = weather_service.analyze_travel_conditions(weather_data)
            
            return jsonify({
                'success': True,
                'weather_data': weather_data,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Route weather failed: {e}")
            return jsonify({'error': 'Weather service unavailable'}), 500
    
    # Social features API endpoints
    @app.route('/api/social/share-trip', methods=['POST'])
    @login_required
    async def share_trip():
        """Share a trip with the community."""
        try:
            user = get_current_user()
            data = request.get_json()
            
            trip_id = data.get('trip_id')
            share_type = data.get('share_type', 'public')
            message = data.get('message', '')
            
            result = social_service.share_trip(user['id'], trip_id, share_type, message)
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Trip sharing failed: {e}")
            return jsonify({'error': 'Failed to share trip'}), 500
    
    @app.route('/api/social/public-trips')
    def get_public_trips():
        """Get public trips from the community."""
        try:
            limit = request.args.get('limit', 20, type=int)
            route_type = request.args.get('route_type')
            
            trips = social_service.get_public_trips(limit, route_type)
            return jsonify({'success': True, 'trips': trips})
            
        except Exception as e:
            logger.error(f"Public trips fetch failed: {e}")
            return jsonify({'error': 'Failed to get public trips'}), 500
    
    @app.route('/api/social/review-trip', methods=['POST'])
    @login_required
    async def review_trip():
        """Add a review for a shared trip."""
        try:
            user = get_current_user()
            data = request.get_json()
            
            trip_id = data.get('trip_id')
            rating = data.get('rating')
            review_text = data.get('review_text', '')
            photos = data.get('photos', [])
            
            result = social_service.add_trip_review(user['id'], trip_id, rating, review_text, photos)
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Trip review failed: {e}")
            return jsonify({'error': 'Failed to add review'}), 500
    
    @app.route('/shared-trip/<share_id>')
    def view_shared_trip(share_id):
        """View a shared trip."""
        try:
            trip = social_service.get_shared_trip(share_id)
            if not trip:
                return "Trip not found or no longer available", 404
            
            reviews = social_service.get_trip_reviews(trip['trip_id'])
            return render_template('shared_trip.html', trip=trip, reviews=reviews)
            
        except Exception as e:
            logger.error(f"Shared trip view failed: {e}")
            return "Trip unavailable", 500
    
    # Emergency assistance API endpoints
    @app.route('/api/emergency/request', methods=['POST'])
    @login_required
    async def handle_emergency():
        """Handle emergency assistance request."""
        try:
            user = get_current_user()
            data = request.get_json()
            
            emergency_type = data.get('emergency_type')
            location = data.get('location')
            description = data.get('description', '')
            
            response = await emergency_service.handle_emergency_request(
                user['id'], emergency_type, location, description, user
            )
            
            return jsonify(response)
            
        except Exception as e:
            logger.error(f"Emergency handling failed: {e}")
            return jsonify({
                'error': 'Emergency service unavailable',
                'fallback_number': '112'
            }), 500
    
    @app.route('/api/emergency/safety-briefing', methods=['POST'])
    async def get_safety_briefing():
        """Get safety briefing for a destination."""
        try:
            data = request.get_json()
            destination = data.get('destination')
            route_type = data.get('route_type', 'scenic')
            
            briefing = await emergency_service.get_safety_briefing(destination, route_type)
            return jsonify({'success': True, 'briefing': briefing})
            
        except Exception as e:
            logger.error(f"Safety briefing failed: {e}")
            return jsonify({'error': 'Safety briefing unavailable'}), 500
    
    @app.route('/api/emergency/setup-contacts', methods=['POST'])
    @login_required
    def setup_emergency_contacts():
        """Setup emergency contacts for a user."""
        try:
            user = get_current_user()
            data = request.get_json()
            
            contacts = data.get('contacts', [])
            result = emergency_service.setup_emergency_contacts(user['id'], contacts)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Emergency contacts setup failed: {e}")
            return jsonify({'error': 'Failed to setup emergency contacts'}), 500
    
    # Advanced trip features
    @app.route('/api/budget-optimization', methods=['POST'])
    @login_required
    async def optimize_budget():
        """AI-powered budget optimization."""
        try:
            user = get_current_user()
            data = request.get_json()
            
            trip_data = data.get('trip_data', {})
            budget_limit = data.get('budget_limit')
            preferences = data.get('preferences', {})
            
            # Get user travel preferences
            user_preferences = {}
            if user.get('travel_preferences'):
                try:
                    user_preferences = json.loads(user['travel_preferences'])
                except json.JSONDecodeError:
                    pass
            
            # Use Claude AI for budget optimization
            optimization_prompt = f"""
            Optimize this travel budget for maximum value:
            
            Trip Data: {trip_data}
            Budget Limit: €{budget_limit}
            User Preferences: {user_preferences}
            Current Preferences: {preferences}
            
            Provide specific recommendations for:
            1. Cost-saving opportunities
            2. Value-for-money alternatives
            3. Budget reallocation suggestions
            4. Seasonal timing optimizations
            5. Hidden cost awareness
            
            Return as JSON with optimized budget breakdown.
            """
            
            messages = [{'role': 'user', 'content': optimization_prompt}]
            response = await claude_service._make_request(
                messages, max_tokens=2000,
                system_prompt="You are a travel budget optimization expert. Provide practical, money-saving advice while maintaining trip quality."
            )
            
            try:
                optimization = json.loads(response) if response else {}
            except json.JSONDecodeError:
                optimization = {'recommendations': [response] if response else ['Budget optimization unavailable']}
            
            return jsonify({
                'success': True,
                'optimization': optimization
            })
            
        except Exception as e:
            logger.error(f"Budget optimization failed: {e}")
            return jsonify({'error': 'Budget optimization failed'}), 500
    
    @app.route('/api/restaurant-recommendations', methods=['POST'])
    @login_required
    async def get_personalized_restaurants():
        """Get AI-personalized restaurant recommendations."""
        try:
            user = get_current_user()
            data = request.get_json()
            
            location = data.get('location', {})
            preferences = data.get('preferences', {})
            budget = data.get('budget', 'medium')
            
            # Get user travel preferences
            user_preferences = {}
            if user.get('travel_preferences'):
                try:
                    user_preferences = json.loads(user['travel_preferences'])
                except json.JSONDecodeError:
                    pass
            
            # Use Claude AI for personalized recommendations
            recommendations_prompt = f"""
            Recommend restaurants for this traveler:
            
            Location: {location}
            Budget: {budget}
            Preferences: {preferences}
            User History: {user_preferences}
            
            Provide 5-10 specific restaurant recommendations with:
            1. Name and type of cuisine
            2. Why it matches their preferences
            3. Price range and signature dishes
            4. Best time to visit
            5. Any special tips
            
            Focus on authentic, highly-rated places that match their travel style.
            """
            
            messages = [{'role': 'user', 'content': recommendations_prompt}]
            response = await claude_service._make_request(
                messages, max_tokens=2000,
                system_prompt="You are a local food expert with deep knowledge of European restaurants. Provide authentic, personalized recommendations."
            )
            
            return jsonify({
                'success': True,
                'recommendations': response or 'Restaurant recommendations unavailable'
            })
            
        except Exception as e:
            logger.error(f"Restaurant recommendations failed: {e}")
            return jsonify({'error': 'Restaurant recommendations failed'}), 500
    
    # Language assistance
    @app.route('/api/translate', methods=['POST'])
    async def translate_text():
        """AI-powered translation assistance."""
        try:
            data = request.get_json()
            text = data.get('text', '')
            target_language = data.get('target_language', 'english')
            context = data.get('context', 'travel')
            
            translation_prompt = f"""
            Translate this travel-related text to {target_language}:
            "{text}"
            
            Context: {context}
            
            Provide:
            1. Direct translation
            2. Pronunciation guide if helpful
            3. Cultural context if relevant
            4. Alternative phrasings if appropriate
            """
            
            messages = [{'role': 'user', 'content': translation_prompt}]
            response = await claude_service._make_request(
                messages, max_tokens=1000,
                system_prompt="You are a multilingual travel assistant. Provide accurate translations with cultural context."
            )
            
            return jsonify({
                'success': True,
                'translation': response or 'Translation unavailable'
            })
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return jsonify({'error': 'Translation service unavailable'}), 500
    
    logger.info("Enhanced application initialized with all new features")
    return app

# Create the enhanced app instance
app = create_enhanced_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
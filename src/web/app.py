"""
Enhanced Flask application with AI features, user accounts, and advanced functionality.
"""
import os
import json
import asyncio
from typing import List
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
# from ..services.booking_service import BookingService  # Replaced with Amadeus
from ..services.foursquare_service import FoursquareService

# Import new services and features
from ..core.database import get_database, get_user_manager, get_trip_manager
from ..web.auth_routes import auth_bp, login_required, get_current_user
from ..services.claude_ai_service import get_claude_service
from ..services.weather_service import get_weather_service
from ..services.social_service import get_social_service
from ..services.emergency_service import get_emergency_service
from ..services.memory_service import get_memory_service
from ..services.opentripmap_service import get_opentripmap_service
from ..services.amadeus_service import get_amadeus_service
from ..core.exceptions import TravelPlannerException, ValidationError

# Configure logging
configure_logging(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    json_logs=os.getenv('FLASK_ENV') == 'production'
)

logger = structlog.get_logger(__name__)
security_logger = SecurityLogger()

def get_category_from_kinds(kinds: List[str]) -> str:
    """Convert OpenTripMap kinds to display category."""
    if not kinds:
        return 'Attraction'
    
    # Map kinds to user-friendly categories
    kind_mapping = {
        'religion': 'Religious Site',
        'churches': 'Church',
        'museums': 'Museum',
        'monuments': 'Monument',
        'architecture': 'Architecture',
        'historic': 'Historic Site',
        'cultural': 'Cultural Site',
        'bridges': 'Bridge',
        'castles': 'Castle',
        'palaces': 'Palace',
        'squares': 'Square',
        'parks': 'Park'
    }
    
    # Find first matching category
    for kind in kinds:
        if kind in kind_mapping:
            return kind_mapping[kind]
    
    # Default fallback
    return kinds[0].title().replace('_', ' ') if kinds else 'Attraction'

def create_app() -> Flask:
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
    # booking_service = BookingService()  # Replaced with Amadeus
    foursquare_service = FoursquareService()
    claude_service = get_claude_service()
    weather_service = get_weather_service()
    social_service = get_social_service()
    emergency_service = get_emergency_service()
    memory_service = get_memory_service()
    opentripmap_service = get_opentripmap_service()
    amadeus_service = get_amadeus_service()
    
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
    def plan_trip():
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
            
            # Validate input - convert frontend data to expected format
            form_data = {
                'start_city': data.get('start_location', ''),
                'end_city': data.get('end_location', ''),
                'travel_days': 5,  # Default to 5 days
                'nights_at_destination': 2,  # Default
                'season': 'spring'  # Default season
            }
            
            result = validation_service.validate_trip_request(form_data)
            if not result.success:
                return jsonify({'error': result.error_message}), 400
            
            # Get the validated trip request from the validation result
            validated_trip_request = result.data
            
            # The validated request already has the correct format for the travel planner
            # Just use it directly since it matches the TripRequest model from core.models
            trip_request = validated_trip_request
            
            # Plan the trip using the correct method
            plan_result = travel_planner.generate_routes(trip_request)
            
            if not plan_result.success:
                return jsonify({'error': plan_result.error_message}), 500
            
            # The plan_result.data should contain the routes
            # Sanitize the data to handle JSON serialization issues (like Season enum)
            response_data = validation_service.sanitize_output(plan_result.data)
            
            # Save search to history
            try:
                session_id = session.get('session_id', 'anonymous')
                search_data = {
                    'start_location': data['start_location'],
                    'end_location': data['end_location'],
                    'route_types': data.get('route_types', []),
                    'results': response_data,
                    'timestamp': datetime.now().isoformat()
                }
                memory_service.save_search_history(user['id'] if user else None, session_id, search_data)
            except Exception as e:
                logger.warning(f"Failed to save search history: {e}")
            
            # Enhance with AI personalization if user is logged in and Claude is available
            if user and user_preferences and 'routes' in response_data:
                try:
                    # Get AI-enhanced route suggestions
                    for route in response_data.get('routes', []):
                        # AI enhancement would be done async, but for now we skip it to avoid errors
                        # ai_enhancements = await claude_service.analyze_travel_preferences({
                        #     'route_data': route,
                        #     'user_preferences': user_preferences,
                        #     'user_history': user
                        # })
                        # route['ai_suggestions'] = ai_enhancements
                        pass
                except Exception as e:
                    logger.warning(f"AI enhancement failed: {e}")
            
            return jsonify(response_data)
            
        except Exception as e:
            logger.error("Trip planning failed", error=str(e))
            return jsonify({'error': 'Trip planning service unavailable'}), 500
    
    @app.route('/api/trip-data', methods=['POST'])
    def get_trip_data():
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
                        try:
                            # Use Amadeus service - run async call properly
                            import asyncio
                            
                            # Create a proper async function to call Amadeus
                            async def get_amadeus_hotels():
                                async with amadeus_service:
                                    return await amadeus_service.find_hotels(city_coords, city_name)
                            
                            # Run the async call and get results
                            try:
                                hotels = asyncio.run(get_amadeus_hotels())
                                hotels_data[city_name] = hotels
                                
                                # Check if we got real data or fallback data
                                if hotels and hotels[0].get('source') == 'amadeus':
                                    logger.info(f"Successfully fetched {len(hotels)} REAL hotels from Amadeus for {city_name}")
                                else:
                                    logger.warning(f"Using {len(hotels)} FALLBACK hotels for {city_name} - Amadeus API returned no real data")
                                    
                            except Exception as e:
                                logger.warning(f"Amadeus API failed for {city_name}: {e}")
                                # Only use fallback if Amadeus fails
                                hotels_data[city_name] = amadeus_service._get_fallback_hotels(city_name, 10)
                                logger.warning(f"Using {len(hotels_data[city_name])} FALLBACK hotels for {city_name} due to API error")
                                
                        except Exception as e:
                            logger.error(f"Critical error fetching hotels for {city_name}: {e}")
                            # If everything fails, use fallback data
                            hotels_data[city_name] = amadeus_service._get_fallback_hotels(city_name, 10)
                        
                        # Fetch restaurants and activities
                        try:
                            # Use async methods for both Foursquare and OpenTripMap
                            async def get_combined_data():
                                # Get restaurants from Foursquare
                                restaurants = await foursquare_service.find_restaurants(city_coords, city_name, limit=10)
                                
                                # Get activities from OpenTripMap (better for attractions)
                                async with opentripmap_service:
                                    opentripmap_activities = await opentripmap_service.get_city_attractions(
                                        coordinates=city_coords,
                                        radius_km=5,
                                        limit=10,
                                        kinds='cultural,historic,architecture,museums,churches,monuments'
                                    )
                                
                                # Format OpenTripMap data to match expected format
                                formatted_activities = []
                                for attraction in opentripmap_activities:
                                    if attraction.get('xid'):  # Real OpenTripMap data
                                        formatted_activities.append({
                                            'name': attraction.get('name', 'Unknown Attraction'),
                                            'rating': attraction.get('rating', 4),
                                            'price_level': 0,  # Most attractions are free
                                            'address': f"{city_name}, {attraction.get('kinds', [])}",
                                            'category': get_category_from_kinds(attraction.get('kinds', [])),
                                            'website': attraction.get('wikipedia') or '',
                                            'url': attraction.get('wikipedia') or '',
                                            'hours': 'Check local listings',
                                            'photo': attraction.get('preview', {}).get('source', ''),
                                            'source': 'opentripmap'
                                        })
                                
                                # If no real OpenTripMap data, try Foursquare activities as backup
                                if not formatted_activities:
                                    foursquare_activities = await foursquare_service.find_activities(city_coords, city_name, limit=10)
                                    formatted_activities = foursquare_activities
                                
                                return restaurants, formatted_activities
                            
                            restaurants, activities = asyncio.run(get_combined_data())
                            
                            # Check if we got real data or fallback data
                            if restaurants and restaurants[0].get('source') == 'foursquare':
                                logger.info(f"Successfully fetched {len(restaurants)} REAL restaurants from Foursquare for {city_name}")
                            else:
                                logger.warning(f"Using {len(restaurants)} FALLBACK restaurants for {city_name} - Foursquare API returned no real data")
                                
                            if activities and activities[0].get('source') == 'opentripmap':
                                logger.info(f"Successfully fetched {len(activities)} REAL attractions from OpenTripMap for {city_name}")
                            elif activities and activities[0].get('source') == 'foursquare':
                                logger.info(f"Successfully fetched {len(activities)} REAL activities from Foursquare for {city_name}")
                            else:
                                logger.warning(f"Using {len(activities)} FALLBACK activities for {city_name} - Both APIs returned no real data")
                                
                        except Exception as e:
                            logger.warning(f"Combined API calls failed for {city_name}: {e}")
                            # Use fallback data if both APIs fail
                            restaurants = foursquare_service._get_fallback_restaurants(city_name, 10)
                            activities = foursquare_service._get_fallback_activities(city_name, 10)
                            logger.warning(f"Using {len(restaurants)} FALLBACK restaurants and {len(activities)} FALLBACK activities for {city_name} due to API errors")
                        
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
    
    # AI Assistant Chat API
    @app.route('/api/ai-chat', methods=['POST'])
    def ai_chat():
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
            try:
                # Use sync version since we're in a Flask route
                import asyncio
                try:
                    # Try to get running loop
                    loop = asyncio.get_running_loop()
                    # We're in an event loop, need to handle differently
                    response = "I'm currently unable to process your request. Please try again later."
                except RuntimeError:
                    # No running loop, can use asyncio.run
                    response = asyncio.run(claude_service.travel_chat_assistant(
                        user_message, chat_history, user_context
                    ))
            except Exception as e:
                logger.error(f"AI chat service error: {e}")
                # Provide fallback response
                response = "I'm currently unable to process your request. Please try again later."
            
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
    def save_trip():
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
    
    # Weather API endpoints
    @app.route('/api/weather/route', methods=['POST'])
    def get_route_weather():
        """Get weather for all cities in a route."""
        try:
            data = request.get_json()
            route_cities = data.get('cities', [])
            
            try:
                weather_data = weather_service.get_route_weather(route_cities)
                analysis = weather_service.analyze_travel_conditions(weather_data)
            except:
                # Fallback weather data
                weather_data = {}
                analysis = {'overall_conditions': 'unknown', 'recommendations': ['Weather data unavailable']}
            
            return jsonify({
                'success': True,
                'weather_data': weather_data,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Route weather failed: {e}")
            return jsonify({'error': 'Weather service unavailable'}), 500
    
    # AI Assistant Chat interface
    @app.route('/ai-assistant')
    def ai_assistant():
        """AI travel assistant chat interface."""
        return render_template('ai_assistant.html')
    
    # Travel insights page
    @app.route('/travel-insights')
    @login_required
    def travel_insights():
        """Travel insights and analytics page."""
        return render_template('travel_insights.html')
    
    @app.route('/api/travel-insights')
    @login_required
    def get_travel_insights():
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
                    try:
                        insights = claude_service.generate_travel_insights(analytics_dict)
                    except:
                        insights = "Travel insights are currently unavailable."
                    
                    return jsonify({
                        'success': True,
                        'insights': insights,
                        'analytics': analytics_dict
                    })
            
            return jsonify({'error': 'No travel data available'}), 404
            
        except Exception as e:
            logger.error("Travel insights failed", error=str(e))
            return jsonify({'error': 'Insights generation failed'}), 500
    
    # Photo analysis
    @app.route('/api/ai-photo-analysis', methods=['POST'])
    def analyze_photo():
        """Analyze photo for destination suggestions."""
        try:
            data = request.get_json()
            image_data = data.get('image_data')
            image_type = data.get('image_type', 'image/jpeg')
            photo_description = data.get('description', '')
            
            if not image_data and not photo_description:
                return jsonify({'error': 'Image data or photo description required'}), 400
            
            try:
                if image_data:
                    # Handle actual image analysis
                    suggestions = claude_service.analyze_photo_for_destinations(image_data=image_data)
                else:
                    # Handle text description fallback
                    suggestions = claude_service.analyze_photo_for_destinations(photo_description=photo_description)
            except Exception as e:
                logger.error(f"Photo analysis service error: {e}")
                suggestions = [{
                    "destination": "Analysis Unavailable", 
                    "country": "Europe", 
                    "description": "Photo analysis service is currently unavailable. Please try again later."
                }]
            
            return jsonify({
                'success': True,
                'destinations': suggestions
            })
            
        except Exception as e:
            logger.error("Photo analysis failed", error=str(e))
            return jsonify({'error': 'Photo analysis failed'}), 500
    
    # Memory and Session Management API
    @app.route('/api/session/save', methods=['POST'])
    def save_session_state():
        """Save current session state."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Get session ID from session or generate new one
            session_id = session.get('session_id')
            if not session_id:
                import secrets
                session_id = secrets.token_urlsafe(32)
                session['session_id'] = session_id
            
            user = get_current_user()
            user_id = user['id'] if user else None
            
            success = memory_service.save_session_state(user_id, session_id, data)
            
            if success:
                return jsonify({'success': True, 'message': 'Session state saved'})
            else:
                return jsonify({'error': 'Failed to save session state'}), 500
                
        except Exception as e:
            logger.error("Save session state failed", error=str(e))
            return jsonify({'error': 'Failed to save session state'}), 500
    
    @app.route('/api/session/restore', methods=['GET'])
    def restore_session_state():
        """Restore session state."""
        try:
            session_id = session.get('session_id')
            if not session_id:
                return jsonify({'state': None})
            
            state_data = memory_service.get_session_state(session_id)
            
            return jsonify({'state': state_data})
            
        except Exception as e:
            logger.error("Restore session state failed", error=str(e))
            return jsonify({'error': 'Failed to restore session state'}), 500
    
    @app.route('/api/trip-preparation/save', methods=['POST'])
    def save_trip_preparation():
        """Save trip preparation data."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No preparation data provided'}), 400
            
            session_id = session.get('session_id')
            if not session_id:
                import secrets
                session_id = secrets.token_urlsafe(32)
                session['session_id'] = session_id
            
            user = get_current_user()
            user_id = user['id'] if user else None
            
            prep_id = memory_service.save_trip_preparation(user_id, session_id, data)
            
            if prep_id:
                return jsonify({'success': True, 'prep_id': prep_id, 'message': 'Trip preparation saved'})
            else:
                return jsonify({'error': 'Failed to save trip preparation'}), 500
                
        except Exception as e:
            logger.error("Save trip preparation failed", error=str(e))
            return jsonify({'error': 'Failed to save trip preparation'}), 500
    
    @app.route('/api/trip-preparation/list', methods=['GET'])
    def get_trip_preparations():
        """Get all trip preparations for user."""
        try:
            session_id = session.get('session_id', 'anonymous')
            user = get_current_user()
            user_id = user['id'] if user else None
            
            preparations = memory_service.get_trip_preparations(user_id, session_id)
            
            return jsonify({'success': True, 'preparations': preparations})
            
        except Exception as e:
            logger.error("Get trip preparations failed", error=str(e))
            return jsonify({'error': 'Failed to get trip preparations'}), 500
    
    @app.route('/api/search-history', methods=['GET'])
    def get_search_history():
        """Get search history for user."""
        try:
            session_id = session.get('session_id', 'anonymous')
            user = get_current_user()
            user_id = user['id'] if user else None
            
            limit = int(request.args.get('limit', 20))
            history = memory_service.get_search_history(user_id, session_id, limit)
            
            return jsonify({'success': True, 'history': history})
            
        except Exception as e:
            logger.error("Get search history failed", error=str(e))
            return jsonify({'error': 'Failed to get search history'}), 500
    
    # OpenTripMap City and Attractions API endpoints
    @app.route('/api/cities/<country>', methods=['GET'])
    def get_cities_by_country(country):
        """Get comprehensive list of cities for a country."""
        try:
            if country.lower() not in ['france', 'italy', 'spain']:
                return jsonify({'error': 'Country not supported. Use: france, italy, or spain'}), 400
            
            # This would typically be cached or pre-loaded
            # For now, return fallback data immediately
            cities = opentripmap_service._get_fallback_cities(country)
            
            return jsonify({
                'success': True,
                'country': country,
                'cities': cities,
                'count': len(cities)
            })
            
        except Exception as e:
            logger.error(f"Get cities failed for {country}: {e}")
            return jsonify({'error': 'Failed to get cities'}), 500
    
    @app.route('/api/city-info', methods=['POST'])
    def get_city_info():
        """Get detailed information about a specific city."""
        try:
            data = request.get_json()
            city_name = data.get('city_name', '').strip()
            country_code = data.get('country_code', '').strip()
            
            if not city_name:
                return jsonify({'error': 'City name is required'}), 400
            
            # Use fallback data for immediate response
            city_info = opentripmap_service._get_fallback_city_info(city_name, country_code)
            
            return jsonify({
                'success': True,
                'city': city_info
            })
            
        except Exception as e:
            logger.error(f"Get city info failed: {e}")
            return jsonify({'error': 'Failed to get city information'}), 500
    
    @app.route('/api/city-attractions', methods=['POST'])
    def get_city_attractions():
        """Get attractions and points of interest for a city."""
        try:
            data = request.get_json()
            coordinates = data.get('coordinates', {})
            radius = data.get('radius_km', 10)
            limit = data.get('limit', 20)
            kinds = data.get('kinds', 'cultural,historic,architecture,museums')
            
            lat = coordinates.get('latitude')
            lon = coordinates.get('longitude')
            
            if not lat or not lon:
                return jsonify({'error': 'City coordinates are required'}), 400
            
            from ..core.models import Coordinates
            city_coords = Coordinates(latitude=lat, longitude=lon)
            
            # Use fallback data for immediate response
            attractions = opentripmap_service._get_fallback_attractions(city_coords, limit)
            
            return jsonify({
                'success': True,
                'attractions': attractions,
                'count': len(attractions)
            })
            
        except Exception as e:
            logger.error(f"Get city attractions failed: {e}")
            return jsonify({'error': 'Failed to get city attractions'}), 500
    
    @app.route('/api/collect-city-data', methods=['POST'])
    @login_required
    def collect_city_data():
        """Trigger comprehensive city data collection (admin only)."""
        try:
            user = get_current_user()
            if not user or user.get('role') != 'admin':
                return jsonify({'error': 'Admin access required'}), 403
            
            # This would trigger the background data collection
            # For now, return status
            return jsonify({
                'success': True,
                'message': 'City data collection initiated',
                'status': 'Data collection would run in background'
            })
            
        except Exception as e:
            logger.error(f"City data collection failed: {e}")
            return jsonify({'error': 'Failed to initiate data collection'}), 500
    
    logger.info("Enhanced application initialized with all new features")
    return app

# Create the enhanced app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
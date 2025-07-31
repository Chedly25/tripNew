"""
Production Flask application with proper security and error handling.
"""
import os
from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import BadRequest, InternalServerError
import structlog
from ..infrastructure.config import SecureConfigurationService
from ..infrastructure.database import DatabaseManager
from ..infrastructure.logging import configure_logging, SecurityLogger
from ..services.google_places_city_service import GooglePlacesCityService
from ..services.route_service import ProductionRouteService
from ..services.validation_service import ValidationService
from ..services.travel_planner import TravelPlannerServiceImpl
from ..core.exceptions import TravelPlannerException, ValidationError
from ..core.models import ServiceResult

# Configure logging first
configure_logging(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    json_logs=os.getenv('FLASK_ENV') == 'production'
)

logger = structlog.get_logger(__name__)
security_logger = SecurityLogger()


def create_app() -> Flask:
    """Application factory with dependency injection."""
    # Set template folder to the original location
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    # Security configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(32))
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None
    
    # Initialize services
    config_service = SecureConfigurationService()
    
    # Validate configuration on startup
    config_result = config_service.validate_configuration()
    if not config_result.success:
        logger.error("Configuration validation failed", 
                    error=config_result.error_message)
        if config_service.is_production():
            raise SystemExit("Invalid configuration in production")
    
    # Initialize database (would be PostgreSQL in production)
    # For demo, skip database initialization
    db_manager = None
    logger.info("Running in demo mode without database")
    
    # Initialize services with dependency injection
    city_service = GooglePlacesCityService()  # Uses Google Places API for dynamic discovery
    route_service = ProductionRouteService(config_service)
    validation_service = ValidationService()
    
    travel_planner = TravelPlannerServiceImpl(
        city_service, route_service, validation_service
    )
    
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
            "connect-src 'self' https: *.tile.openstreetmap.org api.openrouteservice.org; "
            "frame-src 'none'"
        )
        return response
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """Handle validation errors."""
        logger.warning("Validation error", error=str(e))
        return jsonify({'error': str(e)}), 400
    
    @app.errorhandler(TravelPlannerException)
    def handle_travel_planner_error(e):
        """Handle application-specific errors."""
        logger.error("Travel planner error", error=str(e))
        return jsonify({'error': 'Service temporarily unavailable'}), 500
    
    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        """Handle bad requests."""
        security_logger.log_validation_error("bad_request", {
            "path": request.path,
            "method": request.method
        })
        return jsonify({'error': 'Invalid request'}), 400
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        """Handle internal server errors."""
        logger.error("Internal server error", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/')
    def index():
        """Landing page."""
        try:
            return render_template('travel_planner_main.html')
        except Exception as e:
            logger.error("Template rendering failed", error=str(e))
            return "Service temporarily unavailable", 500
    
    @app.route('/results')
    def results():
        """Results page for displaying travel plans."""
        try:
            return render_template('travel_results_enhanced.html')
        except Exception as e:
            logger.error("Results template rendering failed", error=str(e))
            return "Service temporarily unavailable", 500
    
    @app.route('/trip-details')
    def trip_details():
        """Detailed trip preparation page."""
        try:
            return render_template('trip_details.html')
        except Exception as e:
            logger.error("Trip details template rendering failed", error=str(e))
            return "Service temporarily unavailable", 500
    
    @app.route('/api/trip-data', methods=['POST'])
    def get_trip_data():
        """Get detailed trip data including hotels, restaurants, and activities."""
        try:
            import asyncio
            from ..services.foursquare_service import FoursquareService
            from ..services.booking_service import BookingService
            
            data = request.get_json()
            if not data or 'cities' not in data:
                return jsonify({'error': 'Cities data required'}), 400
            
            cities = data['cities']
            
            async def fetch_trip_data():
                # Initialize services
                foursquare = FoursquareService()
                booking = BookingService()
                
                trip_data = {
                    'hotels': {},
                    'restaurants': {},
                    'activities': {}
                }
                
                # Get data for each city
                for city in cities:
                    city_name = city.get('name')
                    coordinates = city.get('coordinates')
                    
                    if not city_name or not coordinates:
                        continue
                    
                    from ..core.models import Coordinates
                    coord_obj = Coordinates(latitude=coordinates[0], longitude=coordinates[1])
                    
                    # Get hotels, restaurants, and activities concurrently
                    hotels_task = booking.find_hotels(coord_obj, city_name, limit=4)
                    restaurants_task = foursquare.find_restaurants(coord_obj, city_name, limit=6)
                    activities_task = foursquare.find_activities(coord_obj, city_name, limit=6)
                    
                    hotels, restaurants, activities = await asyncio.gather(
                        hotels_task, restaurants_task, activities_task
                    )
                    
                    trip_data['hotels'][city_name] = hotels
                    trip_data['restaurants'][city_name] = restaurants
                    trip_data['activities'][city_name] = activities
                
                # Close sessions
                await foursquare.close()
                await booking.close()
                
                return trip_data
            
            # Run the async function
            trip_data = asyncio.run(fetch_trip_data())
            
            return jsonify({
                'success': True,
                'data': trip_data
            })
            
        except Exception as e:
            logger.error("Trip data retrieval failed", error=str(e))
            return jsonify({'error': 'Failed to retrieve trip data'}), 500
    
    @app.route('/test')
    def test_frontend():
        """Test frontend functionality."""
        try:
            return render_template('../../../test_frontend.html')
        except Exception:
            # Return inline HTML if template fails
            return """
            <!DOCTYPE html>
            <html><head><title>Test</title></head>
            <body>
                <h1>App is running!</h1>
                <p>Backend is working. Form test:</p>
                <form action="/plan" method="post">
                    <input name="start_city" value="Aix-en-Provence" placeholder="Start">
                    <input name="end_city" value="Venice" placeholder="End">
                    <input type="hidden" name="travel_days" value="5">
                    <input type="hidden" name="nights_at_destination" value="2">
                    <input type="hidden" name="season" value="summer">
                    <input type="hidden" name="trip_type" value="home">
                    <button type="submit">Test</button>
                </form>
            </body></html>
            """
    
    @app.route('/plan', methods=['POST'])
    def plan_trip():
        """Main trip planning endpoint."""
        
        try:
            # Validate request data
            form_data = request.form.to_dict()
            validation_result = validation_service.validate_trip_request(form_data)
            
            if not validation_result.success:
                return jsonify({'error': validation_result.error_message}), 400
            
            trip_request = validation_result.data
            
            # Generate routes
            routes_result = travel_planner.generate_routes(trip_request)
            
            if not routes_result.success:
                logger.error("Route generation failed", 
                           error=routes_result.error_message)
                return jsonify({'error': 'Unable to generate routes'}), 500
            
            # Sanitize output data
            response_data = validation_service.sanitize_output(routes_result.data)
            
            # For testing, let's also render directly to results page
            return jsonify({
                'success': True,
                'data': response_data
            })
            
        except Exception as e:
            logger.error("Trip planning failed", error=str(e))
            return jsonify({'error': 'Service temporarily unavailable'}), 500
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        checks = {
            'database': False,  # No database in demo mode
            'config': config_result.success,
            'services': True
        }
        
        all_healthy = all(checks.values())
        status_code = 200 if all_healthy else 503
        
        return jsonify({
            'healthy': all_healthy,
            'checks': checks,
            'version': '2.0.0'
        }), status_code
    
    return app


def run_development():
    """Run development server."""
    app = create_app()
    app.run(host='0.0.0.0', port=5004, debug=True)


if __name__ == '__main__':
    run_development()
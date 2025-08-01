"""
API endpoints for enhanced trip features.
"""
from flask import Blueprint, request, jsonify, session
from datetime import datetime, date
import json
import structlog

from src.services.budget_service import BudgetService
from src.services.journal_service import JournalService
from src.services.packing_service import PackingService
from src.services.transportation_service import TransportationService
from src.services.emergency_service import get_emergency_service
from src.services.marketplace_service import MarketplaceService
from src.services.optimization_service import OptimizationService
from src.core.exceptions import ValidationError, ServiceError

logger = structlog.get_logger(__name__)

# Create blueprint
enhanced_bp = Blueprint('enhanced_features', __name__, url_prefix='/api/enhanced')

# Initialize services
budget_service = BudgetService()
journal_service = JournalService()
packing_service = PackingService()
transportation_service = TransportationService()
emergency_service = get_emergency_service()
marketplace_service = MarketplaceService()
optimization_service = OptimizationService()


def require_auth():
    """Check if user is authenticated."""
    if 'user_id' not in session:
        raise ValidationError("Authentication required")
    return session['user_id']


# Budget Tracking Endpoints
@enhanced_bp.route('/budget/expenses', methods=['POST'])
def add_expense():
    """Add a new expense."""
    try:
        user_id = require_auth()
        data = request.get_json()
        
        trip_id = data.get('trip_id')
        if not trip_id:
            return jsonify({'error': 'trip_id is required'}), 400
        
        expense_id = budget_service.add_expense(trip_id, user_id, data)
        return jsonify({'expense_id': expense_id, 'success': True})
        
    except (ValidationError, ServiceError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Add expense failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/budget/expenses/<int:trip_id>', methods=['GET'])
def get_trip_expenses(trip_id):
    """Get expenses for a trip."""
    try:
        require_auth()
        expenses = budget_service.get_trip_expenses(trip_id)
        return jsonify({'expenses': expenses})
        
    except Exception as e:
        logger.error(f"Get expenses failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/budget/summary/<int:trip_id>', methods=['GET'])
def get_budget_summary(trip_id):
    """Get budget summary for a trip."""
    try:
        require_auth()
        summary = budget_service.calculate_trip_budget_summary(trip_id)
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Get budget summary failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Travel Journal Endpoints
@enhanced_bp.route('/journal/entries', methods=['POST'])
def create_journal_entry():
    """Create a new journal entry."""
    try:
        user_id = require_auth()
        data = request.get_json()
        
        trip_id = data.get('trip_id')
        if not trip_id:
            return jsonify({'error': 'trip_id is required'}), 400
        
        entry_id = journal_service.create_entry(trip_id, user_id, data)
        return jsonify({'entry_id': entry_id, 'success': True})
        
    except (ValidationError, ServiceError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Create journal entry failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/journal/entries/<int:trip_id>', methods=['GET'])
def get_trip_journal(trip_id):
    """Get journal entries for a trip."""
    try:
        user_id = require_auth()
        include_private = request.args.get('include_private', 'false').lower() == 'true'
        
        entries = journal_service.get_trip_journal(trip_id, user_id, include_private)
        return jsonify({'entries': entries})
        
    except Exception as e:
        logger.error(f"Get journal entries failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/journal/diary/<int:trip_id>', methods=['GET'])
def generate_trip_diary(trip_id):
    """Generate complete trip diary."""
    try:
        require_auth()
        diary = journal_service.generate_trip_diary(trip_id)
        return jsonify(diary)
        
    except Exception as e:
        logger.error(f"Generate diary failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Packing Assistant Endpoints
@enhanced_bp.route('/packing/generate', methods=['POST'])
def generate_packing_list():
    """Generate a packing list."""
    try:
        user_id = require_auth()
        data = request.get_json()
        
        trip_id = data.get('trip_id')
        trip_data = data.get('trip_data', {})
        
        if not trip_id:
            return jsonify({'error': 'trip_id is required'}), 400
        
        list_id = packing_service.generate_packing_list(trip_id, user_id, trip_data)
        return jsonify({'list_id': list_id, 'success': True})
        
    except Exception as e:
        logger.error(f"Generate packing list failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/packing/lists/<int:trip_id>', methods=['GET'])
def get_packing_lists(trip_id):
    """Get packing lists for a trip."""
    try:
        user_id = require_auth()
        lists = packing_service.get_trip_packing_lists(trip_id, user_id)
        return jsonify({'packing_lists': lists})
        
    except Exception as e:
        logger.error(f"Get packing lists failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/packing/items/<int:list_id>/status', methods=['PUT'])
def update_packing_item_status(list_id):
    """Update packing item status."""
    try:
        user_id = require_auth()
        data = request.get_json()
        
        item_name = data.get('item_name')
        packed = data.get('packed', False)
        
        success = packing_service.update_item_status(list_id, user_id, item_name, packed)
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"Update item status failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Transportation Endpoints
@enhanced_bp.route('/transport/city/<city_name>', methods=['GET'])
def get_city_transportation(city_name):
    """Get transportation info for a city."""
    try:
        require_auth()
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        transport_data = transportation_service.get_city_transportation(city_name, force_refresh)
        return jsonify(transport_data)
        
    except Exception as e:
        logger.error(f"Get transportation failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/transport/route-options', methods=['POST'])
def calculate_route_options():
    """Calculate transportation route options."""
    try:
        require_auth()
        data = request.get_json()
        
        start = data.get('start')
        end = data.get('end')
        preferences = data.get('preferences', {})
        
        options = transportation_service.calculate_route_options(start, end, preferences)
        return jsonify({'options': options})
        
    except Exception as e:
        logger.error(f"Calculate route options failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Emergency Services Endpoints
@enhanced_bp.route('/emergency/contacts', methods=['GET'])
def get_emergency_contacts():
    """Get emergency contacts."""
    try:
        require_auth()
        country = request.args.get('country')
        service_type = request.args.get('service_type')
        
        contacts = emergency_service.get_official_emergency_contacts(country, service_type)
        return jsonify({'contacts': contacts})
        
    except Exception as e:
        logger.error(f"Get emergency contacts failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/emergency/safety-tips/<country>', methods=['GET'])
def get_safety_tips(country):
    """Get safety tips for a country."""
    try:
        require_auth()
        activity_type = request.args.get('activity_type')
        
        tips = emergency_service.get_safety_tips(country, activity_type)
        return jsonify(tips)
        
    except Exception as e:
        logger.error(f"Get safety tips failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Marketplace Endpoints
@enhanced_bp.route('/marketplace/experiences', methods=['GET'])
def search_experiences():
    """Search for local experiences."""
    try:
        require_auth()
        
        city = request.args.get('city')
        category = request.args.get('category')
        max_price = request.args.get('max_price', type=float)
        language = request.args.get('language')
        date_str = request.args.get('date')
        limit = request.args.get('limit', 20, type=int)
        
        date_filter = None
        if date_str:
            date_filter = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        experiences = marketplace_service.search_experiences(
            city, category, max_price, language, date_filter, limit
        )
        return jsonify({'experiences': experiences})
        
    except Exception as e:
        logger.error(f"Search experiences failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/marketplace/experiences', methods=['POST'])
def create_experience():
    """Create a new experience."""
    try:
        user_id = require_auth()
        data = request.get_json()
        
        experience_id = marketplace_service.create_experience(user_id, data)
        return jsonify({'experience_id': experience_id, 'success': True})
        
    except (ValidationError, ServiceError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Create experience failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/marketplace/experiences/<int:experience_id>/book', methods=['POST'])
def book_experience(experience_id):
    """Book an experience."""
    try:
        user_id = require_auth()
        data = request.get_json()
        
        booking_id = marketplace_service.book_experience(experience_id, user_id, data)
        return jsonify({'booking_id': booking_id, 'success': True})
        
    except (ValidationError, ServiceError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Book experience failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/marketplace/bookings', methods=['GET'])
def get_user_bookings():
    """Get user's bookings."""
    try:
        user_id = require_auth()
        status = request.args.get('status')
        
        bookings = marketplace_service.get_user_bookings(user_id, status)
        return jsonify({'bookings': bookings})
        
    except Exception as e:
        logger.error(f"Get bookings failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Optimization Endpoints
@enhanced_bp.route('/optimization/optimize/<int:trip_id>', methods=['POST'])
def optimize_itinerary(trip_id):
    """Optimize trip itinerary."""
    try:
        user_id = require_auth()
        optimization_params = request.get_json() or {}
        
        result = optimization_service.optimize_itinerary(trip_id, user_id, optimization_params)
        return jsonify(result)
        
    except (ValidationError, ServiceError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Optimize itinerary failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@enhanced_bp.route('/optimization/preferences', methods=['POST'])
def save_optimization_preferences():
    """Save user optimization preferences."""
    try:
        user_id = require_auth()
        data = request.get_json()
        
        preferences = data.get('preferences', {})
        trip_id = data.get('trip_id')
        
        success = optimization_service.save_user_preferences(user_id, preferences, trip_id)
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"Save preferences failed: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Utility endpoints
@enhanced_bp.route('/categories/expenses', methods=['GET'])
def get_expense_categories():
    """Get expense categories."""
    return jsonify({'categories': budget_service.get_expense_categories()})


@enhanced_bp.route('/categories/packing', methods=['GET'])
def get_packing_categories():
    """Get packing categories."""
    return jsonify({'categories': packing_service.get_categories()})


@enhanced_bp.route('/categories/experiences', methods=['GET'])
def get_experience_categories():
    """Get experience categories."""
    return jsonify({'categories': marketplace_service.get_categories()})


# Error handlers
@enhanced_bp.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({'error': str(e)}), 400


@enhanced_bp.errorhandler(ServiceError)
def handle_service_error(e):
    return jsonify({'error': str(e)}), 500
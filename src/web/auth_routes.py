"""
Authentication routes for user registration, login, and profile management.
"""
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
from functools import wraps
import re
from typing import Optional, Dict
import structlog
from ..core.database import get_user_manager, get_trip_manager

logger = structlog.get_logger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> tuple:
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def login_required(f):
    """Decorator to require user login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user() -> Optional[Dict]:
    """Get current logged in user."""
    if 'session_token' in session:
        user_manager = get_user_manager()
        return user_manager.get_user_by_session(session['session_token'])
    return None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'GET':
        return render_template('auth/register.html')
    
    data = request.get_json() if request.is_json else request.form
    
    # Validate input
    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    
    errors = []
    
    if not email or not validate_email(email):
        errors.append("Valid email address is required")
    
    if not username or len(username) < 3:
        errors.append("Username must be at least 3 characters long")
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append("Username can only contain letters, numbers, and underscores")
    
    password_valid, password_msg = validate_password(password)
    if not password_valid:
        errors.append(password_msg)
    
    if errors:
        if request.is_json:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        for error in errors:
            flash(error, 'error')
        return render_template('auth/register.html')
    
    # Create user
    user_manager = get_user_manager()
    user_id = user_manager.create_user(email, username, password, first_name, last_name)
    
    if user_id:
        # Create session
        session_token = user_manager.create_session(user_id)
        session['user_id'] = user_id
        session['username'] = username
        session['session_token'] = session_token
        
        logger.info(f"User registered successfully: {username}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Account created successfully',
                'user': {'id': user_id, 'username': username, 'email': email}
            })
        
        flash('Account created successfully! Welcome to Road Trip Planner!', 'success')
        return redirect(url_for('main.index'))
    else:
        error_msg = "Email or username already exists"
        if request.is_json:
            return jsonify({'error': error_msg}), 409
        flash(error_msg, 'error')
        return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    data = request.get_json() if request.is_json else request.form
    
    login_field = data.get('login', '').strip()
    password = data.get('password', '')
    
    if not login_field or not password:
        error_msg = "Email/username and password are required"
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return render_template('auth/login.html')
    
    user_manager = get_user_manager()
    user = user_manager.authenticate_user(login_field, password)
    
    if user:
        # Create session
        session_token = user_manager.create_session(user['id'])
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['session_token'] = session_token
        
        logger.info(f"User logged in successfully: {user['username']}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Logged in successfully',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name']
                }
            })
        
        flash(f'Welcome back, {user["first_name"] or user["username"]}!', 'success')
        return redirect(url_for('main.index'))
    else:
        error_msg = "Invalid email/username or password"
        if request.is_json:
            return jsonify({'error': error_msg}), 401
        flash(error_msg, 'error')
        return render_template('auth/login.html')

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """User logout."""
    if 'session_token' in session:
        user_manager = get_user_manager()
        user_manager.logout_user(session['session_token'])
    
    session.clear()
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    trip_manager = get_trip_manager()
    user_trips = trip_manager.get_user_trips(user['id'], limit=10)
    favorite_trips = trip_manager.get_favorite_trips(user['id'])
    
    return render_template('auth/profile.html', 
                         user=user, 
                         trips=user_trips, 
                         favorites=favorite_trips)

@auth_bp.route('/api/user')
@login_required
def get_user_info():
    """Get current user information via API."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify({
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'created_at': user['created_at'],
            'last_login': user['last_login']
        }
    })

@auth_bp.route('/api/trips')
@login_required
def get_user_trips():
    """Get user's saved trips via API."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    trip_manager = get_trip_manager()
    trips = trip_manager.get_user_trips(user['id'])
    
    return jsonify({
        'trips': trips,
        'total': len(trips)
    })

@auth_bp.route('/api/trips/save', methods=['POST'])
@login_required
def save_trip():
    """Save a trip via API."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    if not data or 'trip_data' not in data:
        return jsonify({'error': 'Trip data is required'}), 400
    
    trip_name = data.get('trip_name', f"Trip to {data['trip_data'].get('end_city', {}).get('name', 'Unknown')}")
    trip_data = data['trip_data']
    is_favorite = data.get('is_favorite', False)
    is_public = data.get('is_public', False)
    
    trip_manager = get_trip_manager()
    trip_id = trip_manager.save_trip(user['id'], trip_name, trip_data, is_favorite, is_public)
    
    return jsonify({
        'success': True,
        'trip_id': trip_id,
        'message': 'Trip saved successfully'
    })

@auth_bp.route('/api/trips/<int:trip_id>/favorite', methods=['POST'])
@login_required
def toggle_trip_favorite(trip_id):
    """Toggle favorite status of a trip."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    trip_manager = get_trip_manager()
    new_status = trip_manager.toggle_favorite(user['id'], trip_id)
    
    return jsonify({
        'success': True,
        'is_favorite': new_status,
        'message': 'Favorite status updated'
    })

@auth_bp.route('/api/trips/<int:trip_id>', methods=['DELETE'])
@login_required
def delete_trip(trip_id):
    """Delete a trip."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    trip_manager = get_trip_manager()
    success = trip_manager.delete_trip(user['id'], trip_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Trip deleted successfully'
        })
    else:
        return jsonify({'error': 'Trip not found or permission denied'}), 404
"""
Simplified Flask application that works without complex dependencies
"""
import os
from flask import Flask, render_template, request, jsonify
import json

def create_simple_app():
    """Create a simple working Flask app"""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config['SECRET_KEY'] = 'dev-key-123'
    
    @app.route('/')
    def index():
        """Simple landing page"""
        return render_template('travel_planner_main.html')
    
    @app.route('/results')
    def results():
        """Results page"""
        return render_template('travel_results_enhanced.html')
    
    @app.route('/plan_trip', methods=['POST'])
    def plan_trip():
        """Simplified trip planning endpoint"""
        try:
            data = request.get_json()
            print(f"Received form data: {data}")
            
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            # Validate required fields
            required_fields = ['start_city', 'end_city', 'duration', 'budget']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Parse duration range
            duration_range = data.get('duration', '7-10')
            duration_parts = duration_range.split('-')
            if len(duration_parts) >= 2:
                min_days = int(duration_parts[0])
                max_days = int(duration_parts[1].replace('+', ''))
                travel_days = (min_days + max_days) // 2
            else:
                travel_days = 7
            
            # Parse travel styles
            travel_style_raw = data.get('travel_style', 'scenic')
            travel_styles = [style.strip() for style in travel_style_raw.split(',') if style.strip()]
            primary_travel_style = travel_styles[0] if travel_styles else 'scenic'
            
            # Generate realistic route data
            start_city = data.get('start_city', '')
            end_city = data.get('end_city', '')
            
            # Route coordinates based on common European routes
            route_coords = get_route_coordinates(start_city, end_city)
            
            # Calculate realistic distances and costs
            distance = calculate_distance(start_city, end_city)
            duration_minutes = int((distance / 80) * 60)  # 80 km/h average
            fuel_cost = int((distance / 100) * 7 * 1.50)  # 7L/100km, €1.50/L
            
            # Create response
            response = {
                'success': True,
                'data': {
                    'routes': [{
                        'route_type': primary_travel_style,
                        'start_city': {'name': start_city, 'country': get_country(start_city)},
                        'end_city': {'name': end_city, 'country': get_country(end_city)},
                        'total_distance': distance,
                        'total_duration': duration_minutes,
                        'estimated_fuel_cost': fuel_cost,
                        'coordinates': route_coords,
                        'intermediate_cities': get_intermediate_cities(start_city, end_city)
                    }],
                    'trip_details': {
                        'duration_days': travel_days,
                        'season': 'summer',
                        'travel_style': primary_travel_style
                    },
                    'budget_info': get_budget_info(data.get('budget', 'mid-range'))
                }
            }
            
            print(f"Sending successful response for {start_city} to {end_city}")
            return jsonify(response)
            
        except Exception as e:
            print(f"Error in /plan_trip: {e}")
            return jsonify({'error': f'Trip planning failed: {str(e)}'}), 500
    
    return app

def get_route_coordinates(start_city, end_city):
    """Get route coordinates for common European routes"""
    routes = {
        ('Aix-en-Provence', 'Venice'): [
            [43.5263, 5.4454],   # Aix-en-Provence
            [43.7102, 7.2620],   # Nice
            [44.1069, 9.5108],   # Cinque Terre area
            [44.4949, 11.3426],  # Bologna
            [45.4408, 12.3155]   # Venice
        ],
        ('Paris', 'Rome'): [
            [48.8566, 2.3522],   # Paris
            [45.7640, 4.8357],   # Lyon
            [43.2965, 5.3698],   # Marseille
            [41.9028, 12.4964]   # Rome
        ],
        ('Barcelona', 'Prague'): [
            [41.3851, 2.1734],   # Barcelona
            [43.7710, 11.2480],  # Florence
            [46.0569, 14.5058],  # Ljubljana
            [50.0755, 14.4378]   # Prague
        ]
    }
    
    # Try direct route
    route_key = (start_city, end_city)
    if route_key in routes:
        return routes[route_key]
    
    # Try reverse
    reverse_key = (end_city, start_city)
    if reverse_key in routes:
        return list(reversed(routes[reverse_key]))
    
    # Default route for testing
    return routes[('Aix-en-Provence', 'Venice')]

def calculate_distance(start_city, end_city):
    """Calculate approximate distance between cities"""
    distances = {
        ('Aix-en-Provence', 'Venice'): 700,
        ('Paris', 'Rome'): 1400,
        ('Barcelona', 'Prague'): 1300,
        ('Berlin', 'Madrid'): 1900,
        ('Amsterdam', 'Vienna'): 1100
    }
    
    route_key = (start_city, end_city)
    if route_key in distances:
        return distances[route_key]
    
    reverse_key = (end_city, start_city)
    if reverse_key in distances:
        return distances[reverse_key]
    
    # Default distance
    return 700

def get_country(city_name):
    """Get country for a city"""
    countries = {
        'Aix-en-Provence': 'France',
        'Nice': 'France',
        'Paris': 'France',
        'Lyon': 'France',
        'Marseille': 'France',
        'Venice': 'Italy',
        'Rome': 'Italy',
        'Milan': 'Italy',
        'Florence': 'Italy',
        'Bologna': 'Italy',
        'Barcelona': 'Spain',
        'Madrid': 'Spain',
        'Prague': 'Czech Republic',
        'Vienna': 'Austria',
        'Berlin': 'Germany',
        'Munich': 'Germany',
        'Amsterdam': 'Netherlands',
        'Brussels': 'Belgium'
    }
    return countries.get(city_name, 'Europe')

def get_intermediate_cities(start_city, end_city):
    """Get intermediate cities for the route"""
    routes = {
        ('Aix-en-Provence', 'Venice'): [
            {'name': 'Nice', 'country': 'France'},
            {'name': 'Bologna', 'country': 'Italy'}
        ],
        ('Paris', 'Rome'): [
            {'name': 'Lyon', 'country': 'France'},
            {'name': 'Florence', 'country': 'Italy'}
        ]
    }
    
    route_key = (start_city, end_city)
    if route_key in routes:
        return routes[route_key]
    
    reverse_key = (end_city, start_city)
    if reverse_key in routes:
        return list(reversed(routes[reverse_key]))
    
    return [{'name': 'Intermediate City', 'country': 'Europe'}]

def get_budget_info(budget_range):
    """Get budget information"""
    budget_info = {
        'budget': {
            'daily_budget': 'EUR30-50',
            'accommodation': 'Hostels, budget hotels',
            'food': 'Local markets, street food'
        },
        'mid-range': {
            'daily_budget': 'EUR50-100',
            'accommodation': '3-star hotels, B&Bs',
            'food': 'Mix of restaurants and cafes'
        },
        'luxury': {
            'daily_budget': 'EUR100+',
            'accommodation': '4-5 star hotels',
            'food': 'Fine dining, exclusive venues'
        }
    }
    return budget_info.get(budget_range, budget_info['mid-range'])

if __name__ == '__main__':
    app = create_simple_app()
    print("Starting simplified travel planning app...")
    print("Visit http://localhost:5001 to test")
    app.run(debug=True, port=5001)
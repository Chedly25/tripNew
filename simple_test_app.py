#!/usr/bin/env python3
"""
Simple Flask app to test the /plan_trip endpoint
"""
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/plan_trip', methods=['POST'])
def plan_trip_test():
    """Test the /plan_trip endpoint with mock data"""
    try:
        data = request.get_json()
        print(f"Received form data: {data}")
        
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
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
        
        # Mock successful response
        mock_response = {
            'success': True,
            'data': {
                'routes': [{
                    'route_type': primary_travel_style,
                    'start_city': {'name': data.get('start_city', 'Start')},
                    'end_city': {'name': data.get('end_city', 'End')},
                    'total_distance': 700,
                    'total_duration': 525,  # minutes
                    'estimated_fuel_cost': 73,
                    'coordinates': [
                        [43.5263, 5.4454],   # Aix-en-Provence
                        [43.7102, 7.2620],   # Nice
                        [44.1069, 9.5108],   # Cinque Terre area
                        [44.4949, 11.3426],  # Bologna
                        [45.4408, 12.3155]   # Venice
                    ],
                    'intermediate_cities': [
                        {'name': 'Nice', 'country': 'France'},
                        {'name': 'Bologna', 'country': 'Italy'}
                    ]
                }],
                'trip_details': {
                    'duration_days': travel_days,
                    'season': 'summer',
                    'travel_style': primary_travel_style
                },
                'budget_info': {
                    'daily_budget': 'EUR50-100',
                    'accommodation': '3-star hotels, B&Bs'
                }
            }
        }
        
        print(f"Sending response: {json.dumps(mock_response, indent=2)}")
        return jsonify(mock_response)
        
    except Exception as e:
        print(f"Error in /plan_trip: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/')
def index():
    return """
    <h1>Flask Test App</h1>
    <p>POST to /plan_trip to test the endpoint</p>
    <pre>
    curl -X POST -H "Content-Type: application/json" \\
         -d '{"start_city":"Aix-en-Provence","end_city":"Venice","duration":"7-10","budget":"mid-range","travel_style":"cultural"}' \\
         http://localhost:5000/plan_trip
    </pre>
    """

if __name__ == '__main__':
    print("Starting simple Flask test app...")
    print("Test the /plan_trip endpoint at http://localhost:5000")
    app.run(debug=True, port=5000)
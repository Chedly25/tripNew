from src.web.app import create_app
import json

app = create_app()
with app.test_client() as client:
    form_data = {
        'start_city': 'Aix-en-Provence',
        'end_city': 'Venice',
        'travel_days': '5',
        'nights_at_destination': '2',
        'season': 'summer',
        'trip_type': 'home'
    }
    
    response = client.post('/plan', data=form_data)
    result = response.get_json()
    
    if result and result.get('success'):
        routes = result.get('data', {}).get('routes', [])
        if routes:
            print("FIRST ROUTE DETAILS:")
            route = routes[0]
            print(f"Name: {route['name']}")
            print(f"Intermediate cities: {len(route['intermediate_cities'])}")
            for i, city in enumerate(route['intermediate_cities']):
                print(f"  {i+1}. {city}")
            print(f"Start city structure: {route['start_city']}")
            print(f"End city structure: {route['end_city']}")
    else:
        print("ERROR:", result)
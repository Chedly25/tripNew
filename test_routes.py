from src.web.app import create_app

app = create_app()
with app.test_client() as client:
    # Test the route planning endpoint
    form_data = {
        'start_city': 'Aix-en-Provence',
        'end_city': 'Venice',
        'travel_days': '5',
        'nights_at_destination': '2',
        'season': 'summer',
        'trip_type': 'home'
    }
    
    print("Testing route planning...")
    response = client.post('/plan', data=form_data)
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        try:
            result = response.get_json()
            if result and result.get('success'):
                routes = result.get('data', {}).get('routes', [])
                print(f'SUCCESS: Generated {len(routes)} routes')
                for i, route in enumerate(routes, 1):
                    print(f'  Route {i}: {route.get("name", "Unknown")} ({route.get("total_distance_km", 0)}km)')
            else:
                print(f'ERROR: {result.get("error", "Unknown error") if result else "No response data"}')
        except Exception as e:
            print(f'ERROR parsing response: {e}')
            print(f'Raw response: {response.data.decode()[:200]}...')
    else:
        print(f'ERROR: Status {response.status_code}')
        print(f'Response: {response.data.decode()[:200]}...')
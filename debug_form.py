from src.web.app import create_app

app = create_app()
with app.test_client() as client:
    print("Testing form submission...")
    
    # Test the route planning endpoint with exact form data
    form_data = {
        'start_city': 'Aix-en-Provence',
        'end_city': 'Venice',
        'travel_days': '5',
        'nights_at_destination': '2',
        'season': 'summer',
        'trip_type': 'home'
    }
    
    response = client.post('/plan', data=form_data)
    print(f'Response Status: {response.status_code}')
    
    if response.status_code == 200:
        result = response.get_json()
        print(f'Success: {result.get("success")}')
        if result and result.get('success'):
            data = result.get('data', {})
            routes = data.get('routes', [])
            print(f'Number of routes: {len(routes)}')
            if routes:
                print('First route structure:')
                first_route = routes[0]
                for key in first_route.keys():
                    print(f'  {key}: {type(first_route[key])}')
        else:
            print(f'Error: {result.get("error")}')
    else:
        print(f'Error response: {response.data.decode()}')
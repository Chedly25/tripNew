"""
Test environment variables in Flask app context
"""
import os

# Set credentials for testing
os.environ['AMADEUS_CLIENT_ID'] = 'SD5SUkyySqflaZC8gFOwEVKeXsAbfSRZ'
os.environ['AMADEUS_CLIENT_SECRET'] = 'zpwLbkjctXUnfaiB'
os.environ['FOURSQUARE_API_KEY'] = 'VLWY02FCX44U25TLQB243URQIIZX1Q0USJ521ZZ0SLQXG4R3'

def test_flask_env_vars():
    """Test environment variables in Flask app context."""
    print("Testing Environment Variables in Flask App Context")
    print("=" * 55)
    
    # Test environment variables before Flask app creation
    print("Before Flask app creation:")
    print(f"AMADEUS_CLIENT_ID: {os.getenv('AMADEUS_CLIENT_ID')}")
    print(f"AMADEUS_CLIENT_SECRET: {os.getenv('AMADEUS_CLIENT_SECRET', 'NOT_SET')[:10]}...")
    print(f"FOURSQUARE_API_KEY: {os.getenv('FOURSQUARE_API_KEY', 'NOT_SET')[:10]}...")
    
    # Create Flask app
    from src.web.app import create_app
    app = create_app()
    
    # Test environment variables after Flask app creation
    print("\nAfter Flask app creation:")
    print(f"AMADEUS_CLIENT_ID: {os.getenv('AMADEUS_CLIENT_ID')}")
    print(f"AMADEUS_CLIENT_SECRET: {os.getenv('AMADEUS_CLIENT_SECRET', 'NOT_SET')[:10]}...")
    print(f"FOURSQUARE_API_KEY: {os.getenv('FOURSQUARE_API_KEY', 'NOT_SET')[:10]}...")
    
    # Test service instances
    print("\nService instances:")
    from src.services.amadeus_service import get_amadeus_service
    from src.services.foursquare_service import FoursquareService
    
    amadeus_service = get_amadeus_service()
    foursquare_service = FoursquareService()
    
    print(f"Amadeus service client_id: {amadeus_service.client_id}")
    print(f"Amadeus service client_secret: {amadeus_service.client_secret[:10] if amadeus_service.client_secret else 'NOT_SET'}...")
    print(f"Foursquare service api_key: {foursquare_service.api_key[:10] if foursquare_service.api_key else 'NOT_SET'}...")
    
    # Test API calls within Flask context
    with app.app_context():
        print("\nWithin Flask app context:")
        print(f"AMADEUS_CLIENT_ID: {os.getenv('AMADEUS_CLIENT_ID')}")
        print(f"AMADEUS_CLIENT_SECRET: {os.getenv('AMADEUS_CLIENT_SECRET', 'NOT_SET')[:10]}...")
        
        # Test if service can authenticate
        import asyncio
        
        async def test_auth():
            try:
                async with amadeus_service:
                    success = await amadeus_service._get_access_token()
                    if success:
                        print("✅ Amadeus authentication SUCCESS in Flask context!")
                        return True
                    else:
                        print("❌ Amadeus authentication FAILED in Flask context!")
                        return False
            except Exception as e:
                print(f"❌ Amadeus authentication ERROR in Flask context: {e}")
                return False
        
        auth_result = asyncio.run(test_auth())
        
        if auth_result:
            print("The issue is NOT with environment variables or Flask context")
        else:
            print("The issue IS with environment variables or Flask context")

if __name__ == "__main__":
    test_flask_env_vars()
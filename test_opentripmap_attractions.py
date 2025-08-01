"""
Test OpenTripMap API for real attractions in Venice
"""
import os
import asyncio
import json

# Set OpenTripMap API key
os.environ['OPENTRIPMAP_API_KEY'] = '5ae2e3f221c38a28845f05b695632f298c9cd7dcec52ac9251a5f7fd'

from src.services.opentripmap_service import get_opentripmap_service
from src.core.models import Coordinates

async def test_opentripmap_attractions():
    """Test OpenTripMap API for Venice attractions."""
    print("Testing OpenTripMap API for Venice Attractions")
    print("=" * 50)
    
    service = get_opentripmap_service()
    
    # Venice coordinates
    venice_coords = Coordinates(latitude=45.4408, longitude=12.3155)
    
    print(f"API Key: {service.api_key[:20]}..." if service.api_key else "No API key found")
    print(f"Venice coordinates: {venice_coords.latitude}, {venice_coords.longitude}")
    
    try:
        async with service:
            print("\n1. Testing attractions search...")
            attractions = await service.get_city_attractions(
                coordinates=venice_coords,
                radius_km=5,
                limit=10,
                kinds='cultural,historic,architecture,museums,churches'
            )
            
            print(f"Found {len(attractions)} attractions:")
            for i, attraction in enumerate(attractions[:5], 1):
                print(f"\n{i}. {attraction.get('name', 'Unknown')}")
                print(f"   Kinds: {attraction.get('kinds', [])}")
                print(f"   Rating: {attraction.get('rating', 'N/A')}")
                print(f"   Distance: {attraction.get('distance', 'N/A')} m")
                print(f"   XID: {attraction.get('xid', 'N/A')}")
                
                # Check if it's real OpenTripMap data
                if attraction.get('xid'):
                    print("   [SUCCESS] REAL OPENTRIPMAP DATA!")
                else:
                    print("   [FALLBACK] Fallback data")
            
            # Test getting detailed info for first attraction
            if attractions and attractions[0].get('xid'):
                print(f"\n2. Testing detailed attraction info...")
                xid = attractions[0]['xid']
                details = await service.get_attraction_details(xid)
                
                if details:
                    print(f"Detailed info for {details.get('name', 'Unknown')}:")
                    print(f"   Description: {details.get('wikipedia_extracts', {}).get('text', 'No description')[:200]}...")
                    print(f"   Address: {details.get('address', {})}")
                    print(f"   Image: {details.get('image', 'No image')}")
                    print("   [SUCCESS] DETAILED DATA AVAILABLE!")
                
            # Save results
            results = {
                'attractions': attractions,
                'test_timestamp': str(asyncio.get_event_loop().time())
            }
            
            with open('opentripmap_venice_test.json', 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to opentripmap_venice_test.json")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nOpenTripMap Venice Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_opentripmap_attractions())
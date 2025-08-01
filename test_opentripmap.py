"""
Test script for OpenTripMap API integration.
This will test the API with the provided key and collect sample city data.
"""
import os
import asyncio
import json
from datetime import datetime

# Set the API key for testing
os.environ['OPENTRIPMAP_API_KEY'] = '5ae2e3f221c38a28845f05b695632f298c9cd7dcec52ac9251a5f7fd'

from src.services.opentripmap_service import OpenTripMapService
from src.core.models import Coordinates


async def test_opentripmap_functionality():
    """Test OpenTripMap API with the provided key."""
    print("🗺️  Testing OpenTripMap API Integration")
    print("=" * 50)
    
    service = OpenTripMapService()
    results = {}
    
    async with service:
        # Test 1: Get city information
        print("\n📍 Test 1: Getting city information...")
        cities_to_test = [
            ('Paris', 'FR'),
            ('Rome', 'IT'),
            ('Barcelona', 'ES')
        ]
        
        results['city_info'] = {}
        for city, country in cities_to_test:
            print(f"   Getting info for {city}, {country}...")
            city_info = await service.get_city_info(city, country)
            results['city_info'][f"{city}_{country}"] = city_info
            print(f"   ✅ {city}: Population {city_info.get('population', 'N/A')}")
        
        # Test 2: Get attractions for Paris
        print("\n🏛️  Test 2: Getting attractions for Paris...")
        paris_coords = Coordinates(latitude=48.8566, longitude=2.3522)
        attractions = await service.get_city_attractions(
            paris_coords, 
            radius_km=5, 
            limit=20,
            kinds='cultural,historic,museums'
        )
        results['paris_attractions'] = attractions
        print(f"   ✅ Found {len(attractions)} attractions in Paris")
        
        # Show top 5 attractions
        for i, attraction in enumerate(attractions[:5]):
            print(f"      {i+1}. {attraction.get('name', 'Unknown')} (Rating: {attraction.get('rating', 'N/A')})")
        
        # Test 3: Get cities in France (sample)
        print("\n🇫🇷 Test 3: Getting cities in France...")
        french_cities = await service.get_cities_in_country('france', limit=100)
        results['french_cities'] = french_cities
        print(f"   ✅ Found {len(french_cities)} cities in France")
        
        # Show top 10 cities
        for i, city in enumerate(french_cities[:10]):
            print(f"      {i+1}. {city.get('name', 'Unknown')} (Types: {', '.join(city.get('types', []))})")
        
        # Test 4: Get comprehensive data for all three countries (limited)
        print("\n🌍 Test 4: Getting comprehensive city data...")
        all_cities = await service.search_cities_comprehensive()
        results['all_cities_summary'] = {
            country: len(cities) for country, cities in all_cities.items()
        }
        
        for country, cities in all_cities.items():
            print(f"   ✅ {country.title()}: {len(cities)} cities")
        
        # Test 5: Get detailed attraction info
        print("\n🔍 Test 5: Getting detailed attraction information...")
        if attractions and attractions[0].get('xid'):
            first_attraction_xid = attractions[0]['xid']
            print(f"   Getting details for XID: {first_attraction_xid}")
            details = await service.get_attraction_details(first_attraction_xid)
            results['attraction_details'] = details
            if details:
                print(f"   ✅ {details.get('name', 'Unknown')}")
                print(f"      Description: {details.get('info', {}).get('descr', 'No description')[:100]}...")
            else:
                print("   ❌ No details available")
    
    # Save results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'opentripmap_test_results_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Test results saved to: {filename}")
    print("\n🎉 OpenTripMap API testing completed!")
    
    return results


async def collect_major_european_cities():
    """Collect comprehensive data for major European cities."""
    print("\n🏙️  Collecting Major European Cities Data")
    print("=" * 50)
    
    service = OpenTripMapService()
    
    # Major cities with coordinates
    major_cities = {
        'france': [
            {'name': 'Paris', 'lat': 48.8566, 'lon': 2.3522},
            {'name': 'Lyon', 'lat': 45.7640, 'lon': 4.8357},
            {'name': 'Marseille', 'lat': 43.2965, 'lon': 5.3698},
            {'name': 'Nice', 'lat': 43.7102, 'lon': 7.2620},
            {'name': 'Toulouse', 'lat': 43.6047, 'lon': 1.4442},
            {'name': 'Strasbourg', 'lat': 48.5734, 'lon': 7.7521},
            {'name': 'Bordeaux', 'lat': 44.8378, 'lon': -0.5792},
            {'name': 'Nantes', 'lat': 47.2184, 'lon': -1.5536},
            {'name': 'Lille', 'lat': 50.6292, 'lon': 3.0573},
            {'name': 'Rennes', 'lat': 48.1173, 'lon': -1.6778},
        ],
        'italy': [
            {'name': 'Rome', 'lat': 41.9028, 'lon': 12.4964},
            {'name': 'Milan', 'lat': 45.4642, 'lon': 9.1900},
            {'name': 'Naples', 'lat': 40.8518, 'lon': 14.2681},
            {'name': 'Turin', 'lat': 45.0703, 'lon': 7.6869},
            {'name': 'Florence', 'lat': 43.7696, 'lon': 11.2558},
            {'name': 'Venice', 'lat': 45.4408, 'lon': 12.3155},
            {'name': 'Bologna', 'lat': 44.4949, 'lon': 11.3426},
            {'name': 'Genoa', 'lat': 44.4056, 'lon': 8.9463},
            {'name': 'Palermo', 'lat': 38.1157, 'lon': 13.3615},
            {'name': 'Catania', 'lat': 37.5079, 'lon': 15.0830},
        ],
        'spain': [
            {'name': 'Madrid', 'lat': 40.4168, 'lon': -3.7038},
            {'name': 'Barcelona', 'lat': 41.3851, 'lon': 2.1734},
            {'name': 'Valencia', 'lat': 39.4699, 'lon': -0.3763},
            {'name': 'Seville', 'lat': 37.3891, 'lon': -5.9845},
            {'name': 'Zaragoza', 'lat': 41.6488, 'lon': -0.8891},
            {'name': 'Malaga', 'lat': 36.7213, 'lon': -4.4214},
            {'name': 'Murcia', 'lat': 37.9922, 'lon': -1.1307},
            {'name': 'Palma', 'lat': 39.5696, 'lon': 2.6502},
            {'name': 'Bilbao', 'lat': 43.2627, 'lon': -2.9253},
            {'name': 'Granada', 'lat': 37.1773, 'lon': -3.5986},
        ]
    }
    
    enhanced_data = {}
    
    async with service:
        for country, cities in major_cities.items():
            print(f"\n🌍 Processing {country.title()}...")
            enhanced_data[country] = []
            
            for i, city in enumerate(cities, 1):
                print(f"   {i}/{len(cities)} Processing {city['name']}...")
                
                # Get city info
                city_info = await service.get_city_info(city['name'])
                
                # Get attractions
                coords = Coordinates(latitude=city['lat'], longitude=city['lon'])
                attractions = await service.get_city_attractions(
                    coords,
                    radius_km=10,
                    limit=15,
                    kinds='cultural,historic,architecture,museums,monuments'
                )
                
                enhanced_city = {
                    'name': city['name'],
                    'country': country,
                    'coordinates': {'latitude': city['lat'], 'longitude': city['lon']},
                    'info': city_info,
                    'attractions_count': len(attractions),
                    'top_attractions': attractions[:10],
                    'last_updated': datetime.now().isoformat()
                }
                
                enhanced_data[country].append(enhanced_city)
                print(f"      ✅ Found {len(attractions)} attractions")
                
                # Rate limiting - be respectful to the API
                await asyncio.sleep(0.5)
    
    # Save enhanced data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'enhanced_european_cities_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(enhanced_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Enhanced city data saved to: {filename}")
    
    # Summary
    total_cities = sum(len(cities) for cities in enhanced_data.values())
    total_attractions = sum(
        sum(city['attractions_count'] for city in cities) 
        for cities in enhanced_data.values()
    )
    
    print(f"\n📊 Collection Summary:")
    print(f"   Total cities: {total_cities}")
    print(f"   Total attractions: {total_attractions}")
    
    return enhanced_data


if __name__ == "__main__":
    print("OpenTripMap API Test & Data Collection")
    print("====================================")
    
    # Run API functionality test first
    print("Running API functionality test...")
    asyncio.run(test_opentripmap_functionality())
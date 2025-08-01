"""
Script to collect comprehensive city data from OpenTripMap API
for France, Italy, and Spain.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.opentripmap_service import OpenTripMapService
import structlog

logger = structlog.get_logger(__name__)


async def collect_comprehensive_city_data():
    """Collect comprehensive city data for France, Italy, and Spain."""
    logger.info("Starting comprehensive city data collection...")
    
    service = OpenTripMapService()
    
    async with service:
        # Get comprehensive city data
        all_cities = await service.search_cities_comprehensive()
        
        # Create output directory
        output_dir = Path(__file__).parent.parent.parent / 'data'
        output_dir.mkdir(exist_ok=True)
        
        # Save raw data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for country, cities in all_cities.items():
            filename = f'cities_{country}_{timestamp}.json'
            filepath = output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cities, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(cities)} cities for {country} to {filename}")
        
        # Create consolidated file
        consolidated_file = output_dir / f'all_cities_{timestamp}.json'
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            json.dump(all_cities, f, indent=2, ensure_ascii=False)
        
        total_cities = sum(len(cities) for cities in all_cities.values())
        logger.info(f"Collection complete! Total cities: {total_cities}")
        logger.info(f"Data saved to: {consolidated_file}")
        
        return all_cities


async def collect_major_cities_with_attractions():
    """Collect major cities with their top attractions."""
    logger.info("Collecting major cities with attractions...")
    
    # Major cities to focus on
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
    
    service = OpenTripMapService()
    enhanced_cities = {}
    
    async with service:
        for country, cities in major_cities.items():
            enhanced_cities[country] = []
            
            for city in cities:
                logger.info(f"Processing {city['name']}, {country}")
                
                # Get city info
                from ..core.models import Coordinates
                coords = Coordinates(latitude=city['lat'], longitude=city['lon'])
                
                # Get attractions
                attractions = await service.get_city_attractions(
                    coords, 
                    radius_km=15, 
                    limit=20,
                    kinds='cultural,historic,architecture,museums,monuments'
                )
                
                enhanced_city = {
                    'name': city['name'],
                    'country': country,
                    'coordinates': {'latitude': city['lat'], 'longitude': city['lon']},
                    'attractions_count': len(attractions),
                    'top_attractions': attractions[:10],  # Top 10 attractions
                    'source': 'opentripmap_enhanced'
                }
                
                enhanced_cities[country].append(enhanced_city)
                
                # Rate limiting
                await asyncio.sleep(0.5)
        
        # Save enhanced data
        output_dir = Path(__file__).parent.parent.parent / 'data'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        enhanced_file = output_dir / f'enhanced_cities_{timestamp}.json'
        
        with open(enhanced_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_cities, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Enhanced cities data saved to: {enhanced_file}")
        
        return enhanced_cities


async def test_api_functionality():
    """Test OpenTripMap API functionality with sample queries."""
    logger.info("Testing OpenTripMap API functionality...")
    
    service = OpenTripMapService()
    
    async with service:
        # Test 1: Get city info
        paris_info = await service.get_city_info("Paris", "FR")
        logger.info(f"Paris info: {paris_info}")
        
        # Test 2: Get attractions near Paris
        if paris_info and paris_info['coordinates']:
            from ..core.models import Coordinates
            paris_coords = Coordinates(
                latitude=paris_info['coordinates']['latitude'],
                longitude=paris_info['coordinates']['longitude']
            )
            
            attractions = await service.get_city_attractions(paris_coords, radius_km=5, limit=10)
            logger.info(f"Found {len(attractions)} attractions near Paris")
            
            # Test 3: Get detailed info about first attraction
            if attractions and attractions[0].get('xid'):
                details = await service.get_attraction_details(attractions[0]['xid'])
                logger.info(f"Attraction details: {details}")
        
        # Test 4: Get cities in France (limited sample)
        french_cities = await service.get_cities_in_country("france", limit=50)
        logger.info(f"Found {len(french_cities)} cities in France (sample)")


if __name__ == "__main__":
    # Set up logging
    import structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        cache_logger_on_first_use=True,
    )
    
    print("OpenTripMap City Data Collection Script")
    print("=" * 50)
    print("1. Test API functionality")
    print("2. Collect comprehensive city data")
    print("3. Collect major cities with attractions")
    print("4. Run all")
    
    choice = input("Enter your choice (1-4): ").strip()
    
    if choice == "1":
        asyncio.run(test_api_functionality())
    elif choice == "2":
        asyncio.run(collect_comprehensive_city_data())
    elif choice == "3":
        asyncio.run(collect_major_cities_with_attractions())
    elif choice == "4":
        asyncio.run(test_api_functionality())
        asyncio.run(collect_major_cities_with_attractions())
        asyncio.run(collect_comprehensive_city_data())
    else:
        print("Invalid choice. Exiting.")
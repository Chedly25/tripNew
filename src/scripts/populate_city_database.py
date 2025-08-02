#!/usr/bin/env python3
"""
City Database Population Script

This script uses multiple free APIs to gather comprehensive city data:
- GeoNames API (free with registration)
- OpenStreetMap Nominatim (completely free)
- Wikidata API (free)
- UNESCO World Heritage API (free)

Run this to populate your database with rich European city data.
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.enhanced_city_service import get_enhanced_city_service
import structlog

logger = structlog.get_logger(__name__)


class CityDatabasePopulator:
    """Populates city database with comprehensive data from multiple free APIs."""
    
    def __init__(self):
        self.enhanced_service = get_enhanced_city_service()
        self.output_file = project_root / "data" / "european_cities_enhanced.json"
        self.ensure_data_directory()
    
    def ensure_data_directory(self):
        """Create data directory if it doesn't exist."""
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
    
    async def populate_database(self):
        """Main population process."""
        logger.info("Starting city database population...")
        
        async with self.enhanced_service:
            # Step 1: Get bulk European cities
            logger.info("Fetching bulk European city data...")
            bulk_cities = await self.enhanced_service.get_european_cities_bulk(limit=500)
            
            # Step 2: Enrich high-priority cities
            priority_cities = [
                'Paris', 'Rome', 'Barcelona', 'Madrid', 'London', 'Amsterdam',
                'Vienna', 'Prague', 'Berlin', 'Munich', 'Venice', 'Florence',
                'Nice', 'Zurich', 'Brussels', 'Lyon', 'Milan', 'Naples',
                'Lisbon', 'Porto', 'Athens', 'Budapest', 'Warsaw', 'Krakow'
            ]
            
            enriched_cities = []
            for city_name in priority_cities:
                logger.info(f"Enriching data for {city_name}...")
                
                try:
                    enrichment = await self.enhanced_service.enrich_city_data(city_name)
                    
                    enriched_city = {
                        'name': city_name,
                        'basic_info': enrichment.basic_info,
                        'population_data': enrichment.population_data,
                        'cultural_sites': enrichment.cultural_sites,
                        'unesco_sites': enrichment.unesco_sites,
                        'tourism_score': enrichment.tourism_score,
                        'enhanced': True,
                        'last_updated': str(asyncio.get_event_loop().time())
                    }
                    
                    enriched_cities.append(enriched_city)
                    
                    # Rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed to enrich {city_name}: {e}")
                    continue
            
            # Step 3: Combine and categorize all cities
            final_dataset = {
                'metadata': {
                    'generated_at': str(asyncio.get_event_loop().time()),
                    'total_cities': len(bulk_cities) + len(enriched_cities),
                    'enhanced_cities': len(enriched_cities),
                    'bulk_cities': len(bulk_cities),
                    'data_sources': [
                        'GeoNames', 'OpenStreetMap', 'Wikidata', 'UNESCO'
                    ]
                },
                'enhanced_cities': enriched_cities,
                'bulk_cities': bulk_cities,
                'city_types': self.categorize_cities(enriched_cities + bulk_cities)
            }
            
            # Step 4: Save to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(final_dataset, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Database populated! Saved {final_dataset['metadata']['total_cities']} cities to {self.output_file}")
            
            # Step 5: Generate summary
            self.print_summary(final_dataset)
    
    def categorize_cities(self, cities: List[Dict]) -> Dict[str, List[str]]:
        """Categorize cities by type and characteristics."""
        categories = {
            'capitals': [],
            'coastal': [],
            'mountain': [],
            'cultural_heritage': [],
            'unesco_sites': [],
            'large_cities': [],
            'small_towns': [],
            'wine_regions': [],
            'ski_resorts': []
        }
        
        for city in cities:
            name = city.get('name', '')
            basic_info = city.get('basic_info', {})
            population = basic_info.get('population', 0)
            feature_code = basic_info.get('feature_code', '')
            
            # Categorize based on available data
            if feature_code in ['PPLC', 'PPLA']:  # Capital or administrative center
                categories['capitals'].append(name)
            
            if population > 500000:
                categories['large_cities'].append(name)
            elif population < 50000:
                categories['small_towns'].append(name)
            
            if city.get('unesco_sites'):
                categories['unesco_sites'].append(name)
            
            if city.get('cultural_sites'):
                categories['cultural_heritage'].append(name)
        
        return categories
    
    def print_summary(self, dataset: Dict):
        """Print a summary of the populated database."""
        metadata = dataset['metadata']
        categories = dataset['city_types']
        
        print("\n" + "="*60)
        print("🌍 EUROPEAN CITY DATABASE POPULATION COMPLETE!")
        print("="*60)
        print(f"📊 Total Cities: {metadata['total_cities']}")
        print(f"✨ Enhanced Cities: {metadata['enhanced_cities']}")
        print(f"📍 Bulk Cities: {metadata['bulk_cities']}")
        print("\n📋 Categories:")
        
        for category, cities in categories.items():
            if cities:
                print(f"  {category.replace('_', ' ').title()}: {len(cities)} cities")
        
        print(f"\n💾 Data saved to: {self.output_file}")
        print("\n🎯 Next Steps:")
        print("1. Import this data into your city service")
        print("2. Add city type filtering to route generation")
        print("3. Use tourism scores for better recommendations")
        print("4. Integrate UNESCO sites into itineraries")
        print("="*60)


async def main():
    """Main execution function."""
    print("🚀 Starting European City Database Population...")
    print("📡 Using FREE APIs: GeoNames, OpenStreetMap, Wikidata, UNESCO")
    print("⏱️  This may take 5-10 minutes for comprehensive data...")
    
    # Check for GeoNames username
    geonames_user = os.getenv('GEONAMES_USERNAME')
    if not geonames_user:
        print("\n⚠️  WARNING: No GEONAMES_USERNAME environment variable found.")
        print("   Sign up at http://www.geonames.org/login for free API access")
        print("   The script will continue with limited GeoNames data.")
    
    populator = CityDatabasePopulator()
    await populator.populate_database()


if __name__ == "__main__":
    asyncio.run(main())
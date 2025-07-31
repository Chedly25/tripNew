"""
Seed database with comprehensive European cities data.
"""
import asyncio
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any
from ..src.models.database_models import City, Base
from ..src.infrastructure.database import DatabaseManager
from ..src.infrastructure.config import SecureConfigurationService


EUROPEAN_CITIES_DATA = [
    {
        "name": "Paris", "country": "FR", "country_name": "France",
        "latitude": 48.8566, "longitude": 2.3522, "population": 2140526,
        "region": "Île-de-France", "timezone": "Europe/Paris",
        "tourism_types": ["cultural", "romantic", "fashion", "culinary", "art"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 180,
        "is_tourist_destination": True
    },
    {
        "name": "Rome", "country": "IT", "country_name": "Italy",
        "latitude": 41.9028, "longitude": 12.4964, "population": 2872800,
        "region": "Lazio", "timezone": "Europe/Rome",
        "tourism_types": ["cultural", "historic", "religious", "culinary"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 150,
        "is_tourist_destination": True
    },
    {
        "name": "Barcelona", "country": "ES", "country_name": "Spain", 
        "latitude": 41.3851, "longitude": 2.1734, "population": 1620343,
        "region": "Catalonia", "timezone": "Europe/Madrid",
        "tourism_types": ["cultural", "architectural", "coastal", "culinary"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 140,
        "is_tourist_destination": True
    },
    {
        "name": "Amsterdam", "country": "NL", "country_name": "Netherlands",
        "latitude": 52.3676, "longitude": 4.9041, "population": 821752,
        "region": "North Holland", "timezone": "Europe/Amsterdam",
        "tourism_types": ["cultural", "canals", "museums", "nightlife"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 160,
        "is_tourist_destination": True
    },
    {
        "name": "Vienna", "country": "AT", "country_name": "Austria",
        "latitude": 48.2082, "longitude": 16.3738, "population": 1911191,
        "region": "Vienna", "timezone": "Europe/Vienna",
        "tourism_types": ["cultural", "classical_music", "imperial", "coffeehouse"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 130,
        "is_tourist_destination": True
    },
    {
        "name": "Prague", "country": "CZ", "country_name": "Czech Republic",
        "latitude": 50.0755, "longitude": 14.4378, "population": 1280508,
        "region": "Prague", "timezone": "Europe/Prague", 
        "tourism_types": ["cultural", "historic", "architectural", "beer"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 90,
        "is_tourist_destination": True
    },
    {
        "name": "Venice", "country": "IT", "country_name": "Italy",
        "latitude": 45.4408, "longitude": 12.3155, "population": 261905,
        "region": "Veneto", "timezone": "Europe/Rome",
        "tourism_types": ["romantic", "canals", "historic", "art"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 200,
        "is_tourist_destination": True
    },
    {
        "name": "Florence", "country": "IT", "country_name": "Italy",
        "latitude": 43.7696, "longitude": 11.2558, "population": 382258,
        "region": "Tuscany", "timezone": "Europe/Rome",
        "tourism_types": ["art", "renaissance", "cultural", "culinary"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 170,
        "is_tourist_destination": True
    },
    {
        "name": "Santorini", "country": "GR", "country_name": "Greece",
        "latitude": 36.3932, "longitude": 25.4615, "population": 15550,
        "region": "South Aegean", "timezone": "Europe/Athens",
        "tourism_types": ["romantic", "scenic", "coastal", "sunset"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 250,
        "is_tourist_destination": True
    },
    {
        "name": "Dubrovnik", "country": "HR", "country_name": "Croatia",
        "latitude": 42.6507, "longitude": 18.0944, "population": 41562,
        "region": "Dubrovnik-Neretva", "timezone": "Europe/Zagreb",
        "tourism_types": ["historic", "coastal", "cultural", "medieval"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 180,
        "is_tourist_destination": True
    },
    {
        "name": "Edinburgh", "country": "GB", "country_name": "United Kingdom",
        "latitude": 55.9533, "longitude": -3.1883, "population": 464990,
        "region": "Scotland", "timezone": "Europe/London",
        "tourism_types": ["historic", "cultural", "castles", "festivals"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 140,
        "is_tourist_destination": True
    },
    {
        "name": "Reykjavik", "country": "IS", "country_name": "Iceland",
        "latitude": 64.1466, "longitude": -21.9426, "population": 123246,
        "region": "Capital Region", "timezone": "Atlantic/Reykjavik",
        "tourism_types": ["nature", "northern_lights", "geothermal", "adventure"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 200,
        "is_tourist_destination": True
    },
    {
        "name": "Bruges", "country": "BE", "country_name": "Belgium",
        "latitude": 51.2093, "longitude": 3.2247, "population": 117073,
        "region": "West Flanders", "timezone": "Europe/Brussels",
        "tourism_types": ["medieval", "canals", "chocolate", "historic"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 120,
        "is_tourist_destination": True
    },
    {
        "name": "Salzburg", "country": "AT", "country_name": "Austria",
        "latitude": 47.8095, "longitude": 13.0550, "population": 145871,
        "region": "Salzburg", "timezone": "Europe/Vienna",
        "tourism_types": ["cultural", "classical_music", "historic", "mozart"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 140,
        "is_tourist_destination": True
    },
    {
        "name": "Copenhagen", "country": "DK", "country_name": "Denmark",
        "latitude": 55.6761, "longitude": 12.5683, "population": 602481,
        "region": "Capital Region", "timezone": "Europe/Copenhagen",
        "tourism_types": ["design", "hygge", "cycling", "culinary"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 170,
        "is_tourist_destination": True
    },
    {
        "name": "Stockholm", "country": "SE", "country_name": "Sweden",
        "latitude": 59.3293, "longitude": 18.0686, "population": 935619,
        "region": "Stockholm County", "timezone": "Europe/Stockholm",
        "tourism_types": ["design", "archipelago", "museums", "old_town"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 160,
        "is_tourist_destination": True
    },
    {
        "name": "Lisbon", "country": "PT", "country_name": "Portugal",
        "latitude": 38.7223, "longitude": -9.1393, "population": 505526,
        "region": "Lisbon", "timezone": "Europe/Lisbon",
        "tourism_types": ["historic", "trams", "fado", "coastal"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 110,
        "is_tourist_destination": True
    },
    {
        "name": "Porto", "country": "PT", "country_name": "Portugal",
        "latitude": 41.1579, "longitude": -8.6291, "population": 237591,
        "region": "Norte", "timezone": "Europe/Lisbon",
        "tourism_types": ["historic", "port_wine", "riverside", "azulejo"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 90,
        "is_tourist_destination": True
    },
    {
        "name": "Nice", "country": "FR", "country_name": "France",
        "latitude": 43.7102, "longitude": 7.2620, "population": 342522,
        "region": "Provence-Alpes-Côte d'Azur", "timezone": "Europe/Paris",
        "tourism_types": ["coastal", "riviera", "art", "promenade"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 160,
        "is_tourist_destination": True
    },
    {
        "name": "Aix-en-Provence", "country": "FR", "country_name": "France",
        "latitude": 43.5297, "longitude": 5.4474, "population": 143006,
        "region": "Provence-Alpes-Côte d'Azur", "timezone": "Europe/Paris",
        "tourism_types": ["cultural", "art", "markets", "fountains"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 130,
        "is_tourist_destination": True
    },
    {
        "name": "Lyon", "country": "FR", "country_name": "France",
        "latitude": 45.7640, "longitude": 4.8357, "population": 515695,
        "region": "Auvergne-Rhône-Alpes", "timezone": "Europe/Paris",
        "tourism_types": ["culinary", "renaissance", "silk", "traboules"],
        "tourist_season_peak": "spring", "average_hotel_price_eur": 120,
        "is_tourist_destination": True
    },
    {
        "name": "Milan", "country": "IT", "country_name": "Italy",
        "latitude": 45.4642, "longitude": 9.1900, "population": 1396059,
        "region": "Lombardy", "timezone": "Europe/Rome",
        "tourism_types": ["fashion", "design", "business", "shopping"],
        "tourist_season_peak": "autumn", "average_hotel_price_eur": 160,
        "is_tourist_destination": True
    },
    {
        "name": "Geneva", "country": "CH", "country_name": "Switzerland",
        "latitude": 46.2044, "longitude": 6.1432, "population": 201818,
        "region": "Geneva", "timezone": "Europe/Zurich",
        "tourism_types": ["international", "lake", "luxury", "watches"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 300,
        "is_tourist_destination": True
    },
    {
        "name": "Zurich", "country": "CH", "country_name": "Switzerland",
        "latitude": 47.3769, "longitude": 8.5417, "population": 415367,
        "region": "Zurich", "timezone": "Europe/Zurich",
        "tourism_types": ["business", "lake", "mountains", "banking"],
        "tourist_season_peak": "summer", "average_hotel_price_eur": 280,
        "is_tourist_destination": True
    },
    {
        "name": "Munich", "country": "DE", "country_name": "Germany",
        "latitude": 48.1351, "longitude": 11.5820, "population": 1471508,
        "region": "Bavaria", "timezone": "Europe/Berlin",
        "tourism_types": ["beer", "oktoberfest", "bavarian", "alps"],
        "tourist_season_peak": "autumn", "average_hotel_price_eur": 140,
        "is_tourist_destination": True
    }
]


async def seed_cities_database(db_manager: DatabaseManager):
    """Seed the database with European cities data."""
    print("Seeding cities database...")
    
    with db_manager.get_session() as session:
        # Check if cities already exist
        existing_count = session.query(City).count()
        if existing_count > 0:
            print(f"Cities already seeded ({existing_count} cities found)")
            return
        
        # Insert cities
        cities_created = 0
        for city_data in EUROPEAN_CITIES_DATA:
            city = City(**city_data)
            session.add(city)
            cities_created += 1
        
        session.commit()
        print(f"Successfully seeded {cities_created} cities")


if __name__ == "__main__":
    # Run seeding script
    config = SecureConfigurationService()
    db_config = config.get_database_config()
    db_manager = DatabaseManager(db_config)
    
    # Create tables
    db_manager.create_tables()
    
    # Seed cities
    asyncio.run(seed_cities_database(db_manager))
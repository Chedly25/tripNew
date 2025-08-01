"""
Core interfaces defining service contracts.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .models import City, TravelRoute, TripRequest, ServiceResult, Coordinates


class CityRepository(ABC):
    """Interface for city data access."""
    
    @abstractmethod
    def get_city_by_name(self, name: str) -> Optional[City]:
        pass
    
    @abstractmethod
    def find_cities_by_type(self, city_type: str) -> List[City]:
        pass
    
    @abstractmethod
    def find_cities_in_region(self, region: str) -> List[City]:
        pass
    
    @abstractmethod
    def find_cities_near_route(self, start: Coordinates, end: Coordinates, 
                              max_deviation_km: float = 50) -> List[City]:
        pass


class RouteService(ABC):
    """Interface for route calculation services."""
    
    @abstractmethod
    def calculate_route(self, start: City, end: City, 
                       waypoints: List[City] = None) -> ServiceResult:
        pass
    
    @abstractmethod
    def optimize_multi_city_route(self, cities: List[City]) -> ServiceResult:
        pass


class WeatherService(ABC):
    """Interface for weather information services."""
    
    @abstractmethod
    def get_weather_forecast(self, coordinates: Coordinates, 
                           days: int = 5) -> ServiceResult:
        pass


class AccommodationService(ABC):
    """Interface for accommodation search services."""
    
    @abstractmethod
    def search_hotels(self, city: City, checkin_date: str, 
                     nights: int, guests: int = 2) -> ServiceResult:
        pass


class TravelPlannerService(ABC):
    """Main service interface for travel planning."""
    
    @abstractmethod
    def generate_routes(self, request: TripRequest) -> ServiceResult:
        pass
    
    @abstractmethod
    def get_route_details(self, route_id: str) -> ServiceResult:
        pass


class ConfigurationService(ABC):
    """Interface for configuration management."""
    
    @abstractmethod
    def get_api_key(self, service_name: str) -> Optional[str]:
        pass
    
    @abstractmethod
    def get_database_config(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def validate_configuration(self) -> ServiceResult:
        pass
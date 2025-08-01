"""
Core domain models for the travel planning system.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class RouteType(Enum):
    FASTEST = "fastest"
    SCENIC = "scenic"
    CULTURAL = "cultural"
    CULINARY = "culinary"
    ADVENTURE = "adventure"
    ROMANTIC = "romantic"
    BUDGET = "budget"
    WELLNESS = "wellness"
    HIDDEN_GEMS = "hidden_gems"


class Season(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


@dataclass
class Coordinates:
    latitude: float
    longitude: float
    
    def __post_init__(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}")


@dataclass
class City:
    name: str
    coordinates: Coordinates
    country: str
    population: Optional[int] = None
    region: Optional[str] = None
    types: List[str] = None
    # Enhanced attributes for better route suggestions
    rating: Optional[float] = None
    unesco: bool = False
    elevation_m: Optional[int] = None
    climate: Optional[str] = None
    avg_temp_c: Optional[Dict[str, int]] = None
    specialties: List[str] = None
    best_months: List[int] = None
    accessibility: Optional[str] = None
    cost_level: Optional[str] = None
    tourist_density: Optional[str] = None
    unique_features: List[str] = None
    nearby_attractions: List[str] = None
    transport_links: List[str] = None
    ideal_stay_hours: Optional[int] = None
    walking_city: bool = True
    parking_difficulty: Optional[str] = None
    
    def __post_init__(self):
        if self.types is None:
            self.types = []
        if self.specialties is None:
            self.specialties = []
        if self.best_months is None:
            self.best_months = []
        if self.unique_features is None:
            self.unique_features = []
        if self.nearby_attractions is None:
            self.nearby_attractions = []
        if self.transport_links is None:
            self.transport_links = []


@dataclass
class RouteSegment:
    start: City
    end: City
    distance_km: float
    duration_hours: float
    description: Optional[str] = None


@dataclass
class TravelRoute:
    route_type: RouteType
    segments: List[RouteSegment]
    total_distance_km: float
    total_duration_hours: float
    intermediate_cities: List[City]
    description: str
    estimated_cost: Optional[float] = None
    
    @property
    def start_city(self) -> City:
        return self.segments[0].start if self.segments else None
    
    @property
    def end_city(self) -> City:
        return self.segments[-1].end if self.segments else None


@dataclass
class TripRequest:
    start_city: str
    end_city: str
    travel_days: int
    nights_at_destination: int
    season: Season
    claude_api_key: Optional[str] = None
    
    def __post_init__(self):
        if self.travel_days < 1 or self.travel_days > 30:
            raise ValueError(f"Invalid travel days: {self.travel_days}")
        if self.nights_at_destination < 0 or self.nights_at_destination > self.travel_days:
            raise ValueError(f"Invalid nights at destination: {self.nights_at_destination}")


@dataclass
class ServiceResult:
    success: bool
    data: Any = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    @classmethod
    def success_result(cls, data: Any = None):
        return cls(success=True, data=data)
    
    @classmethod
    def error_result(cls, message: str, code: Optional[str] = None):
        return cls(success=False, error_message=message, error_code=code)
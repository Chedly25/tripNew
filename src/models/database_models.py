"""
Production database models with proper relationships and indexing.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    
    # Relationships
    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    api_usage = relationship("APIUsage", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.email}>"


class City(Base):
    """City master data with comprehensive information."""
    __tablename__ = 'cities'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    country = Column(String(2), nullable=False, index=True)  # ISO country code
    country_name = Column(String(100), nullable=False)
    region = Column(String(100))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    population = Column(Integer)
    timezone = Column(String(50))
    elevation_m = Column(Integer)
    
    # Tourism data
    is_tourist_destination = Column(Boolean, default=False)
    tourism_types = Column(JSON)  # ['cultural', 'scenic', 'culinary', etc.]
    tourist_season_peak = Column(String(20))  # 'summer', 'winter', etc.
    average_hotel_price_eur = Column(Float)
    
    # Geographic indexes for spatial queries
    __table_args__ = (
        Index('idx_city_coordinates', 'latitude', 'longitude'),
        Index('idx_city_country_name', 'country', 'name'),
    )
    
    def __repr__(self):
        return f"<City {self.name}, {self.country_name}>"


class Trip(Base):
    """User trip planning record."""
    __tablename__ = 'trips'
    
    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Trip details
    name = Column(String(200))
    start_city_id = Column(Integer, ForeignKey('cities.id'), nullable=False)
    end_city_id = Column(Integer, ForeignKey('cities.id'), nullable=False)
    travel_days = Column(Integer, nullable=False)
    nights_at_destination = Column(Integer, nullable=False)
    season = Column(String(20), nullable=False)
    
    # Trip metadata
    status = Column(String(20), default='planning')  # planning, confirmed, completed, cancelled
    total_distance_km = Column(Float)
    estimated_cost_eur = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    departure_date = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="trips")
    start_city = relationship("City", foreign_keys=[start_city_id])
    end_city = relationship("City", foreign_keys=[end_city_id])
    routes = relationship("Route", back_populates="trip", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="trip")
    
    def __repr__(self):
        return f"<Trip {self.name or self.public_id}>"


class Route(Base):
    """Calculated route for a trip."""
    __tablename__ = 'routes'
    
    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey('trips.id'), nullable=False)
    route_type = Column(String(50), nullable=False)  # fastest, scenic, cultural, etc.
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Route data
    total_distance_km = Column(Float, nullable=False)
    total_duration_hours = Column(Float, nullable=False)
    estimated_fuel_cost_eur = Column(Float)
    route_geometry = Column(Text)  # GeoJSON or encoded polyline
    waypoints = Column(JSON)  # List of intermediate city IDs
    
    # External API data
    openroute_data = Column(JSON)
    google_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    is_selected = Column(Boolean, default=False)
    
    # Relationships
    trip = relationship("Trip", back_populates="routes")
    route_segments = relationship("RouteSegment", back_populates="route", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Route {self.route_type} for trip {self.trip_id}>"


class RouteSegment(Base):
    """Individual segment of a route between two cities."""
    __tablename__ = 'route_segments'
    
    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey('routes.id'), nullable=False)
    segment_order = Column(Integer, nullable=False)
    
    start_city_id = Column(Integer, ForeignKey('cities.id'), nullable=False)
    end_city_id = Column(Integer, ForeignKey('cities.id'), nullable=False)
    
    distance_km = Column(Float, nullable=False)
    duration_hours = Column(Float, nullable=False)
    segment_geometry = Column(Text)
    driving_instructions = Column(JSON)
    
    # Relationships
    route = relationship("Route", back_populates="route_segments")
    start_city = relationship("City", foreign_keys=[start_city_id])
    end_city = relationship("City", foreign_keys=[end_city_id])
    
    __table_args__ = (
        Index('idx_route_segment_order', 'route_id', 'segment_order'),
    )


class WeatherForecast(Base):
    """Cached weather forecasts for cities."""
    __tablename__ = 'weather_forecasts'
    
    id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey('cities.id'), nullable=False)
    forecast_date = Column(DateTime, nullable=False)
    
    # Weather data
    temperature_c = Column(Float)
    feels_like_c = Column(Float)
    humidity_percent = Column(Integer)
    wind_speed_ms = Column(Float)
    precipitation_mm = Column(Float)
    weather_description = Column(String(100))
    weather_icon = Column(String(10))
    
    # Data source and freshness
    data_source = Column(String(50), default='openweather')
    fetched_at = Column(DateTime, default=func.now())
    
    # Relationships
    city = relationship("City")
    
    __table_args__ = (
        Index('idx_weather_city_date', 'city_id', 'forecast_date'),
        Index('idx_weather_freshness', 'fetched_at'),
    )


class Accommodation(Base):
    """Hotels and accommodations data."""
    __tablename__ = 'accommodations'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(200), unique=True, index=True)  # Google Place ID, Booking.com ID, etc.
    city_id = Column(Integer, ForeignKey('cities.id'), nullable=False)
    
    # Basic info
    name = Column(String(200), nullable=False)
    address = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Hotel data
    star_rating = Column(Integer)
    review_rating = Column(Float)
    review_count = Column(Integer)
    price_level = Column(Integer)  # 1-4 scale
    hotel_type = Column(String(50))  # hotel, hostel, apartment, etc.
    
    # Amenities and features
    amenities = Column(JSON)
    room_types = Column(JSON)
    
    # Pricing (cached)
    average_price_eur = Column(Float)
    price_updated_at = Column(DateTime)
    
    # Data source
    data_source = Column(String(50), default='google_places')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    city = relationship("City")
    bookings = relationship("Booking", back_populates="accommodation")
    
    __table_args__ = (
        Index('idx_accommodation_city_rating', 'city_id', 'review_rating'),
        Index('idx_accommodation_coordinates', 'latitude', 'longitude'),
    )


class Restaurant(Base):
    """Restaurant and dining data."""
    __tablename__ = 'restaurants'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(200), unique=True, index=True)
    city_id = Column(Integer, ForeignKey('cities.id'), nullable=False)
    
    # Basic info
    name = Column(String(200), nullable=False)
    address = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Restaurant data
    cuisine_types = Column(JSON)
    price_level = Column(Integer)  # 1-4 scale
    review_rating = Column(Float)
    review_count = Column(Integer)
    
    # Operating info
    opening_hours = Column(JSON)
    phone_number = Column(String(20))
    website = Column(String(200))
    
    # Data source
    data_source = Column(String(50), default='google_places')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    city = relationship("City")
    
    __table_args__ = (
        Index('idx_restaurant_city_rating', 'city_id', 'review_rating'),
        Index('idx_restaurant_cuisine', 'city_id', 'cuisine_types'),
    )


class Booking(Base):
    """User bookings for accommodations."""
    __tablename__ = 'bookings'
    
    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    trip_id = Column(Integer, ForeignKey('trips.id'), nullable=False)
    accommodation_id = Column(Integer, ForeignKey('accommodations.id'), nullable=False)
    
    # Booking details
    check_in_date = Column(DateTime, nullable=False)
    check_out_date = Column(DateTime, nullable=False)
    guests = Column(Integer, default=2)
    room_type = Column(String(100))
    
    # Pricing
    total_price_eur = Column(Float)
    currency = Column(String(3), default='EUR')
    
    # Booking status
    status = Column(String(20), default='planned')  # planned, booked, confirmed, cancelled
    booking_reference = Column(String(100))
    external_booking_url = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    trip = relationship("Trip", back_populates="bookings")
    accommodation = relationship("Accommodation", back_populates="bookings")


class APIUsage(Base):
    """Track API usage for billing and rate limiting."""
    __tablename__ = 'api_usage'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # API call details
    api_service = Column(String(50), nullable=False)  # openroute, openweather, google_places
    endpoint = Column(String(100), nullable=False)
    http_status = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Request details
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    request_id = Column(String(36))
    
    # Cost tracking
    estimated_cost_cents = Column(Integer)  # Cost in cents/hundredths
    
    # Timestamp
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_usage")
    
    __table_args__ = (
        Index('idx_api_usage_service_date', 'api_service', 'created_at'),
        Index('idx_api_usage_user_date', 'user_id', 'created_at'),
        Index('idx_api_usage_ip_date', 'ip_address', 'created_at'),
    )


class SystemHealth(Base):
    """System health and monitoring data."""
    __tablename__ = 'system_health'
    
    id = Column(Integer, primary_key=True)
    service_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # healthy, degraded, down
    
    # Metrics
    response_time_ms = Column(Integer)
    error_rate_percent = Column(Float)
    throughput_requests_per_minute = Column(Integer)
    
    # Additional data
    details = Column(JSON)
    
    # Timestamp
    checked_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_health_service_time', 'service_name', 'checked_at'),
    )
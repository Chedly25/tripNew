"""
Input validation service with comprehensive security checks.
"""
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import structlog
from ..core.models import TripRequest, Season, ServiceResult
from ..core.exceptions import ValidationError
from ..infrastructure.logging import SecurityLogger

logger = structlog.get_logger(__name__)
security_logger = SecurityLogger()


class ValidationService:
    """Comprehensive input validation with security focus."""
    
    def __init__(self):
        self.max_trip_days = 30
        self.max_string_length = 100
        self.allowed_characters = re.compile(r'^[a-zA-Z0-9\s\-\'\.\,àáâäãåąčćđèéêëěìíîïńñòóôöõøùúûüýÿžšş]+$')
    
    def validate_trip_request(self, form_data: Dict[str, Any]) -> ServiceResult:
        """Validate complete trip request with security checks."""
        errors = []
        
        try:
            # Validate city names
            start_city = self._validate_city_name(form_data.get('start_city', ''))
            if not start_city:
                errors.append("Invalid start city")
            
            end_city = self._validate_city_name(form_data.get('end_city', ''))
            if not end_city:
                errors.append("Invalid end city")
            
            # Validate travel days
            travel_days = self._validate_travel_days(form_data.get('travel_days'))
            if travel_days is None:
                errors.append("Invalid travel days")
            
            # Validate nights at destination
            nights = self._validate_nights(form_data.get('nights_at_destination'), travel_days)
            if nights is None:
                errors.append("Invalid nights at destination")
            
            # Validate season
            season = self._validate_season(form_data.get('season'))
            if not season:
                errors.append("Invalid season")
            
            # Validate API key if provided
            api_key_valid = self._validate_api_key(form_data.get('claude_api_key', ''))
            
            if errors:
                security_logger.log_validation_error("trip_request", {
                    "errors": errors,
                    "form_keys": list(form_data.keys())
                })
                return ServiceResult.error_result(f"Validation failed: {'; '.join(errors)}")
            
            # Create validated request object
            trip_request = TripRequest(
                start_city=start_city,
                end_city=end_city,
                travel_days=travel_days,
                nights_at_destination=nights,
                season=season,
                claude_api_key=form_data.get('claude_api_key') if api_key_valid else None
            )
            
            return ServiceResult.success_result(trip_request)
            
        except Exception as e:
            logger.error("Validation error", error=str(e))
            return ServiceResult.error_result("Validation failed")
    
    def _validate_city_name(self, city_name: Any) -> Optional[str]:
        """Validate and sanitize city name."""
        if not isinstance(city_name, str):
            return None
        
        # Basic sanitization
        city_name = city_name.strip()
        
        if not city_name or len(city_name) > self.max_string_length:
            return None
        
        # Check for suspicious patterns
        if not self.allowed_characters.match(city_name):
            security_logger.log_validation_error("suspicious_city_name", {
                "input": city_name[:50]  # Log first 50 chars only
            })
            return None
        
        # Prevent common injection patterns
        dangerous_patterns = ['<script', 'javascript:', 'data:', 'vbscript:', 'onload=']
        city_lower = city_name.lower()
        for pattern in dangerous_patterns:
            if pattern in city_lower:
                security_logger.log_validation_error("injection_attempt", {
                    "pattern": pattern,
                    "input": city_name[:50]
                })
                return None
        
        return city_name
    
    def _validate_travel_days(self, travel_days: Any) -> Optional[int]:
        """Validate travel days parameter."""
        try:
            if isinstance(travel_days, str):
                travel_days = int(travel_days)
            
            if not isinstance(travel_days, int):
                return None
            
            if travel_days < 1 or travel_days > self.max_trip_days:
                return None
            
            return travel_days
            
        except (ValueError, TypeError):
            return None
    
    def _validate_nights(self, nights: Any, travel_days: Optional[int]) -> Optional[int]:
        """Validate nights at destination."""
        try:
            if isinstance(nights, str):
                nights = int(nights)
            
            if not isinstance(nights, int):
                return None
            
            if nights < 0:
                return None
            
            if travel_days and nights > travel_days:
                return None
            
            return nights
            
        except (ValueError, TypeError):
            return None
    
    def _validate_season(self, season: Any) -> Optional[Season]:
        """Validate season parameter."""
        if not isinstance(season, str):
            return None
        
        season_lower = season.lower().strip()
        
        try:
            return Season(season_lower)
        except ValueError:
            return None
    
    def _validate_api_key(self, api_key: Any) -> bool:
        """Validate API key format without exposing it."""
        if not isinstance(api_key, str):
            return False
        
        api_key = api_key.strip()
        
        # Basic format validation (Anthropic keys start with 'sk-ant-')
        if not api_key:
            return True  # Empty is allowed
        
        if len(api_key) < 20 or len(api_key) > 200:
            return False
        
        # Check for suspicious patterns in API key
        if not re.match(r'^[a-zA-Z0-9\-_]+$', api_key):
            security_logger.log_validation_error("invalid_api_key_format", {
                "length": len(api_key)
            })
            return False
        
        return True
    
    def sanitize_output(self, data: Any) -> Any:
        """Sanitize data for output to prevent XSS and handle JSON serialization."""
        if isinstance(data, str):
            # Basic HTML escaping
            return (data
                   .replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))
        
        elif isinstance(data, Enum):
            # Convert enums to their string values
            return data.value
        
        elif hasattr(data, '__dict__'):
            # Handle dataclass and other objects with __dict__
            result = {}
            for key, value in data.__dict__.items():
                if not key.startswith('_'):  # Skip private attributes
                    result[key] = self.sanitize_output(value)
            return result
        
        elif isinstance(data, dict):
            return {k: self.sanitize_output(v) for k, v in data.items()}
        
        elif isinstance(data, list):
            return [self.sanitize_output(item) for item in data]
        
        elif isinstance(data, (datetime, timedelta)):
            # Convert datetime objects to ISO strings
            return data.isoformat() if hasattr(data, 'isoformat') else str(data)
        
        return data
    
    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate geographic coordinates."""
        try:
            return (-90 <= lat <= 90) and (-180 <= lon <= 180)
        except (ValueError, TypeError):
            return False
"""
Custom exceptions for the travel planning system.
"""


class TravelPlannerException(Exception):
    """Base exception for travel planner errors."""
    pass


class ValidationError(TravelPlannerException):
    """Raised when input validation fails."""
    pass


class ConfigurationError(TravelPlannerException):
    """Raised when configuration is invalid or missing."""
    pass


class ExternalServiceError(TravelPlannerException):
    """Raised when external service calls fail."""
    def __init__(self, message: str, service_name: str, status_code: int = None):
        super().__init__(message)
        self.service_name = service_name
        self.status_code = status_code


class DatabaseError(TravelPlannerException):
    """Raised when database operations fail."""
    pass


class AuthenticationError(TravelPlannerException):
    """Raised when authentication fails."""
    pass


class RateLimitError(TravelPlannerException):
    """Raised when rate limits are exceeded."""
    pass


class ServiceError(TravelPlannerException):
    """Raised when service operations fail."""
    pass
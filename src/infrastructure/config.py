"""
Secure configuration management.
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from ..core.interfaces import ConfigurationService
from ..core.exceptions import ConfigurationError
from ..core.models import ServiceResult


@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 5
    max_overflow: int = 10
    
    def get_connection_string(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class APIConfig:
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 60


class SecureConfigurationService(ConfigurationService):
    """Production-ready configuration service with security best practices."""
    
    def __init__(self):
        self._api_keys = {}
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from environment variables."""
        # API keys should only come from environment
        self._api_keys = {
            'anthropic': os.getenv('ANTHROPIC_API_KEY'),
            'openweather': os.getenv('OPENWEATHER_API_KEY'),
            'google_maps': os.getenv('GOOGLE_MAPS_API_KEY'),
            'openroute': os.getenv('OPENROUTE_API_KEY')
        }
        
        # Remove None values
        self._api_keys = {k: v for k, v in self._api_keys.items() if v is not None}
    
    def get_api_key(self, service_name: str) -> Optional[str]:
        """Get API key for a service. Never log or expose keys."""
        key = self._api_keys.get(service_name.lower())
        if not key:
            return None
        
        # Validate key format (basic check)
        if len(key.strip()) < 10:
            return None
            
        return key.strip()
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration from environment."""
        try:
            return DatabaseConfig(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5432)),
                database=os.getenv('DB_NAME', 'travel_planner'),
                username=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', ''),
                pool_size=int(os.getenv('DB_POOL_SIZE', 5)),
                max_overflow=int(os.getenv('DB_MAX_OVERFLOW', 10))
            )
        except (ValueError, TypeError) as e:
            raise ConfigurationError(f"Invalid database configuration: {e}")
    
    def get_api_config(self) -> APIConfig:
        """Get API configuration."""
        try:
            return APIConfig(
                timeout=int(os.getenv('API_TIMEOUT', 30)),
                max_retries=int(os.getenv('API_MAX_RETRIES', 3)),
                rate_limit_per_minute=int(os.getenv('API_RATE_LIMIT', 60))
            )
        except (ValueError, TypeError) as e:
            raise ConfigurationError(f"Invalid API configuration: {e}")
    
    def validate_configuration(self) -> ServiceResult:
        """Validate that required configuration is present."""
        errors = []
        
        # Check database config
        try:
            db_config = self.get_database_config()
            if not db_config.password:
                errors.append("Database password not configured")
        except ConfigurationError as e:
            errors.append(str(e))
        
        # Check for at least one API key
        if not self._api_keys:
            errors.append("No API keys configured")
        
        # Validate environment
        if not os.getenv('FLASK_ENV'):
            errors.append("FLASK_ENV not set")
        
        if errors:
            return ServiceResult.error_result(
                f"Configuration validation failed: {'; '.join(errors)}"
            )
        
        return ServiceResult.success_result("Configuration valid")
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return os.getenv('FLASK_ENV', '').lower() in ('development', 'dev')
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return os.getenv('FLASK_ENV', '').lower() == 'production'
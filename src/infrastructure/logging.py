"""
Structured logging configuration.
"""
import logging
import sys
from typing import Dict, Any
import structlog
from datetime import datetime


def configure_logging(level: str = "INFO", json_logs: bool = True):
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class SecurityLogger:
    """Specialized logger for security events."""
    
    def __init__(self):
        self.logger = get_logger("security")
    
    def log_authentication_attempt(self, success: bool, user_info: Dict[str, Any]):
        """Log authentication attempts."""
        self.logger.info(
            "authentication_attempt",
            success=success,
            timestamp=datetime.utcnow().isoformat(),
            **{k: v for k, v in user_info.items() if k != 'password'}  # Never log passwords
        )
    
    def log_api_key_usage(self, service: str, success: bool):
        """Log API key usage without exposing the key."""
        self.logger.info(
            "api_key_usage",
            service=service,
            success=success,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def log_rate_limit_violation(self, client_ip: str, endpoint: str):
        """Log rate limit violations."""
        self.logger.warning(
            "rate_limit_violation",
            client_ip=client_ip,
            endpoint=endpoint,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def log_validation_error(self, error_type: str, details: Dict[str, Any]):
        """Log validation errors."""
        self.logger.warning(
            "validation_error",
            error_type=error_type,
            details=details,
            timestamp=datetime.utcnow().isoformat()
        )
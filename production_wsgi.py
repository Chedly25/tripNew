#!/usr/bin/env python3
"""
Production WSGI entry point for European Travel Planner.
Optimized for cloud deployment with proper error handling and monitoring.
"""
import os
import sys
import logging
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

try:
    # Import the production application
    from app_runner import app as application
    
    # Configure for production
    application.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', os.urandom(32)),
        'DEBUG': False,
        'TESTING': False,
        'PREFERRED_URL_SCHEME': 'https'
    })
    
    logger.info("Production WSGI application initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize production application: {e}")
    raise

# For gunicorn
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    application.run(host='0.0.0.0', port=port)
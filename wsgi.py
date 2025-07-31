#!/usr/bin/env python3
"""
Simple WSGI entry point for production deployment.
"""
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Import the working application
from app_runner import app as application

# Configure for production
application.config.update({
    'SECRET_KEY': os.environ.get('SECRET_KEY', os.urandom(32)),
    'DEBUG': False,
    'TESTING': False
})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    application.run(host='0.0.0.0', port=port)
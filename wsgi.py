#!/usr/bin/env python3
"""
Simple WSGI entry point for production deployment.
"""
import os
import sys

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Import the working application directly
from app_runner import app as application

# Configure for production
application.config.update({
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'fallback-production-key-12345'),
    'DEBUG': False,
    'TESTING': False
})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting Flask server on port {port}")
    application.run(host='0.0.0.0', port=port, debug=False)
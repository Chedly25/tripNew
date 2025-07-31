#!/usr/bin/env python3
"""
Production WSGI entry point for the REAL travel planner with APIs.
"""
import os
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Import the REAL production application with APIs
from production_app import app as application

# Configure for production
application.config.update({
    'SECRET_KEY': os.environ.get('SECRET_KEY', os.urandom(32)),
    'DEBUG': False,
    'TESTING': False
})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting REAL production Flask server on port {port}")
    application.run(host='0.0.0.0', port=port, debug=False)
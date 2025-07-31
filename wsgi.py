#!/usr/bin/env python3
"""
Production WSGI entry point for the REAL travel planner with APIs.
"""
import os
import sys
from pathlib import Path

try:
    # Add project root to path for imports
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    # Set production environment
    os.environ.setdefault('FLASK_ENV', 'production')

    # Import the REAL production application with ALL features
    from src.web.app import create_app
    application = create_app()

    # Configure for production
    application.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', os.urandom(32).hex()),
        'DEBUG': False,
        'TESTING': False
    })

except Exception as startup_error:
    print(f"WSGI startup error: {startup_error}")
    import traceback
    traceback.print_exc()
    
    # Create minimal fallback Flask app
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error():
        return f"App failed to start: {str(startup_error)}", 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting REAL production Flask server on port {port}")
    application.run(host='0.0.0.0', port=port, debug=False)
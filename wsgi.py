#!/usr/bin/env python3
"""
Simple WSGI entry point for Heroku deployment.
"""
import os

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Import the simple working application
from simple_app import app as application

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask server on port {port}")
    application.run(host='0.0.0.0', port=port, debug=False)
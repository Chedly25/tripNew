#!/usr/bin/env python3
"""
Production application entry point.
"""
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.web.app import create_app, run_development

if __name__ == '__main__':
    if os.getenv('FLASK_ENV') == 'production':
        # In production, use gunicorn
        print("Use gunicorn for production: gunicorn -w 4 -b 0.0.0.0:5000 run:app")
        app = create_app()
    else:
        # Development server
        run_development()

# For gunicorn
app = create_app()
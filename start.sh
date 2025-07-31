#!/bin/bash
# Simple startup script for Railway deployment

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting application with gunicorn..."
exec gunicorn wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
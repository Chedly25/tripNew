#!/usr/bin/env python3
"""
Startup script that finds Python and runs the application
"""
import os
import sys
import subprocess

# Try to find Python executable
python_paths = [
    '/usr/bin/python3',
    '/usr/bin/python',
    '/usr/local/bin/python3',
    '/usr/local/bin/python',
    sys.executable
]

python_exe = None
for path in python_paths:
    if os.path.exists(path):
        python_exe = path
        break

if not python_exe:
    python_exe = 'python3'  # fallback

print(f"Using Python: {python_exe}")
print(f"Python version: {sys.version}")

# Import and run the application directly
if __name__ == "__main__":
    # Import the application
    from wsgi import application
    
    # Get port from environment
    port = int(os.environ.get('PORT', 8000))
    
    print(f"Starting Flask application on port {port}")
    application.run(host='0.0.0.0', port=port, debug=False)
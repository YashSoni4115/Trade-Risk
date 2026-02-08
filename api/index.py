"""
Vercel Serverless Function Handler
Wraps the Flask application for Vercel deployment.
"""

import sys
import os
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Set environment variable for data path
os.environ['DATA_PATH'] = str(backend_path / "data" / "processed")

from src.routes import create_app

# Create the Flask app - Vercel uses the 'app' variable for WSGI
app = create_app(str(backend_path / "data" / "processed"))

# Handler function for Vercel serverless (if needed)
def handler(request, context=None):
    """Vercel serverless handler."""
    return app(request.environ, request.start_response)
#!/usr/bin/env python3
"""
Startup script for the Fitness Builder API.
Loads environment variables and starts the FastAPI server.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from app.api.main import app

def main():
    """Start the FastAPI server."""
    
    # Get configuration from environment variables
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    
    print("🚀 Starting Fitness Builder API Server")
    print("=" * 50)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Reload: {reload}")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print()
    
    # Start the server
    uvicorn.run(
        "app.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    main() 
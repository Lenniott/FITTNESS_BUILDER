"""
FastAPI main application for the video processing API.
"""

import os
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import uvicorn
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env file
load_dotenv()

from app.api.middleware import setup_middleware
from app.api.endpoints import router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Gilgamesh Video Processing API",
    description="AI-powered video processing and exercise clip extraction with user-curated routines",
    version="1.0.0"
)

# Serve static files from storage directory
import os
storage_path = "/app/storage" if os.path.exists("/app/storage") else "./storage"
app.mount("/storage", StaticFiles(directory=storage_path), name="storage")

# Setup middleware
setup_middleware(app)

# Include routers
app.include_router(router, prefix="/api/v1")

# Removed: Workout compilation endpoints - Old system, replaced with user-curated routines

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Gilgamesh Video Processing API", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "database": "connected",
            "qdrant": "connected",
            "ai_services": "available"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 
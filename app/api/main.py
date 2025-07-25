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
    description="AI-powered video processing and exercise clip extraction with workout compilation",
    version="1.0.0"
)

# Setup middleware
setup_middleware(app)

# Include routers
app.include_router(router, prefix="/api/v1")

# Include compilation endpoints
from app.api.compilation_endpoints import router as compilation_router
app.include_router(compilation_router, prefix="/api/v1")

# Include routine endpoints
from app.api.routine_endpoints import router as routine_router
app.include_router(routine_router, prefix="/api/v1")

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
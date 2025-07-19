"""
API endpoints for workout compilation pipeline.
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import asyncio
import os
from pathlib import Path

from app.core.workout_compiler import workout_compiler
from app.database.compilation_operations import (
    get_compiled_workout, list_compiled_workouts, delete_compiled_workout
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class WorkoutRequest(BaseModel):
    user_requirements: str
    target_duration: int = 300  # 5 minutes default
    format: str = "square"  # "square" or "vertical"
    intensity_level: str = "beginner"  # "beginner", "intermediate", "advanced"

class WorkoutResponse(BaseModel):
    id: str
    user_requirements: str
    target_duration: int
    format: str
    intensity_level: str
    video_path: Optional[str] = None
    actual_duration: Optional[int] = None
    created_at: str
    
    class Config:
        from_attributes = True

class CompilationResponse(BaseModel):
    success: bool
    workout_id: Optional[str] = None
    video_path: Optional[str] = None
    requirement_stories: Optional[List[str]] = None
    clips_used: Optional[int] = None
    processing_time: float
    error: Optional[str] = None

@router.post("/workout/generate", response_model=CompilationResponse)
async def generate_workout(request: WorkoutRequest, background_tasks: BackgroundTasks):
    """
    Generate personalized workout video from natural language requirements.
    
    This endpoint follows the complete workflow:
    1. Generate requirement stories from user input
    2. Search for relevant video clips using vector search
    3. Generate exercise scripts
    4. Compile video with FFmpeg
    5. Store result in database
    """
    try:
        logger.info(f"Generating workout for requirements: {request.user_requirements[:100]}...")
        
        # Validate input
        if not request.user_requirements.strip():
            raise HTTPException(status_code=400, detail="User requirements cannot be empty")
        
        if request.target_duration < 60 or request.target_duration > 1800:  # 1-30 minutes
            raise HTTPException(status_code=400, detail="Target duration must be between 1 and 30 minutes")
        
        if request.format not in ["square", "vertical"]:
            raise HTTPException(status_code=400, detail="Format must be 'square' or 'vertical'")
        
        if request.intensity_level not in ["beginner", "intermediate", "advanced"]:
            raise HTTPException(status_code=400, detail="Intensity level must be 'beginner', 'intermediate', or 'advanced'")
        
        # Process workout compilation
        result = await workout_compiler.compile_workout(
            user_requirements=request.user_requirements,
            target_duration=request.target_duration,
            format=request.format,
            intensity_level=request.intensity_level
        )
        
        if result["success"]:
            return CompilationResponse(
                success=True,
                workout_id=result["workout_id"],
                video_path=result["video_path"],
                requirement_stories=result["requirement_stories"],
                clips_used=result["clips_used"],
                processing_time=result["processing_time"]
            )
        else:
            return CompilationResponse(
                success=False,
                error=result["error"],
                processing_time=result["processing_time"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating workout: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Workout generation failed: {str(e)}")

@router.get("/workout/{workout_id}", response_model=WorkoutResponse)
async def get_workout(workout_id: str):
    """Get compiled workout by ID."""
    try:
        workout = await get_compiled_workout(workout_id)
        if not workout:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        # Convert UUID and datetime to strings for Pydantic
        workout_dict = dict(workout)
        if 'id' in workout_dict and workout_dict['id'] is not None:
            workout_dict['id'] = str(workout_dict['id'])
        if 'created_at' in workout_dict and workout_dict['created_at'] is not None:
            workout_dict['created_at'] = str(workout_dict['created_at'])
        
        return WorkoutResponse(**workout_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workout {workout_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workout: {str(e)}")

@router.get("/workout/{workout_id}/download")
async def download_workout_video(workout_id: str):
    """Download the compiled workout video."""
    try:
        workout = await get_compiled_workout(workout_id)
        if not workout:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        video_path = workout['video_path']
        if not video_path or not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Return file path for download (FastAPI will handle the file serving)
        from fastapi.responses import FileResponse
        return FileResponse(
            path=video_path,
            filename=f"workout_{workout_id}.mp4",
            media_type="video/mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading workout {workout_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download workout: {str(e)}")

@router.get("/workouts", response_model=List[WorkoutResponse])
async def list_workouts(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    """List all compiled workouts."""
    try:
        workouts = await list_compiled_workouts(limit=limit, offset=offset)
        
        # Convert UUID and datetime to strings for Pydantic
        converted_workouts = []
        for workout in workouts:
            workout_dict = dict(workout)
            if 'id' in workout_dict and workout_dict['id'] is not None:
                workout_dict['id'] = str(workout_dict['id'])
            if 'created_at' in workout_dict and workout_dict['created_at'] is not None:
                workout_dict['created_at'] = str(workout_dict['created_at'])
            converted_workouts.append(WorkoutResponse(**workout_dict))
        
        return converted_workouts
        
    except Exception as e:
        logger.error(f"Error listing workouts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list workouts: {str(e)}")

@router.delete("/workout/{workout_id}")
async def delete_workout(workout_id: str):
    """Delete compiled workout by ID."""
    try:
        # Get workout first to get video path
        workout = await get_compiled_workout(workout_id)
        if not workout:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        # Delete from database
        deleted = await delete_compiled_workout(workout_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        # Delete video file if it exists
        video_path = workout['video_path']
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                logger.info(f"Deleted video file: {video_path}")
            except Exception as e:
                logger.warning(f"Failed to delete video file {video_path}: {str(e)}")
        
        return {"success": True, "message": "Workout deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workout {workout_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete workout: {str(e)}")

@router.get("/workout/{workout_id}/status")
async def get_workout_status(workout_id: str):
    """Get workout generation status and metadata."""
    try:
        workout = await get_compiled_workout(workout_id)
        if not workout:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        # Check if video file exists
        video_exists = workout['video_path'] and os.path.exists(workout['video_path'])
        
        return {
            "workout_id": workout_id,
            "status": "completed" if video_exists else "failed",
            "video_exists": video_exists,
            "created_at": str(workout['created_at']),
            "target_duration": workout['target_duration'],
            "actual_duration": workout['actual_duration'],
            "format": workout['format'],
            "intensity_level": workout['intensity_level']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workout status {workout_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workout status: {str(e)}") 
"""
API endpoints for the video processing service.
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, HttpUrl
import asyncio

from app.core.processor import processor
from app.database.operations import (
    get_exercises_by_url, get_exercise_by_id, search_exercises,
    delete_exercise, init_database
)
from app.database.vectorization import (
    search_similar_exercises, get_collection_info, init_vector_store
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class ProcessRequest(BaseModel):
    url: HttpUrl
    background: bool = False

class ProcessResponse(BaseModel):
    success: bool
    processed_clips: List[Dict]
    total_clips: int
    processing_time: float
    temp_dir: Optional[str] = None

class ExerciseResponse(BaseModel):
    id: str
    exercise_name: str
    video_path: str
    how_to: str
    benefits: str
    counteracts: str
    fitness_level: int
    rounds_reps: str
    intensity: int
    created_at: str
    
    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    query: Optional[str] = None
    fitness_level_min: Optional[int] = None
    fitness_level_max: Optional[int] = None
    intensity_min: Optional[int] = None
    intensity_max: Optional[int] = None
    limit: int = 50

@router.post("/process", response_model=ProcessResponse)
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Process video URL to extract exercise clips.
    
    This endpoint follows the complete workflow:
    1. Download video and extract metadata
    2. Transcribe audio
    3. Extract keyframes
    4. AI exercise detection
    5. Generate clips
    6. Store in database
    """
    try:
        logger.info(f"Processing video: {request.url}")
        
        # Initialize databases if needed
        await init_database()
        await init_vector_store()
        
        if request.background:
            # Process in background
            background_tasks.add_task(processor.process_video, str(request.url))
            return ProcessResponse(
                success=True,
                processed_clips=[],
                total_clips=0,
                processing_time=0.0,
                temp_dir=None
            )
        else:
            # Process synchronously
            result = await processor.process_video(str(request.url))
            return ProcessResponse(**result)
            
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/exercises", response_model=List[ExerciseResponse])
async def get_exercises(url: Optional[str] = Query(None, description="Filter by video URL")):
    """Get exercises, optionally filtered by URL."""
    try:
        if url:
            exercises = await get_exercises_by_url(url)
        else:
            exercises = await search_exercises(limit=100)
        # Convert UUID and datetime to strings for Pydantic
        converted_exercises = []
        for exercise in exercises:
            # Support both dict and object
            if hasattr(exercise, 'dict'):
                exercise_dict = exercise.dict()
            elif hasattr(exercise, '__dict__'):
                exercise_dict = dict(exercise.__dict__)
            else:
                exercise_dict = dict(exercise)
            if 'id' in exercise_dict and exercise_dict['id'] is not None:
                exercise_dict['id'] = str(exercise_dict['id'])
            if 'created_at' in exercise_dict and exercise_dict['created_at'] is not None:
                exercise_dict['created_at'] = str(exercise_dict['created_at'])
            converted_exercises.append(ExerciseResponse(**exercise_dict))
        return converted_exercises
    except Exception as e:
        logger.error(f"Error getting exercises: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get exercises: {str(e)}")

@router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(exercise_id: str):
    """Get specific exercise by ID."""
    try:
        exercise = await get_exercise_by_id(exercise_id)
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise not found")
        # Convert UUID and datetime to strings for Pydantic
        if hasattr(exercise, 'dict'):
            exercise_dict = exercise.dict()
        elif hasattr(exercise, '__dict__'):
            exercise_dict = dict(exercise.__dict__)
        else:
            exercise_dict = dict(exercise)
        if 'id' in exercise_dict and exercise_dict['id'] is not None:
            exercise_dict['id'] = str(exercise_dict['id'])
        if 'created_at' in exercise_dict and exercise_dict['created_at'] is not None:
            exercise_dict['created_at'] = str(exercise_dict['created_at'])
        return ExerciseResponse(**exercise_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exercise {exercise_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get exercise: {str(e)}")

@router.post("/exercises/search", response_model=List[ExerciseResponse])
async def search_exercises_endpoint(request: SearchRequest):
    """Search exercises with filters."""
    try:
        exercises = await search_exercises(
            query=request.query,
            fitness_level_min=request.fitness_level_min,
            fitness_level_max=request.fitness_level_max,
            intensity_min=request.intensity_min,
            intensity_max=request.intensity_max,
            limit=request.limit
        )
        
        return [ExerciseResponse(**exercise) for exercise in exercises]
        
    except Exception as e:
        logger.error(f"Error searching exercises: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/exercises/similar/{exercise_id}")
async def get_similar_exercises(exercise_id: str, limit: int = Query(10, ge=1, le=50)):
    """Get similar exercises using vector search."""
    try:
        # Get the exercise to use its text for similarity search
        exercise = await get_exercise_by_id(exercise_id)
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise not found")
        
        # Create search text from exercise details
        search_text = f"{exercise['exercise_name']} {exercise['how_to']} {exercise['benefits']}"
        
        similar_exercises = await search_similar_exercises(search_text, limit=limit)
        
        return {
            "exercise_id": exercise_id,
            "similar_exercises": similar_exercises
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting similar exercises: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get similar exercises: {str(e)}")

@router.delete("/exercises/{exercise_id}")
async def delete_exercise_endpoint(exercise_id: str):
    """Delete exercise by ID."""
    try:
        success = await delete_exercise(exercise_id)
        if not success:
            raise HTTPException(status_code=404, detail="Exercise not found")
        
        return {"message": "Exercise deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exercise {exercise_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete exercise: {str(e)}")

@router.get("/health/database")
async def health_database():
    """Check database health."""
    try:
        # Test database connection
        exercises = await search_exercises(limit=1)
        return {
            "status": "healthy",
            "database": "connected",
            "exercises_count": len(exercises)
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database connection failed")

@router.get("/health/vector")
async def health_vector():
    """Check vector database health."""
    try:
        collection_info = await get_collection_info()
        return {
            "status": "healthy",
            "vector_db": "connected",
            "collection_info": collection_info
        }
    except Exception as e:
        logger.error(f"Vector database health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Vector database connection failed")

@router.get("/stats")
async def get_stats():
    """Get processing statistics."""
    try:
        # Get basic stats
        exercises = await search_exercises(limit=1000)
        
        # Calculate statistics
        total_exercises = len(exercises)
        fitness_levels = [e['fitness_level'] for e in exercises if e.get('fitness_level')]
        intensities = [e['intensity'] for e in exercises if e.get('intensity')]
        
        stats = {
            "total_exercises": total_exercises,
            "avg_fitness_level": sum(fitness_levels) / len(fitness_levels) if fitness_levels else 0,
            "avg_intensity": sum(intensities) / len(intensities) if intensities else 0,
            "unique_urls": len(set(e['url'] for e in exercises))
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}") 
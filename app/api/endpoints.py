"""
API endpoints for the video processing service.
"""

import logging
from typing import Dict, List, Optional, Union
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from pydantic import BaseModel, HttpUrl, field_validator
import uuid
import asyncio
import os
from pathlib import Path as FilePath  # Use FilePath for filesystem paths
import uuid
import subprocess

from app.core.processor import processor
from app.database.operations import (
    get_exercises_by_url, get_exercise_by_id, search_exercises,
    delete_exercise, init_database, store_workout_routine, get_workout_routine
)
from app.database.vectorization import (
    search_similar_exercises, get_collection_info, init_vector_store,
    search_diverse_exercises_with_database_data
)
from app.database.job_status import create_job, update_job_status, get_job_status
from app.core.exercise_story_generator import generate_exercise_stories
# Removed: exercise_selector import - was part of old complex routine system, replaced with user-curated routines

logger = logging.getLogger(__name__)

def escape_error_message(error: Exception) -> str:
    """Escape format specifiers in error messages to prevent format specifier errors."""
    return str(error).replace('%', '%%')

router = APIRouter()

# Removed: compilation_endpoints import - file was deleted, import no longer needed

# Pydantic models for request/response
class ProcessRequest(BaseModel):
    url: HttpUrl
    background: bool = False
    
    @field_validator('background', mode='before')
    @classmethod
    def convert_string_to_bool(cls, v):
        if isinstance(v, str):
            return v.lower() == 'true'
        return v

class BulkExerciseRequest(BaseModel):
    exercise_ids: List[str]

class StoryGenerationRequest(BaseModel):
    user_prompt: str
    story_count: int = 5

class StoryGenerationResponse(BaseModel):
    stories: List[str]

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
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    how_to: str
    benefits: str
    counteracts: str
    fitness_level: int
    rounds_reps: str
    intensity: int
    qdrant_id: Optional[str] = None
    created_at: str
    
    @field_validator('qdrant_id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    query: Optional[str] = None
    fitness_level_min: Optional[int] = None
    fitness_level_max: Optional[int] = None
    intensity_min: Optional[int] = None
    intensity_max: Optional[int] = None
    limit: int = 50

class CreateRoutineRequest(BaseModel):
    exercise_ids: List[str]
    name: str
    description: Optional[str] = None

class CreateRoutineResponse(BaseModel):
    routine_id: str
    name: str
    exercise_ids: List[str]
    description: Optional[str] = None
    created_at: str
    
    @field_validator('routine_id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if v is not None:
            return str(v)
        return v

@router.post("/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Process video URL to extract exercise clips.
    If background=True, start job in background and return job_id for polling.
    """
    try:
        logger.info(f"Processing video: {request.url}")
        await init_database()
        await init_vector_store()
        if request.background:
            # Generate job ID and create job record
            job_id = str(uuid.uuid4())
            await create_job(job_id)
            # Start background processing with job_id
            background_tasks.add_task(processor.process_video, str(request.url), job_id)
            return {"success": True, "processed_clips": [], "total_clips": 0, "processing_time": 0.0, "temp_dir": None, "job_id": job_id}
        else:
            result = await processor.process_video(str(request.url))
            return ProcessResponse(**result)
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error processing video: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {error_msg}")

# Remove old complex routine endpoints
# @router.post("/generate-routine", response_model=RAGPipelineResponse)
# @router.get("/routines/{routine_id}", response_model=RAGPipelineResponse)

# Simple routine CRUD operations
@router.post("/routines", response_model=CreateRoutineResponse)
async def create_routine(request: CreateRoutineRequest):
    """Create a new routine with the specified exercise IDs."""
    try:
        from app.database.operations import store_workout_routine
        from datetime import datetime
        
        # Store in database and get the actual routine ID
        routine_id = await store_workout_routine(
            name=request.name,
            description=request.description,
            exercise_ids=request.exercise_ids
        )
        
        logger.info(f"Created routine {routine_id} with {len(request.exercise_ids)} exercises")
        
        return CreateRoutineResponse(
            routine_id=routine_id,
            name=request.name,
            exercise_ids=request.exercise_ids,
            description=request.description,
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating routine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create routine: {str(e)}")

@router.get("/routines/{routine_id}", response_model=CreateRoutineResponse)
async def get_routine(routine_id: str):
    """Get a routine by ID."""
    try:
        from app.database.operations import get_workout_routine
        
        routine = await get_workout_routine(routine_id)
        if not routine:
            raise HTTPException(status_code=404, detail="Routine not found")
        
        return CreateRoutineResponse(
            routine_id=str(routine['id']),  # Use the actual UUID from database
            name=routine['name'],
            exercise_ids=routine['exercise_ids'],
            description=routine.get('description'),
            created_at=str(routine['created_at'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting routine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get routine: {str(e)}")

@router.get("/routines", response_model=List[CreateRoutineResponse])
async def list_routines(limit: int = Query(50, ge=1, le=100)):
    """List all routines."""
    try:
        from app.database.operations import get_recent_workout_routines
        
        routines = await get_recent_workout_routines(limit)
        
        response_routines = []
        for routine in routines:
            response_routines.append(CreateRoutineResponse(
                routine_id=str(routine['id']),  # Convert UUID to string
                name=routine['name'],
                exercise_ids=routine['exercise_ids'],
                description=routine.get('description'),
                created_at=str(routine['created_at'])
            ))
        
        return response_routines
        
    except Exception as e:
        logger.error(f"Error listing routines: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list routines: {str(e)}")

@router.delete("/routines/{routine_id}")
async def delete_routine(routine_id: str):
    """Delete a routine by ID."""
    try:
        from app.database.operations import delete_workout_routine
        
        success = await delete_workout_routine(routine_id)
        if not success:
            raise HTTPException(status_code=404, detail="Routine not found")
        
        return {"message": "Routine deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting routine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete routine: {str(e)}")

@router.get("/job-status/{job_id}")
async def job_status(job_id: str = Path(..., description="Job ID to check status for")):
    """
    Poll for background job status/result by job ID.
    """
    job = await get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

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
            exercise_dict = dict(exercise)
            if 'id' in exercise_dict and exercise_dict['id'] is not None:
                exercise_dict['id'] = str(exercise_dict['id'])
            if 'created_at' in exercise_dict and exercise_dict['created_at'] is not None:
                exercise_dict['created_at'] = str(exercise_dict['created_at'])
            converted_exercises.append(ExerciseResponse(**exercise_dict))
        return converted_exercises
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error getting exercises: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to get exercises: {error_msg}")

@router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(exercise_id: str):
    """Get specific exercise by ID."""
    try:
        exercise = await get_exercise_by_id(exercise_id)
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise not found")
        # Convert UUID and datetime to strings for Pydantic
        exercise_dict = dict(exercise)
        if 'id' in exercise_dict and exercise_dict['id'] is not None:
            exercise_dict['id'] = str(exercise_dict['id'])
        if 'created_at' in exercise_dict and exercise_dict['created_at'] is not None:
            exercise_dict['created_at'] = str(exercise_dict['created_at'])
        return ExerciseResponse(**exercise_dict)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error getting exercise {exercise_id}: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to get exercise: {error_msg}")

@router.post("/exercises/bulk", response_model=List[ExerciseResponse])
async def get_exercises_bulk(request: BulkExerciseRequest):
    """Get multiple exercises by their IDs."""
    try:
        exercises = []
        for exercise_id in request.exercise_ids:
            exercise = await get_exercise_by_id(exercise_id)
            if exercise:
                # Convert UUID and datetime to strings for Pydantic
                exercise_dict = dict(exercise)
                if 'id' in exercise_dict and exercise_dict['id'] is not None:
                    exercise_dict['id'] = str(exercise_dict['id'])
                if 'created_at' in exercise_dict and exercise_dict['created_at'] is not None:
                    exercise_dict['created_at'] = str(exercise_dict['created_at'])
                exercises.append(ExerciseResponse(**exercise_dict))
            else:
                logger.warning(f"Exercise {exercise_id} not found")
        
        return exercises
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error getting exercises bulk: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to get exercises: {error_msg}")

@router.post("/stories/generate", response_model=StoryGenerationResponse)
async def generate_exercise_stories(request: StoryGenerationRequest):
    """Generate exercise requirement stories from user prompt."""
    try:
        from app.core.exercise_story_generator import generate_exercise_stories
        
        logger.info(f"Generating {request.story_count} exercise stories for prompt: {request.user_prompt}")
        
        stories = generate_exercise_stories(request.user_prompt, request.story_count)
        
        logger.info(f"Generated {len(stories)} exercise stories")
        return StoryGenerationResponse(stories=stories)
        
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error generating exercise stories: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to generate exercise stories: {error_msg}")

# Removed: POST /api/v1/exercises/search - Redundant with semantic search
# Removed: GET /api/v1/exercises/similar/{exercise_id} - Not used in new workflow

# Removed: DELETE /api/v1/exercises/all - Too dangerous
# Removed: DELETE /api/v1/exercises/url/{url:path} - Not needed

@router.delete("/exercises/{exercise_id}")
async def delete_exercise_endpoint(exercise_id: str):
    """Delete exercise by ID with cascade cleanup."""
    try:
        from app.database.operations import delete_exercise
        
        success = await delete_exercise(exercise_id)
        if not success:
            raise HTTPException(status_code=404, detail="Exercise not found")
        
        return {"message": "Exercise deleted successfully with cascade cleanup"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exercise {exercise_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete exercise: {str(e)}")

# Removed: DELETE /api/v1/exercises/batch - Too complex

# Removed: DELETE /api/v1/exercises/purge-low-quality - Too complex

# Removed: GET /api/v1/exercises/deletion-preview - Not needed

# Removed: POST /api/v1/exercises/{exercise_id}/generate-clip - Not used

class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10

class SemanticSearchResponse(BaseModel):
    exercise_ids: List[str]
    total_found: int

# Removed: POST /api/v1/exercises/semantic-search - Redundant with semantic-search-ids

@router.post("/exercises/semantic-search-ids", response_model=SemanticSearchResponse)
async def semantic_search_exercises_ids(request: SemanticSearchRequest):
    """
    Search exercises using natural language queries and return only exercise IDs.
    
    This endpoint is designed for the new routine architecture where the UI
    will fetch full exercise details separately using the bulk endpoint.
    """
    try:
        from app.database.vectorization import search_similar_exercises
        
        # Search for similar exercises using vector search
        similar_exercises = await search_similar_exercises(request.query, limit=request.limit)
        
        if not similar_exercises:
            return SemanticSearchResponse(exercise_ids=[], total_found=0)
        
        # Extract database IDs directly from vector results metadata
        exercise_ids = []
        for exercise in similar_exercises:
            database_id = exercise['metadata'].get('database_id')
            if database_id:
                exercise_ids.append(database_id)
        
        return SemanticSearchResponse(
            exercise_ids=exercise_ids,
            total_found=len(exercise_ids)
        )
        
    except Exception as e:
        logger.error(f"Error in semantic search IDs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")

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

# Removed: GET /api/v1/cleanup/analysis - Not needed

# Removed: GET /api/v1/cleanup/orphaned-files - Not needed

# Removed: DELETE /api/v1/cleanup/orphaned-files - Not needed

# Removed: DELETE /api/v1/cleanup/temp-files - Not needed

# Removed: GET /api/v1/cleanup/preview - Not needed 
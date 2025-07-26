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
from app.core.exercise_selector import exercise_selector

logger = logging.getLogger(__name__)

def escape_error_message(error: Exception) -> str:
    """Escape format specifiers in error messages to prevent format specifier errors."""
    return str(error).replace('%', '%%')

router = APIRouter()

# Import compilation endpoints
from app.api.compilation_endpoints import router as compilation_router

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

class RAGPipelineRequest(BaseModel):
    user_prompt: str
    target_duration: Optional[int] = None
    intensity_level: str = "moderate"
    exercises_per_story: int = 3
    initial_limit: int = 40
    score_threshold: float = 0.3

class ExerciseInRoutine(BaseModel):
    order: int
    exercise_name: str
    how_to: str
    benefits: str
    counteracts: str
    fitness_level: int
    rounds_reps: str
    intensity: int

class RoutineMetadata(BaseModel):
    total_exercises: int
    database_operations: Dict[str, List[str]]

class RoutineResponse(BaseModel):
    exercises: List[ExerciseInRoutine]
    metadata: RoutineMetadata

class RAGPipelineResponse(BaseModel):
    success: bool
    routine_id: str
    routine: RoutineResponse
    user_requirements: str
    target_duration: int
    intensity_level: str
    created_at: str
    processing_time: float

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

@router.post("/generate-routine", response_model=RAGPipelineResponse)
async def generate_workout_routine(request: RAGPipelineRequest):
    """
    Generate a complete workout routine using the RAG pipeline.
    
    This endpoint performs the complete workflow:
    1. Generate exercise stories from user prompt
    2. Search for diverse exercises for each story
    3. Select and order exercises for routine
    4. Create final JSON structure
    5. Store routine in database
    
    Args:
        user_prompt: The user's fitness requirements/goals
        target_duration: Target duration in seconds (optional, auto-calculated if not provided)
        intensity_level: Desired intensity (low/moderate/high)
        exercises_per_story: Number of exercises to find per story
        initial_limit: Initial search limit for vector search
        score_threshold: Minimum similarity score for vector search
        
    Returns:
        Complete routine with exercises and metadata
    """
    import time
    start_time = time.time()
    
    try:
        logger.info(f"Starting RAG pipeline for user prompt: {request.user_prompt}")
        
        # Initialize databases
        await init_database()
        await init_vector_store()
        
        # Step 1: Generate exercise stories
        logger.info("Step 1: Generating exercise stories...")
        stories = generate_exercise_stories(request.user_prompt)
        logger.info(f"Generated {len(stories)} exercise stories")
        
        # Step 2: Search for exercises for each story
        logger.info("Step 2: Searching for exercises for each story...")
        all_exercise_results = []
        
        for i, story in enumerate(stories, 1):
            logger.info(f"Searching for story {i}: {story[:50]}...")
            results = await search_diverse_exercises_with_database_data(
                story, 
                target_count=request.exercises_per_story,
                initial_limit=request.initial_limit,
                score_threshold=request.score_threshold
            )
            logger.info(f"Found {len(results)} exercises for story {i}")
            all_exercise_results.extend(results)
        
        logger.info(f"Total exercises found: {len(all_exercise_results)}")
        
        # Step 3: Select and order exercises for routine
        logger.info("Step 3: Selecting and ordering exercises for routine...")
        selected_database_ids = await exercise_selector.select_routine_from_stories_and_results(
            original_prompt=request.user_prompt,
            exercise_stories=stories,
            exercise_results=all_exercise_results
        )
        
        logger.info(f"Selected {len(selected_database_ids)} exercises for routine")
        
        # Step 4: Create final JSON structure
        logger.info("Step 4: Creating final JSON structure...")
        final_routine_json = await exercise_selector.create_final_routine_json(
            selected_database_ids=selected_database_ids,
            exercise_results=all_exercise_results
        )
        
        # Step 5: Store routine in database
        logger.info("Step 5: Storing routine in database...")
        routine_id = await store_workout_routine(
            user_requirements=request.user_prompt,
            routine_json=final_routine_json,
            target_duration=request.target_duration,
            intensity_level=request.intensity_level
        )
        
        # Step 6: Retrieve stored routine for response
        stored_routine = await get_workout_routine(routine_id)
        
        if not stored_routine:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored routine")
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Convert stored routine to response format
        routine_data = stored_routine['routine_data']['routine']
        
        # Convert exercises to response format
        exercises = []
        for exercise in routine_data['exercises']:
            exercises.append(ExerciseInRoutine(**exercise))
        
        # Create metadata
        metadata = RoutineMetadata(**routine_data['metadata'])
        
        # Create routine response
        routine_response = RoutineResponse(
            exercises=exercises,
            metadata=metadata
        )
        
        # Create final response
        response = RAGPipelineResponse(
            success=True,
            routine_id=routine_id,
            routine=routine_response,
            user_requirements=stored_routine['user_requirements'],
            target_duration=stored_routine['target_duration'],
            intensity_level=stored_routine['intensity_level'],
            created_at=str(stored_routine['created_at']),
            processing_time=processing_time
        )
        
        logger.info(f"RAG pipeline completed successfully in {processing_time:.2f}s")
        return response
        
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error in RAG pipeline: {error_msg}")
        raise HTTPException(status_code=500, detail=f"RAG pipeline failed: {error_msg}")

@router.get("/routines/{routine_id}", response_model=RAGPipelineResponse)
async def get_routine(routine_id: str):
    """
    Get a stored workout routine by ID.
    
    Args:
        routine_id: The UUID of the stored routine
        
    Returns:
        Complete routine data
    """
    try:
        stored_routine = await get_workout_routine(routine_id)
        
        if not stored_routine:
            raise HTTPException(status_code=404, detail="Routine not found")
        
        # Convert stored routine to response format
        routine_data = stored_routine['routine_data']['routine']
        
        # Convert exercises to response format
        exercises = []
        for exercise in routine_data['exercises']:
            exercises.append(ExerciseInRoutine(**exercise))
        
        # Create metadata
        metadata = RoutineMetadata(**routine_data['metadata'])
        
        # Create routine response
        routine_response = RoutineResponse(
            exercises=exercises,
            metadata=metadata
        )
        
        # Create final response
        response = RAGPipelineResponse(
            success=True,
            routine_id=routine_id,
            routine=routine_response,
            user_requirements=stored_routine['user_requirements'],
            target_duration=stored_routine['target_duration'],
            intensity_level=stored_routine['intensity_level'],
            created_at=str(stored_routine['created_at']),
            processing_time=0.0  # Not available for stored routines
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error retrieving routine {routine_id}: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve routine: {error_msg}")

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

@router.delete("/exercises/all")
async def delete_all_exercises():
    """Delete ALL exercises, clips, and vector embeddings."""
    try:
        from app.database.operations import delete_all_exercises as db_delete_all
        from app.database.vectorization import delete_all_embeddings
        
        # Delete from database
        deleted_count = await db_delete_all()
        
        # Delete from vector store
        vector_deleted = await delete_all_embeddings()
        
        # Delete all clip files
        clips_deleted = 0
        clips_dir = FilePath("storage/clips")
        if clips_dir.exists():
            for clip_file in clips_dir.glob("*.mp4"):
                try:
                    clip_file.unlink()
                    clips_deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete clip file {clip_file}: {str(e)}")
        
        return {
            "message": "All exercises deleted successfully",
            "database_deleted": deleted_count,
            "vector_deleted": vector_deleted,
            "clips_deleted": clips_deleted
        }
        
    except Exception as e:
        logger.error(f"Error deleting all exercises: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete all exercises: {str(e)}")

@router.delete("/exercises/url/{url:path}")
async def delete_exercises_by_url(url: str):
    """Delete all exercises and clips for a specific URL."""
    try:
        from app.database.operations import delete_exercises_by_url as db_delete_by_url
        from app.database.vectorization import delete_embeddings_by_url
        
        # Delete from database
        deleted_count = await db_delete_by_url(url)
        
        # Delete from vector store
        vector_deleted = await delete_embeddings_by_url(url)
        
        # Delete clip files
        clips_deleted = 0
        exercises = await get_exercises_by_url(url)
        for exercise in exercises:
            if exercise.get('video_path') and os.path.exists(exercise['video_path']):
                try:
                    os.remove(exercise['video_path'])
                    clips_deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete clip file {exercise['video_path']}: {str(e)}")
        
        return {
            "message": "Exercises deleted successfully",
            "database_deleted": deleted_count,
            "vector_deleted": vector_deleted,
            "clips_deleted": clips_deleted
        }
        
    except Exception as e:
        logger.error(f"Error deleting exercises for URL {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete exercises: {str(e)}")

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

@router.delete("/exercises/batch")
async def delete_exercises_by_criteria(
    fitness_level_min: Optional[int] = Query(None, description="Minimum fitness level (0-10)"),
    fitness_level_max: Optional[int] = Query(None, description="Maximum fitness level (0-10)"),
    intensity_min: Optional[int] = Query(None, description="Minimum intensity (0-10)"),
    intensity_max: Optional[int] = Query(None, description="Maximum intensity (0-10)"),
    exercise_name_pattern: Optional[str] = Query(None, description="Pattern to match exercise names"),
    created_before: Optional[str] = Query(None, description="Delete exercises created before this date (ISO format)"),
    created_after: Optional[str] = Query(None, description="Delete exercises created after this date (ISO format)")
):
    """
    Delete exercises based on criteria with cascade cleanup.
    
    This endpoint allows you to delete multiple exercises based on various filters.
    All deletions include cascade cleanup (database, vector store, files, compiled workouts).
    
    Examples:
    - Delete all beginner exercises: ?fitness_level_max=3
    - Delete high intensity exercises: ?intensity_min=8
    - Delete exercises with "test" in name: ?exercise_name_pattern=test
    - Delete old exercises: ?created_before=2024-01-01
    """
    try:
        from app.database.operations import delete_exercises_by_criteria
        
        deleted_count = await delete_exercises_by_criteria(
            fitness_level_min=fitness_level_min,
            fitness_level_max=fitness_level_max,
            intensity_min=intensity_min,
            intensity_max=intensity_max,
            exercise_name_pattern=exercise_name_pattern,
            created_before=created_before,
            created_after=created_after
        )
        
        return {
            "message": f"Successfully deleted {deleted_count} exercises with cascade cleanup",
            "deleted_count": deleted_count,
            "criteria": {
                "fitness_level_min": fitness_level_min,
                "fitness_level_max": fitness_level_max,
                "intensity_min": intensity_min,
                "intensity_max": intensity_max,
                "exercise_name_pattern": exercise_name_pattern,
                "created_before": created_before,
                "created_after": created_after
            }
        }
        
    except Exception as e:
        logger.error(f"Error deleting exercises by criteria: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete exercises: {str(e)}")

@router.delete("/exercises/purge-low-quality")
async def purge_low_quality_exercises(
    fitness_level_threshold: int = Query(3, description="Delete exercises below this fitness level"),
    intensity_threshold: int = Query(3, description="Delete exercises below this intensity level"),
    name_patterns: Optional[str] = Query(None, description="Comma-separated patterns to match for deletion")
):
    """
    Purge low-quality exercises with cascade cleanup.
    
    This endpoint is specifically designed to remove "bad clips" based on quality criteria.
    It deletes exercises that are:
    - Below a certain fitness level (indicating poor quality)
    - Below a certain intensity level (indicating boring content)
    - Match specific name patterns (indicating test/placeholder content)
    
    Examples:
    - Delete all low-quality exercises: /purge-low-quality
    - Delete very low quality: ?fitness_level_threshold=2&intensity_threshold=2
    - Delete test content: ?name_patterns=test,demo,placeholder
    """
    try:
        from app.database.operations import delete_exercises_by_criteria
        
        # Build criteria for low-quality exercises
        criteria = {
            "fitness_level_max": fitness_level_threshold,
            "intensity_max": intensity_threshold,
            "exercise_name_pattern": None,
            "created_before": None,
            "created_after": None
        }
        
        # Add name patterns if provided
        if name_patterns:
            patterns = [p.strip() for p in name_patterns.split(",")]
            # Use the first pattern as the main pattern
            criteria["exercise_name_pattern"] = patterns[0]
        
        deleted_count = await delete_exercises_by_criteria(**criteria)
        
        return {
            "message": f"Successfully purged {deleted_count} low-quality exercises",
            "deleted_count": deleted_count,
            "quality_thresholds": {
                "fitness_level_threshold": fitness_level_threshold,
                "intensity_threshold": intensity_threshold,
                "name_patterns": name_patterns.split(",") if name_patterns else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error purging low-quality exercises: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to purge exercises: {str(e)}")

@router.get("/exercises/deletion-preview")
async def preview_deletion_by_criteria(
    fitness_level_min: Optional[int] = Query(None, description="Minimum fitness level (0-10)"),
    fitness_level_max: Optional[int] = Query(None, description="Maximum fitness level (0-10)"),
    intensity_min: Optional[int] = Query(None, description="Minimum intensity (0-10)"),
    intensity_max: Optional[int] = Query(None, description="Maximum intensity (0-10)"),
    exercise_name_pattern: Optional[str] = Query(None, description="Pattern to match exercise names"),
    created_before: Optional[str] = Query(None, description="Exercises created before this date (ISO format)"),
    created_after: Optional[str] = Query(None, description="Exercises created after this date (ISO format)")
):
    """
    Preview what would be deleted based on criteria without actually deleting.
    
    This endpoint shows you exactly what would be deleted before you commit to the deletion.
    """
    try:
        from app.database.operations import search_exercises
        
        # Use the same search logic to preview what would be deleted
        exercises = await search_exercises(
            query=exercise_name_pattern,
            fitness_level_min=fitness_level_min,
            fitness_level_max=fitness_level_max,
            intensity_min=intensity_min,
            intensity_max=intensity_max,
            limit=1000  # Get more results for preview
        )
        
        # Apply additional date filters if provided
        if created_before or created_after:
            from datetime import datetime
            filtered_exercises = []
            
            for exercise in exercises:
                created_at = exercise.get('created_at')
                if created_at:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    include = True
                    if created_before:
                        before_date = datetime.fromisoformat(created_before.replace('Z', '+00:00'))
                        if created_at >= before_date:
                            include = False
                    
                    if created_after and include:
                        after_date = datetime.fromisoformat(created_after.replace('Z', '+00:00'))
                        if created_at <= after_date:
                            include = False
                    
                    if include:
                        filtered_exercises.append(exercise)
            
            exercises = filtered_exercises
        
        return {
            "preview_count": len(exercises),
            "exercises": exercises[:50],  # Show first 50 for preview
            "criteria": {
                "fitness_level_min": fitness_level_min,
                "fitness_level_max": fitness_level_max,
                "intensity_min": intensity_min,
                "intensity_max": intensity_max,
                "exercise_name_pattern": exercise_name_pattern,
                "created_before": created_before,
                "created_after": created_after
            }
        }
        
    except Exception as e:
        logger.error(f"Error previewing deletion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to preview deletion: {str(e)}")

@router.post("/exercises/{exercise_id}/generate-clip")
async def generate_clip_from_database(exercise_id: str):
    """Generate a clip for an exercise using its stored start/end times."""
    try:
        # Get exercise from database
        exercise = await get_exercise_by_id(exercise_id)
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise not found")
        
        # Check if we have start/end times
        if not exercise.get('start_time') or not exercise.get('end_time'):
            raise HTTPException(status_code=400, detail="Exercise missing start_time or end_time")
        
        # Find the original video file
        video_path = exercise.get('video_path', '')
        if not video_path or not os.path.exists(video_path):
            # Try to find the original video in temp directories
            temp_dirs = [d for d in FilePath("app/temp").iterdir() if d.is_dir() and d.name.startswith("gilgamesh_download_")]
            video_file = None
            for temp_dir in temp_dirs:
                video_files = list(temp_dir.glob("*.mp4"))
                if video_files:
                    video_file = str(video_files[0])
                    break
            
            if not video_file:
                raise HTTPException(status_code=404, detail="Original video file not found")
        else:
            video_file = video_path
        
        # Generate clip using ffmpeg
        start_time = exercise['start_time']
        end_time = exercise['end_time']
        duration = end_time - start_time
        
        # Create clips directory
        clips_dir = FilePath("storage/clips")
        clips_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate clip filename
        exercise_name_clean = exercise['exercise_name'].replace(' ', '_').lower()
        clip_filename = f"{exercise_name_clean}_{uuid.uuid4().hex[:8]}.mp4"
        clip_path = clips_dir / clip_filename
        
        # Run ffmpeg
        ffmpeg_cmd = [
            'ffmpeg',
            '-y',
            '-i', video_file,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            str(clip_path)
        ]
        
        logger.info(f"Generating clip for exercise {exercise_id}: {exercise['exercise_name']}")
        logger.info(f"Command: {' '.join(ffmpeg_cmd)}")
        
        # Run ffmpeg in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )
        )
        
        if result.returncode == 0 and clip_path.exists():
            file_size = clip_path.stat().st_size
            return {
                "success": True,
                "exercise_id": exercise_id,
                "exercise_name": exercise['exercise_name'],
                "clip_path": str(clip_path),
                "file_size": file_size,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration
            }
        else:
            logger.error(f"ffmpeg failed: {result.stderr}")
            raise HTTPException(status_code=500, detail="Failed to generate clip")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating clip for exercise {exercise_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate clip: {str(e)}")

class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10

@router.post("/exercises/semantic-search")
async def semantic_search_exercises(request: SemanticSearchRequest):
    """
    Search exercises using natural language queries.
    
    Example queries:
    - "I haven't worked out in a month, need mobility and strength, nothing too intense"
    - "I sit a lot all day, need something for my back and hips"
    - "I'm advanced, want high intensity cardio"
    """
    try:
        # Search for similar exercises
        similar_exercises = await search_similar_exercises(request.query, limit=request.limit)
        
        # Format results with exercise details
        results = []
        for exercise in similar_exercises:
            metadata = exercise['metadata']
            results.append({
                'exercise_id': exercise['id'],
                'exercise_name': metadata.get('exercise_name', 'Unknown Exercise'),
                'video_path': metadata.get('video_path', ''),
                'fitness_level': metadata.get('fitness_level', 5),
                'intensity': metadata.get('intensity', 5),
                'duration': metadata.get('duration', 0),
                'benefits': metadata.get('benefits', ''),
                'counteracts': metadata.get('counteracts', ''),
                'how_to': metadata.get('how_to', ''),
                'similarity_score': exercise['score']
            })
        
        return {
            "query": request.query,
            "results": results,
            "total_found": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
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

@router.get("/cleanup/analysis")
async def analyze_storage():
    """
    Analyze storage usage and get cleanup recommendations.
    
    This endpoint provides a comprehensive analysis of your storage usage
    and recommends cleanup actions to free up space.
    """
    try:
        from app.utils.cleanup_utils import get_cleanup_recommendations
        
        recommendations = await get_cleanup_recommendations()
        return recommendations
        
    except Exception as e:
        logger.error(f"Error analyzing storage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze storage: {str(e)}")

@router.get("/cleanup/orphaned-files")
async def find_orphaned_files():
    """
    Find files that exist in storage but are not referenced in the database.
    
    These are typically files from failed processing or manual deletions.
    """
    try:
        from app.utils.cleanup_utils import find_orphaned_files
        
        orphaned_info = await find_orphaned_files()
        return orphaned_info
        
    except Exception as e:
        logger.error(f"Error finding orphaned files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to find orphaned files: {str(e)}")

@router.delete("/cleanup/orphaned-files")
async def cleanup_orphaned_files(confirm: bool = Query(False, description="Set to true to actually delete files")):
    """
    Clean up orphaned files (files not referenced in database).
    
    Args:
        confirm: Must be set to true to actually delete files
        
    Returns:
        Cleanup results
    """
    try:
        from app.utils.cleanup_utils import cleanup_orphaned_files
        
        if not confirm:
            raise HTTPException(status_code=400, detail="Must set confirm=true to delete files")
        
        result = await cleanup_orphaned_files(confirm=True)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up orphaned files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clean up orphaned files: {str(e)}")

@router.delete("/cleanup/temp-files")
async def cleanup_temp_files(
    days_old: int = Query(7, description="Delete files older than this many days"),
    confirm: bool = Query(False, description="Set to true to actually delete files"),
    include_recent: bool = Query(False, description="Include recent temp files (for manual cleanup)")
):
    """
    Clean up old temporary files.
    
    Args:
        days_old: Delete files older than this many days
        confirm: Must be set to true to actually delete files
        include_recent: Include recent temp files (for manual cleanup)
        
    Returns:
        Cleanup results
    """
    try:
        from app.utils.cleanup_utils import cleanup_old_temp_files
        
        if not confirm:
            raise HTTPException(status_code=400, detail="Must set confirm=true to delete files")
        
        result = await cleanup_old_temp_files(days_old=days_old, confirm=True, include_recent=include_recent)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clean up temp files: {str(e)}")

@router.get("/cleanup/preview")
async def preview_cleanup_operations():
    """
    Preview all cleanup operations without actually deleting anything.
    
    This endpoint shows you exactly what would be cleaned up.
    """
    try:
        from app.utils.cleanup_utils import (
            analyze_storage_usage, 
            find_orphaned_files, 
            cleanup_orphaned_files, 
            cleanup_old_temp_files
        )
        
        # Get storage analysis
        storage_analysis = await analyze_storage_usage()
        
        # Preview orphaned file cleanup
        orphaned_preview = await cleanup_orphaned_files(confirm=False)
        
        # Preview temp file cleanup
        temp_preview = await cleanup_old_temp_files(days_old=7, confirm=False)
        
        return {
            "storage_analysis": storage_analysis,
            "orphaned_files_preview": orphaned_preview,
            "temp_files_preview": temp_preview,
            "total_potential_savings_mb": (
                orphaned_preview.get("total_size_mb", 0) + 
                temp_preview.get("total_size_mb", 0)
            )
        }
        
    except Exception as e:
        logger.error(f"Error previewing cleanup operations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to preview cleanup: {str(e)}") 
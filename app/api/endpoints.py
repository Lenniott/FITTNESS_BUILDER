"""
API endpoints for the video processing service.
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, HttpUrl
import asyncio
import os
from pathlib import Path
import uuid
import subprocess

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

# Import compilation endpoints
from app.api.compilation_endpoints import router as compilation_router

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
    start_time: Optional[float] = None
    end_time: Optional[float] = None
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
        clips_dir = Path("storage/clips")
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
            temp_dirs = [d for d in Path("app/temp").iterdir() if d.is_dir() and d.name.startswith("gilgamesh_download_")]
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
        clips_dir = Path("storage/clips")
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
"""
API endpoints for workout routine generation and management.
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from pydantic import BaseModel
import asyncio
import os
from pathlib import Path as FilePath

from app.core.routine_compiler import routine_compiler
from app.database.routine_operations import (
    get_routine, list_routines, delete_routine, update_routine,
    remove_exercise_from_routine, delete_exercise_from_routine_and_system
)
from app.api.routine_models import (
    RoutineRequest, RoutineResponse, RoutineListResponse, 
    DeleteResponse, RemoveExerciseRequest, RoutineData
)

logger = logging.getLogger(__name__)

router = APIRouter()

def escape_error_message(error: Exception) -> str:
    """Escape format specifiers in error messages to prevent format specifier errors."""
    return str(error).replace('%', '%%')

@router.post("/routine/generate", response_model=RoutineResponse)
async def generate_routine(request: RoutineRequest, background_tasks: BackgroundTasks):
    """
    Generate personalized workout routine from natural language requirements.
    
    This endpoint follows the complete workflow:
    1. Generate requirement stories from user input
    2. Search for relevant video clips using vector search
    3. Use second LLM to select unique, diverse exercises
    4. Create JSON routine with all metadata
    5. Store result in database
    """
    try:
        logger.info(f"Generating routine for requirements: {request.user_requirements[:100]}...")
        
        # Validate input
        if not request.user_requirements.strip():
            raise HTTPException(status_code=400, detail="User requirements cannot be empty")
        
        # Process routine compilation
        result = await routine_compiler.compile_routine(
            user_requirements=request.user_requirements
        )
        
        if result["success"]:
            return RoutineResponse(
                success=True,
                routine_id=result["routine_id"],
                routine_data=result["routine_data"],
                requirement_stories=result["requirement_stories"],
                exercises_selected=result["exercises_selected"],
                processing_time=result["processing_time"]
            )
        else:
            return RoutineResponse(
                success=False,
                error=result["error"],
                processing_time=result["processing_time"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error generating routine: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Routine generation failed: {error_msg}")

@router.get("/routine/{routine_id}", response_model=RoutineData)
async def get_routine_endpoint(routine_id: str = Path(..., description="Routine ID to retrieve")):
    """Get routine by ID."""
    try:
        routine = await get_routine(routine_id)
        if not routine:
            raise HTTPException(status_code=404, detail="Routine not found")
        
        # Convert to response model
        routine_data = routine['routine_data']
        return RoutineData(**routine_data)
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error getting routine {routine_id}: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to get routine: {error_msg}")

@router.get("/routines", response_model=RoutineListResponse)
async def list_routines_endpoint(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of routines to return"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """List all routines with pagination."""
    try:
        routines = await list_routines(limit=limit, offset=offset)
        
        # Convert to response models
        routine_data_list = []
        for routine in routines:
            routine_data = routine['routine_data']
            routine_data_list.append(RoutineData(**routine_data))
        
        return RoutineListResponse(
            routines=routine_data_list,
            total_count=len(routine_data_list),
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error listing routines: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to list routines: {error_msg}")

@router.delete("/routine/{routine_id}", response_model=DeleteResponse)
async def delete_routine_endpoint(routine_id: str = Path(..., description="Routine ID to delete")):
    """Delete routine by ID."""
    try:
        # Get routine first to validate it exists
        routine = await get_routine(routine_id)
        if not routine:
            raise HTTPException(status_code=404, detail="Routine not found")
        
        # Delete from database
        deleted = await delete_routine(routine_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Routine not found")
        
        return DeleteResponse(
            success=True,
            message="Routine deleted successfully",
            deleted_count=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error deleting routine {routine_id}: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to delete routine: {error_msg}")

@router.post("/routine/{routine_id}/exercise/{exercise_id}/remove", response_model=RoutineData)
async def remove_exercise_from_routine_endpoint(
    routine_id: str = Path(..., description="Routine ID"),
    exercise_id: str = Path(..., description="Exercise ID to remove"),
    request: RemoveExerciseRequest = None
):
    """Remove exercise from routine."""
    try:
        # Get routine
        routine = await get_routine(routine_id)
        if not routine:
            raise HTTPException(status_code=404, detail="Routine not found")
        
        routine_data = routine['routine_data']
        exercises = routine_data['exercises']
        
        # Find and remove exercise
        exercise_found = False
        updated_exercises = []
        
        for exercise in exercises:
            if exercise['exercise_id'] == exercise_id:
                exercise_found = True
                # If delete_exercise is True, we could delete the exercise completely
                # For now, just remove it from the routine
                if request and request.delete_exercise:
                    logger.info(f"Removing exercise {exercise_id} from routine {routine_id}")
                continue
            updated_exercises.append(exercise)
        
        if not exercise_found:
            raise HTTPException(status_code=404, detail="Exercise not found in routine")
        
        # Update routine data
        routine_data['exercises'] = updated_exercises
        routine_data['metadata']['exercise_count'] = len(updated_exercises)
        
        # Recalculate total duration
        total_duration = sum(ex['duration'] for ex in updated_exercises)
        routine_data['metadata']['total_duration'] = total_duration
        
        # Update in database
        updated = await update_routine(routine_id, routine_data)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update routine")
        
        return RoutineData(**routine_data)
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error removing exercise {exercise_id} from routine {routine_id}: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to remove exercise: {error_msg}")

@router.post("/routine/{routine_id}/exercise/{exercise_id}/delete", response_model=DeleteResponse)
async def delete_exercise_from_routine_endpoint(
    routine_id: str = Path(..., description="Routine ID"),
    exercise_id: str = Path(..., description="Exercise ID to completely delete")
):
    """Remove exercise from routine AND delete it from database/vector store entirely."""
    try:
        # Use the comprehensive deletion function
        deleted = await delete_exercise_from_routine_and_system(routine_id, exercise_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Exercise not found in routine or deletion failed")
        
        return DeleteResponse(
            success=True,
            message="Exercise removed from routine and deleted from system",
            deleted_count=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error deleting exercise {exercise_id} from routine {routine_id}: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to delete exercise: {error_msg}")

@router.get("/routine/{routine_id}/status")
async def get_routine_status(routine_id: str = Path(..., description="Routine ID to check status for")):
    """Get routine status and metadata."""
    try:
        routine = await get_routine(routine_id)
        if not routine:
            raise HTTPException(status_code=404, detail="Routine not found")
        
        routine_data = routine['routine_data']
        
        return {
            "routine_id": routine_id,
            "status": "completed",
            "user_requirements": routine_data['user_requirements'],
            "target_duration": routine_data['target_duration'],
            "actual_duration": routine_data['metadata']['total_duration'],
            "exercise_count": routine_data['metadata']['exercise_count'],
            "intensity_level": routine_data['intensity_level'],
            "format": routine_data['format'],
            "created_at": routine['created_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = escape_error_message(e)
        logger.error(f"Error getting routine status {routine_id}: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to get routine status: {error_msg}") 
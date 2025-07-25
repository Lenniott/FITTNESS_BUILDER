"""
Database operations for storing workout routines.
"""

import asyncio
import logging
import os
import uuid
import json
from typing import Dict, List, Optional
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database connection pool (reuse existing)
from app.database.operations import get_database_connection

async def store_routine(
    user_requirements: str,
    target_duration: int,
    intensity_level: str,
    format: str,
    routine_data: Dict
) -> str:
    """
    Store workout routine in database.
    
    Args:
        user_requirements: Original user input
        target_duration: Target duration in seconds
        intensity_level: Intensity level ('beginner', 'intermediate', 'advanced')
        format: Format ('vertical', 'square')
        routine_data: Complete routine JSON data
        
    Returns:
        Routine ID (UUID)
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        routine_id = str(uuid.uuid4())
        
        await conn.execute("""
            INSERT INTO workout_routines (
                id, user_requirements, target_duration, intensity_level, format, routine_data
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """, routine_id, user_requirements, target_duration, intensity_level, format, json.dumps(routine_data))
        
        logger.info(f"Stored workout routine: {routine_id}")
        return routine_id

async def get_routine(routine_id: str) -> Optional[Dict]:
    """
    Get routine by ID.
    
    Args:
        routine_id: Routine UUID
        
    Returns:
        Routine record or None
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM workout_routines WHERE id = $1
        """, routine_id)
        
        if row:
            routine_dict = dict(row)
            # Parse JSONB back to dict
            routine_dict['routine_data'] = json.loads(routine_dict['routine_data'])
            return routine_dict
        
        return None

async def list_routines(limit: int = 50, offset: int = 0) -> List[Dict]:
    """
    List all routines.
    
    Args:
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        List of routine records
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM workout_routines 
            ORDER BY created_at DESC 
            LIMIT $1 OFFSET $2
        """, limit, offset)
        
        routines = []
        for row in rows:
            routine_dict = dict(row)
            # Parse JSONB back to dict
            routine_dict['routine_data'] = json.loads(routine_dict['routine_data'])
            routines.append(routine_dict)
        
        return routines

async def delete_routine(routine_id: str) -> bool:
    """
    Delete routine by ID.
    
    Args:
        routine_id: Routine UUID
        
    Returns:
        True if deleted, False if not found
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM workout_routines WHERE id = $1
        """, routine_id)
        
        return result == "DELETE 1"

async def update_routine(routine_id: str, routine_data: Dict) -> bool:
    """
    Update routine data.
    
    Args:
        routine_id: Routine UUID
        routine_data: Updated routine JSON data
        
    Returns:
        True if updated, False if not found
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE workout_routines 
            SET routine_data = $2, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, routine_id, json.dumps(routine_data))
        
        return result == "UPDATE 1"

async def remove_exercise_from_routine(routine_id: str, exercise_id: str) -> bool:
    """
    Remove a specific exercise from a routine without deleting the underlying exercise.
    
    Args:
        routine_id: Routine UUID
        exercise_id: Exercise UUID to remove from routine
        
    Returns:
        True if exercise was removed, False if routine or exercise not found
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        # Get current routine data
        row = await conn.fetchrow("""
            SELECT routine_data FROM workout_routines WHERE id = $1
        """, routine_id)
        
        if not row:
            return False
        
        routine_data = json.loads(row['routine_data'])
        exercises = routine_data.get('exercises', [])
        
        # Find and remove the exercise
        original_count = len(exercises)
        exercises = [ex for ex in exercises if ex.get('exercise_id') != exercise_id]
        
        if len(exercises) == original_count:
            # Exercise wasn't found in routine
            return False
        
        # Update routine data
        routine_data['exercises'] = exercises
        routine_data['metadata']['exercise_count'] = len(exercises)
        
        # Recalculate total duration
        total_duration = sum(ex.get('duration', 0) for ex in exercises)
        routine_data['metadata']['total_duration'] = total_duration
        
        # Update the routine
        result = await conn.execute("""
            UPDATE workout_routines 
            SET routine_data = $2, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, routine_id, json.dumps(routine_data))
        
        return result == "UPDATE 1"

async def delete_exercise_from_routine_and_system(routine_id: str, exercise_id: str) -> bool:
    """
    Remove exercise from routine AND delete it from database/vector store entirely.
    This is a complete deletion that removes the exercise from everywhere.
    
    Args:
        routine_id: Routine UUID
        exercise_id: Exercise UUID to completely delete
        
    Returns:
        True if exercise was deleted from everywhere, False if not found
    """
    # First remove from routine
    routine_updated = await remove_exercise_from_routine(routine_id, exercise_id)
    
    if not routine_updated:
        return False
    
    # Then delete the exercise entirely from database and vector store
    from app.database.operations import delete_exercise
    exercise_deleted = await delete_exercise(exercise_id)
    
    return exercise_deleted 
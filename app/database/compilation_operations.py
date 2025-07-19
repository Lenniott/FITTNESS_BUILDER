"""
Database operations for storing compiled workout videos.
"""

import asyncio
import logging
import os
import uuid
from typing import Dict, List, Optional
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database connection pool
_pool = None

async def get_database_connection():
    """Get database connection from pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("PG_HOST", "localhost"),
            port=int(os.getenv("PG_PORT", "5432")),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", ""),
            database=os.getenv("PG_DBNAME", "gilgamesh"),
            min_size=1,
            max_size=10
        )
    return _pool

async def store_compiled_workout(
    user_requirements: str,
    target_duration: int,
    format: str,
    intensity_level: str,
    video_path: str,
    actual_duration: int
) -> str:
    """
    Store compiled workout in database.
    
    Args:
        user_requirements: Original user input
        target_duration: Target duration in seconds
        format: Video format ('square' or 'vertical')
        intensity_level: Intensity level ('beginner', 'intermediate', 'advanced')
        video_path: Path to the compiled video file
        actual_duration: Actual duration of the compiled video in seconds
        
    Returns:
        Workout ID (UUID)
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        workout_id = str(uuid.uuid4())
        
        await conn.execute("""
            INSERT INTO compiled_workouts (
                id, user_requirements, target_duration, format, intensity_level,
                video_path, actual_duration
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, workout_id, user_requirements, target_duration, format, intensity_level,
             video_path, actual_duration)
        
        logger.info(f"Stored compiled workout: {workout_id}")
        return workout_id

async def get_compiled_workout(workout_id: str) -> Optional[Dict]:
    """
    Get compiled workout by ID.
    
    Args:
        workout_id: Workout UUID
        
    Returns:
        Workout record or None
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM compiled_workouts WHERE id = $1
        """, workout_id)
        
        return dict(row) if row else None

async def list_compiled_workouts(limit: int = 50, offset: int = 0) -> List[Dict]:
    """
    List all compiled workouts.
    
    Args:
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        List of workout records
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM compiled_workouts 
            ORDER BY created_at DESC 
            LIMIT $1 OFFSET $2
        """, limit, offset)
        
        workouts = []
        for row in rows:
            workouts.append(dict(row))
        
        return workouts

async def delete_compiled_workout(workout_id: str) -> bool:
    """
    Delete compiled workout by ID.
    
    Args:
        workout_id: Workout UUID
        
    Returns:
        True if deleted, False if not found
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM compiled_workouts WHERE id = $1
        """, workout_id)
        
        return result == "DELETE 1"

async def close_database():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None 
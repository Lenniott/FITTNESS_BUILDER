"""
Database operations for storing exercise data in PostgreSQL.
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

async def init_database():
    """Initialize database tables."""
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        # Create exercises table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                url VARCHAR(500) NOT NULL,
                exercise_name VARCHAR(200) NOT NULL,
                video_path VARCHAR(500) NOT NULL,
                how_to TEXT,
                benefits TEXT,
                counteracts TEXT,
                fitness_level INTEGER CHECK (fitness_level >= 0 AND fitness_level <= 10),
                rounds_reps VARCHAR(200),
                intensity INTEGER CHECK (intensity >= 0 AND intensity <= 10),
                qdrant_id UUID,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on url for faster lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_exercises_url ON exercises(url)
        """)
        
        logger.info("Database tables initialized")

async def store_exercise(
    url: str,
    exercise_name: str,
    video_path: str,
    how_to: str,
    benefits: str,
    counteracts: str,
    fitness_level: int,
    rounds_reps: str,
    intensity: int,
    qdrant_id: Optional[str] = None
) -> str:
    """
    Store exercise data in database.
    
    Args:
        url: Original video URL
        exercise_name: Name of the exercise
        video_path: Path to the video clip
        how_to: Instructions for performing the exercise
        benefits: Benefits of the exercise
        counteracts: Problems this exercise helps solve
        fitness_level: Difficulty level (0-10)
        rounds_reps: Specific instructions for duration/repetitions
        intensity: Intensity level (0-10)
        qdrant_id: Vector database reference ID
        
    Returns:
        Exercise ID (UUID)
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        exercise_id = str(uuid.uuid4())
        
        await conn.execute("""
            INSERT INTO exercises (
                id, url, exercise_name, video_path, how_to, benefits, counteracts,
                fitness_level, rounds_reps, intensity, qdrant_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, exercise_id, url, exercise_name, video_path, how_to, benefits,
             counteracts, fitness_level, rounds_reps, intensity, qdrant_id)
        
        logger.info(f"Stored exercise: {exercise_name} (ID: {exercise_id})")
        return exercise_id

async def get_exercises_by_url(url: str) -> List[Dict]:
    """
    Get all exercises for a specific URL.
    
    Args:
        url: Video URL to search for
        
    Returns:
        List of exercise records
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM exercises WHERE url = $1 ORDER BY created_at DESC
        """, url)
        
        exercises = []
        for row in rows:
            exercises.append(dict(row))
        
        return exercises

async def get_exercise_by_id(exercise_id: str) -> Optional[Dict]:
    """
    Get exercise by ID.
    
    Args:
        exercise_id: Exercise UUID
        
    Returns:
        Exercise record or None
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM exercises WHERE id = $1
        """, exercise_id)
        
        return dict(row) if row else None

async def search_exercises(
    query: str = None,
    fitness_level_min: int = None,
    fitness_level_max: int = None,
    intensity_min: int = None,
    intensity_max: int = None,
    limit: int = 50
) -> List[Dict]:
    """
    Search exercises with filters.
    
    Args:
        query: Text search query
        fitness_level_min: Minimum fitness level
        fitness_level_max: Maximum fitness level
        intensity_min: Minimum intensity
        intensity_max: Maximum intensity
        limit: Maximum results to return
        
    Returns:
        List of matching exercises
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        # Build dynamic query
        conditions = []
        params = []
        param_count = 0
        
        if query:
            param_count += 1
            conditions.append(f"exercise_name ILIKE ${param_count}")
            params.append(f"%{query}%")
        
        if fitness_level_min is not None:
            param_count += 1
            conditions.append(f"fitness_level >= ${param_count}")
            params.append(fitness_level_min)
        
        if fitness_level_max is not None:
            param_count += 1
            conditions.append(f"fitness_level <= ${param_count}")
            params.append(fitness_level_max)
        
        if intensity_min is not None:
            param_count += 1
            conditions.append(f"intensity >= ${param_count}")
            params.append(intensity_min)
        
        if intensity_max is not None:
            param_count += 1
            conditions.append(f"intensity <= ${param_count}")
            params.append(intensity_max)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query_sql = f"""
            SELECT * FROM exercises 
            WHERE {where_clause}
            ORDER BY created_at DESC 
            LIMIT ${param_count + 1}
        """
        params.append(limit)
        
        rows = await conn.fetch(query_sql, *params)
        
        exercises = []
        for row in rows:
            exercises.append(dict(row))
        
        return exercises

async def delete_exercise(exercise_id: str) -> bool:
    """
    Delete exercise by ID.
    
    Args:
        exercise_id: Exercise UUID
        
    Returns:
        True if deleted, False if not found
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM exercises WHERE id = $1
        """, exercise_id)
        
        return result == "DELETE 1"

async def close_database():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")

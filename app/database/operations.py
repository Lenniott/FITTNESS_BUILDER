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
                normalized_url VARCHAR(500) NOT NULL,
                carousel_index INTEGER DEFAULT 1,
                exercise_name VARCHAR(200) NOT NULL,
                video_path VARCHAR(500) NOT NULL,
                start_time DECIMAL(10,3),
                end_time DECIMAL(10,3),
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
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_exercises_url ON exercises(url)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_exercises_normalized_url ON exercises(normalized_url)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_exercises_carousel_index ON exercises(carousel_index)
        """)
        
        # Create unique constraint to prevent duplicate processing of the same exercise
        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_unique_url_index 
            ON exercises(normalized_url, carousel_index, exercise_name)
        """)
        
        logger.info("Database tables initialized")

async def store_exercise(
    url: str,
    normalized_url: str,
    carousel_index: int = 1,
    exercise_name: str = "",
    video_path: str = "",
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    how_to: str = "",
    benefits: str = "",
    counteracts: str = "",
    fitness_level: int = 5,
    rounds_reps: str = "",
    intensity: int = 5,
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
                id, url, normalized_url, carousel_index, exercise_name, video_path, start_time, end_time, 
                how_to, benefits, counteracts, fitness_level, rounds_reps, intensity, qdrant_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        """, exercise_id, url, normalized_url, carousel_index, exercise_name, video_path, start_time, end_time, 
             how_to, benefits, counteracts, fitness_level, rounds_reps, intensity, qdrant_id)
        
        logger.info(f"Stored exercise: {exercise_name} (ID: {exercise_id})")
        return exercise_id

async def check_existing_processing(normalized_url: str, carousel_index: int = 1, exercise_name: Optional[str] = None) -> Optional[Dict]:
    """
    Check if a specific exercise from a URL + carousel_index combination has already been processed.
    
    Args:
        normalized_url: Normalized URL (without query parameters)
        carousel_index: Index of carousel item (default 1 for single videos)
        exercise_name: Specific exercise name to check (optional)
        
    Returns:
        Existing exercise record or None if not found
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        if exercise_name:
            # Check for specific exercise
            row = await conn.fetchrow("""
                SELECT * FROM exercises 
                WHERE normalized_url = $1 AND carousel_index = $2 AND exercise_name = $3
                ORDER BY created_at DESC
                LIMIT 1
            """, normalized_url, carousel_index, exercise_name)
        else:
            # Check if any exercises exist for this URL/carousel combination
            row = await conn.fetchrow("""
                SELECT * FROM exercises 
                WHERE normalized_url = $1 AND carousel_index = $2
                ORDER BY created_at DESC
                LIMIT 1
            """, normalized_url, carousel_index)
        
        return dict(row) if row else None

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
    query: Optional[str] = None,
    fitness_level_min: Optional[int] = None,
    fitness_level_max: Optional[int] = None,
    intensity_min: Optional[int] = None,
    intensity_max: Optional[int] = None,
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
            # Escape % characters to prevent format specifier errors
            escaped_query = query.replace('%', '%%')
            params.append(f"%{escaped_query}%")
        
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
    Delete exercise by ID with cascade cleanup.
    
    Args:
        exercise_id: Exercise UUID
        
    Returns:
        True if deleted, False if not found
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        # First get the exercise to get file paths and qdrant_id
        row = await conn.fetchrow("""
            SELECT * FROM exercises WHERE id = $1
        """, exercise_id)
        
        if not row:
            return False
        
        exercise_data = dict(row)
        
        # Delete from database
        result = await conn.execute("""
            DELETE FROM exercises WHERE id = $1
        """, exercise_id)
        
        if result == "DELETE 1":
            # Cascade cleanup
            await _cascade_cleanup_exercise(exercise_data)
            return True
        
        return False

async def _cascade_cleanup_exercise(exercise_data: Dict):
    """
    Perform cascade cleanup for a deleted exercise.
    
    Args:
        exercise_data: The exercise data that was deleted
    """
    try:
        # 1. Delete from vector store if qdrant_id exists
        if exercise_data.get('qdrant_id'):
            from app.database.vectorization import delete_embedding
            await delete_embedding(exercise_data['qdrant_id'])
        
        # 2. Delete video file if it exists
        video_path = exercise_data.get('video_path', '')
        if video_path:
            await _delete_video_file(video_path)
        
        # 3. Clean up any compiled workouts that reference this exercise
        await _cleanup_compiled_workouts(exercise_data.get('url', ''))
        
        logger.info(f"Cascade cleanup completed for exercise: {exercise_data.get('exercise_name', 'Unknown')}")
        
    except Exception as e:
        logger.error(f"Error during cascade cleanup: {str(e)}")

async def _delete_video_file(video_path: str):
    """
    Delete video file from storage.
    
    Args:
        video_path: Path to video file
    """
    try:
        import os
        from pathlib import Path
        
        # Handle different path formats
        if video_path.startswith('/app/'):
            # Container path
            file_path = Path(video_path)
        elif video_path.startswith('storage/'):
            # Relative path
            file_path = Path(video_path)
        elif video_path.startswith('/tmp/storage/'):
            # Convert to container path
            file_path = Path(video_path.replace('/tmp/storage/', '/app/storage/'))
        else:
            # Assume it's a filename in clips directory
            file_path = Path(f"/app/storage/clips/{os.path.basename(video_path)}")
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted video file: {file_path}")
        else:
            logger.warning(f"Video file not found: {file_path}")
            
    except Exception as e:
        logger.error(f"Error deleting video file {video_path}: {str(e)}")

async def _cleanup_compiled_workouts(source_url: str):
    """
    Clean up compiled workouts that reference exercises from a specific URL.
    
    Args:
        source_url: URL of the source video
    """
    try:
        from app.database.compilation_operations import get_compiled_workouts_by_source_url, delete_compiled_workout
        
        # Get compiled workouts that reference this source
        compiled_workouts = await get_compiled_workouts_by_source_url(source_url)
        
        for workout in compiled_workouts:
            # Delete the compiled video file
            video_path = workout.get('video_path', '')
            if video_path:
                await _delete_video_file(video_path)
            
            # Delete from database
            await delete_compiled_workout(workout['id'])
            
        if compiled_workouts:
            logger.info(f"Cleaned up {len(compiled_workouts)} compiled workouts for URL: {source_url}")
            
    except Exception as e:
        logger.error(f"Error cleaning up compiled workouts: {str(e)}")

async def delete_exercises_by_url(url: str) -> int:
    """
    Delete all exercises for a specific URL with cascade cleanup.
    
    Args:
        url: Video URL to delete
        
    Returns:
        Number of exercises deleted
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        # Get all exercises for this URL first
        rows = await conn.fetch("""
            SELECT * FROM exercises WHERE url = $1
        """, url)
        
        exercises = [dict(row) for row in rows]
        
        # Delete from database
        result = await conn.execute("""
            DELETE FROM exercises WHERE url = $1
        """, url)
        
        # Extract count from result string like "DELETE 5"
        deleted_count = int(result.split()[1]) if result.startswith("DELETE") else 0
        
        if deleted_count > 0:
            # Cascade cleanup for all deleted exercises
            for exercise_data in exercises:
                await _cascade_cleanup_exercise(exercise_data)
        
        logger.info(f"Deleted {deleted_count} exercises for URL: {url}")
        return deleted_count

async def delete_exercises_by_criteria(
    fitness_level_min: Optional[int] = None,
    fitness_level_max: Optional[int] = None,
    intensity_min: Optional[int] = None,
    intensity_max: Optional[int] = None,
    exercise_name_pattern: Optional[str] = None,
    created_before: Optional[str] = None,
    created_after: Optional[str] = None
) -> int:
    """
    Delete exercises based on criteria with cascade cleanup.
    
    Args:
        fitness_level_min: Minimum fitness level
        fitness_level_max: Maximum fitness level
        intensity_min: Minimum intensity
        intensity_max: Maximum intensity
        exercise_name_pattern: Pattern to match exercise names
        created_before: Delete exercises created before this date (ISO format)
        created_after: Delete exercises created after this date (ISO format)
        
    Returns:
        Number of exercises deleted
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        # Build dynamic query to get exercises to delete
        conditions = []
        params = []
        param_count = 0
        
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
        
        if exercise_name_pattern:
            param_count += 1
            conditions.append(f"exercise_name ILIKE ${param_count}")
            # Escape % characters to prevent format specifier errors
            escaped_pattern = exercise_name_pattern.replace('%', '%%')
            params.append(f"%{escaped_pattern}%")
        
        if created_before:
            param_count += 1
            conditions.append(f"created_at < ${param_count}")
            params.append(created_before)
        
        if created_after:
            param_count += 1
            conditions.append(f"created_at > ${param_count}")
            params.append(created_after)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get exercises to delete
        query_sql = f"""
            SELECT * FROM exercises 
            WHERE {where_clause}
        """
        
        rows = await conn.fetch(query_sql, *params)
        exercises = [dict(row) for row in rows]
        
        if not exercises:
            return 0
        
        # Delete from database
        delete_sql = f"""
            DELETE FROM exercises 
            WHERE {where_clause}
        """
        
        result = await conn.execute(delete_sql, *params)
        deleted_count = int(result.split()[1]) if result.startswith("DELETE") else 0
        
        if deleted_count > 0:
            # Cascade cleanup for all deleted exercises
            for exercise_data in exercises:
                await _cascade_cleanup_exercise(exercise_data)
        
        logger.info(f"Deleted {deleted_count} exercises based on criteria")
        return deleted_count

async def delete_all_exercises() -> int:
    """
    Delete ALL exercises from the database with cascade cleanup.
    
    Returns:
        Number of exercises deleted
    """
    pool = await get_database_connection()
    
    async with pool.acquire() as conn:
        # Get all exercises first for cleanup
        rows = await conn.fetch("SELECT * FROM exercises")
        exercises = [dict(row) for row in rows]
        
        # Delete from database
        result = await conn.execute("DELETE FROM exercises")
        deleted_count = int(result.split()[1]) if result.startswith("DELETE") else 0
        
        if deleted_count > 0:
            # Cascade cleanup for all deleted exercises
            for exercise_data in exercises:
                await _cascade_cleanup_exercise(exercise_data)
            
            # Clean up all compiled workouts
            try:
                from app.database.compilation_operations import delete_all_compiled_workouts
                await delete_all_compiled_workouts()
            except Exception as e:
                logger.error(f"Error cleaning up compiled workouts: {str(e)}")
        
        logger.info(f"Deleted {deleted_count} exercises from database")
        return deleted_count

async def close_database():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")

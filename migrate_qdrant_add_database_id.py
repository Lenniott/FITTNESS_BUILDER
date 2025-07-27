#!/usr/bin/env python3
"""
Migration script to add database_id to existing Qdrant points.

This script:
1. Fetches all exercises from PostgreSQL
2. Updates existing Qdrant points to include database_id in metadata
3. Ensures future vectorization includes database_id

Usage:
    python3 migrate_qdrant_add_database_id.py
"""

import asyncio
import os
import logging
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_database_connection():
    """Get database connection pool."""
    import asyncpg
    return await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "192.168.0.47"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "fitness_builder")
    )

def get_qdrant_client():
    """Get Qdrant client."""
    from qdrant_client import QdrantClient
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "192.168.0.47"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
        api_key=os.getenv("QDRANT_API_KEY")
    )

async def migrate_qdrant_points():
    """Migrate existing Qdrant points to include database_id."""
    try:
        # Get database connection
        pool = await get_database_connection()
        
        # Get all exercises from PostgreSQL
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, qdrant_id, exercise_name 
                FROM exercises 
                WHERE qdrant_id IS NOT NULL
                ORDER BY created_at DESC
            """)
        
        logger.info(f"Found {len(rows)} exercises with qdrant_ids")
        
        # Get Qdrant client
        qdrant_client = get_qdrant_client()
        
        # Process each exercise
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for row in rows:
            try:
                database_id = str(row['id'])
                qdrant_id = str(row['qdrant_id'])
                exercise_name = row['exercise_name']
                
                # Get the existing point from Qdrant
                try:
                    point = qdrant_client.retrieve(
                        collection_name="fitness_video_clips",
                        ids=[qdrant_id]
                    )
                    
                    if not point:
                        logger.warning(f"Point {qdrant_id} not found in Qdrant for {exercise_name}")
                        skipped_count += 1
                        continue
                    
                    # Get the first (and only) point
                    point_data = point[0]
                    payload = point_data.payload
                    
                    # Check if database_id already exists
                    if 'database_id' in payload:
                        logger.info(f"Point {qdrant_id} already has database_id for {exercise_name}")
                        skipped_count += 1
                        continue
                    
                    # Add database_id to payload
                    payload['database_id'] = database_id
                    
                    # Update the point in Qdrant
                    qdrant_client.upsert(
                        collection_name="fitness_video_clips",
                        points=[{
                            'id': qdrant_id,
                            'payload': payload
                        }]
                    )
                    
                    logger.info(f"Updated point {qdrant_id} with database_id {database_id} for {exercise_name}")
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error updating point {qdrant_id} for {exercise_name}: {str(e)}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing exercise {row.get('exercise_name', 'Unknown')}: {str(e)}")
                error_count += 1
        
        logger.info(f"Migration complete:")
        logger.info(f"  - Updated: {updated_count}")
        logger.info(f"  - Skipped (already updated): {skipped_count}")
        logger.info(f"  - Errors: {error_count}")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

async def main():
    """Main migration function."""
    logger.info("Starting Qdrant migration to add database_id...")
    await migrate_qdrant_points()
    logger.info("Migration completed!")

if __name__ == "__main__":
    asyncio.run(main()) 
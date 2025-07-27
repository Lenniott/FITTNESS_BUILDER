#!/usr/bin/env python3
"""
Script to fix the database schema by dropping and recreating the workout_routines table.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
from app.database.operations import get_database_connection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_database_schema():
    """Drop and recreate the workout_routines table with the correct schema."""
    print("🔧 Fixing Database Schema")
    print("=" * 50)
    
    try:
        pool = await get_database_connection()
        
        async with pool.acquire() as conn:
            # Check if the table exists and what its current structure is
            print("\n📊 Checking current table structure...")
            
            # Check if table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'workout_routines'
                )
            """)
            
            if table_exists:
                print("✅ Table exists, checking structure...")
                
                # Get current columns
                columns = await conn.fetch("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'workout_routines'
                    ORDER BY ordinal_position
                """)
                
                print("   Current columns:")
                for col in columns:
                    print(f"   - {col['column_name']}: {col['data_type']}")
                
                # Check if old columns exist
                old_columns = ['user_requirements', 'target_duration', 'intensity_level', 'format', 'routine_data']
                has_old_columns = any(col['column_name'] in old_columns for col in columns)
                
                if has_old_columns:
                    print("\n⚠️  Found old schema columns. Dropping and recreating table...")
                    
                    # Drop the table
                    await conn.execute("DROP TABLE IF EXISTS workout_routines CASCADE")
                    print("✅ Dropped old table")
                    
                    # Recreate with correct schema
                    await conn.execute("""
                        CREATE TABLE workout_routines (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            name VARCHAR(200) NOT NULL,
                            description TEXT,
                            exercise_ids TEXT[] NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create indexes
                    await conn.execute("""
                        CREATE INDEX idx_workout_routines_name ON workout_routines(name)
                    """)
                    
                    await conn.execute("""
                        CREATE INDEX idx_workout_routines_created_at ON workout_routines(created_at)
                    """)
                    
                    print("✅ Recreated table with correct schema")
                    
                    # Verify the new structure
                    new_columns = await conn.fetch("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'workout_routines'
                        ORDER BY ordinal_position
                    """)
                    
                    print("\n   New columns:")
                    for col in new_columns:
                        print(f"   - {col['column_name']}: {col['data_type']}")
                    
                else:
                    print("✅ Table already has correct schema")
            else:
                print("📝 Table doesn't exist, creating with correct schema...")
                
                # Create with correct schema
                await conn.execute("""
                    CREATE TABLE workout_routines (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(200) NOT NULL,
                        description TEXT,
                        exercise_ids TEXT[] NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                await conn.execute("""
                    CREATE INDEX idx_workout_routines_name ON workout_routines(name)
                """)
                
                await conn.execute("""
                    CREATE INDEX idx_workout_routines_created_at ON workout_routines(created_at)
                """)
                
                print("✅ Created table with correct schema")
        
        print("\n" + "=" * 50)
        print("🎉 Database schema fix complete!")
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_database_schema()) 
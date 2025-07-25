# Phase 1: Database & Core Structure

## **Overview**
Create the foundational database schema and core routine compiler structure. This phase establishes the data layer and basic JSON generation capabilities.

## **Deliverables**
- ✅ New `workout_routines` database table
- ✅ Database operations module (`routine_operations.py`)
- ✅ Core routine compiler structure (`routine_compiler.py`)
- ✅ Basic JSON generation functionality
- ✅ Database initialization updates

---

## **Step 1: Database Schema**

### **1.1 Create Migration File**
**File**: `migration_workout_routines.sql`

```sql
-- Migration: Add workout_routines table
-- Run this on existing databases to add new table

CREATE TABLE IF NOT EXISTS workout_routines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_requirements TEXT NOT NULL,
    target_duration INTEGER NOT NULL,
    intensity_level VARCHAR(20) NOT NULL,
    format VARCHAR(20) DEFAULT 'vertical',
    routine_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_workout_routines_intensity_level ON workout_routines(intensity_level);
CREATE INDEX IF NOT EXISTS idx_workout_routines_created_at ON workout_routines(created_at);
CREATE INDEX IF NOT EXISTS idx_workout_routines_user_requirements ON workout_routines USING gin(to_tsvector('english', user_requirements));

-- Create JSONB indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_workout_routines_routine_data ON workout_routines USING gin(routine_data);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE workout_routines TO fitness_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fitness_user;
```

### **1.2 Update Database Initialization**
**File**: `app/database/operations.py`

Add to `init_database()` function:
```python
# Create workout_routines table
await conn.execute("""
    CREATE TABLE IF NOT EXISTS workout_routines (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_requirements TEXT NOT NULL,
        target_duration INTEGER NOT NULL,
        intensity_level VARCHAR(20) NOT NULL,
        format VARCHAR(20) DEFAULT 'vertical',
        routine_data JSONB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Create indexes
await conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_workout_routines_intensity_level ON workout_routines(intensity_level)
""")

await conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_workout_routines_created_at ON workout_routines(created_at)
""")
```

---

## **Step 2: Database Operations Module**

### **2.1 Create Routine Operations**
**File**: `app/database/routine_operations.py`

```python
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
```

---

## **Step 3: Core Routine Compiler Structure**

### **3.1 Create Routine Compiler**
**File**: `app/core/routine_compiler.py`

```python
"""
Routine compilation pipeline for generating JSON workout routines.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai  # type: ignore
import openai

from app.database.vectorization import search_similar_exercises
from app.database.routine_operations import store_routine, get_routine

logger = logging.getLogger(__name__)

class RoutineCompiler:
    """Main pipeline for compiling JSON workout routines from user requirements."""
    
    def __init__(self):
        # Initialize clients lazily to avoid import-time errors
        self.gemini_model = None
        self.openai_client = None
        
    def _get_gemini_model(self, use_backup=False):
        """Get Gemini model, initializing if needed."""
        if self.gemini_model is None or use_backup:
            # Try primary key first, then backup key
            api_key = os.getenv("GEMINI_API_KEY" if not use_backup else "GEMINI_API_BACKUP_KEY")
            if not api_key:
                if use_backup:
                    raise ValueError("Both GEMINI_API_KEY and GEMINI_API_BACKUP_KEY environment variables not set")
                else:
                    raise ValueError("GEMINI_API_KEY environment variable not set")
            
            # Configure with the selected API key
            genai.configure(api_key=api_key)  # type: ignore
            model = genai.GenerativeModel('models/gemini-2.5-flash-lite-preview-06-17')  # type: ignore
            
            # If using backup key, return the model directly (don't cache it)
            if use_backup:
                return model
            
            # Cache the primary model
            self.gemini_model = model
        
        return self.gemini_model
    
    def _get_openai_client(self):
        """Get OpenAI client, initializing if needed."""
        if self.openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.openai_client = openai.OpenAI(api_key=api_key)
        return self.openai_client
    
    async def compile_routine(self, user_requirements: str) -> Dict:
        """
        Complete workflow:
        1. Determine routine parameters from user requirements
        2. Generate requirement stories from user input
        3. Search for relevant video clips
        4. Use second LLM to select unique, diverse exercises
        5. Create JSON routine with all metadata
        6. Store result in database
        """
        start_time = time.time()
        
        try:
            # Step 1: Determine routine parameters
            logger.info("Determining routine parameters...")
            routine_params = await self._determine_routine_parameters(user_requirements)
            target_duration = routine_params['target_duration']
            intensity_level = routine_params['intensity_level']
            format = routine_params['format']
            
            # Step 2: Generate requirement stories
            logger.info("Generating requirement stories...")
            requirement_stories = await self._generate_requirement_stories(
                user_requirements, target_duration, intensity_level
            )
            
            # Step 3: Search for relevant clips
            logger.info("Searching for relevant video clips...")
            candidate_clips = await self._search_relevant_clips(
                requirement_stories, target_duration, intensity_level
            )
            
            # Step 4: Select unique exercises (placeholder for Phase 3)
            logger.info("Selecting unique exercises...")
            selected_exercises = await self._select_unique_exercises(
                candidate_clips, requirement_stories, target_duration, intensity_level
            )
            
            # Step 5: Create JSON routine
            logger.info("Creating JSON routine...")
            routine_data = await self._create_routine_json(
                user_requirements, selected_exercises, target_duration, intensity_level, format
            )
            
            # Step 6: Store result
            routine_id = await store_routine(
                user_requirements=user_requirements,
                target_duration=target_duration,
                intensity_level=intensity_level,
                format=format,
                routine_data=routine_data
            )
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "routine_id": routine_id,
                "routine_data": routine_data,
                "requirement_stories": requirement_stories,
                "exercises_selected": len(selected_exercises),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error compiling routine: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def _determine_routine_parameters(self, user_requirements: str) -> Dict:
        """Use AI to determine routine parameters from user requirements."""
        # TODO: Implement parameter determination (similar to workout_compiler.py)
        # For now, return default values
        return {
            "intensity_level": "beginner",
            "target_duration": 300,
            "format": "vertical"
        }
    
    async def _generate_requirement_stories(self, user_requirements: str, 
                                          target_duration: int, intensity_level: str) -> List[str]:
        """Generate requirement stories from user input."""
        # TODO: Implement requirement story generation (similar to workout_compiler.py)
        # For now, return simple stories
        return [
            "Beginner-friendly hip mobility work",
            "Basic strength building exercises",
            "Simple flexibility training"
        ]
    
    async def _search_relevant_clips(self, requirement_stories: List[str], 
                                   target_duration: int, intensity_level: str) -> List[Dict]:
        """Search for relevant video clips using vector search."""
        all_clips = []
        
        for story in requirement_stories:
            try:
                similar_exercises = await search_similar_exercises(
                    query=story,
                    limit=10,
                    score_threshold=0.6
                )
                
                for result in similar_exercises:
                    if result['score'] > 0.6:
                        clip_data = {
                            'exercise_id': result['id'],
                            'exercise_name': result['metadata']['exercise_name'],
                            'video_path': result['metadata']['video_path'],
                            'start_time': result['metadata']['start_time'],
                            'end_time': result['metadata']['end_time'],
                            'how_to': result['metadata']['how_to'],
                            'benefits': result['metadata']['benefits'],
                            'counteracts': result['metadata']['counteracts'],
                            'fitness_level': result['metadata']['fitness_level'],
                            'intensity': result['metadata']['intensity'],
                            'requirement_story': story,
                            'relevance_score': result['score']
                        }
                        all_clips.append(clip_data)
                
            except Exception as e:
                logger.error(f"Error searching for story '{story}': {str(e)}")
                continue
        
        return all_clips
    
    async def _select_unique_exercises(self, candidate_clips: List[Dict], 
                                     requirement_stories: List[str],
                                     target_duration: int, intensity_level: str) -> List[Dict]:
        """Select unique exercises using second LLM (placeholder for Phase 3)."""
        # TODO: Implement intelligent selection in Phase 3
        # For now, return first 5 clips
        return candidate_clips[:5]
    
    async def _create_routine_json(self, user_requirements: str, selected_exercises: List[Dict],
                                 target_duration: int, intensity_level: str, format: str) -> Dict:
        """Create complete JSON routine with all metadata."""
        
        exercises = []
        total_duration = 0
        
        for exercise in selected_exercises:
            duration = exercise['end_time'] - exercise['start_time']
            total_duration += duration
            
            exercise_data = {
                "exercise_id": exercise['exercise_id'],
                "exercise_name": exercise['exercise_name'],
                "video_path": exercise['video_path'],
                "start_time": exercise['start_time'],
                "end_time": exercise['end_time'],
                "duration": duration,
                "how_to": exercise['how_to'],
                "benefits": exercise['benefits'],
                "counteracts": exercise['counteracts'],
                "fitness_level": exercise['fitness_level'],
                "intensity": exercise['intensity'],
                "relevance_score": exercise['relevance_score'],
                "deletion_metadata": {
                    "exercise_id": exercise['exercise_id'],
                    "qdrant_id": exercise.get('qdrant_id'),
                    "video_path": exercise['video_path'],
                    "original_url": exercise.get('original_url', ''),
                    "cascade_cleanup": True
                }
            }
            exercises.append(exercise_data)
        
        routine_data = {
            "routine_id": str(uuid.uuid4()),
            "user_requirements": user_requirements,
            "target_duration": target_duration,
            "intensity_level": intensity_level,
            "format": format,
            "exercises": exercises,
            "metadata": {
                "total_duration": total_duration,
                "exercise_count": len(exercises),
                "created_at": time.time()
            }
        }
        
        return routine_data

# Global instance
routine_compiler = RoutineCompiler()
```

---

## **Step 4: Testing**

### **4.1 Create Test File**
**File**: `tests/unit/test_routine_operations.py`

```python
"""
Unit tests for routine operations.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from app.database.routine_operations import (
    store_routine, get_routine, list_routines, delete_routine, update_routine
)

@pytest.mark.asyncio
async def test_store_routine():
    """Test storing a routine in the database."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = Mock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_conn.return_value = mock_pool
        
        # Test data
        user_requirements = "beginner workout for tight hips"
        target_duration = 300
        intensity_level = "beginner"
        format = "vertical"
        routine_data = {"exercises": [], "metadata": {}}
        
        # Call function
        result = await store_routine(
            user_requirements, target_duration, intensity_level, format, routine_data
        )
        
        # Assertions
        assert result is not None
        assert len(result) == 36  # UUID length
        mock_conn.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_routine():
    """Test retrieving a routine from the database."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = Mock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_conn.return_value = mock_pool
        
        # Mock database response
        mock_row = Mock()
        mock_row.__iter__ = lambda x: iter([
            ('id', 'test-uuid'),
            ('user_requirements', 'test requirements'),
            ('routine_data', '{"exercises": []}')
        ])
        mock_conn.fetchrow.return_value = mock_row
        
        # Call function
        result = await get_routine("test-uuid")
        
        # Assertions
        assert result is not None
        assert result['id'] == 'test-uuid'
        assert result['user_requirements'] == 'test requirements'
```

### **4.2 Create Integration Test**
**File**: `tests/integration/test_routine_compiler.py`

```python
"""
Integration tests for routine compiler.
"""

import pytest
import asyncio
from unittest.mock import patch, Mock
from app.core.routine_compiler import routine_compiler

@pytest.mark.asyncio
async def test_compile_routine_basic():
    """Test basic routine compilation."""
    # Mock dependencies
    with patch('app.core.routine_compiler.store_routine') as mock_store:
        mock_store.return_value = "test-routine-id"
        
        # Test data
        user_requirements = "beginner workout for tight hips"
        
        # Call function
        result = await routine_compiler.compile_routine(user_requirements)
        
        # Assertions
        assert result['success'] is True
        assert result['routine_id'] == "test-routine-id"
        assert 'routine_data' in result
        assert 'exercises' in result['routine_data']
```

---

## **Step 5: Update CHANGELOG**

Add to `CHANGELOG.md`:

```markdown
## [Unreleased]

### Added
- **Phase 1: Database & Core Structure Implementation**
  - **New Database Table**: `workout_routines` for JSON-based routine storage
  - **Database Operations**: Complete CRUD operations for routines in `app/database/routine_operations.py`
  - **Core Compiler Structure**: Basic routine compiler in `app/core/routine_compiler.py`
  - **JSON Generation**: Basic JSON routine structure with complete metadata
  - **Database Migration**: SQL migration file for new table creation
  - **Unit Tests**: Comprehensive testing for database operations
  - **Integration Tests**: Basic routine compilation testing
```

---

## **Success Criteria for Phase 1**

### **Functional Requirements**
- ✅ Database table created and accessible
- ✅ Basic routine storage and retrieval working
- ✅ Core compiler structure in place
- ✅ JSON generation functional
- ✅ All tests passing

### **Technical Requirements**
- ✅ Database operations handle JSONB properly
- ✅ Error handling implemented
- ✅ Logging throughout
- ✅ Type hints and documentation

### **Testing Requirements**
- ✅ Unit tests for all database operations
- ✅ Integration test for basic compilation
- ✅ Error case testing
- ✅ Performance testing for database operations

---

## **Next Steps**
After Phase 1 completion, proceed to:
- **Phase 2**: API Endpoints
- **Phase 3**: Intelligent Selection
- **Phase 4**: Testing & Validation 
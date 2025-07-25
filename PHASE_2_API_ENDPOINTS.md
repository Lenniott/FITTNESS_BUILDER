# Phase 2: API Endpoints

## **Overview**
Create new API endpoints for JSON-based workout routines, replacing the current video compilation endpoints. This phase establishes the REST API layer for routine generation and management.

## **Deliverables**
- ✅ New routine endpoints (`routine_endpoints.py`)
- ✅ Pydantic models for requests/responses
- ✅ Integration with routine compiler
- ✅ Complete CRUD operations
- ✅ Error handling and validation
- ✅ API documentation updates

---

## **Step 1: Create Pydantic Models**

### **1.1 Create Request/Response Models**
**File**: `app/api/routine_models.py`

```python
"""
Pydantic models for routine API endpoints.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class RoutineRequest(BaseModel):
    """Request model for routine generation."""
    user_requirements: str = Field(..., description="Natural language workout requirements")
    target_duration: Optional[int] = Field(None, description="Target duration in seconds")
    intensity_level: Optional[str] = Field(None, description="Intensity level (beginner/intermediate/advanced)")
    format: Optional[str] = Field("vertical", description="Format (vertical/square)")

class ExerciseData(BaseModel):
    """Model for exercise data in routine."""
    exercise_id: str
    exercise_name: str
    video_path: str
    start_time: float
    end_time: float
    duration: float
    how_to: str
    benefits: str
    counteracts: str
    fitness_level: int
    intensity: int
    relevance_score: float
    uniqueness_score: Optional[float] = None
    selection_reason: Optional[str] = None
    deletion_metadata: Dict

class RoutineMetadata(BaseModel):
    """Model for routine metadata."""
    total_duration: int
    exercise_count: int
    variety_score: Optional[float] = None
    progression_flow: Optional[str] = None
    ai_selection_notes: Optional[str] = None
    created_at: float

class RoutineData(BaseModel):
    """Model for complete routine data."""
    routine_id: str
    user_requirements: str
    target_duration: int
    intensity_level: str
    format: str
    exercises: List[ExerciseData]
    metadata: RoutineMetadata

class RoutineResponse(BaseModel):
    """Response model for routine generation."""
    success: bool
    routine_id: Optional[str] = None
    routine_data: Optional[RoutineData] = None
    requirement_stories: Optional[List[str]] = None
    exercises_selected: Optional[int] = None
    processing_time: float
    error: Optional[str] = None

class RoutineListResponse(BaseModel):
    """Response model for routine listing."""
    routines: List[RoutineData]
    total_count: int
    limit: int
    offset: int

class DeleteResponse(BaseModel):
    """Response model for deletion operations."""
    success: bool
    message: str
    deleted_count: Optional[int] = None

class RemoveExerciseRequest(BaseModel):
    """Request model for removing exercise from routine."""
    delete_exercise: bool = Field(False, description="Whether to completely delete the exercise")
```

---

## **Step 2: Create Routine Endpoints**

### **2.1 Create Routine Endpoints Module**
**File**: `app/api/routine_endpoints.py`

```python
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
    get_routine, list_routines, delete_routine, update_routine
)
from app.api.routine_models import (
    RoutineRequest, RoutineResponse, RoutineListResponse, 
    DeleteResponse, RemoveExerciseRequest
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
async def remove_exercise_from_routine(
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
```

---

## **Step 3: Update Main API**

### **3.1 Update Main API File**
**File**: `app/api/main.py`

Add the new routine endpoints:

```python
# Include routine endpoints
from app.api.routine_endpoints import router as routine_router
app.include_router(routine_router, prefix="/api/v1")
```

### **3.2 Update API Documentation**
**File**: `README.md`

Add new API documentation section:

```markdown
## 📊 API Endpoints

### Routine Generation
- `POST /api/v1/routine/generate` - Generate JSON workout routine
- `GET /api/v1/routine/{id}` - Get routine by ID
- `GET /api/v1/routines` - List all routines
- `DELETE /api/v1/routine/{id}` - Delete routine
- `POST /api/v1/routine/{id}/exercise/{exercise_id}/remove` - Remove exercise from routine

### Core Processing (Legacy)
- `POST /api/v1/process` - Process fitness video from URL
- `GET /api/v1/exercises` - List all exercises
- `GET /api/v1/exercises/{id}` - Get specific exercise
```

---

## **Step 4: Create Tests**

### **4.1 Create API Tests**
**File**: `tests/integration/test_routine_endpoints.py`

```python
"""
Integration tests for routine endpoints.
"""

import pytest
import asyncio
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_generate_routine():
    """Test routine generation endpoint."""
    # Mock the routine compiler
    with patch('app.api.routine_endpoints.routine_compiler') as mock_compiler:
        mock_compiler.compile_routine.return_value = {
            "success": True,
            "routine_id": "test-routine-id",
            "routine_data": {
                "routine_id": "test-routine-id",
                "user_requirements": "beginner workout",
                "target_duration": 300,
                "intensity_level": "beginner",
                "format": "vertical",
                "exercises": [],
                "metadata": {
                    "total_duration": 0,
                    "exercise_count": 0,
                    "created_at": 1234567890
                }
            },
            "requirement_stories": ["test story"],
            "exercises_selected": 0,
            "processing_time": 1.0
        }
        
        # Test request
        response = client.post(
            "/api/v1/routine/generate",
            json={
                "user_requirements": "beginner workout for tight hips"
            }
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["routine_id"] == "test-routine-id"

@pytest.mark.asyncio
async def test_get_routine():
    """Test getting routine by ID."""
    # Mock database operation
    with patch('app.api.routine_endpoints.get_routine') as mock_get:
        mock_get.return_value = {
            "id": "test-routine-id",
            "routine_data": {
                "routine_id": "test-routine-id",
                "user_requirements": "beginner workout",
                "target_duration": 300,
                "intensity_level": "beginner",
                "format": "vertical",
                "exercises": [],
                "metadata": {
                    "total_duration": 0,
                    "exercise_count": 0,
                    "created_at": 1234567890
                }
            }
        }
        
        # Test request
        response = client.get("/api/v1/routine/test-routine-id")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["routine_id"] == "test-routine-id"

@pytest.mark.asyncio
async def test_list_routines():
    """Test listing routines."""
    # Mock database operation
    with patch('app.api.routine_endpoints.list_routines') as mock_list:
        mock_list.return_value = [
            {
                "id": "test-routine-id",
                "routine_data": {
                    "routine_id": "test-routine-id",
                    "user_requirements": "beginner workout",
                    "target_duration": 300,
                    "intensity_level": "beginner",
                    "format": "vertical",
                    "exercises": [],
                    "metadata": {
                        "total_duration": 0,
                        "exercise_count": 0,
                        "created_at": 1234567890
                    }
                }
            }
        ]
        
        # Test request
        response = client.get("/api/v1/routines?limit=10&offset=0")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["routines"]) == 1
        assert data["total_count"] == 1
```

---

## **Step 5: Update CHANGELOG**

Add to `CHANGELOG.md`:

```markdown
## [Unreleased]

### Added
- **Phase 2: API Endpoints Implementation**
  - **New Routine Endpoints**: Complete REST API for JSON-based routine generation
  - **Pydantic Models**: Comprehensive request/response models for type safety
  - **Routine Generation**: `POST /api/v1/routine/generate` endpoint
  - **Routine Management**: CRUD operations for routines
  - **Exercise Removal**: Remove exercises from routines with optional deletion
  - **Status Endpoint**: Get routine status and metadata
  - **Integration Tests**: Comprehensive API testing
  - **Error Handling**: Robust error handling and validation
  - **API Documentation**: Complete endpoint documentation
```

---

## **Success Criteria for Phase 2**

### **Functional Requirements**
- ✅ All routine endpoints working correctly
- ✅ Proper request/response validation
- ✅ Error handling for all edge cases
- ✅ Integration with routine compiler
- ✅ Complete CRUD operations

### **Technical Requirements**
- ✅ Pydantic models for type safety
- ✅ Proper HTTP status codes
- ✅ Comprehensive logging
- ✅ API documentation
- ✅ Integration tests passing

### **Testing Requirements**
- ✅ Unit tests for all endpoints
- ✅ Integration tests for API flow
- ✅ Error case testing
- ✅ Performance testing for endpoints

---

## **Next Steps**
After Phase 2 completion, proceed to:
- **Phase 3**: Intelligent Selection
- **Phase 4**: Testing & Validation 
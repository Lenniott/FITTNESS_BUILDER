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
        async def mock_compile_routine(user_requirements):
            return {
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
        mock_compiler.compile_routine = mock_compile_routine
        
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
async def test_generate_routine_empty_requirements():
    """Test routine generation with empty requirements."""
    # Test request
    response = client.post(
        "/api/v1/routine/generate",
        json={
            "user_requirements": ""
        }
    )
    
    # Assertions
    assert response.status_code == 400
    data = response.json()
    assert "empty" in data["detail"].lower()

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
async def test_get_routine_not_found():
    """Test getting non-existent routine."""
    # Mock database operation
    with patch('app.api.routine_endpoints.get_routine') as mock_get:
        mock_get.return_value = None
        
        # Test request
        response = client.get("/api/v1/routine/non-existent-id")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

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

@pytest.mark.asyncio
async def test_delete_routine():
    """Test deleting routine."""
    # Mock database operations
    with patch('app.api.routine_endpoints.get_routine') as mock_get:
        with patch('app.api.routine_endpoints.delete_routine') as mock_delete:
            mock_get.return_value = {"id": "test-routine-id"}
            mock_delete.return_value = True
            
            # Test request
            response = client.delete("/api/v1/routine/test-routine-id")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["deleted_count"] == 1

@pytest.mark.asyncio
async def test_delete_routine_not_found():
    """Test deleting non-existent routine."""
    # Mock database operation
    with patch('app.api.routine_endpoints.get_routine') as mock_get:
        mock_get.return_value = None
        
        # Test request
        response = client.delete("/api/v1/routine/non-existent-id")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

@pytest.mark.asyncio
async def test_remove_exercise_from_routine():
    """Test removing exercise from routine."""
    # Mock database operations
    with patch('app.api.routine_endpoints.get_routine') as mock_get:
        with patch('app.api.routine_endpoints.update_routine') as mock_update:
            mock_get.return_value = {
                "id": "test-routine-id",
                "routine_data": {
                    "routine_id": "test-routine-id",
                    "user_requirements": "beginner workout",
                    "target_duration": 300,
                    "intensity_level": "beginner",
                    "format": "vertical",
                    "exercises": [
                        {
                            "exercise_id": "exercise-1",
                            "exercise_name": "Test Exercise 1",
                            "video_path": "/test/path1.mp4",
                            "start_time": 0.0,
                            "end_time": 30.0,
                            "duration": 30,
                            "how_to": "Test instructions 1",
                            "benefits": "Test benefits 1",
                            "counteracts": "Test problems 1",
                            "fitness_level": 5,
                            "intensity": 5,
                            "relevance_score": 0.8,
                            "deletion_metadata": {
                                "exercise_id": "exercise-1",
                                "video_path": "/test/path1.mp4",
                                "cascade_cleanup": True
                            }
                        },
                        {
                            "exercise_id": "exercise-2",
                            "exercise_name": "Test Exercise 2",
                            "video_path": "/test/path2.mp4",
                            "start_time": 0.0,
                            "end_time": 45.0,
                            "duration": 45,
                            "how_to": "Test instructions 2",
                            "benefits": "Test benefits 2",
                            "counteracts": "Test problems 2",
                            "fitness_level": 5,
                            "intensity": 5,
                            "relevance_score": 0.8,
                            "deletion_metadata": {
                                "exercise_id": "exercise-2",
                                "video_path": "/test/path2.mp4",
                                "cascade_cleanup": True
                            }
                        }
                    ],
                    "metadata": {
                        "total_duration": 75,
                        "exercise_count": 2,
                        "created_at": 1234567890
                    }
                }
            }
            mock_update.return_value = True
            
            # Test request
            response = client.post(
                "/api/v1/routine/test-routine-id/exercise/exercise-1/remove",
                json={"delete_exercise": False}
            )
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["routine_id"] == "test-routine-id"
            assert len(data["exercises"]) == 1

@pytest.mark.asyncio
async def test_remove_exercise_not_found():
    """Test removing non-existent exercise from routine."""
    # Mock database operation
    with patch('app.api.routine_endpoints.get_routine') as mock_get:
        mock_get.return_value = {
            "id": "test-routine-id",
            "routine_data": {
                "routine_id": "test-routine-id",
                "exercises": [
                    {
                        "exercise_id": "exercise-1",
                        "exercise_name": "Test Exercise 1",
                        "video_path": "/test/path1.mp4",
                        "start_time": 0.0,
                        "end_time": 30.0,
                        "duration": 30,
                        "how_to": "Test instructions 1",
                        "benefits": "Test benefits 1",
                        "counteracts": "Test problems 1",
                        "fitness_level": 5,
                        "intensity": 5,
                        "relevance_score": 0.8,
                        "deletion_metadata": {
                            "exercise_id": "exercise-1",
                            "video_path": "/test/path1.mp4",
                            "cascade_cleanup": True
                        }
                    }
                ],
                "metadata": {
                    "total_duration": 30,
                    "exercise_count": 1,
                    "created_at": 1234567890
                }
            }
        }
        
        # Test request
        response = client.post(
            "/api/v1/routine/test-routine-id/exercise/non-existent-exercise/remove"
        )
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

@pytest.mark.asyncio
async def test_delete_exercise_from_routine():
    """Test completely deleting exercise from routine and system."""
    # Mock database operations
    with patch('app.api.routine_endpoints.delete_exercise_from_routine_and_system') as mock_delete:
        mock_delete.return_value = True
        
        # Test request
        response = client.post(
            "/api/v1/routine/test-routine-id/exercise/exercise-1/delete"
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 1

@pytest.mark.asyncio
async def test_get_routine_status():
    """Test getting routine status."""
    # Mock database operation
    with patch('app.api.routine_endpoints.get_routine') as mock_get:
        mock_get.return_value = {
            "id": "test-routine-id",
            "created_at": "2024-01-01T00:00:00Z",
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
        response = client.get("/api/v1/routine/test-routine-id/status")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["routine_id"] == "test-routine-id"
        assert data["status"] == "completed"
        assert data["exercise_count"] == 0 
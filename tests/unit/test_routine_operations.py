"""
Unit tests for routine operations.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.database.routine_operations import (
    store_routine, get_routine, list_routines, delete_routine, update_routine,
    remove_exercise_from_routine, delete_exercise_from_routine_and_system
)
import json

@pytest.mark.asyncio
async def test_store_routine():
    """Test storing a routine in the database."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
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
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock database response
        mock_row = {
            'id': 'test-uuid',
            'user_requirements': 'test requirements',
            'routine_data': '{"exercises": []}'
        }
        mock_conn.fetchrow.return_value = mock_row
        
        # Call function
        result = await get_routine("test-uuid")
        
        # Assertions
        assert result is not None
        assert result['id'] == 'test-uuid'
        assert result['user_requirements'] == 'test requirements'

@pytest.mark.asyncio
async def test_get_routine_not_found():
    """Test retrieving a non-existent routine."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock database response - no row found
        mock_conn.fetchrow.return_value = None
        
        # Call function
        result = await get_routine("non-existent-uuid")
        
        # Assertions
        assert result is None

@pytest.mark.asyncio
async def test_list_routines():
    """Test listing routines from the database."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock database response
        mock_row1 = {
            'id': 'test-uuid-1',
            'user_requirements': 'test requirements 1',
            'routine_data': '{"exercises": []}'
        }
        mock_row2 = {
            'id': 'test-uuid-2',
            'user_requirements': 'test requirements 2',
            'routine_data': '{"exercises": []}'
        }
        mock_conn.fetch.return_value = [mock_row1, mock_row2]
        
        # Call function
        result = await list_routines(limit=10, offset=0)
        
        # Assertions
        assert len(result) == 2
        assert result[0]['id'] == 'test-uuid-1'
        assert result[1]['id'] == 'test-uuid-2'

@pytest.mark.asyncio
async def test_delete_routine():
    """Test deleting a routine from the database."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock successful deletion
        mock_conn.execute.return_value = "DELETE 1"
        
        # Call function
        result = await delete_routine("test-uuid")
        
        # Assertions
        assert result is True
        mock_conn.execute.assert_called_once()

@pytest.mark.asyncio
async def test_delete_routine_not_found():
    """Test deleting a non-existent routine."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock unsuccessful deletion
        mock_conn.execute.return_value = "DELETE 0"
        
        # Call function
        result = await delete_routine("non-existent-uuid")
        
        # Assertions
        assert result is False

@pytest.mark.asyncio
async def test_update_routine():
    """Test updating a routine in the database."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock successful update
        mock_conn.execute.return_value = "UPDATE 1"
        
        # Test data
        routine_id = "test-uuid"
        routine_data = {"exercises": [{"id": "exercise-1"}], "metadata": {}}
        
        # Call function
        result = await update_routine(routine_id, routine_data)
        
        # Assertions
        assert result is True
        mock_conn.execute.assert_called_once()

@pytest.mark.asyncio
async def test_update_routine_not_found():
    """Test updating a non-existent routine."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock unsuccessful update
        mock_conn.execute.return_value = "UPDATE 0"
        
        # Test data
        routine_id = "non-existent-uuid"
        routine_data = {"exercises": [], "metadata": {}}
        
        # Call function
        result = await update_routine(routine_id, routine_data)
        
        # Assertions
        assert result is False

@pytest.mark.asyncio
async def test_remove_exercise_from_routine():
    """Test removing an exercise from a routine."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock routine data with exercises
        routine_data = {
            "exercises": [
                {"exercise_id": "exercise-1", "duration": 30},
                {"exercise_id": "exercise-2", "duration": 45},
                {"exercise_id": "exercise-3", "duration": 60}
            ],
            "metadata": {
                "exercise_count": 3,
                "total_duration": 135
            }
        }
        
        # Mock database response
        mock_row = {
            'routine_data': json.dumps(routine_data)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        # Mock successful update
        mock_conn.execute.return_value = "UPDATE 1"
        
        # Call function
        result = await remove_exercise_from_routine("test-routine-id", "exercise-2")
        
        # Assertions
        assert result is True
        mock_conn.execute.assert_called_once()
        
        # Verify the update call includes the modified routine data
        call_args = mock_conn.execute.call_args[0]
        updated_routine_data = json.loads(call_args[2])
        assert len(updated_routine_data['exercises']) == 2
        assert updated_routine_data['metadata']['exercise_count'] == 2
        assert updated_routine_data['metadata']['total_duration'] == 90

@pytest.mark.asyncio
async def test_remove_exercise_from_routine_not_found():
    """Test removing a non-existent exercise from a routine."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock routine data
        routine_data = {
            "exercises": [
                {"exercise_id": "exercise-1", "duration": 30}
            ],
            "metadata": {
                "exercise_count": 1,
                "total_duration": 30
            }
        }
        
        # Mock database response
        mock_row = {
            'routine_data': json.dumps(routine_data)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        # Call function
        result = await remove_exercise_from_routine("test-routine-id", "non-existent-exercise")
        
        # Assertions
        assert result is False
        mock_conn.execute.assert_not_called()

@pytest.mark.asyncio
async def test_remove_exercise_from_routine_routine_not_found():
    """Test removing an exercise from a non-existent routine."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock database response - no routine found
        mock_conn.fetchrow.return_value = None
        
        # Call function
        result = await remove_exercise_from_routine("non-existent-routine", "exercise-1")
        
        # Assertions
        assert result is False

@pytest.mark.asyncio
async def test_delete_exercise_from_routine_and_system():
    """Test completely deleting an exercise from routine and system."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock routine data
        routine_data = {
            "exercises": [
                {"exercise_id": "exercise-1", "duration": 30},
                {"exercise_id": "exercise-2", "duration": 45}
            ],
            "metadata": {
                "exercise_count": 2,
                "total_duration": 75
            }
        }
        
        # Mock database responses
        mock_row = {
            'routine_data': json.dumps(routine_data)
        }
        mock_conn.fetchrow.return_value = mock_row
        mock_conn.execute.return_value = "UPDATE 1"
        
        # Mock the delete_exercise function
        with patch('app.database.operations.delete_exercise') as mock_delete_exercise:
            mock_delete_exercise.return_value = True
            
            # Call function
            result = await delete_exercise_from_routine_and_system("test-routine-id", "exercise-1")
            
            # Assertions
            assert result is True
            mock_delete_exercise.assert_called_once_with("exercise-1")

@pytest.mark.asyncio
async def test_delete_exercise_from_routine_and_system_exercise_not_in_routine():
    """Test deleting an exercise that's not in the routine."""
    # Mock database connection
    with patch('app.database.routine_operations.get_database_connection') as mock_get_conn:
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_conn
        mock_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_context
        mock_get_conn.return_value = mock_pool
        
        # Mock routine data
        routine_data = {
            "exercises": [
                {"exercise_id": "exercise-1", "duration": 30}
            ],
            "metadata": {
                "exercise_count": 1,
                "total_duration": 30
            }
        }
        
        # Mock database response
        mock_row = {
            'routine_data': json.dumps(routine_data)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        # Call function
        result = await delete_exercise_from_routine_and_system("test-routine-id", "non-existent-exercise")
        
        # Assertions
        assert result is False 
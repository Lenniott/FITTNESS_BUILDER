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

@pytest.mark.asyncio
async def test_compile_routine_with_error():
    """Test routine compilation with error handling."""
    # Mock dependencies to raise an error
    with patch('app.core.routine_compiler.store_routine') as mock_store:
        mock_store.side_effect = Exception("Database error")
        
        # Test data
        user_requirements = "beginner workout for tight hips"
        
        # Call function
        result = await routine_compiler.compile_routine(user_requirements)
        
        # Assertions
        assert result['success'] is False
        assert 'error' in result
        assert 'Database error' in result['error']

@pytest.mark.asyncio
async def test_routine_compiler_structure():
    """Test that routine compiler creates proper JSON structure."""
    # Mock dependencies
    with patch('app.core.routine_compiler.store_routine') as mock_store:
        mock_store.return_value = "test-routine-id"
        
        # Test data
        user_requirements = "beginner workout for tight hips"
        
        # Call function
        result = await routine_compiler.compile_routine(user_requirements)
        
        # Assertions for JSON structure
        routine_data = result['routine_data']
        
        # Check required fields
        assert 'routine_id' in routine_data
        assert 'user_requirements' in routine_data
        assert 'target_duration' in routine_data
        assert 'intensity_level' in routine_data
        assert 'format' in routine_data
        assert 'exercises' in routine_data
        assert 'metadata' in routine_data
        
        # Check metadata structure
        metadata = routine_data['metadata']
        assert 'total_duration' in metadata
        assert 'exercise_count' in metadata
        assert 'created_at' in metadata
        
        # Check that exercises is a list
        assert isinstance(routine_data['exercises'], list)

@pytest.mark.asyncio
async def test_routine_compiler_exercise_structure():
    """Test that exercises in routine have proper structure."""
    # Mock dependencies
    with patch('app.core.routine_compiler.store_routine') as mock_store:
        mock_store.return_value = "test-routine-id"
        
        # Test data
        user_requirements = "beginner workout for tight hips"
        
        # Call function
        result = await routine_compiler.compile_routine(user_requirements)
        
        # Check exercise structure if exercises exist
        exercises = result['routine_data']['exercises']
        if exercises:
            exercise = exercises[0]
            
            # Check required exercise fields
            assert 'exercise_id' in exercise
            assert 'exercise_name' in exercise
            assert 'video_path' in exercise
            assert 'start_time' in exercise
            assert 'end_time' in exercise
            assert 'duration' in exercise
            assert 'how_to' in exercise
            assert 'benefits' in exercise
            assert 'counteracts' in exercise
            assert 'fitness_level' in exercise
            assert 'intensity' in exercise
            assert 'relevance_score' in exercise
            assert 'deletion_metadata' in exercise
            
            # Check deletion metadata structure
            deletion_metadata = exercise['deletion_metadata']
            assert 'exercise_id' in deletion_metadata
            assert 'video_path' in deletion_metadata
            assert 'cascade_cleanup' in deletion_metadata 
"""
Pytest configuration for the Fitness Builder test suite.
Sets up Python path and common fixtures.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path for all tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables for tests
from dotenv import load_dotenv
load_dotenv()

import pytest

@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture."""
    return {
        "base_url": "http://localhost:8000",
        "api_base": "http://localhost:8000/api/v1",
        "timeout": 300,  # 5 minutes for video processing
        "test_video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll (short, safe)
    }

@pytest.fixture(scope="session")
def sample_exercise_data():
    """Sample exercise data for testing."""
    import uuid
    return {
        "url": "https://www.youtube.com/watch?v=test123",
        "normalized_url": "https://www.youtube.com/watch?v=test123",
        "carousel_index": 1,
        "exercise_name": "Test Push-up",
        "video_path": "storage/clips/test_pushup.mp4",
        "start_time": 10.5,
        "end_time": 25.3,
        "how_to": "Start in plank position, lower body, push back up",
        "benefits": "Strengthens chest, shoulders, and triceps",
        "counteracts": "Improves upper body pushing strength",
        "fitness_level": 3,
        "rounds_reps": "3 sets of 10-15 reps",
        "intensity": 5,
        "qdrant_id": str(uuid.uuid4())
    }

@pytest.fixture(scope="session")
def sample_routine_data():
    """Sample routine data for testing."""
    return {
        "name": "Test Routine",
        "description": "A test routine for API testing",
        "exercise_ids": ["test-exercise-1", "test-exercise-2"]
    } 
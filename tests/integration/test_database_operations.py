#!/usr/bin/env python3
"""
Database integration tests for the Fitness Builder service.
Tests PostgreSQL operations, Qdrant vector operations, and job status management.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import asyncio
import uuid
import json
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock

# Import database modules
from app.database.operations import (
    init_database, store_exercise, get_exercise_by_id, 
    get_exercises_by_url, delete_exercise, store_workout_routine,
    get_workout_routine, get_recent_workout_routines, delete_workout_routine
)
from app.database.vectorization import (
    init_vector_store, store_embedding, search_similar_exercises,
    delete_embedding, get_collection_info
)
from app.database.job_status import create_job, update_job_status, get_job_status

class TestDatabaseOperations:
    """Database integration tests."""
    
    @pytest.fixture
    def sample_exercise_data(self) -> Dict:
        """Sample exercise data for testing."""
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
    
    @pytest.fixture
    def sample_routine_data(self) -> Dict:
        """Sample routine data for testing."""
        return {
            "name": "Test Routine",
            "description": "A test routine for database testing",
            "exercise_ids": ["test-exercise-1", "test-exercise-2"]
        }
    
    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test database initialization."""
        print("\n🗄️ Testing Database Initialization...")
        
        try:
            await init_database()
            print("✅ Database initialization successful")
        except Exception as e:
            print(f"❌ Database initialization failed: {str(e)}")
            pytest.fail(f"Database initialization failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_vector_store_initialization(self):
        """Test vector store initialization."""
        print("\n🔍 Testing Vector Store Initialization...")
        
        try:
            await init_vector_store()
            print("✅ Vector store initialization successful")
        except Exception as e:
            print(f"❌ Vector store initialization failed: {str(e)}")
            pytest.fail(f"Vector store initialization failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_exercise_storage_and_retrieval(self, sample_exercise_data):
        """Test storing and retrieving exercises."""
        print("\n💪 Testing Exercise Storage and Retrieval...")
        
        try:
            # Store exercise
            exercise_id = await store_exercise(**sample_exercise_data)
            assert exercise_id is not None
            print(f"✅ Exercise stored with ID: {exercise_id}")
            
            # Retrieve exercise
            retrieved_exercise = await get_exercise_by_id(exercise_id)
            assert retrieved_exercise is not None
            assert retrieved_exercise["exercise_name"] == sample_exercise_data["exercise_name"]
            print(f"✅ Exercise retrieved: {retrieved_exercise['exercise_name']}")
            
            # Test URL-based retrieval
            exercises_by_url = await get_exercises_by_url(sample_exercise_data["url"])
            assert len(exercises_by_url) > 0
            print(f"✅ Found {len(exercises_by_url)} exercises by URL")
            
            # Clean up
            await delete_exercise(exercise_id)
            print("✅ Exercise deleted successfully")
            
        except Exception as e:
            print(f"❌ Exercise storage/retrieval failed: {str(e)}")
            pytest.fail(f"Exercise storage/retrieval failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_vector_operations(self, sample_exercise_data):
        """Test vector database operations."""
        print("\n🔍 Testing Vector Operations...")
        
        try:
            # Store embedding
            point_id = await store_embedding(sample_exercise_data)
            assert point_id is not None
            print(f"✅ Vector embedding stored with ID: {point_id}")
            
            # Search similar exercises
            search_results = await search_similar_exercises(
                "push-up exercise for beginners",
                limit=5
            )
            assert isinstance(search_results, list)
            print(f"✅ Vector search returned {len(search_results)} results")
            
            # Get collection info
            collection_info = await get_collection_info()
            assert "vectors_count" in collection_info
            print(f"✅ Collection info: {collection_info['vectors_count']} vectors")
            
            # Clean up
            await delete_embedding(point_id)
            print("✅ Vector embedding deleted successfully")
            
        except Exception as e:
            print(f"❌ Vector operations failed: {str(e)}")
            pytest.fail(f"Vector operations failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_routine_crud_operations(self, sample_routine_data):
        """Test routine CRUD operations."""
        print("\n🏋️ Testing Routine CRUD Operations...")
        
        try:
            # Create routine
            routine_id = await store_workout_routine(
                name=sample_routine_data["name"],
                description=sample_routine_data["description"],
                exercise_ids=sample_routine_data["exercise_ids"]
            )
            assert routine_id is not None
            print(f"✅ Routine created with ID: {routine_id}")
            
            # Get routine
            retrieved_routine = await get_workout_routine(routine_id)
            assert retrieved_routine is not None
            assert retrieved_routine["name"] == sample_routine_data["name"]
            print(f"✅ Routine retrieved: {retrieved_routine['name']}")
            
            # List recent routines
            recent_routines = await get_recent_workout_routines(limit=10)
            assert isinstance(recent_routines, list)
            print(f"✅ Found {len(recent_routines)} recent routines")
            
            # Delete routine
            delete_success = await delete_workout_routine(routine_id)
            assert delete_success is True
            print("✅ Routine deleted successfully")
            
            # Verify deletion
            deleted_routine = await get_workout_routine(routine_id)
            assert deleted_routine is None
            print("✅ Routine deletion verified")
            
        except Exception as e:
            print(f"❌ Routine CRUD operations failed: {str(e)}")
            pytest.fail(f"Routine CRUD operations failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_job_status_management(self):
        """Test job status management."""
        print("\n📊 Testing Job Status Management...")
        
        try:
            # Create job
            job_id = str(uuid.uuid4())
            await create_job(job_id)
            print(f"✅ Job created: {job_id}")
            
            # Update job status
            test_result = {"status": "processing", "progress": 50}
            await update_job_status(job_id, "in_progress", test_result)
            print("✅ Job status updated to in_progress")
            
            # Get job status
            job_status = await get_job_status(job_id)
            assert job_status is not None
            assert job_status["status"] == "in_progress"
            print(f"✅ Job status retrieved: {job_status['status']}")
            
            # Update to completed
            final_result = {"status": "completed", "clips": 3}
            await update_job_status(job_id, "done", final_result)
            print("✅ Job status updated to done")
            
            # Verify final status
            final_status = await get_job_status(job_id)
            assert final_status["status"] == "done"
            print("✅ Final job status verified")
            
        except Exception as e:
            print(f"❌ Job status management failed: {str(e)}")
            pytest.fail(f"Job status management failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_data_consistency(self, sample_exercise_data):
        """Test data consistency across storage layers."""
        print("\n🔗 Testing Data Consistency...")
        
        try:
            # Store exercise in PostgreSQL
            exercise_id = await store_exercise(**sample_exercise_data)
            print(f"✅ Exercise stored in PostgreSQL: {exercise_id}")
            
            # Store embedding in Qdrant
            point_id = await store_embedding(sample_exercise_data)
            print(f"✅ Embedding stored in Qdrant: {point_id}")
            
            # Verify data consistency
            retrieved_exercise = await get_exercise_by_id(exercise_id)
            assert retrieved_exercise is not None
            assert retrieved_exercise["exercise_name"] == sample_exercise_data["exercise_name"]
            print("✅ PostgreSQL data consistency verified")
            
            # Test vector search with database enrichment
            search_results = await search_similar_exercises(
                "push-up exercise",
                limit=5
            )
            assert isinstance(search_results, list)
            print(f"✅ Vector search with database enrichment: {len(search_results)} results")
            
            # Clean up both storage layers
            await delete_exercise(exercise_id)  # This should cascade to Qdrant
            print("✅ Cascade cleanup completed")
            
        except Exception as e:
            print(f"❌ Data consistency test failed: {str(e)}")
            pytest.fail(f"Data consistency test failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for database operations."""
        print("\n🚨 Testing Error Handling...")
        
        try:
            # Test invalid exercise ID
            invalid_exercise = await get_exercise_by_id("invalid-id")
            assert invalid_exercise is None
            print("✅ Invalid exercise ID handled correctly")
            
            # Test invalid routine ID
            invalid_routine = await get_workout_routine("invalid-id")
            assert invalid_routine is None
            print("✅ Invalid routine ID handled correctly")
            
            # Test invalid job ID
            invalid_job = await get_job_status("invalid-id")
            assert invalid_job is None
            print("✅ Invalid job ID handled correctly")
            
            # Test vector search with empty query
            empty_results = await search_similar_exercises("", limit=5)
            assert isinstance(empty_results, list)
            print("✅ Empty search query handled correctly")
            
        except Exception as e:
            print(f"❌ Error handling test failed: {str(e)}")
            pytest.fail(f"Error handling test failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self):
        """Test bulk database operations."""
        print("\n📦 Testing Bulk Operations...")
        
        try:
            # Create multiple test exercises
            exercise_ids = []
            for i in range(3):
                exercise_data = {
                    "url": f"https://www.youtube.com/watch?v=test{i}",
                    "normalized_url": f"https://www.youtube.com/watch?v=test{i}",
                    "carousel_index": 1,
                    "exercise_name": f"Test Exercise {i}",
                    "video_path": f"storage/clips/test_exercise_{i}.mp4",
                    "start_time": 10.0 + i,
                    "end_time": 25.0 + i,
                    "how_to": f"Instructions for exercise {i}",
                    "benefits": f"Benefits of exercise {i}",
                    "counteracts": f"Counteracts for exercise {i}",
                    "fitness_level": 3 + i,
                    "rounds_reps": f"3 sets for exercise {i}",
                    "intensity": 5 + i,
                    "qdrant_id": str(uuid.uuid4())
                }
                
                exercise_id = await store_exercise(**exercise_data)
                exercise_ids.append(exercise_id)
                print(f"✅ Created exercise {i}: {exercise_id}")
            
            # Test bulk retrieval
            for exercise_id in exercise_ids:
                exercise = await get_exercise_by_id(exercise_id)
                assert exercise is not None
                print(f"✅ Retrieved exercise: {exercise['exercise_name']}")
            
            # Clean up
            for exercise_id in exercise_ids:
                await delete_exercise(exercise_id)
                print(f"✅ Deleted exercise: {exercise_id}")
            
            print("✅ Bulk operations completed successfully")
            
        except Exception as e:
            print(f"❌ Bulk operations failed: {str(e)}")
            pytest.fail(f"Bulk operations failed: {str(e)}")

def run_database_tests():
    """Run all database integration tests."""
    print("🗄️ Starting Database Integration Tests")
    print("=" * 60)
    
    test_instance = TestDatabaseOperations()
    
    # Run all tests
    tests = [
        ("Database Initialization", test_instance.test_database_initialization),
        ("Vector Store Initialization", test_instance.test_vector_store_initialization),
        ("Exercise Storage/Retrieval", test_instance.test_exercise_storage_and_retrieval),
        ("Vector Operations", test_instance.test_vector_operations),
        ("Routine CRUD Operations", test_instance.test_routine_crud_operations),
        ("Job Status Management", test_instance.test_job_status_management),
        ("Data Consistency", test_instance.test_data_consistency),
        ("Error Handling", test_instance.test_error_handling),
        ("Bulk Operations", test_instance.test_bulk_operations),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            asyncio.run(test_func())
            results.append((test_name, "PASSED"))
        except Exception as e:
            print(f"❌ {test_name} FAILED: {str(e)}")
            results.append((test_name, "FAILED"))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DATABASE TEST SUMMARY")
    print("=" * 60)
    
    passed = [r for r in results if r[1] == "PASSED"]
    failed = [r for r in results if r[1] == "FAILED"]
    
    for test_name, status in results:
        status_icon = "✅" if status == "PASSED" else "❌"
        print(f"{status_icon} {test_name}: {status}")
    
    print(f"\n📈 Results: {len(passed)} passed, {len(failed)} failed")
    
    if failed:
        print("\n❌ Failed tests:")
        for test_name, status in failed:
            print(f"   - {test_name}")
    
    if len(passed) == len(tests):
        print("\n🎉 ALL DATABASE TESTS PASSED! Database operations are working correctly.")
    else:
        print(f"\n⚠️  {len(failed)} database tests failed. Check the errors above.")

if __name__ == "__main__":
    run_database_tests() 
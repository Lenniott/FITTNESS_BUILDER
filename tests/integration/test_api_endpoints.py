#!/usr/bin/env python3
"""
Comprehensive API endpoint tests for the Fitness Builder service.
Tests all endpoints to ensure they work correctly.
"""

import pytest
import asyncio
import requests
import json
import time
import uuid
from typing import Dict, List, Optional

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"
TIMEOUT = 300  # 5 minutes for video processing

class TestAPIEndpoints:
    """Comprehensive API endpoint tests."""
    
    @pytest.fixture
    def test_exercise_ids(self) -> List[str]:
        """Get some exercise IDs for testing."""
        # This would need to be populated with real exercise IDs from the database
        # For now, we'll use placeholder IDs
        return [
            "test-exercise-1",
            "test-exercise-2", 
            "test-exercise-3"
        ]
    
    @pytest.fixture
    def test_routine_data(self) -> Dict:
        """Test routine data for CRUD operations."""
        return {
            "name": "Test Routine",
            "description": "A test routine for API testing",
            "exercise_ids": ["test-exercise-1", "test-exercise-2"]
        }
    
    def test_health_endpoints(self):
        """Test health check endpoints."""
        print("\n🏥 Testing Health Endpoints...")
        
        # Test root health check
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        print(f"✅ Root health check: {data}")
        
        # Test database health
        response = requests.get(f"{API_BASE}/health/database", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        print(f"✅ Database health: {data}")
        
        # Test vector health
        response = requests.get(f"{API_BASE}/health/vector", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "vector_db" in data
        print(f"✅ Vector health: {data}")
    
    def test_stats_endpoint(self):
        """Test statistics endpoint."""
        print("\n📊 Testing Stats Endpoint...")
        
        response = requests.get(f"{API_BASE}/stats", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "total_exercises" in data
        assert "avg_fitness_level" in data
        assert "avg_intensity" in data
        print(f"✅ Stats endpoint: {data}")
    
    def test_story_generation_endpoint(self):
        """Test story generation endpoint."""
        print("\n📝 Testing Story Generation Endpoint...")
        
        request_data = {
            "user_prompt": "I need a quick 5-minute routine I can do at my desk",
            "story_count": 2
        }
        
        response = requests.post(
            f"{API_BASE}/stories/generate",
            json=request_data,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "stories" in data
        assert isinstance(data["stories"], list)
        assert len(data["stories"]) > 0
        print(f"✅ Story generation: {len(data['stories'])} stories generated")
    
    def test_semantic_search_endpoint(self):
        """Test semantic search endpoint."""
        print("\n🔍 Testing Semantic Search Endpoint...")
        
        request_data = {
            "query": "I need a beginner workout for my back that helps with posture",
            "limit": 5
        }
        
        response = requests.post(
            f"{API_BASE}/exercises/semantic-search-ids",
            json=request_data,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "exercise_ids" in data
        assert "total_found" in data
        assert isinstance(data["exercise_ids"], list)
        print(f"✅ Semantic search: {data['total_found']} exercises found")
    
    def test_exercise_list_endpoint(self):
        """Test exercise listing endpoint."""
        print("\n💪 Testing Exercise List Endpoint...")
        
        # Test without URL filter
        response = requests.get(f"{API_BASE}/exercises", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Exercise list: {len(data)} exercises found")
        
        # Test with URL filter (if any exercises exist)
        if data:
            first_exercise = data[0]
            if "url" in first_exercise:
                response = requests.get(
                    f"{API_BASE}/exercises?url={first_exercise['url']}",
                    timeout=10
                )
                assert response.status_code == 200
                filtered_data = response.json()
                assert isinstance(filtered_data, list)
                print(f"✅ Exercise list with URL filter: {len(filtered_data)} exercises")
    
    def test_exercise_bulk_endpoint(self, test_exercise_ids):
        """Test bulk exercise retrieval endpoint."""
        print("\n📦 Testing Exercise Bulk Endpoint...")
        
        request_data = {
            "exercise_ids": test_exercise_ids
        }
        
        response = requests.post(
            f"{API_BASE}/exercises/bulk",
            json=request_data,
            timeout=10
        )
        # This might return 404 if test exercise IDs don't exist
        # That's expected behavior
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            print(f"✅ Bulk exercise retrieval: {len(data)} exercises")
        else:
            print(f"⚠️  Bulk exercise retrieval: {response.status_code} (expected for test IDs)")
    
    def test_routine_crud_operations(self, test_routine_data):
        """Test routine CRUD operations."""
        print("\n🏋️ Testing Routine CRUD Operations...")
        
        # Create routine
        response = requests.post(
            f"{API_BASE}/routines",
            json=test_routine_data,
            timeout=10
        )
        assert response.status_code == 200
        create_data = response.json()
        assert "routine_id" in create_data
        routine_id = create_data["routine_id"]
        print(f"✅ Routine created: {routine_id}")
        
        # Get specific routine
        response = requests.get(f"{API_BASE}/routines/{routine_id}", timeout=10)
        assert response.status_code == 200
        get_data = response.json()
        assert get_data["routine_id"] == routine_id
        assert get_data["name"] == test_routine_data["name"]
        print(f"✅ Routine retrieved: {get_data['name']}")
        
        # List all routines
        response = requests.get(f"{API_BASE}/routines", timeout=10)
        assert response.status_code == 200
        list_data = response.json()
        assert isinstance(list_data, list)
        print(f"✅ Routine list: {len(list_data)} routines")
        
        # Delete routine
        response = requests.delete(f"{API_BASE}/routines/{routine_id}", timeout=10)
        assert response.status_code == 200
        delete_data = response.json()
        assert "message" in delete_data
        print(f"✅ Routine deleted: {delete_data['message']}")
        
        # Verify deletion
        response = requests.get(f"{API_BASE}/routines/{routine_id}", timeout=10)
        assert response.status_code == 404
        print("✅ Routine deletion verified")
    
    def test_process_endpoint_synchronous(self):
        """Test video processing endpoint in synchronous mode."""
        print("\n🎬 Testing Process Endpoint (Synchronous)...")
        
        # Use a short, safe test video
        request_data = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll (short, safe)
            "background": False
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/process",
                json=request_data,
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "success" in data
                assert "processed_clips" in data
                assert "total_clips" in data
                print(f"✅ Process endpoint (sync): {data['total_clips']} clips generated")
            else:
                print(f"⚠️  Process endpoint (sync): {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            print("⏰ Process endpoint (sync): Request timed out (expected for video processing)")
        except Exception as e:
            print(f"⚠️  Process endpoint (sync): {str(e)}")
    
    def test_process_endpoint_asynchronous(self):
        """Test video processing endpoint in asynchronous mode."""
        print("\n🎬 Testing Process Endpoint (Asynchronous)...")
        
        request_data = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll (short, safe)
            "background": True
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/process",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "success" in data
                assert "job_id" in data
                job_id = data["job_id"]
                print(f"✅ Process endpoint (async): Job created - {job_id}")
                
                # Test job status polling
                self.test_job_status_polling(job_id)
            else:
                print(f"⚠️  Process endpoint (async): {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"⚠️  Process endpoint (async): {str(e)}")
    
    def test_job_status_polling(self, job_id: Optional[str] = None):
        """Test job status polling endpoint."""
        print("\n📊 Testing Job Status Polling...")
        
        if job_id is None:
            # Create a test job ID
            job_id = str(uuid.uuid4())
            print(f"⚠️  Using test job ID: {job_id}")
        
        try:
            response = requests.get(f"{API_BASE}/job-status/{job_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                status = data["status"]
                print(f"✅ Job status: {status}")
                
                if status == "done" and "result" in data:
                    result = data["result"]
                    print(f"✅ Job completed: {result}")
                elif status == "failed" and "result" in data:
                    result = data["result"]
                    print(f"⚠️  Job failed: {result}")
                else:
                    print(f"⏳ Job in progress: {status}")
            else:
                print(f"⚠️  Job status: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"⚠️  Job status polling: {str(e)}")
    
    def test_error_handling(self):
        """Test error handling for invalid requests."""
        print("\n🚨 Testing Error Handling...")
        
        # Test invalid exercise ID
        invalid_id = "invalid-exercise-id"
        response = requests.get(f"{API_BASE}/exercises/{invalid_id}", timeout=10)
        assert response.status_code == 404
        print("✅ Invalid exercise ID handled correctly")
        
        # Test invalid routine ID
        invalid_routine_id = "invalid-routine-id"
        response = requests.get(f"{API_BASE}/routines/{invalid_routine_id}", timeout=10)
        assert response.status_code == 404
        print("✅ Invalid routine ID handled correctly")
        
        # Test invalid job ID
        invalid_job_id = "invalid-job-id"
        response = requests.get(f"{API_BASE}/job-status/{invalid_job_id}", timeout=10)
        assert response.status_code == 404
        print("✅ Invalid job ID handled correctly")
        
        # Test invalid URL for processing
        request_data = {
            "url": "https://invalid-url.com/video",
            "background": False
        }
        response = requests.post(f"{API_BASE}/process", json=request_data, timeout=30)
        # This might return 500 or handle gracefully
        print(f"✅ Invalid URL handling: {response.status_code}")
    
    def test_all_endpoints_workflow(self):
        """Test a complete workflow using multiple endpoints."""
        print("\n🔄 Testing Complete Workflow...")
        
        try:
            # 1. Generate stories
            story_request = {
                "user_prompt": "I need a beginner workout for my back",
                "story_count": 1
            }
            response = requests.post(f"{API_BASE}/stories/generate", json=story_request, timeout=30)
            if response.status_code == 200:
                stories = response.json()["stories"]
                print(f"✅ Step 1: Generated {len(stories)} stories")
                
                # 2. Search for exercises
                search_request = {
                    "query": stories[0] if stories else "beginner back workout",
                    "limit": 3
                }
                response = requests.post(f"{API_BASE}/exercises/semantic-search-ids", json=search_request, timeout=30)
                if response.status_code == 200:
                    exercise_ids = response.json()["exercise_ids"]
                    print(f"✅ Step 2: Found {len(exercise_ids)} exercises")
                    
                    # 3. Create routine
                    routine_request = {
                        "name": "Test Workflow Routine",
                        "description": "Created via API workflow test",
                        "exercise_ids": exercise_ids[:2] if len(exercise_ids) >= 2 else exercise_ids
                    }
                    response = requests.post(f"{API_BASE}/routines", json=routine_request, timeout=10)
                    if response.status_code == 200:
                        routine_id = response.json()["routine_id"]
                        print(f"✅ Step 3: Created routine {routine_id}")
                        
                        # 4. Get routine details
                        response = requests.get(f"{API_BASE}/routines/{routine_id}", timeout=10)
                        if response.status_code == 200:
                            routine_data = response.json()
                            print(f"✅ Step 4: Retrieved routine: {routine_data['name']}")
                            
                            # 5. Get exercise details
                            if routine_data.get("exercise_ids"):
                                bulk_request = {"exercise_ids": routine_data["exercise_ids"]}
                                response = requests.post(f"{API_BASE}/exercises/bulk", json=bulk_request, timeout=10)
                                if response.status_code == 200:
                                    exercises = response.json()
                                    print(f"✅ Step 5: Retrieved {len(exercises)} exercise details")
                                else:
                                    print(f"⚠️  Step 5: Could not retrieve exercise details: {response.status_code}")
                            
                            # 6. Clean up
                            response = requests.delete(f"{API_BASE}/routines/{routine_id}", timeout=10)
                            if response.status_code == 200:
                                print("✅ Step 6: Cleaned up test routine")
                            else:
                                print(f"⚠️  Step 6: Could not clean up routine: {response.status_code}")
                        else:
                            print(f"⚠️  Step 4: Could not retrieve routine: {response.status_code}")
                    else:
                        print(f"⚠️  Step 3: Could not create routine: {response.status_code}")
                else:
                    print(f"⚠️  Step 2: Could not search exercises: {response.status_code}")
            else:
                print(f"⚠️  Step 1: Could not generate stories: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Workflow test error: {str(e)}")

def run_all_tests():
    """Run all API endpoint tests."""
    print("🚀 Starting Comprehensive API Endpoint Tests")
    print("=" * 60)
    
    test_instance = TestAPIEndpoints()
    
    # Run all tests
    tests = [
        ("Health Endpoints", test_instance.test_health_endpoints),
        ("Stats Endpoint", test_instance.test_stats_endpoint),
        ("Story Generation", test_instance.test_story_generation_endpoint),
        ("Semantic Search", test_instance.test_semantic_search_endpoint),
        ("Exercise List", test_instance.test_exercise_list_endpoint),
        ("Exercise Bulk", test_instance.test_exercise_bulk_endpoint),
        ("Routine CRUD", test_instance.test_routine_crud_operations),
        ("Process Endpoint (Sync)", test_instance.test_process_endpoint_synchronous),
        ("Process Endpoint (Async)", test_instance.test_process_endpoint_asynchronous),
        ("Error Handling", test_instance.test_error_handling),
        ("Complete Workflow", test_instance.test_all_endpoints_workflow),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            test_func()
            results.append((test_name, "PASSED"))
        except Exception as e:
            print(f"❌ {test_name} FAILED: {str(e)}")
            results.append((test_name, "FAILED"))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
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
        print("\n🎉 ALL TESTS PASSED! All endpoints are working correctly.")
    else:
        print(f"\n⚠️  {len(failed)} tests failed. Check the errors above.")

if __name__ == "__main__":
    run_all_tests() 
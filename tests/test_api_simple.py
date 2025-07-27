#!/usr/bin/env python3
"""
Simple API test script that can be run directly.
Tests basic API functionality without complex imports.
"""

import requests
import json
import time

def test_api_endpoints():
    """Test basic API endpoints."""
    print("🚀 Testing API Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    api_base = f"{base_url}/api/v1"
    
    # Test 1: Health check
    print("\n🏥 Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
    
    # Test 2: Database health
    print("\n🗄️ Testing Database Health...")
    try:
        response = requests.get(f"{api_base}/health/database", timeout=10)
        if response.status_code == 200:
            print("✅ Database health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Database health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Database health check error: {str(e)}")
    
    # Test 3: Vector health
    print("\n🔍 Testing Vector Health...")
    try:
        response = requests.get(f"{api_base}/health/vector", timeout=10)
        if response.status_code == 200:
            print("✅ Vector health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Vector health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Vector health check error: {str(e)}")
    
    # Test 4: Stats endpoint
    print("\n📊 Testing Stats Endpoint...")
    try:
        response = requests.get(f"{api_base}/stats", timeout=10)
        if response.status_code == 200:
            print("✅ Stats endpoint passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Stats endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Stats endpoint error: {str(e)}")
    
    # Test 5: Exercise list
    print("\n💪 Testing Exercise List...")
    try:
        response = requests.get(f"{api_base}/exercises", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Exercise list passed: {len(data)} exercises")
        else:
            print(f"❌ Exercise list failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Exercise list error: {str(e)}")
    
    # Test 6: Story generation
    print("\n📝 Testing Story Generation...")
    try:
        request_data = {
            "user_prompt": "I need a quick 5-minute routine I can do at my desk",
            "story_count": 1
        }
        response = requests.post(
            f"{api_base}/stories/generate",
            json=request_data,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Story generation passed: {len(data.get('stories', []))} stories")
        else:
            print(f"❌ Story generation failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Story generation error: {str(e)}")
    
    # Test 7: Semantic search
    print("\n🔍 Testing Semantic Search...")
    try:
        request_data = {
            "query": "I need a beginner workout for my back",
            "limit": 3
        }
        response = requests.post(
            f"{api_base}/exercises/semantic-search-ids",
            json=request_data,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Semantic search passed: {data.get('total_found', 0)} exercises found")
        else:
            print(f"❌ Semantic search failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Semantic search error: {str(e)}")
    
    # Test 8: Routine creation
    print("\n🏋️ Testing Routine Creation...")
    try:
        request_data = {
            "name": "Test API Routine",
            "description": "Created via API test",
            "exercise_ids": ["test-exercise-1", "test-exercise-2"]
        }
        response = requests.post(
            f"{api_base}/routines",
            json=request_data,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            routine_id = data.get('routine_id')
            print(f"✅ Routine creation passed: {routine_id}")
            
            # Test routine retrieval
            response = requests.get(f"{api_base}/routines/{routine_id}", timeout=10)
            if response.status_code == 200:
                print("✅ Routine retrieval passed")
                
                # Clean up - delete routine
                response = requests.delete(f"{api_base}/routines/{routine_id}", timeout=10)
                if response.status_code == 200:
                    print("✅ Routine deletion passed")
                else:
                    print(f"❌ Routine deletion failed: {response.status_code}")
            else:
                print(f"❌ Routine retrieval failed: {response.status_code}")
        else:
            print(f"❌ Routine creation failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Routine creation error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 API Testing Complete!")

if __name__ == "__main__":
    test_api_endpoints() 
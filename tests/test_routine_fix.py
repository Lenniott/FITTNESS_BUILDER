#!/usr/bin/env python3
"""
Simple test to verify routine creation and retrieval fix.
"""

import requests
import json

def test_routine_fix():
    """Test routine creation and retrieval."""
    print("🔧 Testing Routine Fix")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    api_base = f"{base_url}/api/v1"
    
    # Test routine creation
    print("\n🏋️ Testing Routine Creation...")
    try:
        request_data = {
            "name": "Test Routine Fix",
            "description": "Testing the routine fix",
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
            print(f"✅ Routine created successfully: {routine_id}")
            print(f"   Name: {data.get('name')}")
            print(f"   Exercise IDs: {data.get('exercise_ids')}")
            
            # Test routine retrieval
            print("\n📖 Testing Routine Retrieval...")
            response = requests.get(f"{api_base}/routines/{routine_id}", timeout=10)
            
            if response.status_code == 200:
                routine_data = response.json()
                print(f"✅ Routine retrieved successfully")
                print(f"   ID: {routine_data.get('routine_id')}")
                print(f"   Name: {routine_data.get('name')}")
                print(f"   Exercise IDs: {routine_data.get('exercise_ids')}")
                
                # Clean up - delete routine
                print("\n🗑️ Testing Routine Deletion...")
                response = requests.delete(f"{api_base}/routines/{routine_id}", timeout=10)
                
                if response.status_code == 200:
                    print("✅ Routine deleted successfully")
                    
                    # Verify deletion
                    response = requests.get(f"{api_base}/routines/{routine_id}", timeout=10)
                    if response.status_code == 404:
                        print("✅ Routine deletion verified")
                    else:
                        print(f"❌ Routine still exists: {response.status_code}")
                else:
                    print(f"❌ Routine deletion failed: {response.status_code}")
            else:
                print(f"❌ Routine retrieval failed: {response.status_code}")
                print(f"   Error: {response.text}")
        else:
            print(f"❌ Routine creation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 Routine Fix Test Complete!")

if __name__ == "__main__":
    test_routine_fix() 
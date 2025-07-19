#!/usr/bin/env python3
"""
Example script demonstrating the workout compilation API.

This script shows how to:
1. Generate a personalized workout from natural language requirements
2. Retrieve the compiled workout
3. Download the workout video
4. List all compiled workouts
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional

# Note: aiohttp is an optional dependency for this example
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    print("⚠️  aiohttp not installed. Install with: pip install aiohttp")
    HAS_AIOHTTP = False

# API base URL
API_BASE_URL = "http://localhost:8000/api/v1"

async def generate_workout(session: "aiohttp.ClientSession", requirements: str) -> Optional[Dict[str, Any]]:
    """Generate a personalized workout from natural language requirements."""
    
    url = f"{API_BASE_URL}/workout/generate"
    payload = {
        "user_requirements": requirements,
        "target_duration": 300,  # 5 minutes
        "format": "square",  # square or vertical
        "intensity_level": "beginner"  # beginner, intermediate, advanced
    }
    
    print(f"🎯 Generating workout for: {requirements}")
    
    async with session.post(url, json=payload) as response:
        if response.status == 200:
            result = await response.json()
            print(f"✅ Workout generated successfully!")
            print(f"   Workout ID: {result['workout_id']}")
            print(f"   Video Path: {result['video_path']}")
            print(f"   Clips Used: {result['clips_used']}")
            print(f"   Processing Time: {result['processing_time']:.2f}s")
            print(f"   Requirement Stories: {len(result['requirement_stories'])}")
            return result
        else:
            error_text = await response.text()
            print(f"❌ Failed to generate workout: {error_text}")
            return None

async def get_workout_status(session: "aiohttp.ClientSession", workout_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a compiled workout."""
    
    url = f"{API_BASE_URL}/workout/{workout_id}/status"
    
    async with session.get(url) as response:
        if response.status == 200:
            result = await response.json()
            print(f"📊 Workout Status:")
            print(f"   Status: {result['status']}")
            print(f"   Video Exists: {result['video_exists']}")
            print(f"   Target Duration: {result['target_duration']}s")
            print(f"   Actual Duration: {result['actual_duration']}s")
            print(f"   Format: {result['format']}")
            print(f"   Intensity: {result['intensity_level']}")
            return result
        else:
            error_text = await response.text()
            print(f"❌ Failed to get workout status: {error_text}")
            return None

async def download_workout_video(session: aiohttp.ClientSession, workout_id: str, output_path: str):
    """Download a compiled workout video."""
    
    url = f"{API_BASE_URL}/workout/{workout_id}/download"
    
    print(f"📥 Downloading workout video to: {output_path}")
    
    async with session.get(url) as response:
        if response.status == 200:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the video file
            with open(output_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
            
            print(f"✅ Workout video downloaded successfully!")
            print(f"   File size: {os.path.getsize(output_path)} bytes")
        else:
            error_text = await response.text()
            print(f"❌ Failed to download workout video: {error_text}")

async def list_workouts(session: "aiohttp.ClientSession", limit: int = 10) -> Optional[Dict[str, Any]]:
    """List all compiled workouts."""
    
    url = f"{API_BASE_URL}/workouts?limit={limit}"
    
    async with session.get(url) as response:
        if response.status == 200:
            workouts = await response.json()
            print(f"📋 Found {len(workouts)} compiled workouts:")
            
            for i, workout in enumerate(workouts, 1):
                print(f"   {i}. ID: {workout['id']}")
                print(f"      Requirements: {workout['user_requirements'][:50]}...")
                print(f"      Duration: {workout['target_duration']}s")
                print(f"      Format: {workout['format']}")
                print(f"      Intensity: {workout['intensity_level']}")
                print(f"      Created: {workout['created_at']}")
                print()
            
            return workouts
        else:
            error_text = await response.text()
            print(f"❌ Failed to list workouts: {error_text}")
            return None

async def main():
    """Main example function."""
    
    print("🏋️  Workout Compilation API Example")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Example 1: Generate a workout for someone who sits all day
        print("\n1️⃣  Generating workout for desk worker...")
        requirements_1 = "I sit all day, my hips are tight, I want to do handstands"
        result_1 = await generate_workout(session, requirements_1)
        
        if result_1 and result_1['success']:
            workout_id = result_1['workout_id']
            
            # Check status
            await get_workout_status(session, workout_id)
            
            # Download the video
            await download_workout_video(session, workout_id, "downloads/workout_desk_worker.mp4")
        
        # Example 2: Generate a workout for a beginner
        print("\n2️⃣  Generating workout for beginner...")
        requirements_2 = "I'm a complete beginner, I haven't exercised in months, I want to build strength slowly"
        result_2 = await generate_workout(session, requirements_2)
        
        if result_2 and result_2['success']:
            workout_id_2 = result_2['workout_id']
            await download_workout_video(session, workout_id_2, "downloads/workout_beginner.mp4")
        
        # Example 3: Generate a workout for posture improvement
        print("\n3️⃣  Generating workout for posture improvement...")
        requirements_3 = "My posture is terrible from sitting at a computer all day, my back hurts, I need to strengthen my core"
        result_3 = await generate_workout(session, requirements_3)
        
        if result_3 and result_3['success']:
            workout_id_3 = result_3['workout_id']
            await download_workout_video(session, workout_id_3, "downloads/workout_posture.mp4")
        
        # List all workouts
        print("\n4️⃣  Listing all compiled workouts...")
        await list_workouts(session, limit=5)
        
        print("\n✅ Example completed!")

if __name__ == "__main__":
    if not HAS_AIOHTTP:
        print("❌ This example requires aiohttp. Install with: pip install aiohttp")
        exit(1)
    
    # Create downloads directory
    os.makedirs("downloads", exist_ok=True)
    
    # Run the example
    asyncio.run(main()) 
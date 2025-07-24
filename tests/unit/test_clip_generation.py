#!/usr/bin/env python3
"""
Test script to isolate clip generation from AI response data.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

def test_clip_generation():
    """Test clip generation using the latest AI response."""
    
    # Find the latest temp directory
    temp_dir = Path("storage/temp")
    if not temp_dir.exists():
        print("❌ No temp directory found")
        return
    
    # Get the most recent directory
    temp_dirs = [d for d in temp_dir.iterdir() if d.is_dir() and d.name.startswith("gilgamesh_download_")]
    if not temp_dirs:
        print("❌ No download directories found")
        return
    
    latest_dir = max(temp_dirs, key=lambda x: x.stat().st_mtime)
    print(f"📁 Using temp directory: {latest_dir}")
    
    # Check for AI response file
    ai_response_file = latest_dir / "ai_response.txt"
    if not ai_response_file.exists():
        print("❌ No AI response file found")
        return
    
    # Read AI response
    with open(ai_response_file, 'r') as f:
        ai_response = f.read()
    
    print(f"📄 AI Response: {ai_response[:200]}...")
    
    # Parse exercises from AI response
    try:
        # Extract JSON from response
        if "```json" in ai_response:
            json_text = ai_response.split("```json")[1].split("```")[0]
        elif "```" in ai_response:
            json_text = ai_response.split("```")[1]
        else:
            json_text = ai_response
        
        exercises_data = json.loads(json_text.strip())
        exercises = exercises_data.get('exercises', [])
        print(f"✅ Parsed {len(exercises)} exercises from AI response")
        
        for i, exercise in enumerate(exercises):
            print(f"\n🏋️  Exercise {i+1}: {exercise['exercise_name']}")
            print(f"   Start: {exercise['start_time']}s")
            print(f"   End: {exercise['end_time']}s")
            print(f"   Duration: {exercise['end_time'] - exercise['start_time']}s")
        
    except Exception as e:
        print(f"❌ Error parsing AI response: {e}")
        return
    
    # Find video file
    video_files = list(latest_dir.glob("*.mp4"))
    if not video_files:
        print("❌ No video file found")
        return
    
    video_file = video_files[0]
    print(f"🎥 Video file: {video_file}")
    
    # Test clip generation
    print("\n🎬 Testing clip generation...")
    
    for i, exercise in enumerate(exercises):
        try:
            # Create clips directory
            clips_dir = latest_dir / "clips"
            clips_dir.mkdir(exist_ok=True)
            
            # Generate clip filename
            exercise_name_clean = exercise['exercise_name'].replace(' ', '_').lower()
            clip_filename = f"{exercise_name_clean}_test.mp4"
            clip_path = clips_dir / clip_filename
            
            print(f"\n📹 Generating clip for: {exercise['exercise_name']}")
            print(f"   Output: {clip_path}")
            
            # Build ffmpeg command
            start_time = exercise['start_time']
            duration = exercise['end_time'] - exercise['start_time']
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-i', str(video_file),
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                str(clip_path)
            ]
            
            print(f"🔧 Running: {' '.join(ffmpeg_cmd)}")
            
            # Run ffmpeg
            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode == 0:
                if clip_path.exists():
                    file_size = clip_path.stat().st_size
                    print(f"✅ SUCCESS! Clip created: {clip_path} ({file_size:,} bytes)")
                else:
                    print(f"❌ FAILED! Clip file not created")
            else:
                print(f"❌ FAILED! ffmpeg returned code {result.returncode}")
                print(f"   stdout: {result.stdout}")
                print(f"   stderr: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"❌ TIMEOUT! ffmpeg took too long")
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_clip_generation() 
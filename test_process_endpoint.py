#!/usr/bin/env python3
"""
Test script for the /process endpoint.
Demonstrates the complete video processing pipeline.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.core.processor import processor

async def test_process_endpoint():
    """Test the complete video processing pipeline."""
    
    # Use command line argument or default to test URL
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print("🎬 TESTING COMPLETE VIDEO PROCESSING PIPELINE")
    print("=" * 60)
    print(f"URL: {test_url}")
    print()
    
    try:
        # Step 1: Process the video
        print("📥 Step 1: Downloading video and extracting metadata...")
        print("🎤 Step 2: Transcribing audio...")
        print("🖼️  Step 3: Extracting keyframes...")
        print("🤖 Step 4: AI exercise detection...")
        print("✂️  Step 5: Generating clips...")
        print("💾 Step 6: Storing in database...")
        print()
        
        start_time = time.time()
        result = await processor.process_video(test_url)
        processing_time = time.time() - start_time
        
        print("✅ PROCESSING COMPLETE!")
        print("=" * 60)
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Total clips generated: {result['total_clips']}")
        print(f"Temp directory: {result['temp_dir']}")
        print()
        
        # Display results
        if result['processed_clips']:
            print("📋 GENERATED CLIPS:")
            print("-" * 40)
            for i, clip in enumerate(result['processed_clips'], 1):
                print(f"{i}. {clip['exercise_name']}")
                print(f"   ID: {clip['exercise_id']}")
                print(f"   Duration: {clip['total_duration']:.1f}s")
                print(f"   Segments: {clip['segments_count']}")
                print(f"   Path: {clip['video_path']}")
                print()
        else:
            print("⚠️  No clips were generated")
        
        # Show temp directory contents
        if result['temp_dir'] and os.path.exists(result['temp_dir']):
            print("📁 TEMP DIRECTORY CONTENTS:")
            print("-" * 40)
            for root, dirs, files in os.walk(result['temp_dir']):
                level = root.replace(result['temp_dir'], '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    print(f"{subindent}{file} ({file_size:,} bytes)")
        
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_process_endpoint())
    
    if result:
        print("\n🎉 SUCCESS! The video processing pipeline is working correctly.")
        print("You can now use the /process endpoint in your API!")
    else:
        print("\n💥 FAILED! Check the error messages above.") 
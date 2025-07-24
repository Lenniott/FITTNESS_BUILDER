#!/usr/bin/env python3
"""
Test script to verify improved keyframe extraction deduplication.
"""

import asyncio
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.enhanced_keyframe_extraction import enhanced_keyframe_extractor

async def test_improved_deduplication():
    """Test the improved deduplication logic with higher thresholds."""
    
    print("🔬 Testing Improved Keyframe Extraction Deduplication")
    print("=" * 65)
    
    # Use the existing video file
    video_file = "storage/temp/SnapInsta1.mp4"
    
    if not os.path.exists(video_file):
        print(f"❌ Video file not found: {video_file}")
        return
    
    # Create a test frames directory
    frames_dir = "storage/temp/test_improved_deduplication_frames"
    os.makedirs(frames_dir, exist_ok=True)
    
    print(f"📹 Testing with video: {video_file}")
    print(f"📁 Frames will be saved to: {frames_dir}")
    
    # Extract frames with improved deduplication
    frame_files = await enhanced_keyframe_extractor.extract_keyframes(video_file, frames_dir)
    
    print(f"\n✅ Extraction complete!")
    print(f"📊 Total frames extracted: {len(frame_files)}")
    
    # Analyze the results
    method_counts = {}
    timestamps = []
    
    print(f"\n🔍 Detailed frame analysis:")
    for i, frame_path in enumerate(frame_files):
        filename = os.path.basename(frame_path)
        print(f"  {i+1:2d}. {filename}")
        try:
            # Extract method and timestamp
            parts = filename.split('_')
            timestamp = int(parts[1])
            method = parts[2].replace('.jpg', '')
            
            method_counts[method] = method_counts.get(method, 0) + 1
            timestamps.append(timestamp)
            
        except (IndexError, ValueError):
            print(f"    ⚠️  Could not parse: {filename}")
            continue
    
    print(f"\n📈 Frame Analysis:")
    print(f"  Total frames: {len(frame_files)}")
    print(f"  Methods found: {list(method_counts.keys())}")
    
    for method, count in method_counts.items():
        print(f"    {method}: {count} frames")
    
    if timestamps:
        timestamps.sort()
        print(f"\n⏱️  Timing Analysis:")
        print(f"  First frame: {timestamps[0]/1000:.1f}s")
        print(f"  Last frame: {timestamps[-1]/1000:.1f}s")
        print(f"  Time span: {(timestamps[-1] - timestamps[0])/1000:.1f}s")
        
        # Check for duplicates (frames within 100ms are considered duplicates)
        duplicate_groups = {}
        for ts in timestamps:
            rounded_ts = ts // 100  # 100ms windows (more precise)
            if rounded_ts not in duplicate_groups:
                duplicate_groups[rounded_ts] = []
            duplicate_groups[rounded_ts].append(ts)
        
        duplicates = sum(1 for group in duplicate_groups.values() if len(group) > 1)
        print(f"  Duplicate groups: {duplicates}")
        
        if duplicates > 0:
            print(f"  ⚠️  WARNING: Found {duplicates} duplicate groups!")
            for group_ts, group_timestamps in duplicate_groups.items():
                if len(group_timestamps) > 1:
                    print(f"    Duplicate at {group_ts*100/1000:.1f}s: {group_timestamps}")
        else:
            print(f"  ✅ No duplicates found!")
    
    print(f"\n👀 Frames saved to: {frames_dir}")
    print("Please examine the frames to verify deduplication worked correctly")

if __name__ == "__main__":
    asyncio.run(test_improved_deduplication()) 
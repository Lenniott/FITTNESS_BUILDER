#!/usr/bin/env python3
"""
Simple script to extract I-frames, P-frames, and B-frames from video.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.frame_type_extractor import frame_type_extractor

def main():
    video_path = "storage/temp/SnapInsta.mp4"
    
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return
    
    print(f"Extracting frame types from: {video_path}")
    print("This will create three folders:")
    print("  - storage/temp/frame_analysis/i_frames")
    print("  - storage/temp/frame_analysis/p_frames") 
    print("  - storage/temp/frame_analysis/b_frames")
    print()
    
    # Try ffprobe method first (more accurate)
    print("Attempting ffprobe method (more accurate)...")
    results = frame_type_extractor.extract_with_ffprobe(video_path)
    
    if not results:
        print("ffprobe method failed, trying OpenCV method...")
        results = frame_type_extractor.extract_frame_types(video_path)
    
    if results:
        print("\nExtraction complete!")
        print(f"I-frames: {len(results.get('i_frames', []))}")
        print(f"P-frames: {len(results.get('p_frames', []))}")
        print(f"B-frames: {len(results.get('b_frames', []))}")
        print("\nCheck the folders in storage/temp/frame_analysis/")
    else:
        print("Extraction failed!")

if __name__ == "__main__":
    main() 
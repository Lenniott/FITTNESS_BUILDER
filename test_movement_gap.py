#!/usr/bin/env python3
"""
Test script to analyze movement scores in the specific gap.
"""

import cv2
import numpy as np
import os

def analyze_movement_gap(video_file: str):
    """Analyze movement scores in the specific gap between 16.166s and 22.166s."""
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"Cannot open video file: {video_file}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"Video: {duration:.1f}s, {fps:.1f} fps")
    
    movement_history = []
    scores = []
    timestamps = []
    
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        timestamp = frame_count / fps
        
        # Only analyze the gap between 16.166s and 22.166s
        if 16.0 <= timestamp <= 22.5:
            # Convert to grayscale for movement detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            movement_history.append(gray)
            
            # Keep only recent frames for comparison
            if len(movement_history) > 3:
                movement_history.pop(0)
            
            # Calculate movement score if we have enough history
            if len(movement_history) >= 3:
                movement_score = calculate_movement_score(movement_history)
                scores.append(movement_score)
                timestamps.append(timestamp)
                
                # Show scores above different thresholds
                if movement_score > 0.5:  # Show any significant movement
                    print(f"  {timestamp:.3f}s: {movement_score:.2f}")
        
        frame_count += 1
    
    cap.release()
    
    # Analyze scores in the gap
    if scores:
        print(f"\nGap Analysis (16.0s - 22.5s):")
        print(f"Min score: {min(scores):.2f}")
        print(f"Max score: {max(scores):.2f}")
        print(f"Average score: {np.mean(scores):.2f}")
        
        # Show scores above current threshold
        above_threshold = [s for s in scores if s > 0.75]
        print(f"Scores > 0.75: {len(above_threshold)} frames")
        
        # Show scores above lower thresholds
        for threshold in [0.5, 0.6, 0.7, 0.8]:
            above_threshold = [s for s in scores if s > threshold]
            print(f"Scores > {threshold}: {len(above_threshold)} frames")

def calculate_movement_score(frame_history):
    """Calculate movement score between frames using multiple frame comparison."""
    if len(frame_history) < 3:
        return 0.0
    
    # Calculate movement using multiple frame differences for better accuracy
    total_score = 0.0
    count = 0
    
    # Compare current frame with previous 2 frames
    for i in range(1, min(3, len(frame_history))):
        diff = cv2.absdiff(frame_history[-1], frame_history[-1-i])
        score = float(np.mean(diff))
        total_score += score
        count += 1
    
    # Return average movement score
    return total_score / count if count > 0 else 0.0

if __name__ == "__main__":
    video_file = "storage/temp/SnapInsta.mp4"
    if os.path.exists(video_file):
        analyze_movement_gap(video_file)
    else:
        print(f"Video file not found: {video_file}") 
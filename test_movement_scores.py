#!/usr/bin/env python3
"""
Test script to analyze movement scores in a video.
"""

import cv2
import numpy as np
import os

def analyze_movement_scores(video_file: str):
    """Analyze movement scores throughout the video."""
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
        
        frame_count += 1
    
    cap.release()
    
    # Analyze scores
    if scores:
        print(f"\nMovement Score Analysis:")
        print(f"Min score: {min(scores):.2f}")
        print(f"Max score: {max(scores):.2f}")
        print(f"Average score: {np.mean(scores):.2f}")
        print(f"Median score: {np.median(scores):.2f}")
        print(f"Std deviation: {np.std(scores):.2f}")
        
        # Show scores above different thresholds
        thresholds = [1.0, 2.0, 3.0, 5.0, 10.0, 15.0, 20.0]
        for threshold in thresholds:
            above_threshold = [s for s in scores if s > threshold]
            percentage = (len(above_threshold) / len(scores)) * 100
            print(f"Scores > {threshold}: {len(above_threshold)} frames ({percentage:.1f}%)")
        
        # Show top 10 highest scores
        print(f"\nTop 10 highest movement scores:")
        sorted_scores = sorted(zip(timestamps, scores), key=lambda x: x[1], reverse=True)
        for i, (timestamp, score) in enumerate(sorted_scores[:10]):
            print(f"  {timestamp:.3f}s: {score:.2f}")

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
        analyze_movement_scores(video_file)
    else:
        print(f"Video file not found: {video_file}") 
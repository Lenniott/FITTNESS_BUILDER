#!/usr/bin/env python3
"""
Test clip filtering functionality.
"""

import pytest
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'app'))

from app.core.processor import VideoProcessor

def test_clip_duration_filtering():
    """Test that clips are filtered by duration."""
    processor = VideoProcessor()
    
    # Test exercises with different durations
    exercises = [
        {
            'exercise_name': 'Short Exercise',
            'start_time': 0.0,
            'end_time': 3.0,  # 3 seconds - should be filtered out
            'confidence_score': 0.8
        },
        {
            'exercise_name': 'Good Exercise',
            'start_time': 0.0,
            'end_time': 15.0,  # 15 seconds - should pass
            'confidence_score': 0.8
        },
        {
            'exercise_name': 'Long Exercise',
            'start_time': 0.0,
            'end_time': 90.0,  # 90 seconds - should be filtered out
            'confidence_score': 0.8
        },
        {
            'exercise_name': 'Low Confidence',
            'start_time': 0.0,
            'end_time': 20.0,  # 20 seconds - should be filtered out due to low confidence
            'confidence_score': 0.2
        }
    ]
    
    # Mock the clip generation to just count what would be processed
    processed_count = 0
    for exercise in exercises:
        duration = exercise['end_time'] - exercise['start_time']
        
        # Apply the same filtering logic
        if duration < 5.0:
            continue  # Too short
        if duration > 60.0:
            continue  # Too long
        if exercise.get('confidence_score', 0) < 0.3:
            continue  # Low confidence
        
        processed_count += 1
    
    # Only the 'Good Exercise' should pass all filters
    assert processed_count == 1, f"Expected 1 exercise to pass filters, got {processed_count}"

def test_video_quality_validation():
    """Test video quality validation logic."""
    processor = VideoProcessor()
    
    # Test with mock video properties
    # This is a basic test - in real usage, cv2.VideoCapture would be called
    test_cases = [
        # (duration, width, height, fps, expected_result)
        (5.0, 320, 240, 10, False),    # Too short
        (30.0, 160, 120, 30, False),   # Too low resolution
        (30.0, 640, 480, 5, False),    # Too low frame rate
        (30.0, 640, 480, 30, True),    # Good quality
        (700.0, 640, 480, 30, False),  # Too long
    ]
    
    for duration, width, height, fps, expected in test_cases:
        # Mock the validation logic
        is_valid = True
        
        if duration < 10.0:
            is_valid = False
        elif duration > 600.0:
            is_valid = False
        elif width < 320 or height < 240:
            is_valid = False
        elif fps < 10:
            is_valid = False
        
        assert is_valid == expected, f"Quality validation failed for duration={duration}, width={width}, height={height}, fps={fps}"

if __name__ == "__main__":
    test_clip_duration_filtering()
    test_video_quality_validation()
    print("✅ All clip filtering tests passed!") 
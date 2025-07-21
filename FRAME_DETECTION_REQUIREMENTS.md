"""
KEYFRAME EXTRACTION SYSTEM - REQUIREMENTS & FLOW

GOAL: Extract meaningful frames from video for AI exercise analysis

REQUIREMENTS:
1. Detect major scene changes (cuts) to segment video
2. Use consistent naming: cut_{cutNumber}_frame_{frameNumberOfTheOriginalVideo}_time_{timeStampInmilliseconds}
3. the goal is to keep the least amount of frames necessary to capture a comprehensive range of movement.
4. the most frames per second should be 8.
5. The least frames per second for any video is 1 frame per second.
7. Use OpenCV for video processing

FLOW:
1. DETECT CUTS
   - Scan video for major scene changes using frame difference analysis
   - Use threshold to identify significant visual changes (scene cuts, camera switches)
   - Return list of cut timestamps where major changes occur
   - Always preserve first and last frame of entire video

2. EXTRACT FRAMES AT 8 FPS
   - For each cut segment (between cuts), extract frames at 8 FPS (every 0.125 seconds)
   - Use original video frame numbers in naming convention
   - Ensure minimum 1 frame per second baseline
   - Respect maximum 8 frames per second limit

3. IDENTIFY BIGGEST CHANGES
   - For each extracted frame, calculate change score by comparing to adjacent frames
   - Keep frames that show significant movement or changes
   - Always keep: first frame, last frame, and cut boundary frames
   - For other frames: keep only if they represent meaningful movement changes
   - Goal: Keep least frames necessary to capture comprehensive movement range

4. APPLY FRAME RATE CONSTRAINTS
   - Ensure minimum 1 frame per second across entire video
   - Ensure maximum 8 frames per second across entire video
   - Balance between movement coverage and frame efficiency

5. FINAL OUTPUT
   - Consistent naming: cut_{cutNumber}_frame_{frameNumberOfTheOriginalVideo}_time_{timeStampInmilliseconds}
   - All frames represent meaningful movement moments
   - Optimized for AI exercise analysis with minimal redundant frames

EXAMPLE OUTPUT:
cut_1_frame_1_time_0.jpg (video start)
cut_1_frame_15_time_3750.jpg (movement change)
cut_1_frame_31_time_7750.jpg (movement change)
cut_2_frame_47_time_11750.jpg (cut boundary)
cut_2_frame_63_time_15750.jpg (movement change)
...
cut_4_frame_127_time_31750.jpg (video end)

GOAL: Extract the minimum number of frames that capture all significant movement changes for AI exercise analysis.
"""
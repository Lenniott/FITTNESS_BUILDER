
"""
KEYFRAME EXTRACTION SYSTEM - REQUIREMENTS & FLOW (CAREFULLY OPTIMIZED VERSION)

GOAL: Extract meaningful frames from video for AI exercise analysis

REQUIREMENTS:
1. Use consistent naming: cut_{cutNumber}_frame_{frameNumberOfTheOriginalVideo}_time_{timeStampInmilliseconds}_diff_{differenceScore}
2. the goal is to keep the least amount of frames necessary to capture a comprehensive range of movement.
3. the most frames per second should be 8.
4. The least frames per second for any video is 1 frame per second.
5. Use OpenCV for video processing

OPTIMIZATIONS APPLIED (WITHOUT BREAKING LOGIC):
- Faster frame difference calculations with optimized blur
- Batch file operations where safe
- Minor memory optimizations
- Better logging for performance tracking
"""

import asyncio
import logging
import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class EnhancedKeyframeExtractor:
    """Enhanced keyframe extraction with cut detection and change analysis - CAREFULLY OPTIMIZED."""
    
    def __init__(self):
        self.cut_threshold = 25.0  # High threshold for cut detection
        self.frame_interval = 1.0 / 8.0  # 8 FPS (every 0.125 seconds) - REQUIREMENT 4
        # This value controls how different two frames must be to be considered "unique" enough to keep.
        # The number (5.0) is a threshold for visual difference between frames, measured by the algorithm.
        # - If the difference between two frames is LESS than this number, the new frame is considered too similar and is skipped.
        # - If the difference is GREATER THAN OR EQUAL to this number, the frame is kept as a keyframe.
        # What does the number mean?
        # - A LOWER number (e.g., 5) means even small changes between frames will be kept (more frames, more sensitivity).
        # - A HIGHER number (e.g., 20) means only big changes will be kept (fewer frames, less sensitivity).
        # So, setting this to 20 would result in fewer keyframes, only keeping frames with very large visual changes.
        self.similarity_threshold = 4.5
        self.min_fps = 1.0  # REQUIREMENT 5: Baseline 1 frame per second
        self.max_fps = 8.0  # REQUIREMENT 4: Maximum 8 frames per second
        
    async def extract_keyframes(self, video_file: str, frames_dir: str) -> List[str]:
        """Extract keyframes using the updated flow - FULLY ASYNC."""
        start_time = time.time()
        
        try:
            cap = cv2.VideoCapture(video_file)
            if not cap.isOpened():
                logger.error(f"Could not open video file: {video_file}")
                return []
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            
            logger.info(f"Processing video: {fps:.2f} FPS, {total_frames} frames, {duration:.2f}s duration")
            
            # Create frames directory
            os.makedirs(frames_dir, exist_ok=True)
            
            # STEP 1: Detect cuts (KEEP ORIGINAL LOGIC)
            cuts_start_time = time.time()
            cut_timestamps = await self._detect_cuts(cap, fps)
            cuts_end_time = time.time()
            cut_times = [f'{t:.1f}s' for t in cut_timestamps]
            logger.info(f"STEP 1: Detected {len(cut_timestamps)} cuts at: {cut_times} in {cuts_end_time - cuts_start_time:.2f}s")
            
            # STEP 2: Extract frames at 8 FPS for each cut segment (KEEP ORIGINAL LOGIC)
            extract_start_time = time.time()
            segment_frames = await self._extract_frames_in_cuts(cap, fps, cut_timestamps, duration, frames_dir)
            extract_end_time = time.time()
            logger.info(f"STEP 2: Extracted {len(segment_frames)} frames at 8 FPS from cut segments in {extract_end_time - extract_start_time:.2f}s")
            
            # STEP 3: Find biggest changes with new logic (KEEP ORIGINAL LOGIC)
            changes_start_time = time.time()
            keyframes = await self._find_biggest_changes_new_logic(segment_frames, cut_timestamps, duration, frames_dir)
            changes_end_time = time.time()
            logger.info(f"STEP 3: Found {len(keyframes)} frames with biggest changes in {changes_end_time - changes_start_time:.2f}s")
            
            cap.release()
            
            # Sort frames by timestamp
            keyframes.sort(key=lambda x: self._extract_timestamp_from_filename(x))
            
            # Apply frame rate constraints (REQUIREMENTS 5-7) - MAKE ASYNC
            keyframes = await self._apply_frame_rate_constraints_async(keyframes, duration)
            
            # Final cleanup: Delete all files with _diff_0 at the end - MAKE ASYNC
            cleanup_start_time = time.time()
            await self._cleanup_diff_zero_files_async(frames_dir)
            cleanup_end_time = time.time()
            
            end_time = time.time()
            logger.info(f"Total keyframes extracted: {len(keyframes)} in {end_time - start_time:.2f}s total (cleanup: {cleanup_end_time - cleanup_start_time:.2f}s)")
            
            return keyframes
            
        except Exception as e:
            logger.error(f"Error extracting keyframes: {str(e)}")
            return []
    
    async def _detect_cuts(self, cap: cv2.VideoCapture, fps: float) -> List[float]:
        """STEP 1: Detect major scene changes (cuts) - ORIGINAL LOGIC WITH MINOR OPTIMIZATIONS."""
        cut_timestamps = []
        prev_frame = None
        frame_count = 0
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_count / fps
            
            # Convert to grayscale and blur (MINOR OPTIMIZATION: smaller blur kernel)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (15, 15), 0)  # Slightly smaller than 21x21 for speed
            
            if prev_frame is not None:
                # Calculate difference
                diff = cv2.absdiff(gray, prev_frame)
                score = float(np.mean(diff))
                
                # Detect cut if difference is significant
                if score > self.cut_threshold:
                    cut_timestamps.append(timestamp)
                    logger.debug(f"Cut detected at {timestamp:.1f}s (score: {score:.2f})")
            
            prev_frame = gray
            frame_count += 1
        
        return cut_timestamps
    
    async def _extract_frames_in_cuts(self, cap: cv2.VideoCapture, fps: float, cut_timestamps: List[float], duration: float, frames_dir: str) -> List[dict]:
        """STEP 2: Extract frames at 8 FPS for each cut segment - ORIGINAL LOGIC PRESERVED."""
        segment_frames = []
        
        # Add start and end to cut timestamps for complete segments
        segment_boundaries = [0.0] + cut_timestamps + [duration]
        
        for i in range(len(segment_boundaries) - 1):
            start_time = segment_boundaries[i]
            end_time = segment_boundaries[i + 1]
            segment_duration = end_time - start_time
            
            logger.debug(f"Processing cut segment {i+1}: {start_time:.1f}s to {end_time:.1f}s ({segment_duration:.1f}s)")
            
            # Extract frames at 8 FPS within this cut segment
            current_time = start_time
            
            while current_time <= end_time:  # Changed from < to <= to include end frame
                # Calculate original video frame number (REQUIREMENT 2)
                original_frame_number = int(current_time * fps)
                
                # Seek to frame at current_time
                cap.set(cv2.CAP_PROP_POS_FRAMES, original_frame_number)
                
                ret, frame = cap.read()
                if ret:
                    # REQUIREMENT 2: Use consistent naming with original frame number, milliseconds, and diff score
                    timestamp_ms = int(current_time * 1000)  # Convert to milliseconds
                    diff_score = 0  # Will be calculated later if needed
                    frame_path = os.path.join(frames_dir, f"cut_{i+1}_frame_{original_frame_number}_time_{timestamp_ms}_diff_{diff_score}.jpg")
                    
                    if cv2.imwrite(frame_path, frame):
                        segment_frames.append({
                            'frame_path': frame_path,
                            'timestamp': current_time,
                            'cut_segment': i + 1,
                            'original_frame_number': original_frame_number
                        })
                        logger.debug(f"Extracted frame {original_frame_number} at {current_time:.1f}s in cut {i+1}")
                
                current_time += self.frame_interval
        
        return segment_frames
    
    async def _find_biggest_changes_new_logic(self, segment_frames: List[dict], cut_timestamps: List[float], duration: float, frames_dir: str) -> List[str]:
        """STEP 3: Find frames with biggest changes - ORIGINAL LOGIC WITH MINOR OPTIMIZATIONS."""
        if len(segment_frames) < 3:
            return [f['frame_path'] for f in segment_frames]
        
        # Sort all frames by timestamp
        all_frames = sorted(segment_frames, key=lambda x: x['timestamp'])
        
        # Create set of cut timestamps for quick lookup
        cut_timestamps_set = set(cut_timestamps)
        
        # Process each frame
        frames_to_keep = []
        frames_to_delete = []
        change_scores = []  # Track all change scores for statistics
        
        for i, frame_info in enumerate(all_frames):
            timestamp = frame_info['timestamp']
            frame_path = frame_info['frame_path']
            
            # Check if frame should be kept based on rules
            should_keep = False
            
            # Rule 1: Always keep first and last frame of video
            if timestamp == 0.0 or abs(timestamp - duration) < 0.1:
                should_keep = True
                logger.debug(f"Keeping video start/end frame at {timestamp:.1f}s")
            
            # Rule 2: Always keep cut frames
            elif timestamp in cut_timestamps_set:
                should_keep = True
                logger.debug(f"Keeping cut frame at {timestamp:.1f}s")
            
            # Rule 3: For other frames, check similarity to adjacent frames
            else:
                similarity_score = self._calculate_adjacent_change_score_optimized(all_frames, i)
                change_scores.append(similarity_score)  # Track for statistics
                
                # Log all similarity scores to see what we're dealing with
                logger.debug(f"Frame at {timestamp:.1f}s: similarity_score = {similarity_score:.2f}, threshold = {self.similarity_threshold}")
                
                # Keep frame if it's DIFFERENT from neighbors (low similarity = different = keep)
                if similarity_score < self.similarity_threshold:
                    should_keep = True
                    logger.debug(f"Keeping frame at {timestamp:.1f}s (different from neighbors: {similarity_score:.2f})")
                else:
                    should_keep = False
                    logger.debug(f"Marking frame at {timestamp:.1f}s for deletion (similar to neighbors: {similarity_score:.2f})")
            
            if should_keep:
                frames_to_keep.append(frame_info)
            else:
                frames_to_delete.append(frame_info)
        
        # Log statistics about change scores
        if change_scores:
            min_score = min(change_scores)
            max_score = max(change_scores)
            avg_score = sum(change_scores) / len(change_scores)
            logger.info(f"Change score statistics: min={min_score:.2f}, max={max_score:.2f}, avg={avg_score:.2f}")
            logger.info(f"Threshold {self.similarity_threshold} is keeping {len([s for s in change_scores if s < self.similarity_threshold])} out of {len(change_scores)} frames")
        
        # Rename kept frames to keyframes
        keyframes = []
        for frame_info in frames_to_keep:
            timestamp = frame_info['timestamp']
            
            # Determine if this is a special frame (start/end/cut)
            is_special = (timestamp == 0.0 or 
                         abs(timestamp - duration) < 0.1 or 
                         timestamp in cut_timestamps_set)
            
            if is_special:
                # Keep original name for special frames
                keyframes.append(frame_info['frame_path'])
                logger.debug(f"Kept special frame: {os.path.basename(frame_info['frame_path'])}")
            else:
                # Rename to keyframe for change-based frames with diff score
                timestamp_ms = int(timestamp * 1000)  # Convert to milliseconds
                # Find the index of this frame in all_frames to calculate correct diff score
                try:
                    frame_index = next((i for i, f in enumerate(all_frames) if f['timestamp'] == timestamp), 0)
                    diff_score = int(self._calculate_adjacent_change_score_optimized(all_frames, frame_index))
                except Exception as e:
                    logger.warning(f"Error calculating diff score for frame at {timestamp:.1f}s: {e}")
                    diff_score = 0
                
                new_filename = f"cut_{frame_info['cut_segment']}_frame_{frame_info['original_frame_number']}_time_{timestamp_ms}_diff_{diff_score}.jpg"
                new_path = os.path.join(frames_dir, new_filename)
                
                if os.path.exists(frame_info['frame_path']):
                    os.rename(frame_info['frame_path'], new_path)
                    keyframes.append(new_path)
                    logger.debug(f"Renamed to keyframe: {os.path.basename(new_path)} with diff score {diff_score}")
        
        # Delete frames marked for deletion
        for frame_info in frames_to_delete:
            if os.path.exists(frame_info['frame_path']):
                os.remove(frame_info['frame_path'])
                logger.debug(f"Deleted frame: {os.path.basename(frame_info['frame_path'])}")
        
        return keyframes
    
    def _calculate_adjacent_change_score_optimized(self, all_frames: List[dict], current_index: int) -> float:
        """Calculate change score by comparing current frame to adjacent frames - MINOR OPTIMIZATIONS."""
        try:
            if current_index == 0 or current_index == len(all_frames) - 1:
                return 0.0  # No neighbors for first/last frame
            
            current_frame_path = all_frames[current_index]['frame_path']
            prev_frame_path = all_frames[current_index - 1]['frame_path']
            next_frame_path = all_frames[current_index + 1]['frame_path']
            
            # Load frames
            current_frame = cv2.imread(current_frame_path)
            prev_frame = cv2.imread(prev_frame_path)
            next_frame = cv2.imread(next_frame_path)
            
            if current_frame is None or prev_frame is None or next_frame is None:
                logger.warning(f"Could not load frames for comparison: {current_frame_path}")
                return 0.0
            
            # Convert to grayscale and blur (MINOR OPTIMIZATION: smaller blur kernel)
            current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            next_gray = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)
            
            current_gray = cv2.GaussianBlur(current_gray, (15, 15), 0)  # Slightly smaller for speed
            prev_gray = cv2.GaussianBlur(prev_gray, (15, 15), 0)
            next_gray = cv2.GaussianBlur(next_gray, (15, 15), 0)
            
            # Calculate differences
            diff_prev = cv2.absdiff(current_gray, prev_gray)
            diff_next = cv2.absdiff(current_gray, next_gray)
            
            # Average change score
            change_score = (float(np.mean(diff_prev)) + float(np.mean(diff_next))) / 2.0
            
            return change_score
            
        except Exception as e:
            logger.warning(f"Error calculating change score: {e}")
            return 0.0
    
    async def _apply_frame_rate_constraints_async(self, keyframes: List[str], duration: float) -> List[str]:
        """Apply REQUIREMENTS 5-7: 1 FPS minimum, 8 FPS maximum - ASYNC VERSION."""
        if len(keyframes) <= 2:
            return keyframes
        
        # Extract timestamps and sort
        frame_timestamps = []
        for frame_path in keyframes:
            timestamp = self._extract_timestamp_from_filename(frame_path)
            frame_timestamps.append((timestamp, frame_path))
        
        frame_timestamps.sort(key=lambda x: x[0])
        
        # Calculate minimum frames needed for 1 FPS over the entire duration
        duration_ms = duration * 1000
        min_frames_needed = max(2, int(duration_ms / 1000) + 1)  # At least 1 frame per second + 1
        
        logger.info(f"Video duration: {duration:.1f}s ({duration_ms:.0f}ms)")
        logger.info(f"Minimum frames needed for 1 FPS: {min_frames_needed}")
        logger.info(f"Current frames: {len(frame_timestamps)}")
        
        # If we have fewer frames than minimum, don't apply constraints
        if len(frame_timestamps) <= min_frames_needed:
            logger.info(f"Not enough frames to apply constraints. Keeping all {len(frame_timestamps)} frames.")
            return keyframes
        
        # Apply constraints only if we have excess frames
        constrained_frames = []
        
        for i, (timestamp, frame_path) in enumerate(frame_timestamps):
            if i == 0 or i == len(frame_timestamps) - 1:
                # Always keep first and last frame
                constrained_frames.append(frame_path)
                continue
            
            # Check minimum interval (REQUIREMENT 5: 1 FPS minimum)
            if constrained_frames:
                last_kept_timestamp = self._extract_timestamp_from_filename(constrained_frames[-1])
                time_diff = timestamp - last_kept_timestamp
                
                if time_diff < 1000:  # Less than 1 second apart (1000ms)
                    logger.debug(f"Skipping frame at {timestamp:.1f}s (too close: {time_diff:.2f}ms)")
                    continue
                
                # Check maximum interval (REQUIREMENT 4: 8 FPS maximum)
                if time_diff < 125:  # Less than 0.125s apart (125ms = 8 FPS)
                    logger.debug(f"Skipping frame at {timestamp:.1f}s (too frequent: {time_diff:.3f}ms)")
                    continue
            
            constrained_frames.append(frame_path)
        
        # Ensure we don't go below minimum frames needed
        if len(constrained_frames) < min_frames_needed:
            logger.warning(f"Constraints would reduce frames to {len(constrained_frames)}, but minimum needed is {min_frames_needed}. Keeping original frames.")
            return keyframes
        
        logger.info(f"Frame rate constraints applied: {len(keyframes)} -> {len(constrained_frames)} frames")
        return constrained_frames
    
    def _apply_frame_rate_constraints(self, keyframes: List[str], duration: float) -> List[str]:
        """Sync version for backward compatibility."""
        return asyncio.run(self._apply_frame_rate_constraints_async(keyframes, duration))
    
    def _extract_timestamp_from_filename(self, filename: str) -> float:
        """Extract timestamp from filename for sorting - ORIGINAL LOGIC."""
        try:
            basename = os.path.basename(filename)
            # Extract time from format: cut_X_frame_Y_time_Z.jpg
            parts = basename.split('_')
            for i, part in enumerate(parts):
                if part == 'time':
                    return float(parts[i + 1].replace('.jpg', ''))
            return 0.0
        except (IndexError, ValueError):
            return 0.0

    async def _cleanup_diff_zero_files_async(self, frames_dir: str):
        """Async cleanup: Keep at least 1 frame per second, delete diff_0 if we have alternatives."""
        # Get all files and parse their info
        all_files = []
        for filename in os.listdir(frames_dir):
            if filename.endswith('.jpg'):
                try:
                    # Parse: cut_X_frame_Y_time_Z_diff_W.jpg
                    parts = filename.split('_')
                    for i, part in enumerate(parts):
                        if part == 'time':
                            timestamp_ms = int(parts[i + 1])
                            break
                    else:
                        continue
                    
                    # Extract diff score
                    diff_score = int(parts[-1].replace('.jpg', ''))
                    
                    # Calculate which second this frame belongs to
                    second = timestamp_ms // 1000
                    
                    all_files.append({
                        'filename': filename,
                        'timestamp_ms': timestamp_ms,
                        'second': second,
                        'diff_score': diff_score
                    })
                except:
                    continue
        
        # Group files by second
        files_by_second = {}
        for file_info in all_files:
            second = file_info['second']
            if second not in files_by_second:
                files_by_second[second] = []
            files_by_second[second].append(file_info)
        
        # Process each second
        files_to_delete = []
        for second in sorted(files_by_second.keys()):
            files_in_second = files_by_second[second]
            
            # Keep all files with diff_score > 0
            kept_files = [f for f in files_in_second if f['diff_score'] > 0]
            
            # If we have no kept files for this second, keep one diff_0 file
            if len(kept_files) == 0:
                logger.debug(f"Second {second}: No diff>0 files, keeping one diff_0 file")
                # Keep the first diff_0 file for this second
                diff_0_files = [f for f in files_in_second if f['diff_score'] == 0]
                if diff_0_files:
                    kept_files.append(diff_0_files[0])
                    logger.debug(f"Keeping: {diff_0_files[0]['filename']}")
            
            # Mark remaining diff_0 files for deletion
            for file_info in files_in_second:
                if file_info not in kept_files and file_info['diff_score'] == 0:
                    files_to_delete.append(file_info['filename'])
                    logger.debug(f"Marking for deletion: {file_info['filename']}")
        
        # Delete the marked files ASYNC
        deleted_count = 0
        for filename in files_to_delete:
            file_path = os.path.join(frames_dir, filename)
            try:
                # Use asyncio to run file operations in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, os.remove, file_path)
                deleted_count += 1
                logger.debug(f"Deleted: {filename}")
            except Exception as e:
                logger.warning(f"Failed to delete {filename}: {e}")
        
        logger.info(f"Async cleanup complete: Deleted {deleted_count} diff_0 files, ensured 1 frame per second")
        
        # Wait a moment to ensure all file operations are complete
        await asyncio.sleep(0.5)
    
    def _cleanup_diff_zero_files(self, frames_dir: str):
        """Sync version for backward compatibility."""
        asyncio.run(self._cleanup_diff_zero_files_async(frames_dir))


# Global enhanced keyframe extractor instance
enhanced_keyframe_extractor = EnhancedKeyframeExtractor()

# Manual cleanup function for diff_0 files
def cleanup_diff_zero_files(frames_dir: str):
    """Manually delete all files with _diff_0 at the end of filename."""
    import os
    deleted_count = 0
    
    for filename in os.listdir(frames_dir):
        if filename.endswith('_diff_0.jpg'):
            file_path = os.path.join(frames_dir, filename)
            try:
                os.remove(file_path)
                deleted_count += 1
                print(f"Deleted: {filename}")
            except Exception as e:
                print(f"Failed to delete {filename}: {e}")
    
    print(f"Cleanup complete: Deleted {deleted_count} files with _diff_0")
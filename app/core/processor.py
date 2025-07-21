
"""
Core video processing pipeline for exercise clip extraction.

PLAN:
1. (services/downloaders.py) download the video and description & tags (in storage/temp) 
2. (services/transcription.py) get the transcript - first make sure it has audio > then get the transcript
3. (utils/enhanced_keyframe_extraction.py) extract the frames from the video
4. Build prompt with all frames, transcript, video description and tags, and video duration
5. Send to LLM with all frames and get JSON response
6. Use JSON to create video clips from the original video
7. Save clips to storage/clips as {exercise_name}_{urlid}.mp4
8. Save clip information to database
9. Save all data to qdrant database as a vector
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import cv2
import ffmpeg
import numpy as np
from openai import OpenAI
import google.generativeai as genai  # type: ignore
import subprocess

from app.services.downloaders import download_media_and_metadata
from app.services.transcription import transcribe_audio
from app.database.operations import store_exercise, get_database_connection, check_existing_processing
from app.database.vectorization import store_embedding
from app.utils.url_processor import extract_carousel_info, detect_carousel_items
from app.utils.enhanced_keyframe_extraction import enhanced_keyframe_extractor

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Main video processing pipeline for exercise detection and clip generation."""
    
    def __init__(self):
        # Initialize clients lazily to avoid import-time errors
        self.openai_client = None
        self.gemini_model = None
        
    def _get_openai_client(self):
        """Get OpenAI client, initializing if needed."""
        if self.openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.openai_client = OpenAI(api_key=api_key)
        return self.openai_client
    
    def _get_gemini_model(self, use_backup=False):
        """Get Gemini model, initializing if needed."""
        if self.gemini_model is None or use_backup:
            # Try primary key first, then backup key
            api_key = os.getenv("GEMINI_API_KEY" if not use_backup else "GEMINI_API_BACKUP_KEY")
            if not api_key:
                if use_backup:
                    raise ValueError("Both GEMINI_API_KEY and GEMINI_API_BACKUP_KEY environment variables not set")
                else:
                    raise ValueError("GEMINI_API_KEY environment variable not set")
            
            # Configure with the selected API key
            genai.configure(api_key=api_key)  # type: ignore
            model = genai.GenerativeModel('models/gemini-2.5-flash-lite-preview-06-17')  # type: ignore
            
            # If using backup key, return the model directly (don't cache it)
            if use_backup:
                return model
            
            # Cache the primary model
            self.gemini_model = model
        
        return self.gemini_model
        
    async def process_video(self, url: str) -> Dict:
        """
        Complete video processing pipeline.
        
        Args:
            url: Video URL to process
            
        Returns:
            Dict with processing results
        """
        start_time = time.time()
        temp_dir = None
        
        try:
            # Extract carousel information
            normalized_url, carousel_index = extract_carousel_info(url)
            logger.info(f"Processing URL: {url} -> normalized: {normalized_url}, carousel_index: {carousel_index}")
            
            # Check if already processed (but allow multiple exercises per URL/carousel)
            # We'll let the database constraint handle duplicates at the exercise level
            logger.info(f"Processing URL: {normalized_url} (index: {carousel_index}) - allowing multiple exercises")
            
            # Step 1: Download video and extract metadata
            logger.info(f"Starting video processing for: {url}")
            download_result = await download_media_and_metadata(url)
            temp_dir = download_result['temp_dir']
            
            # Process all video files from the download
            all_stored_exercises = []
            
            # Get all video files from the download result
            video_files = download_result['files']
            logger.info(f"Processing {len(video_files)} video files from download")
            
            # Process each video file individually
            for i, video_file in enumerate(video_files):
                logger.info(f"Processing video {i+1}/{len(video_files)}: {os.path.basename(video_file)}")
                
                # Step 2: Transcribe audio for this video
                logger.info(f"Transcribing audio for {os.path.basename(video_file)}...")
                transcript = await transcribe_audio(video_file)
                
                # Save transcript to temp directory for debugging
                transcript_file = os.path.join(temp_dir, f"transcript_{i+1}.json")
                with open(transcript_file, 'w') as f:
                    json.dump(transcript, f, indent=2)
                logger.info(f"Saved transcript to: {transcript_file}")
                
                # Step 3: Extract keyframes for this video
                logger.info(f"Extracting keyframes for {os.path.basename(video_file)}...")
                frames_dir = os.path.join(temp_dir, f"frames_{i+1}")
                os.makedirs(frames_dir, exist_ok=True)
                
                # Extract frames using enhanced keyframe extractor
                frame_files = await enhanced_keyframe_extractor.extract_keyframes(video_file, frames_dir)
                logger.info(f"Enhanced keyframe extractor completed, extracted {len(frame_files)} frames")
                
                # Get ALL frames from the folder (bypass any filtering)
                all_frames_in_folder = []
                if os.path.exists(frames_dir):
                    for filename in os.listdir(frames_dir):
                        if filename.endswith('.jpg'):
                            frame_path = os.path.join(frames_dir, filename)
                            all_frames_in_folder.append(frame_path)
                
                logger.info(f"Found {len(all_frames_in_folder)} frames in folder vs {len(frame_files)} from extractor")
                
                # Use ALL frames from folder instead of filtered list
                frame_files = all_frames_in_folder
                
                # Step 4: AI exercise detection for this video
                logger.info(f"Detecting exercises with AI for {os.path.basename(video_file)}...")
                
                # Add carousel context for better AI decision making
                carousel_context = ""
                if download_result.get('is_carousel', False):
                    carousel_count = download_result.get('carousel_count', 1)
                    carousel_context = f"""
CAROUSEL CONTEXT:
This is video {i+1} of {carousel_count} in an Instagram carousel.
- First videos in carousels are often intro/hook videos with no actual exercises
- Look for text overlays, captions, or spoken content that indicates this is just an intro
- If the video shows text like "these exercises..." but never specifies what they are, it's likely an intro
- If the video has large, all-encompassing text overlays without specific exercise instructions, skip it
- Only process videos that contain actual exercise demonstrations or specific workout instructions
"""
                
                exercises = await self._detect_exercises(
                    video_file=video_file,
                    transcript=transcript,
                    frames=frame_files,
                    metadata=download_result,
                    temp_dir=temp_dir,
                    carousel_context=carousel_context,
                    carousel_index=i+1,
                    total_carousel_items=download_result.get('carousel_count', 1)
                )
                
                # Step 5: Generate clips for this video
                logger.info(f"Generating exercise clips for {os.path.basename(video_file)}...")
                clips = await self._generate_clips(video_file, exercises, temp_dir)
                
                # Step 6: Store in database for this video
                logger.info(f"Storing exercises in database for {os.path.basename(video_file)}...")
                stored_exercises = await self._store_exercises(url, normalized_url, carousel_index, clips)
                all_stored_exercises.extend(stored_exercises)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "processed_clips": all_stored_exercises,
                "total_clips": len(all_stored_exercises),
                "processing_time": processing_time,
                "temp_dir": temp_dir
            }
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            if temp_dir and os.path.exists(temp_dir):
                await self._cleanup_temp_files(temp_dir)
            raise
    
    async def _detect_exercises(self, video_file: str, transcript: List[Dict], 
                               frames: List[str], metadata: Dict, temp_dir: Optional[str] = None,
                               carousel_context: str = "", carousel_index: int = 1, 
                               total_carousel_items: int = 1) -> List[Dict]:
        """Use Gemini to detect exercises in the video."""
        
        # Get video duration using OpenCV
        cap = cv2.VideoCapture(video_file)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = total_frames / fps if fps > 0 else 0
        cap.release()
        
        # Analyze transcript quality - check if transcript duration matches video duration
        transcript_text = ""
        meaningful_transcript = False
        
        # Calculate transcript duration
        if transcript:
            transcript_duration = max(segment['end'] for segment in transcript)
            # Check if transcript duration is close to video duration (within 10% tolerance)
            duration_diff = abs(transcript_duration - video_duration)
            duration_tolerance = video_duration * 0.1  # 10% tolerance
            
            if duration_diff <= duration_tolerance:
                meaningful_transcript = True
                logger.info(f"Transcript duration ({transcript_duration:.1f}s) matches video duration ({video_duration:.1f}s)")
            else:
                logger.info(f"Transcript duration ({transcript_duration:.1f}s) doesn't match video duration ({video_duration:.1f}s) - likely music/silence")
        else:
            logger.info("No transcript available")
        
        # Only include transcript if it contains meaningful content
        if meaningful_transcript:
            for segment in transcript:
                transcript_text += f"[{segment['start']:.1f}s - {segment['end']:.1f}s] {segment['text']}\n"
            transcript_section = f"TRANSCRIPT: {transcript_text}"
        else:
            transcript_section = ""
            logger.info("Transcript excluded from AI prompt - likely music/silence only")
        
        # Prepare frame data for Gemini
        frame_data = []
        frame_explanations = []
        
        # Get all available frames and sort by timestamp
        available_frames = []
        logger.info(f"🔍 Processing {len(frames)} total frames from enhanced keyframe extractor")
        
        # Log all frame paths to debug
        logger.info(f"📄 All frame paths from extractor:")
        for i, frame_path in enumerate(frames):
            logger.info(f"  {i+1:2d}. {frame_path}")
        
        # Use ALL frames that exist
        available_frames = []
        for frame_path in frames:
            if os.path.exists(frame_path):
                available_frames.append(frame_path)
                logger.info(f"✅ Using frame: {os.path.basename(frame_path)}")
            else:
                logger.warning(f"⚠️  Frame file does not exist: {frame_path}")
        
        logger.info(f"📊 Found {len(available_frames)} frames out of {len(frames)} total frames")
        
        if len(available_frames) == 0:
            logger.warning("No frames to process!")
            return []
        
        for frame_path in available_frames:
            # Just read the original frame file and send it to LLM
            with open(frame_path, 'rb') as f:
                frame_data.append({
                    'mime_type': 'image/jpeg',
                    'data': f.read()
                })
            
            # Extract frame information for explanation using simplified naming convention
            filename = os.path.basename(frame_path)
            # New format: cut_X_start_time_Y_end_time_Z.jpg
            parts = filename.replace('.jpg', '').split('_')
            
            if len(parts) >= 6:  # cut_X_start_time_Y_end_time_Z
                cut_number = parts[1]
                start_time_ms = int(parts[3])
                end_time_ms = int(parts[5])
                start_time_seconds = start_time_ms / 1000.0
                end_time_seconds = end_time_ms / 1000.0
                
                # Explain what each component means
                frame_explanation = f"Cut {cut_number}: {start_time_seconds:.3f}s to {end_time_seconds:.3f}s"
                frame_explanations.append(frame_explanation)
        
        # Create simplified cut start/end time information
        cut_start_end_time = "\n".join(frame_explanations) if frame_explanations else "No cuts available"
        # Log exactly how many frames we're sending
        logger.info(f"🚀 Sending {len(frame_data)} frames to LLM")
        logger.info(f"📊 Frame explanations count: {len(frame_explanations)}")
        
        # Create prompt for Gemini
        prompt = f"""
Analyze this workout video and extract individual exercise segments with complete details:

VIDEO METADATA:
- Description: {metadata.get('description', 'No description')}
- Tags: {', '.join(metadata.get('tags', []))}
- Duration: {video_duration:.1f} seconds (actual video duration)

{carousel_context}

{transcript_section}

FRAME ANALYSIS:
The frames show different video segments/cuts with their start and end times:
{cut_start_end_time}

FRAMES: [attached keyframes with movement analysis]

CRITICAL RULES:
1. **NO OVERLAPPING EXERCISES**: Each exercise must have unique, non-overlapping time ranges
2. **ONE EXERCISE PER TIME SEGMENT**: If multiple frames show the same time period, identify ONE primary exercise
3. **AVOID DUPLICATES**: Do not create multiple exercises that describe the same movement pattern
4. **PRIORITIZE COMPLETE MOVEMENTS**: Choose the most complete/representative exercise for each time segment

EXERCISE FLOW CONCEPT:
An "exercise flow" is a series of exercises performed in sequence that together form one complete repetition. For example:
- A yoga flow might be: Downward Dog → Plank → Chaturanga → Upward Dog → Downward Dog
- A strength flow might be: Push-up → Mountain Climber → Burpee → Jump Squat
- A mobility flow might be: Cat-Cow → Child's Pose → Thread the Needle → Pigeon Pose

Each flow is considered ONE exercise with multiple movements within it. The entire flow gets one exercise name and timing.

For each distinct exercise or flow you identify, provide a JSON response with:
{{
  "exercises": [
    {{
      "exercise_name": "specific exercise name or flow name",
      "start_time": 0.0,
      "end_time": 0.0,
      "how_to": "detailed step-by-step instructions for the entire exercise or flow",
      "benefits": "physical/mental benefits, muscles targeted, nervous system effects",
      "counteracts": "problems this exercise helps solve (sitting, stiffness, etc.)",
      "fitness_level": 0-10,
      "rounds_reps": "specific instructions for duration/repetitions",
      "intensity": 0-10,
      "confidence_score": 0.95
    }}
  ]
}}

DETECTION RULES:
- Look for sustained movement patterns that last 3.5+ seconds
- Skip intro segments (first 2-3 seconds usually)
- Skip outro segments (last 2-3 seconds usually) 
- Skip brief demonstrations or transitions
- Each exercise should show a complete movement pattern
- Use EXACT frame timestamps for start_time and end_time
- Focus on exercises with instructional value
- Avoid repetitive or low-quality segments
- If you see a series of connected movements, treat them as ONE flow exercise
- If movements are clearly separate with pauses, treat them as separate exercises
- **CRITICAL**: Ensure NO time overlap between exercises - each second should only belong to ONE exercise
- If the entire video shows one continuous movement, identify it as ONE exercise
"""
        
        # Save AI prompt and metadata to temp directory for debugging
        if temp_dir:
            debug_data = {
                "prompt": prompt,
                "metadata": metadata,
                "transcript_segments": len(transcript),
                "frame_count": len(frame_data),
                "transcript_text": transcript_text,
                "video_duration": video_duration,
                "meaningful_transcript": meaningful_transcript,
                "transcript_included": bool(transcript_section),
                "frame_explanations": frame_explanations
            }
            debug_file = os.path.join(temp_dir, "ai_debug_data.json")
            with open(debug_file, 'w') as f:
                json.dump(debug_data, f, indent=2)
            logger.info(f"Saved AI debug data to: {debug_file}")
        
        try:
            # Call Gemini with multimodal input (try primary key first)
            try:
                gemini_model = self._get_gemini_model(use_backup=False)
                response = gemini_model.generate_content([prompt] + frame_data)
                logger.info("Successfully used primary Gemini API key")
            except Exception as primary_error:
                logger.warning(f"Primary Gemini API failed: {str(primary_error)}")
                logger.info("Attempting to use backup Gemini API key...")
                
                # Try backup key
                gemini_model = self._get_gemini_model(use_backup=True)
                response = gemini_model.generate_content([prompt] + frame_data)
                logger.info("Successfully used backup Gemini API key")
            
            # Parse JSON response with better error handling
            response_text = response.text.strip()
            logger.info(f"Raw AI response: {response_text[:200]}...")
            
            # Save AI response to temp directory for debugging
            if temp_dir:
                response_file = os.path.join(temp_dir, "ai_response.txt")
                with open(response_file, 'w') as f:
                    f.write(response_text)
                logger.info(f"Saved AI response to: {response_file}")
            
            # Try to extract JSON from various formats
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1]
            
            # Clean up the JSON text
            json_text = json_text.strip()
            if json_text.startswith('{') and json_text.endswith('}'):
                try:
                    exercises_data = json.loads(json_text)
                    exercises = exercises_data.get('exercises', [])
                    logger.info(f"Successfully parsed {len(exercises)} exercises from AI response")
                    return exercises
                except json.JSONDecodeError as json_error:
                    logger.error(f"JSON parsing error: {json_error}")
                    logger.error(f"Problematic JSON: {json_text}")
                    # Try to fix common JSON issues
                    try:
                        # Remove any trailing commas and comments
                        json_text = json_text.replace(',}', '}').replace(',]', ']')
                        # Remove JavaScript-style comments
                        import re
                        json_text = re.sub(r'//.*$', '', json_text, flags=re.MULTILINE)
                        json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)
                        exercises_data = json.loads(json_text)
                        exercises = exercises_data.get('exercises', [])
                        logger.info(f"Fixed JSON parsing, found {len(exercises)} exercises")
                        return exercises
                    except:
                        logger.error("Failed to fix JSON, using fallback")
                        return self._fallback_exercise_detection(transcript)
            else:
                logger.error("No valid JSON found in AI response")
                return self._fallback_exercise_detection(transcript)
            
        except Exception as e:
            logger.error(f"Error in AI exercise detection: {str(e)}")
            # Fallback: return basic exercise detection
            return self._fallback_exercise_detection(transcript)
    
    def _fallback_exercise_detection(self, transcript: List[Dict]) -> List[Dict]:
        """Fallback exercise detection when AI fails."""
        exercises = []
        
        # Simple heuristic: look for exercise-related keywords
        exercise_keywords = [
            'push-up', 'squat', 'plank', 'lunge', 'burpee', 'jumping jack',
            'mountain climber', 'sit-up', 'crunch', 'bridge', 'downward dog',
            'warrior', 'tree pose', 'sun salutation'
        ]
        
        for segment in transcript:
            text_lower = segment['text'].lower()
            for keyword in exercise_keywords:
                if keyword in text_lower:
                    exercises.append({
                        'exercise_name': keyword.replace('-', ' ').title(),
                        'start_time': segment['start'],
                        'end_time': segment['end'],
                        'how_to': f"Perform {keyword.replace('-', ' ')} as demonstrated in the video",
                        'benefits': "Improves strength and fitness",
                        'counteracts': "Sedentary lifestyle",
                        'fitness_level': 5,
                        'rounds_reps': "Follow video instructions",
                        'intensity': 5,
                        'confidence_score': 0.3
                    })
                    break
        
        return exercises
    
    async def _generate_clips(self, video_file: str, exercises: List[Dict], 
                             temp_dir: str, min_duration: float = 5.0) -> List[Dict]:
        """Generate video clips for each detected exercise."""
        clips = []
        
        logger.info(f"Starting clip generation for {len(exercises)} exercises")
        logger.info(f"Video file: {video_file}")
        logger.info(f"Temp dir: {temp_dir}")
        
        # Check for overlapping exercises and consolidate them
        if len(exercises) > 1:
            logger.info(f"Multiple exercises detected, checking for overlaps...")
            
            # Sort exercises by start time
            sorted_exercises = sorted(exercises, key=lambda x: x['start_time'])
            
            # Check for significant overlaps (>50% overlap)
            consolidated_exercises = []
            for i, exercise in enumerate(sorted_exercises):
                is_overlapping = False
                
                for j, other_exercise in enumerate(sorted_exercises):
                    if i == j:
                        continue
                    
                    # Calculate overlap
                    overlap_start = max(exercise['start_time'], other_exercise['start_time'])
                    overlap_end = min(exercise['end_time'], other_exercise['end_time'])
                    overlap_duration = max(0, overlap_end - overlap_start)
                    
                    exercise_duration = exercise['end_time'] - exercise['start_time']
                    other_duration = other_exercise['end_time'] - other_exercise['start_time']
                    
                    # Check if overlap is significant (>50% of either exercise)
                    overlap_ratio_exercise = overlap_duration / exercise_duration if exercise_duration > 0 else 0
                    overlap_ratio_other = overlap_duration / other_duration if other_duration > 0 else 0
                    
                    if float(overlap_ratio_exercise) > 0.5 or float(overlap_ratio_other) > 0.5:
                        logger.warning(f"⚠️  Significant overlap detected between '{exercise['exercise_name']}' and '{other_exercise['exercise_name']}'")
                        logger.warning(f"   Overlap: {overlap_duration:.1f}s ({overlap_ratio_exercise:.1%} of exercise, {overlap_ratio_other:.1%} of other)")
                        is_overlapping = True
                        break
                
                if not is_overlapping:
                    consolidated_exercises.append(exercise)
                else:
                    # If overlapping, keep the one with higher confidence or longer duration
                    exercise_confidence = float(exercise.get('confidence_score', 0))
                    other_confidence = float(other_exercise.get('confidence_score', 0))
                    
                    if exercise_confidence > other_confidence:
                        consolidated_exercises.append(exercise)
                        logger.info(f"✅ Kept '{exercise['exercise_name']}' (higher confidence)")
                    elif float(exercise_duration) > float(other_duration):
                        consolidated_exercises.append(exercise)
                        logger.info(f"✅ Kept '{exercise['exercise_name']}' (longer duration)")
                    else:
                        logger.info(f"✅ Kept '{other_exercise['exercise_name']}' (better choice)")
            
            if len(consolidated_exercises) < len(exercises):
                logger.info(f"Consolidated {len(exercises)} exercises down to {len(consolidated_exercises)} non-overlapping exercises")
                exercises = consolidated_exercises
        
        # If only one exercise detected, ensure it covers the full video duration
        if len(exercises) == 1:
            exercise = exercises[0]
            video_duration = self._get_video_duration(video_file)
            
            # If the exercise doesn't cover most of the video, extend it
            exercise_duration = exercise['end_time'] - exercise['start_time']
            video_coverage = exercise_duration / video_duration if video_duration > 0 else 0
            
            if video_coverage < 0.8:  # If exercise covers less than 80% of video
                logger.info(f"Single exercise detected but only covers {video_coverage:.1%} of video")
                logger.info(f"Extending exercise to cover full video duration")
                exercise['start_time'] = 0.0
                exercise['end_time'] = video_duration
                exercise['exercise_name'] = f"{exercise['exercise_name']} (Full Video)"
        
        # Additional check: Prevent multiple clips with start times within 3 seconds of each other
        if len(exercises) > 1:
            logger.info(f"Checking for exercises with start times within 3 seconds of each other...")
            
            # Sort by start time again
            sorted_exercises = sorted(exercises, key=lambda x: x['start_time'])
            filtered_exercises = []
            
            for i, exercise in enumerate(sorted_exercises):
                too_close = False
                
                # Check against all previously accepted exercises
                for accepted_exercise in filtered_exercises:
                    time_diff = abs(exercise['start_time'] - accepted_exercise['start_time'])
                    
                    if time_diff <= 3.0:  # Within 3 seconds
                        logger.warning(f"⚠️  Exercise '{exercise['exercise_name']}' starts too close to '{accepted_exercise['exercise_name']}' ({time_diff:.1f}s apart)")
                        logger.warning(f"   Skipping '{exercise['exercise_name']}' to prevent duplicate clips")
                        too_close = True
                        break
                
                if not too_close:
                    filtered_exercises.append(exercise)
                    logger.info(f"✅ Accepted '{exercise['exercise_name']}' (start time: {exercise['start_time']:.1f}s)")
                else:
                    logger.info(f"❌ Skipped '{exercise['exercise_name']}' (too close to existing exercise)")
            
            if len(filtered_exercises) < len(exercises):
                logger.info(f"Filtered {len(exercises)} exercises down to {len(filtered_exercises)} with adequate time separation")
                exercises = filtered_exercises
        
        for i, exercise in enumerate(exercises):
            try:
                logger.info(f"Processing exercise {i+1}/{len(exercises)}: {exercise['exercise_name']}")
                
                # Create clips directory in storage
                clips_dir = os.path.join("storage", "clips")
                os.makedirs(clips_dir, exist_ok=True)
                logger.info(f"Created clips directory: {clips_dir}")
                
                # Generate unique filename with URL ID
                exercise_name_clean = exercise['exercise_name'].replace(' ', '_').lower()
                url_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID as URL ID
                clip_filename = f"{exercise_name_clean}_{url_id}.mp4"
                clip_path = os.path.join(clips_dir, clip_filename)
                logger.info(f"Clip path: {clip_path}")
                
                # Extract clip using subprocess and ffmpeg
                start_time = exercise['start_time']
                duration = exercise['end_time'] - exercise['start_time']
                
                # Filter out clips that are too short
                if duration < min_duration:
                    logger.warning(f"⚠️  Skipping {exercise['exercise_name']} - duration {duration:.1f}s < {min_duration}s minimum")
                    continue
                
                # Filter out clips that are too long (likely not useful)
                if duration > 60.0:
                    logger.warning(f"⚠️  Skipping {exercise['exercise_name']} - duration {duration:.1f}s > 60s maximum")
                    continue
                
                # Check if the exercise has meaningful content
                if exercise.get('confidence_score', 0) < 0.3:
                    logger.warning(f"⚠️  Skipping {exercise['exercise_name']} - low confidence score {exercise.get('confidence_score', 0):.2f}")
                    continue
                
                logger.info(f"Extracting clip: {start_time}s to {exercise['end_time']}s (duration: {duration}s)")
                
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-y',
                    '-i', video_file,
                    '-ss', str(start_time),
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    clip_path
                ]
                logger.info(f"Running ffmpeg command: {' '.join(ffmpeg_cmd)}")
                
                # Run ffmpeg in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                )
                logger.info(f"ffmpeg stdout: {result.stdout[:500]}")
                logger.info(f"ffmpeg stderr: {result.stderr[:500]}")
                if result.returncode != 0:
                    logger.error(f"ffmpeg failed with return code {result.returncode}")
                    continue
                
                # Verify clip was created
                if os.path.exists(clip_path):
                    file_size = os.path.getsize(clip_path)
                    exercise['clip_path'] = clip_path
                    exercise['segments'] = [{
                        'start_time': start_time,
                        'end_time': exercise['end_time']
                    }]
                    clips.append(exercise)
                    logger.info(f"✅ Generated clip: {clip_path} ({file_size:,} bytes)")
                else:
                    logger.error(f"❌ Failed to generate clip for {exercise['exercise_name']} - file not created")
                    
            except Exception as e:
                logger.error(f"❌ Error generating clip for {exercise['exercise_name']}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue
        
        logger.info(f"Clip generation complete. Generated {len(clips)} clips out of {len(exercises)} exercises")
        return clips
    
    async def _store_exercises(self, url: str, normalized_url: str, carousel_index: int, clips: List[Dict]) -> List[Dict]:
        """Store exercises in database and vector store."""
        stored_exercises = []
        
        for clip in clips:
            try:
                # Store in vector database with complete exercise data
                exercise_data = {
                    'exercise_name': clip['exercise_name'],
                    'video_path': clip['clip_path'],
                    'start_time': clip['start_time'],
                    'end_time': clip['end_time'],
                    'how_to': clip['how_to'],
                    'benefits': clip['benefits'],
                    'counteracts': clip['counteracts'],
                    'fitness_level': clip['fitness_level'],
                    'rounds_reps': clip['rounds_reps'],
                    'intensity': clip['intensity'],
                    'url': url
                }
                
                qdrant_id = await store_embedding(exercise_data)
                
                # Store in PostgreSQL
                exercise_id = await store_exercise(
                    url=url,
                    normalized_url=normalized_url,
                    carousel_index=carousel_index,
                    exercise_name=clip['exercise_name'],
                    video_path=clip['clip_path'],
                    start_time=clip['start_time'],
                    end_time=clip['end_time'],
                    how_to=clip['how_to'],
                    benefits=clip['benefits'],
                    counteracts=clip['counteracts'],
                    fitness_level=clip['fitness_level'],
                    rounds_reps=clip['rounds_reps'],
                    intensity=clip['intensity'],
                    qdrant_id=qdrant_id
                )
                
                stored_exercises.append({
                    'exercise_id': exercise_id,
                    'exercise_name': clip['exercise_name'],
                    'video_path': clip['clip_path'],
                    'segments_count': len(clip['segments']),
                    'total_duration': sum(s['end_time'] - s['start_time'] for s in clip['segments']),
                    'segments': clip['segments']
                })
                
            except Exception as e:
                logger.error(f"Error storing exercise {clip['exercise_name']}: {str(e)}")
                continue
        
        return stored_exercises
    
    def _get_video_duration(self, video_file: str) -> float:
        """Get video duration using OpenCV."""
        try:
            cap = cv2.VideoCapture(video_file)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            cap.release()
            return duration
        except Exception as e:
            logger.error(f"Error getting video duration: {str(e)}")
            return 0.0

    async def _cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files."""
        try:
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {str(e)}")

# Global processor instance
processor = VideoProcessor()        
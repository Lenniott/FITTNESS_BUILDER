
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
import time
from typing import Dict, List, Optional, Tuple
import uuid
from dotenv import load_dotenv
import cv2
from openai import OpenAI
import google.generativeai as genai  # type: ignore
import subprocess

from app.services.downloaders import download_media_and_metadata
from app.services.transcription import transcribe_audio
from app.database.operations import store_exercise, check_existing_processing
from app.database.vectorization import store_embedding
from app.utils.url_processor import extract_carousel_info
from app.utils.enhanced_keyframe_extraction import enhanced_keyframe_extractor
from app.database.job_status import update_job_status

logger = logging.getLogger(__name__)

"""
NOTE: This file implements the core video processing pipeline for extracting exercise clips from fitness videos. It:
- Downloads the video and metadata
- Transcribes audio if present
- Extracts all keyframes from the video
- Builds a prompt with all frames, transcript, description, tags, and duration
- Sends all frames and context to an LLM (Gemini) to detect exercises
- Receives a JSON response with exercise segments (name, start/end, how-to, etc.)
- Generates video clips for each exercise segment
- Saves clips to storage and records metadata in the database and vector store
- Handles carousels (multi-video posts) and edge cases (music-only, intros, etc.)
- Cleans up temp files after processing
Inputs: video URL. Outputs: processed exercise clips, metadata, and database records.
"""

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
        
    async def process_video(self, url: str, job_id: Optional[str] = None) -> Dict:
        """
        Complete video processing pipeline.
        If job_id is provided, update job status as the job progresses.
        """
        start_time = time.time()
        temp_dir = None
        try:
            if job_id is not None:
                await update_job_status(job_id, 'in_progress')
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
- First videos in carousels are often intro/hook videos and the exercises are hidden under the text so are not useful or they are a montage of exercises so we should skip them, unless we can see a full exercise clearly in the video.
- Look for text overlays, captions, or spoken content that indicates this is just an intro
- If the video shows text is in the center of the screen obstructing the exercise, skip it.
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
                
                # After AI/LLM response, ensure all start_time and end_time are floats
                for ex in exercises:
                    try:
                        ex['start_time'] = float(ex['start_time'])
                        ex['end_time'] = float(ex['end_time'])
                    except Exception as e:
                        logger.warning(f"Skipping exercise with non-numeric times: {ex} ({e})")
                        ex['start_time'] = -1
                        ex['end_time'] = -1
                # Remove any exercises with invalid times
                exercises = [ex for ex in exercises if ex['start_time'] != -1 and ex['end_time'] != -1]
                
                # Step 5: Generate clips for this video
                logger.info(f"Generating exercise clips for {os.path.basename(video_file)}...")
                clips = await self._generate_clips(video_file, exercises, temp_dir)
                
                # Step 6: Store in database for this video
                logger.info(f"Storing exercises in database for {os.path.basename(video_file)}...")
                stored_exercises = await self._store_exercises(url, normalized_url, carousel_index, clips)
                all_stored_exercises.extend(stored_exercises)
            
            processing_time = time.time() - start_time
            
            result = {
                "success": True,
                "processed_clips": all_stored_exercises,
                "total_clips": len(all_stored_exercises),
                "processing_time": processing_time,
                "temp_dir": temp_dir
            }
            if job_id is not None:
                await update_job_status(job_id, 'done', result)
            return result
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            if temp_dir and os.path.exists(temp_dir):
                await self._cleanup_temp_files(temp_dir)
            if job_id is not None:
                await update_job_status(job_id, 'failed', {"error": str(e)})
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
        
        for idx, frame_path in enumerate(available_frames):
            # Just read the original frame file and send it to LLM
            with open(frame_path, 'rb') as f:
                frame_data.append({
                    'mime_type': 'image/jpeg',
                    'data': f.read()
                })
            
            # Extract frame information for explanation using simplified naming convention
            filename = os.path.basename(frame_path)
            # Format: cut_{cutNumber}_frame_{frameNumber}_time_{timestamp_ms}_diff_{diffScore}.jpg
            parts = filename.replace('.jpg', '').split('_')
            try:
                cut_number = parts[1]
                timestamp_ms = int(parts[5])
                timestamp_seconds = timestamp_ms / 1000.0
                frame_explanation = (
                    f"{idx+1}. Cut {cut_number}, Time {timestamp_seconds:.3f}s"
                )
                frame_explanations.append(frame_explanation)
            except Exception as e:
                logger.warning(f"Could not parse frame filename: {filename} ({e})")
        
        # Create simplified cut start/end time information
        cut_start_end_time = "\n".join(frame_explanations) if frame_explanations else "No cuts available"
        # Log exactly how many frames we're sending
        logger.info(f"🚀 Sending {len(frame_data)} frames to LLM")
        logger.info(f"📊 Frame explanations count: {len(frame_explanations)}")
        
        # Build carousel context section
        carousel_context_section = f"""
📌 CAROUSEL CONTEXT
This video is item {carousel_index} of {total_carousel_items} in a carousel post.

Carousel slides in fitness content often serve different purposes:

1. **Video 1 (First)**: 
   - Often a hook or promotional showreel.
   - May contain title text or overlay obstructing the movement.
   - May contain a fast montage of exercises with no complete reps.
   - 🤖 Rule: **Skip unless full, clearly visible exercise movement is demonstrated.**

2. **Middle Videos (2 to N-1)**:
   - Typically feature fully demonstrated exercises.
   - 🤖 Rule: **Prioritize for exercise detection.**

3. **Final Video (Last)**:
   - Might showcase additional tips, credits, or cool-downs.
   - 🤖 Rule: **Analyze carefully—include only if instructional content or movement is clear.**

Use this structure to decide which frames are worth processing as exercise clips.
"""

        # Create prompt for Gemini
        prompt = f"""
You're an expert in exercise video segmentation. Your task is to analyze a video's frames, visual cuts (with timestamps), transcript (when available), and video description to identify discrete *exercise segments*.

Use the following process step-by-step:

---

**STEP 1: Frame Cut Analysis**
Read each named cut (e.g., ) and answer:
- Does it depict a *full single exercise* or *a sequence (flow)*?
- Is there enough visible movement (minimum 3.5s) to identify an exercise?
- Is it a demonstration (incomplete/mid-rep), a transition, or a useful tutorial segment?
- Is the movement unique (vs already described)?

✅ Keep if:
- The movement is sustained (3.5s+) and visually instructive.
- It shows a unique movement pattern.
- It starts close to the frame's `start_time` and ends cleanly.

🚫 Skip if:
- There's overlaid text over the exercise (e.g. intro).
- It's a montage, warm-up clip, or transition between moves.
- It's repeated content or an unclear camera angle.
- No noteworthy movement occurs.

---

**STEP 2: Timestamp Anchoring**
For valid frames:
- Align start and end times with the actual timestamps from frame labeling (e.g., start_time = 14.0 if frame = "cut_3_frame_123_time_14000_diff_7.jpg").

---

**STEP 3: Build JSON Output**
For each exercise, you must provide a clear, actionable recommendation for `rounds_reps`:
- If the video does not specify, use your expertise to recommend a typical rep/round scheme for this movement, as a fitness instructor would (e.g., "Perform 10-12 controlled reps per side, resting 30 seconds between sets." or "Complete 3 rounds of 45 seconds each, focusing on form.").
- Never leave this field vague or empty—always provide a clear, actionable recommendation.

Provide final results in this format (use numbers for start_time and end_time):

```json
{{
  "exercises": [
    {{
      "exercise_name": "Downward Dog → Upward Dog Flow",
      "start_time": 14.0,
      "end_time": 20.5,
      "how_to": "Start in downward dog... transition through chaturanga... upward dog...",
      "benefits": "Improves spinal mobility and shoulder strength.",
      "counteracts": "Great if you sit long hours; releases tension in lower back.",
      "fitness_level": 3,
      "rounds_reps": "Perform 10-12 controlled reps per side, resting 30 seconds between sets.",
      "intensity": 4,
      "confidence_score": 0.91
    }}
  ]
}}
```

Output must:

Include only non-overlapping exercises;
Avoid repetitive entries;
Respect the real start/end boundaries tied to frame metadata;
Treat flows (chained movements) as one exercise if performed as a full circuit.

{carousel_context_section}

VIDEO METADATA

Description: {metadata.get('description', 'No description')}
Tags: {', '.join(metadata.get('tags', []))}
Duration: {video_duration:.1f} seconds
TRANSCRIPT
{transcript_section or "None (music / silent video)"}

FRAME TIMESTAMPS
{cut_start_end_time}

Please analyze the video and return a JSON structure of distinct exercises using the logic above.
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
        
        # Pre-filter: Only keep exercises with valid float times
        def is_valid_time(ex):
            try:
                float(ex.get('start_time', -1))
                float(ex.get('end_time', -1))
                return True
            except (TypeError, ValueError):
                logger.warning(f"Skipping exercise with invalid times: {ex}")
                return False

        filtered_exercises = [ex for ex in exercises if is_valid_time(ex)]
        # Now all start/end times are valid floats

        # Sort by start time
        filtered_exercises.sort(key=lambda x: float(x['start_time']))

        consolidated_exercises = []
        for i, exercise in enumerate(filtered_exercises):
            start_time = float(exercise['start_time'])
            end_time = float(exercise['end_time'])
            is_overlapping = False
            for j, other_exercise in enumerate(filtered_exercises):
                if i == j:
                    continue
                other_start = float(other_exercise['start_time'])
                other_end = float(other_exercise['end_time'])
                # Overlap logic
                overlap_start = max(start_time, other_start)
                overlap_end = min(end_time, other_end)
                overlap_duration = max(0.0, overlap_end - overlap_start)
                exercise_duration = end_time - start_time
                other_duration = other_end - other_start
                overlap_ratio_exercise = overlap_duration / exercise_duration if exercise_duration > 0 else 0.0
                overlap_ratio_other = overlap_duration / other_duration if other_duration > 0 else 0.0
                if overlap_ratio_exercise > 0.5 or overlap_ratio_other > 0.5:
                    is_overlapping = True
                    break
            if not is_overlapping:
                consolidated_exercises.append(exercise)
        # If only one exercise detected, ensure it covers the full video duration
        if len(consolidated_exercises) == 1:
            exercise = consolidated_exercises[0]
            video_duration = self._get_video_duration(video_file)
            start_time = float(exercise.get('start_time', 0.0))
            end_time = float(exercise.get('end_time', 0.0))
            if start_time == -1 or end_time == -1: # Check for -1 from is_valid_time
                logger.warning(f"⚠️  Invalid start or end time for single exercise: {exercise}")
                return []
            exercise_duration = end_time - start_time
            video_coverage = exercise_duration / video_duration if video_duration > 0 else 0.0
            if video_coverage < 0.8:
                logger.info(f"Single exercise detected but only covers {video_coverage:.1%} of video")
                logger.info(f"Extending exercise to cover full video duration")
                exercise['start_time'] = 0.0
                exercise['end_time'] = video_duration
                exercise['exercise_name'] = f"{exercise['exercise_name']} (Full Video)"
        # Additional check: Prevent multiple clips with start times within 3 seconds of each other
        if len(consolidated_exercises) > 1:
            logger.info(f"Checking for exercises with start times within 3 seconds of each other...")
            sorted_exercises = []
            for ex in consolidated_exercises:
                st = float(ex.get('start_time', 0.0))
                if st == -1: # Check for -1 from is_valid_time
                    logger.warning(f"⚠️  Skipping exercise with invalid start_time: {ex}")
                    continue
                sorted_exercises.append(ex)
            sorted_exercises = sorted(sorted_exercises, key=lambda x: float(x['start_time']))
            filtered_exercises = []
            for i, exercise in enumerate(sorted_exercises):
                too_close = False
                start_time = float(exercise.get('start_time', 0.0))
                if start_time == -1: # Check for -1 from is_valid_time
                    logger.warning(f"⚠️  Invalid start_time for exercise: {exercise}")
                    continue
                for accepted_exercise in filtered_exercises:
                    accepted_start = float(accepted_exercise.get('start_time', 0.0))
                    if accepted_start == -1: # Check for -1 from is_valid_time
                        continue
                    time_diff = abs(start_time - accepted_start)
                    if time_diff <= 3.0:
                        logger.warning(f"⚠️  Exercise '{exercise['exercise_name']}' starts too close to '{accepted_exercise['exercise_name']}' ({time_diff:.1f}s apart)")
                        logger.warning(f"   Skipping '{exercise['exercise_name']}' to prevent duplicate clips")
                        too_close = True
                        break
                if not too_close:
                    filtered_exercises.append(exercise)
                    logger.info(f"✅ Accepted '{exercise['exercise_name']}' (start time: {start_time:.1f}s)")
                else:
                    logger.info(f"❌ Skipped '{exercise['exercise_name']}' (too close to existing exercise)")
            if len(filtered_exercises) < len(consolidated_exercises):
                logger.info(f"Filtered {len(consolidated_exercises)} exercises down to {len(filtered_exercises)} with adequate time separation")
                consolidated_exercises = filtered_exercises
        for i, exercise in enumerate(consolidated_exercises):
            try:
                logger.info(f"Processing exercise {i+1}/{len(consolidated_exercises)}: {exercise['exercise_name']}")
                clips_dir = os.path.join("storage", "clips")
                os.makedirs(clips_dir, exist_ok=True)
                logger.info(f"Created clips directory: {clips_dir}")
                exercise_name_clean = exercise['exercise_name'].replace(' ', '_').lower()
                url_id = str(uuid.uuid4())[:8]
                clip_filename = f"{exercise_name_clean}_{url_id}.mp4"
                clip_path = os.path.join(clips_dir, clip_filename)
                logger.info(f"Clip path: {clip_path}")
                start_time = float(exercise.get('start_time', 0.0))
                end_time = float(exercise.get('end_time', 0.0))
                if start_time == -1 or end_time == -1: # Check for -1 from is_valid_time
                    logger.warning(f"⚠️  Skipping {exercise['exercise_name']} - invalid start or end time: {exercise}")
                    continue
                duration = end_time - start_time
                if duration < min_duration:
                    logger.warning(f"⚠️  Skipping {exercise['exercise_name']} - duration {duration:.1f}s < {min_duration}s minimum")
                    continue
                if duration > 60.0:
                    logger.warning(f"⚠️  Skipping {exercise['exercise_name']} - duration {duration:.1f}s > 60s maximum")
                    continue
                if float(exercise.get('confidence_score', 0.0)) < 0.3: # Check for -1 from is_valid_time
                    logger.warning(f"⚠️  Skipping {exercise['exercise_name']} - low confidence score {exercise.get('confidence_score', 0):.2f}")
                    continue
                logger.info(f"Extracting clip: {start_time}s to {end_time}s (duration: {duration}s)")
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
                if os.path.exists(clip_path):
                    file_size = os.path.getsize(clip_path)
                    exercise['clip_path'] = clip_path
                    exercise['segments'] = [{
                        'start_time': start_time,
                        'end_time': end_time
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
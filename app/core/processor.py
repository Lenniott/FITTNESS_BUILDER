"""
Core video processing pipeline for exercise clip extraction.
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
    
    def _get_gemini_model(self):
        """Get Gemini model, initializing if needed."""
        if self.gemini_model is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('models/gemini-2.5-flash-lite-preview-06-17')
        return self.gemini_model
        
    async def process_video(self, url: str) -> Dict:
        """
        Complete video processing pipeline with carousel support.
        
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
            
            # For carousels, we need to download first to know how many items exist
            # For single videos, we can check immediately
            if 'instagram.com' in url and '/p/' in url:
                # This might be a carousel - download first to check
                logger.info(f"Potential carousel detected, downloading to check item count")
            else:
                # Single video - check if already processed
                existing_exercise = await check_existing_processing(normalized_url, carousel_index)
                if existing_exercise:
                    logger.info(f"URL already processed: {normalized_url} (index: {carousel_index})")
                    return {
                        "success": True,
                        "processed_clips": [{
                            'exercise_id': existing_exercise['id'],
                            'exercise_name': existing_exercise['exercise_name'],
                            'video_path': existing_exercise['video_path'],
                            'segments_count': 1,
                            'total_duration': existing_exercise['end_time'] - existing_exercise['start_time'] if existing_exercise['end_time'] and existing_exercise['start_time'] else 0,
                            'segments': [{
                                'start_time': existing_exercise['start_time'],
                                'end_time': existing_exercise['end_time']
                            }] if existing_exercise['start_time'] and existing_exercise['end_time'] else []
                        }],
                        "total_clips": 1,
                        "processing_time": 0,
                        "temp_dir": None,
                        "already_processed": True
                    }
            
            # Step 1: Download video and extract metadata
            logger.info(f"Starting video processing for: {url}")
            download_result = await download_media_and_metadata(url)
            temp_dir = download_result['temp_dir']
            
            # Check if this is a carousel with multiple files
            is_carousel = download_result.get('is_carousel', False)
            carousel_count = download_result.get('carousel_count', 1)
            
            if is_carousel and carousel_count > 1:
                logger.info(f"Detected carousel with {carousel_count} items")
                return await self._process_carousel(url, normalized_url, download_result, temp_dir, start_time)
            else:
                # Single video processing
                video_file = download_result['files'][0] if download_result['files'] else None
                
                if not video_file:
                    raise ValueError("No video file downloaded")
                
                return await self._process_single_video(url, normalized_url, carousel_index, video_file, download_result, temp_dir, start_time)
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            if temp_dir and os.path.exists(temp_dir):
                await self._cleanup_temp_files(temp_dir)
            raise
    
    async def _extract_keyframes(self, video_file: str, frames_dir: str) -> List[str]:
        """Extract keyframes and interval frames from video."""
        cap = cv2.VideoCapture(video_file)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        # Extract keyframes every 2 seconds + additional frames between
        keyframe_interval = int(fps * 2)  # Every 2 seconds
        frame_files = []
        
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Extract keyframes at regular intervals
            if frame_count % keyframe_interval == 0:
                timestamp_ms = int((frame_count / fps) * 1000)
                frame_path = os.path.join(frames_dir, f"frame_{timestamp_ms:06d}.jpg")
                cv2.imwrite(frame_path, frame)
                frame_files.append(frame_path)
            
            # Also extract frames at 1/3 and 2/3 of each interval for better coverage
            elif frame_count % (keyframe_interval // 3) == 0:
                timestamp_ms = int((frame_count / fps) * 1000)
                frame_path = os.path.join(frames_dir, f"frame_{timestamp_ms:06d}.jpg")
                cv2.imwrite(frame_path, frame)
                frame_files.append(frame_path)
            
            frame_count += 1
        
        cap.release()
        logger.info(f"Extracted {len(frame_files)} frames from video")
        return frame_files
    
    async def _detect_exercises(self, video_file: str, transcript: List[Dict], 
                               frames: List[str], metadata: Dict, temp_dir: Optional[str] = None) -> List[Dict]:
        """Use Gemini to detect exercises in the video."""
        
        # Prepare transcript text
        transcript_text = ""
        for segment in transcript:
            transcript_text += f"[{segment['start']:.1f}s - {segment['end']:.1f}s] {segment['text']}\n"
        
        # Prepare frame data for Gemini
        frame_data = []
        for frame_path in frames[:20]:  # Limit to 20 frames to avoid token limits
            if os.path.exists(frame_path):
                with open(frame_path, 'rb') as f:
                    frame_data.append({
                        'mime_type': 'image/jpeg',
                        'data': f.read()
                    })
        
        # Create prompt for Gemini
        prompt = f"""
Analyze this workout video and extract individual exercise segments with complete details:

VIDEO METADATA:
- Description: {metadata.get('description', 'No description')}
- Tags: {', '.join(metadata.get('tags', []))}
- Duration: {len(transcript) * 5} seconds (estimated)

TRANSCRIPT: {transcript_text}

FRAMES: [attached keyframes and interval frames]

For each distinct exercise you identify, provide a JSON response with:
{{
  "exercises": [
    {{
      "exercise_name": "specific exercise name",
      "start_time": 0.0,
      "end_time": 0.0,
      "how_to": "detailed step-by-step instructions",
      "benefits": "physical/mental benefits, muscles targeted, nervous system effects",
      "counteracts": "problems this exercise helps solve (sitting, stiffness, etc.)",
      "fitness_level": 0-10,
      "rounds_reps": "specific instructions for duration/repetitions",
      "intensity": 0-10,
      "confidence_score": 0.95
    }}
  ]
}}

Focus on identifying distinct exercises with clear start/end times. Provide comprehensive details for each exercise.
"""
        
        # Save AI prompt and metadata to temp directory for debugging
        if temp_dir:
            debug_data = {
                "prompt": prompt,
                "metadata": metadata,
                "transcript_segments": len(transcript),
                "frame_count": len(frame_data),
                "transcript_text": transcript_text
            }
            debug_file = os.path.join(temp_dir, "ai_debug_data.json")
            with open(debug_file, 'w') as f:
                json.dump(debug_data, f, indent=2)
            logger.info(f"Saved AI debug data to: {debug_file}")
        
        try:
            # Call Gemini with multimodal input
            gemini_model = self._get_gemini_model()
            response = gemini_model.generate_content([prompt] + frame_data)
            
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
                             temp_dir: str) -> List[Dict]:
        """Generate video clips for each detected exercise."""
        clips = []
        
        logger.info(f"Starting clip generation for {len(exercises)} exercises")
        logger.info(f"Video file: {video_file}")
        logger.info(f"Temp dir: {temp_dir}")
        
        for i, exercise in enumerate(exercises):
            try:
                logger.info(f"Processing exercise {i+1}/{len(exercises)}: {exercise['exercise_name']}")
                
                # Create clips directory in storage
                clips_dir = os.path.join("storage", "clips")
                os.makedirs(clips_dir, exist_ok=True)
                logger.info(f"Created clips directory: {clips_dir}")
                
                # Generate unique filename
                exercise_name_clean = exercise['exercise_name'].replace(' ', '_').lower()
                clip_filename = f"{exercise_name_clean}_{uuid.uuid4().hex[:8]}.mp4"
                clip_path = os.path.join(clips_dir, clip_filename)
                logger.info(f"Clip path: {clip_path}")
                
                # Extract clip using subprocess and ffmpeg
                start_time = exercise['start_time']
                duration = exercise['end_time'] - exercise['start_time']
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
    
    async def _process_single_video(self, url: str, normalized_url: str, carousel_index: int, 
                                   video_file: str, download_result: Dict, temp_dir: str, start_time: float) -> Dict:
        """Process a single video file."""
        # Step 2: Transcribe audio
        logger.info("Transcribing audio...")
        transcript = await transcribe_audio(video_file)
        
        # Save transcript to temp directory for debugging
        transcript_file = os.path.join(temp_dir, "transcript.json")
        with open(transcript_file, 'w') as f:
            json.dump(transcript, f, indent=2)
        logger.info(f"Saved transcript to: {transcript_file}")
        
        # Step 3: Extract keyframes
        logger.info("Extracting keyframes...")
        frames_dir = os.path.join(temp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        frame_files = await self._extract_keyframes(video_file, frames_dir)
        
        # Step 4: AI exercise detection
        logger.info("Detecting exercises with AI...")
        exercises = await self._detect_exercises(
            video_file=video_file,
            transcript=transcript,
            frames=frame_files,
            metadata=download_result,
            temp_dir=temp_dir
        )
        
        # Step 5: Generate clips
        logger.info("Generating exercise clips...")
        clips = await self._generate_clips(video_file, exercises, temp_dir)
        
        # Step 6: Store in database
        logger.info("Storing exercises in database...")
        stored_exercises = await self._store_exercises(url, normalized_url, carousel_index, clips)
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "processed_clips": stored_exercises,
            "total_clips": len(stored_exercises),
            "processing_time": processing_time,
            "temp_dir": temp_dir
        }
    
    async def _process_carousel(self, url: str, normalized_url: str, download_result: Dict, 
                               temp_dir: str, start_time: float) -> Dict:
        """Process all items in a carousel."""
        all_clips = []
        total_processing_time = 0
        carousel_count = len(download_result['files'])
        
        # Check if ALL carousel items are already processed
        all_processed = True
        existing_items = []
        
        for i in range(carousel_count):
            carousel_index = i + 1
            existing_exercise = await check_existing_processing(normalized_url, carousel_index)
            if existing_exercise:
                existing_items.append({
                    'exercise_id': existing_exercise['id'],
                    'exercise_name': existing_exercise['exercise_name'],
                    'video_path': existing_exercise['video_path'],
                    'segments_count': 1,
                    'total_duration': existing_exercise['end_time'] - existing_exercise['start_time'] if existing_exercise['end_time'] and existing_exercise['start_time'] else 0,
                    'segments': [{
                        'start_time': existing_exercise['start_time'],
                        'end_time': existing_exercise['end_time']
                    }] if existing_exercise['start_time'] and existing_exercise['end_time'] else [],
                    'carousel_index': carousel_index
                })
            else:
                all_processed = False
        
        # If all items are processed, return them
        if all_processed and existing_items:
            logger.info(f"All {carousel_count} carousel items already processed")
            return {
                "success": True,
                "processed_clips": existing_items,
                "total_clips": len(existing_items),
                "processing_time": 0,
                "temp_dir": None,
                "carousel_processed": True,
                "already_processed": True
            }
        
        # Process items that haven't been processed yet
        for i, video_file in enumerate(download_result['files']):
            carousel_index = i + 1
            logger.info(f"Processing carousel item {carousel_index}/{carousel_count}")
            
            # Check if this carousel item is already processed
            existing_exercise = await check_existing_processing(normalized_url, carousel_index)
            if existing_exercise:
                logger.info(f"Carousel item {carousel_index} already processed")
                all_clips.append({
                    'exercise_id': existing_exercise['id'],
                    'exercise_name': existing_exercise['exercise_name'],
                    'video_path': existing_exercise['video_path'],
                    'segments_count': 1,
                    'total_duration': existing_exercise['end_time'] - existing_exercise['start_time'] if existing_exercise['end_time'] and existing_exercise['start_time'] else 0,
                    'segments': [{
                        'start_time': existing_exercise['start_time'],
                        'end_time': existing_exercise['end_time']
                    }] if existing_exercise['start_time'] and existing_exercise['end_time'] else [],
                    'carousel_index': carousel_index
                })
                continue
            
            try:
                # Process this carousel item
                item_result = await self._process_single_video(url, normalized_url, carousel_index, video_file, download_result, temp_dir, start_time)
                all_clips.extend(item_result['processed_clips'])
                total_processing_time += item_result['processing_time']
                
            except Exception as e:
                logger.error(f"Error processing carousel item {carousel_index}: {str(e)}")
                continue
        
        return {
            "success": True,
            "processed_clips": all_clips,
            "total_clips": len(all_clips),
            "processing_time": total_processing_time,
            "temp_dir": temp_dir,
            "carousel_processed": True
        }
    
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
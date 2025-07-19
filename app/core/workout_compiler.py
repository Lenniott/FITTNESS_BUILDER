"""
Workout compilation pipeline for generating personalized workout videos.
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

import google.generativeai as genai  # type: ignore
import openai
import subprocess

from app.database.vectorization import search_similar_exercises
from app.database.operations import get_exercise_by_id
from app.database.compilation_operations import store_compiled_workout, get_compiled_workout

logger = logging.getLogger(__name__)

class WorkoutCompiler:
    """Main pipeline for compiling workout videos from user requirements."""
    
    def __init__(self):
        # Initialize clients lazily to avoid import-time errors
        self.gemini_model = None
        self.openai_client = None
        
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
    
    def _get_openai_client(self):
        """Get OpenAI client, initializing if needed."""
        if self.openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.openai_client = openai.OpenAI(api_key=api_key)
        return self.openai_client
    
    async def _determine_workout_parameters(self, user_requirements: str) -> Dict:
        """Use AI to determine workout parameters from user requirements."""
        
        prompt = f"""
Analyze the user's fitness requirements and determine appropriate workout parameters:

User Requirements: {user_requirements}

Determine the following parameters:

1. **Intensity Level**: 
   - "beginner" - for people who haven't exercised in months, are new to fitness, or have physical limitations
   - "intermediate" - for people with some fitness experience, regular exercisers
   - "advanced" - for people with significant fitness experience, athletes

2. **Target Duration**: 
   - Estimate based on user's needs and fitness level
   - Beginner: 180-300 seconds (3-5 minutes)
   - Intermediate: 300-600 seconds (5-10 minutes)  
   - Advanced: 600-900 seconds (10-15 minutes)

3. **Format**: 
   - Default to "vertical" for mobile phone viewing
   - Only use "square" if specifically requested

Return a JSON response like:
{{
  "intensity_level": "beginner",
  "target_duration": 300,
  "format": "vertical"
}}

Consider the user's language carefully:
- Words like "beginner", "first time", "haven't exercised", "slowly" → beginner
- Words like "intermediate", "some experience", "regular" → intermediate  
- Words like "advanced", "athlete", "experienced" → advanced
- Duration hints like "quick", "short" → shorter duration
- Duration hints like "comprehensive", "thorough" → longer duration
"""
        
        try:
            # Call Gemini with text input
            try:
                gemini_model = self._get_gemini_model(use_backup=False)
                response = gemini_model.generate_content(prompt)
                logger.info("Successfully used primary Gemini API key for parameter determination")
            except Exception as primary_error:
                logger.warning(f"Primary Gemini API failed: {str(primary_error)}")
                logger.info("Attempting to use backup Gemini API key...")
                
                # Try backup key
                gemini_model = self._get_gemini_model(use_backup=True)
                response = gemini_model.generate_content(prompt)
                logger.info("Successfully used backup Gemini API key for parameter determination")
            
            # Parse JSON response
            response_text = response.text.strip()
            logger.info(f"Parameter determination response: {response_text[:200]}...")
            
            # Extract JSON
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1]
            
            # Parse JSON
            json_text = json_text.strip()
            if json_text.startswith('{') and json_text.endswith('}'):
                try:
                    params = json.loads(json_text)
                    logger.info(f"Successfully parsed workout parameters: {params}")
                    return params
                except json.JSONDecodeError as json_error:
                    logger.error(f"JSON parsing error: {json_error}")
                    return self._fallback_workout_parameters(user_requirements)
            else:
                logger.error("No valid JSON found in parameter determination response")
                return self._fallback_workout_parameters(user_requirements)
            
        except Exception as e:
            logger.error(f"Error determining workout parameters: {str(e)}")
            return self._fallback_workout_parameters(user_requirements)
    
    def _fallback_workout_parameters(self, user_requirements: str) -> Dict:
        """Fallback workout parameters when AI fails."""
        requirements_lower = user_requirements.lower()
        
        # Determine intensity level
        if any(word in requirements_lower for word in ['beginner', 'first time', 'haven\'t exercised', 'slowly', 'new']):
            intensity_level = "beginner"
            target_duration = 300  # 5 minutes
        elif any(word in requirements_lower for word in ['advanced', 'athlete', 'experienced']):
            intensity_level = "advanced"
            target_duration = 600  # 10 minutes
        else:
            intensity_level = "intermediate"
            target_duration = 450  # 7.5 minutes
        
        # Default to vertical format for mobile
        format = "vertical"
        
        return {
            "intensity_level": intensity_level,
            "target_duration": target_duration,
            "format": format
        }
    
    async def compile_workout(self, user_requirements: str) -> Dict:
        """
        Complete workflow:
        1. Determine workout parameters from user requirements
        2. Generate requirement stories from user input
        3. Search for relevant video clips
        4. Generate exercise scripts
        5. Compile video with overlays
        6. Store result
        """
        start_time = time.time()
        
        try:
            # Step 1: Determine workout parameters from user requirements
            logger.info("Determining workout parameters...")
            workout_params = await self._determine_workout_parameters(user_requirements)
            target_duration = workout_params['target_duration']
            intensity_level = workout_params['intensity_level']
            format = workout_params['format']
            
            # Step 2: Generate requirement stories
            logger.info("Generating requirement stories...")
            requirement_stories = await self._generate_requirement_stories(
                user_requirements, target_duration, intensity_level
            )
            
            # Step 3: Search for relevant clips
            logger.info("Searching for relevant video clips...")
            relevant_clips = await self._search_relevant_clips(
                requirement_stories, target_duration, intensity_level
            )
            
            # Step 4: Generate exercise scripts
            logger.info("Generating exercise scripts...")
            clips_with_scripts = await self._generate_exercise_scripts(relevant_clips)
            
            # Step 5: Compile video
            logger.info("Compiling workout video...")
            video_path = await self._compile_video(
                clips_with_scripts, target_duration, format
            )
            
            # Step 6: Store result
            workout_id = await store_compiled_workout(
                user_requirements=user_requirements,
                target_duration=target_duration,
                format=format,
                intensity_level=intensity_level,
                video_path=video_path,
                actual_duration=target_duration  # TODO: get actual duration
            )
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "workout_id": workout_id,
                "video_path": video_path,
                "requirement_stories": requirement_stories,
                "clips_used": len(clips_with_scripts),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error compiling workout: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def _generate_requirement_stories(self, user_requirements: str, 
                                          target_duration: int, intensity_level: str) -> List[str]:
        """Use AI to transform user input into 4-6 exercise requirement stories."""
        
        prompt = f"""
<role>
You are a fitness coach specializing in analyzing user requirements and creating exercise requirement stories for video compilation systems.
</role>

<tone>
Be empathetic, practical, and solution-focused. Understand user pain points and constraints while providing actionable exercise requirements.
</tone>

<context>
User Input: {user_requirements}
Target Duration: {target_duration} minutes
Intensity Level: {intensity_level}
</context>

<task>
Analyze the user's requirements and create exercise requirement stories that capture:

1. **Pain Points**: What problems they're experiencing (tight hips, weak shoulders, etc.)
2. **Counteractions**: What sedentary habits they're trying to overcome (sitting all day, poor posture, etc.)
3. **Fitness Goals**: What skills they want to achieve (handstand, muscle up, splits, etc.)
4. **Constraints**: Time limitations, equipment availability, environment restrictions
5. **Intensity Needs**: Appropriate difficulty level based on their current fitness
6. **Progression Path**: What they need to work on to achieve their goals

Create 4-6 requirement stories that are descriptive paragraphs (not exercise names).
Each story should be searchable and match our database fields: fitness_level, intensity, counteracts, benefits.
</task>

<output_format>
Return a JSON array of requirement stories like:
{{
  "requirement_stories": [
    "Tight hip mobility training for someone who sits all day and has lower back soreness",
    "Shoulder strength and flexibility development for handstand progression",
    "Beginner-friendly strength building for someone who hasn't exercised in months",
    "Chest-to-knee compression work for handstand preparation"
  ]
}}
</output_format>

IMPORTANT: Focus on stories that will match our existing video content database with fields:
- fitness_level (0-10 scale)
- intensity (0-10 scale) 
- counteracts (problems this solves)
- benefits (physical/mental benefits)
- how_to (detailed instructions)
"""
        
        try:
            # Call Gemini with text input
            try:
                gemini_model = self._get_gemini_model(use_backup=False)
                response = gemini_model.generate_content(prompt)
                logger.info("Successfully used primary Gemini API key")
            except Exception as primary_error:
                logger.warning(f"Primary Gemini API failed: {str(primary_error)}")
                logger.info("Attempting to use backup Gemini API key...")
                
                # Try backup key
                gemini_model = self._get_gemini_model(use_backup=True)
                response = gemini_model.generate_content(prompt)
                logger.info("Successfully used backup Gemini API key")
            
            # Parse JSON response
            response_text = response.text.strip()
            logger.info(f"Raw AI response: {response_text[:200]}...")
            
            # Extract JSON
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1]
            
            # Parse JSON
            json_text = json_text.strip()
            if json_text.startswith('{') and json_text.endswith('}'):
                try:
                    data = json.loads(json_text)
                    stories = data.get('requirement_stories', [])
                    logger.info(f"Successfully parsed {len(stories)} requirement stories")
                    return stories
                except json.JSONDecodeError as json_error:
                    logger.error(f"JSON parsing error: {json_error}")
                    return self._fallback_requirement_stories(user_requirements)
            else:
                logger.error("No valid JSON found in AI response")
                return self._fallback_requirement_stories(user_requirements)
            
        except Exception as e:
            logger.error(f"Error generating requirement stories: {str(e)}")
            return self._fallback_requirement_stories(user_requirements)
    
    def _fallback_requirement_stories(self, user_requirements: str) -> List[str]:
        """Fallback requirement stories when AI fails."""
        # Simple keyword-based fallback
        requirements_lower = user_requirements.lower()
        
        stories = []
        
        if any(word in requirements_lower for word in ['sit', 'sitting', 'desk']):
            stories.append("Mobility training for someone who sits all day")
        
        if any(word in requirements_lower for word in ['hip', 'tight']):
            stories.append("Hip flexibility and mobility work")
        
        if any(word in requirements_lower for word in ['handstand', 'hand stand']):
            stories.append("Shoulder strength and balance training for handstand progression")
        
        if any(word in requirements_lower for word in ['beginner', 'start', 'first time']):
            stories.append("Beginner-friendly strength building exercises")
        
        if any(word in requirements_lower for word in ['back', 'spine', 'posture']):
            stories.append("Posture correction and back strengthening")
        
        if any(word in requirements_lower for word in ['flexibility', 'stretch']):
            stories.append("General flexibility and mobility training")
        
        # Ensure we have at least 3 stories
        if len(stories) < 3:
            stories.extend([
                "General fitness and conditioning",
                "Core strength and stability work"
            ])
        
        return stories[:6]  # Limit to 6 stories
    
    async def _search_relevant_clips(self, requirement_stories: List[str], 
                                   target_duration: int, intensity_level: str) -> List[Dict]:
        """Use vector search to find relevant video clips for each requirement."""
        
        all_clips = []
        clips_per_story = max(1, target_duration // 60)  # Roughly 1 clip per minute
        
        for story in requirement_stories:
            try:
                # Search for similar exercises using our existing vector search
                similar_exercises = await search_similar_exercises(
                    query=story,
                    limit=clips_per_story * 2,  # Get more to filter
                    score_threshold=0.6  # Lower threshold for compilation
                )
                
                # Filter and format clips
                for result in similar_exercises:
                    if result['score'] > 0.6:  # Additional quality filter
                        clip_data = {
                            'exercise_id': result['id'],
                            'exercise_name': result['metadata']['exercise_name'],
                            'video_path': result['metadata']['video_path'],
                            'start_time': result['metadata']['start_time'],
                            'end_time': result['metadata']['end_time'],
                            'how_to': result['metadata']['how_to'],
                            'benefits': result['metadata']['benefits'],
                            'counteracts': result['metadata']['counteracts'],
                            'fitness_level': result['metadata']['fitness_level'],
                            'intensity': result['metadata']['intensity'],
                            'requirement_story': story,
                            'relevance_score': result['score']
                        }
                        all_clips.append(clip_data)
                
            except Exception as e:
                logger.error(f"Error searching for story '{story}': {str(e)}")
                continue
        
        # Sort by relevance and limit total clips
        all_clips.sort(key=lambda x: x['relevance_score'], reverse=True)
        max_clips = min(len(all_clips), target_duration // 30)  # Roughly 1 clip per 30 seconds
        
        return all_clips[:max_clips]
    
    async def _generate_exercise_scripts(self, clips: List[Dict]) -> List[Dict]:
        """Generate detailed exercise instructions for each clip."""
        
        for clip in clips:
            # Use existing how_to field as base, enhance if needed
            if not clip['how_to'] or len(clip['how_to']) < 50:
                # Generate enhanced instructions
                clip['exercise_script'] = await self._enhance_exercise_instructions(clip)
            else:
                clip['exercise_script'] = clip['how_to']
        
        return clips
    
    async def _enhance_exercise_instructions(self, clip: Dict) -> str:
        """Enhance exercise instructions using AI."""
        
        prompt = f"""
Enhance the exercise instructions for: {clip['exercise_name']}

Current instructions: {clip['how_to']}
Benefits: {clip['benefits']}
Problems it solves: {clip['counteracts']}
Fitness level: {clip['fitness_level']}/10
Intensity: {clip['intensity']}/10

Create detailed, step-by-step instructions that include:
1. Starting position
2. Movement execution
3. Form cues and safety tips
4. Repetition guidance
5. Modifications for different fitness levels

Format as clear, actionable instructions.
"""
        
        try:
            gemini_model = self._get_gemini_model(use_backup=False)
            response = gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error enhancing instructions: {str(e)}")
            return clip['how_to']  # Fallback to original
    
    async def _compile_video(self, clips: List[Dict], target_duration: int, 
                           format: str) -> str:
        """Use FFmpeg to stitch clips into final workout video."""
        
        # Create output directory
        output_dir = Path("storage/compiled_workouts")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        workout_id = str(uuid.uuid4())
        output_path = output_dir / f"workout_{workout_id}.mp4"
        
        # Create temporary file list for FFmpeg
        temp_list_file = f"/tmp/workout_clips_{workout_id}.txt"
        
        with open(temp_list_file, 'w') as f:
            for clip in clips:
                # Fix video path to use correct relative path
                video_path = clip['video_path']
                if video_path.startswith('/tmp/'):
                    # Remove /tmp/ prefix and use relative path from project root
                    video_path = video_path.replace('/tmp/', '')
                elif video_path.startswith('storage/'):
                    # Already correct relative path
                    pass
                else:
                    # Assume it's a relative path from project root
                    pass
                
                # Add clip with duration info
                f.write(f"file '{video_path}'\n")
                f.write(f"inpoint {clip['start_time']}\n")
                f.write(f"outpoint {clip['end_time']}\n")
        
        try:
            # FFmpeg command to concatenate clips
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', temp_list_file,
                '-c', 'copy',
                '-y',  # Overwrite output
                str(output_path)
            ]
            
            # Execute FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise Exception(f"Video compilation failed: {result.stderr}")
            
            logger.info(f"Successfully compiled workout video: {output_path}")
            return str(output_path)
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)

# Global instance
workout_compiler = WorkoutCompiler() 
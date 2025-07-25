"""
Routine compilation pipeline for generating JSON workout routines.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai  # type: ignore
import openai

from app.database.vectorization import search_similar_exercises
from app.database.routine_operations import store_routine, get_routine

logger = logging.getLogger(__name__)

class RoutineCompiler:
    """Main pipeline for compiling JSON workout routines from user requirements."""
    
    def __init__(self):
        # Initialize clients lazily to avoid import-time errors
        self.gemini_model = None
        self.openai_client = None
        self._current_user_requirements = ""
        
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
    
    async def compile_routine(self, user_requirements: str) -> Dict:
        """
        Complete workflow:
        1. Determine routine parameters from user requirements
        2. Generate requirement stories from user input
        3. Search for relevant video clips
        4. Use second LLM to select unique, diverse exercises
        5. Create JSON routine with all metadata
        6. Store result in database
        """
        start_time = time.time()
        
        # Store user requirements for use in exercise selection
        self._current_user_requirements = user_requirements
        
        try:
            # Step 1: Determine routine parameters
            logger.info("Determining routine parameters...")
            routine_params = await self._determine_routine_parameters(user_requirements)
            target_duration = routine_params['target_duration']
            intensity_level = routine_params['intensity_level']
            format = routine_params['format']
            
            # Step 2: Generate requirement stories
            logger.info("Generating requirement stories...")
            requirement_stories = await self._generate_requirement_stories(
                user_requirements, target_duration, intensity_level
            )
            
            # Step 3: Search for relevant clips
            logger.info("Searching for relevant video clips...")
            candidate_clips = await self._search_relevant_clips(
                requirement_stories, target_duration, intensity_level
            )
            
            # Step 4: Select unique exercises (placeholder for Phase 3)
            logger.info("Selecting unique exercises...")
            selected_exercises = await self._select_unique_exercises(
                candidate_clips, requirement_stories, target_duration, intensity_level
            )
            
            # Step 5: Create JSON routine
            logger.info("Creating JSON routine...")
            routine_data = await self._create_routine_json(
                user_requirements, selected_exercises, target_duration, intensity_level, format
            )
            
            # Step 6: Store result
            routine_id = await store_routine(
                user_requirements=user_requirements,
                target_duration=target_duration,
                intensity_level=intensity_level,
                format=format,
                routine_data=routine_data
            )
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "routine_id": routine_id,
                "routine_data": routine_data,
                "requirement_stories": requirement_stories,
                "exercises_selected": len(selected_exercises),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error compiling routine: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def _determine_routine_parameters(self, user_requirements: str) -> Dict:
        """Use AI to determine routine parameters from user requirements."""
        # TODO: Implement parameter determination (similar to workout_compiler.py)
        # For now, return default values
        return {
            "intensity_level": "beginner",
            "target_duration": 300,
            "format": "vertical"
        }
    
    async def _generate_requirement_stories(self, user_requirements: str, 
                                          target_duration: int, intensity_level: str) -> List[str]:
        """Generate requirement stories from user input."""
        # TODO: Implement requirement story generation (similar to workout_compiler.py)
        # For now, return simple stories
        return [
            "Beginner-friendly hip mobility work",
            "Basic strength building exercises",
            "Simple flexibility training"
        ]
    
    async def _search_relevant_clips(self, requirement_stories: List[str], 
                                   target_duration: int, intensity_level: str) -> List[Dict]:
        """Search for relevant video clips using vector search."""
        all_clips = []
        
        for story in requirement_stories:
            try:
                similar_exercises = await search_similar_exercises(
                    query=story,
                    limit=10,
                    score_threshold=0.6
                )
                
                for result in similar_exercises:
                    if result['score'] > 0.6:
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
        
        return all_clips
    
    async def _select_unique_exercises(self, candidate_clips: List[Dict], 
                                     requirement_stories: List[str],
                                     target_duration: int, intensity_level: str) -> List[Dict]:
        """Select unique exercises using intelligent natural language understanding."""
        from app.core.exercise_selector import exercise_selector
        
        return await exercise_selector.select_intelligent_routine(
            candidate_clips=candidate_clips,
            requirement_stories=requirement_stories,
            user_requirements=self._current_user_requirements,
            target_duration=target_duration,
            intensity_level=intensity_level
        )
    
    async def _create_routine_json(self, user_requirements: str, selected_exercises: List[Dict],
                                 target_duration: int, intensity_level: str, format: str) -> Dict:
        """Create complete JSON routine with all metadata."""
        
        exercises = []
        total_duration = 0
        
        for exercise in selected_exercises:
            duration = exercise['end_time'] - exercise['start_time']
            total_duration += duration
            
            exercise_data = {
                "exercise_id": exercise['exercise_id'],
                "exercise_name": exercise['exercise_name'],
                "video_path": exercise['video_path'],
                "start_time": exercise['start_time'],
                "end_time": exercise['end_time'],
                "duration": duration,
                "how_to": exercise['how_to'],
                "benefits": exercise['benefits'],
                "counteracts": exercise['counteracts'],
                "fitness_level": exercise['fitness_level'],
                "intensity": exercise['intensity'],
                "relevance_score": exercise['relevance_score'],
                "deletion_metadata": {
                    "exercise_id": exercise['exercise_id'],
                    "qdrant_id": exercise.get('qdrant_id'),
                    "video_path": exercise['video_path'],
                    "original_url": exercise.get('original_url', ''),
                    "cascade_cleanup": True
                }
            }
            exercises.append(exercise_data)
        
        routine_data = {
            "routine_id": str(uuid.uuid4()),
            "user_requirements": user_requirements,
            "target_duration": target_duration,
            "intensity_level": intensity_level,
            "format": format,
            "exercises": exercises,
            "metadata": {
                "total_duration": total_duration,
                "exercise_count": len(exercises),
                "created_at": time.time()
            }
        }
        
        return routine_data

# Global instance
routine_compiler = RoutineCompiler() 
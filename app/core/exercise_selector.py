"""
Intelligent exercise selection engine using natural language understanding.

This module focuses purely on natural language understanding without any hardcoded biases.
It uses the second LLM to intelligently curate routines based on:
- Exercise stories from the first LLM
- Clip details from vector search
- User requirements
- Content similarity analysis

The goal is to create thoughtful, well-rounded routines that avoid duplicates
based on content similarity, not just IDs.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ExerciseSelector:
    """
    Intelligent exercise selector using natural language understanding.
    
    This selector focuses purely on content analysis and natural language
    understanding without any hardcoded exercise knowledge or biases.
    """
    
    def __init__(self):
        """Initialize the exercise selector."""
        self._gemini_model = None
        self._openai_client = None
    
    def _get_gemini_model(self, use_backup=False):
        """Get Gemini model instance."""
        if self._gemini_model is None:
            api_key = os.getenv("GEMINI_API_BACKUP_KEY" if use_backup else "GEMINI_API_KEY")
            genai.configure(api_key=api_key)
            self._gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        return self._gemini_model
    
    def _get_openai_client(self):
        """Get OpenAI client instance."""
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._openai_client
    
    async def select_intelligent_routine(
        self,
        candidate_clips: List[Dict],
        requirement_stories: List[str],
        user_requirements: str,
        target_duration: int,
        intensity_level: str
    ) -> List[Dict]:
        """
        Intelligently select exercises for a well-rounded routine.
        
        This method uses natural language understanding to:
        1. Analyze content similarity between clips
        2. Create a thoughtful, well-rounded routine
        3. Avoid duplicates based on content, not just IDs
        4. Ensure the routine meets user requirements
        
        Args:
            candidate_clips: List of clips from vector search
            requirement_stories: Stories from first LLM
            user_requirements: Original user requirements
            target_duration: Target routine duration
            intensity_level: Desired intensity level
            
        Returns:
            List of selected exercises for the routine
        """
        try:
            logger.info(f"Starting intelligent exercise selection for {len(candidate_clips)} candidate clips")
            
            # Step 1: Prepare context for the second LLM
            context = self._prepare_selection_context(
                candidate_clips, requirement_stories, user_requirements,
                target_duration, intensity_level
            )
            
            # Step 2: Use second LLM to intelligently select exercises
            selected_exercises = await self._curate_routine_with_llm(context)
            
            # Step 3: Validate and finalize selection
            final_selection = self._validate_and_finalize_selection(
                selected_exercises, candidate_clips, target_duration
            )
            
            logger.info(f"Selected {len(final_selection)} exercises for routine")
            return final_selection
            
        except Exception as e:
            logger.error(f"Error in intelligent exercise selection: {str(e)}")
            # Fallback to simple selection
            return self._fallback_selection(candidate_clips, target_duration)
    
    def _prepare_selection_context(
        self,
        candidate_clips: List[Dict],
        requirement_stories: List[str],
        user_requirements: str,
        target_duration: int,
        intensity_level: str
    ) -> str:
        """Prepare comprehensive context for the second LLM."""
        
        # Create detailed clip information
        clips_info = []
        for i, clip in enumerate(candidate_clips):
            clip_info = f"""
Clip {i+1}:
- Name: {clip['exercise_name']}
- Duration: {clip['end_time'] - clip['start_time']:.1f}s
- Instructions: {clip['how_to']}
- Benefits: {clip['benefits']}
- Problems it solves: {clip['counteracts']}
- Fitness Level: {clip['fitness_level']}/10
- Intensity: {clip['intensity']}/10
- Relevance Score: {clip['relevance_score']:.3f}
- Story Match: {clip['requirement_story']}
"""
            clips_info.append(clip_info)
        
        context = f"""
USER REQUIREMENTS: {user_requirements}

TARGET DURATION: {target_duration} seconds
INTENSITY LEVEL: {intensity_level}

REQUIREMENT STORIES (from first LLM):
{chr(10).join(f"- {story}" for story in requirement_stories)}

AVAILABLE EXERCISE CLIPS ({len(candidate_clips)} total):
{chr(10).join(clips_info)}

TASK: Create a thoughtful, well-rounded workout routine by selecting exercises from the available clips.

SELECTION CRITERIA:
1. CONTENT UNIQUENESS: Avoid exercises that are too similar in movement patterns, target areas, or execution style
2. ROUTINE FLOW: Create logical progression and variety in the workout
3. REQUIREMENT ALIGNMENT: Ensure exercises address the user's specific needs
4. DURATION FIT: Stay within target duration while maintaining quality
5. INTENSITY MATCH: Match the desired intensity level
6. WELL-ROUNDED: Ensure the routine covers different aspects of fitness (strength, mobility, etc.)

ANALYSIS APPROACH:
- Compare exercise instructions, benefits, and movement patterns
- Look for natural progression and variety
- Consider how exercises complement each other
- Avoid redundancy while maintaining effectiveness

Please analyze the clips and select the best combination for a complete, effective routine.
"""
        
        return context
    
    async def _curate_routine_with_llm(self, context: str) -> List[Dict]:
        """Use the second LLM to intelligently curate the routine."""
        
        prompt = f"""
{context}

Based on the available clips and requirements, please select the best exercises for a complete workout routine.

Return your response as a JSON array with the selected clip numbers (1-based) and reasoning:

{{
  "selected_clips": [
    {{
      "clip_number": 1,
      "reasoning": "This exercise provides a good warm-up and addresses the user's need for...",
      "role_in_routine": "warm-up/strength/mobility/etc"
    }}
  ],
  "routine_analysis": {{
    "total_duration": 0,
    "variety_score": 0.0,
    "progression_flow": "description of how exercises flow together",
    "requirement_coverage": "how well the routine addresses user needs",
    "uniqueness_analysis": "analysis of content diversity"
  }}
}}

Focus on creating a thoughtful, well-rounded routine that avoids content duplication.
"""
        
        try:
            # Try primary Gemini API
            try:
                gemini_model = self._get_gemini_model(use_backup=False)
                response = gemini_model.generate_content(prompt)
                logger.info("Successfully used primary Gemini API for routine curation")
            except Exception as primary_error:
                logger.warning(f"Primary Gemini API failed: {str(primary_error)}")
                logger.info("Attempting to use backup Gemini API...")
                
                # Try backup key
                gemini_model = self._get_gemini_model(use_backup=True)
                response = gemini_model.generate_content(prompt)
                logger.info("Successfully used backup Gemini API for routine curation")
            
            # Parse JSON response
            response_text = response.text.strip()
            logger.info(f"LLM response: {response_text[:200]}...")
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                selection_data = json.loads(json_str)
                
                return selection_data.get('selected_clips', [])
            else:
                logger.warning("Could not extract JSON from LLM response")
                return []
                
        except Exception as e:
            logger.error(f"Error in LLM routine curation: {str(e)}")
            return []
    
    def _validate_and_finalize_selection(
        self,
        llm_selection: List[Dict],
        candidate_clips: List[Dict],
        target_duration: int
    ) -> List[Dict]:
        """Validate LLM selection and finalize the routine."""
        
        selected_clips = []
        total_duration = 0
        
        for selection in llm_selection:
            clip_number = selection.get('clip_number', 0)
            
            # Validate clip number
            if 1 <= clip_number <= len(candidate_clips):
                clip = candidate_clips[clip_number - 1]
                duration = clip['end_time'] - clip['start_time']
                
                # Check if adding this clip would exceed target duration
                if total_duration + duration <= target_duration:
                    selected_clips.append(clip)
                    total_duration += duration
                else:
                    logger.info(f"Skipping clip {clip_number} - would exceed target duration")
            else:
                logger.warning(f"Invalid clip number: {clip_number}")
        
        logger.info(f"Final selection: {len(selected_clips)} clips, {total_duration:.1f}s total")
        return selected_clips
    
    def _fallback_selection(self, candidate_clips: List[Dict], target_duration: int) -> List[Dict]:
        """Fallback selection when LLM fails."""
        logger.info("Using fallback selection method")
        
        selected_clips = []
        total_duration = 0
        
        # Simple selection: take clips until we reach target duration
        for clip in candidate_clips:
            duration = clip['end_time'] - clip['start_time']
            
            if total_duration + duration <= target_duration:
                selected_clips.append(clip)
                total_duration += duration
            else:
                break
        
        logger.info(f"Fallback selection: {len(selected_clips)} clips, {total_duration:.1f}s total")
        return selected_clips

# Global instance
exercise_selector = ExerciseSelector() 
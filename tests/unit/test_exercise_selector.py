"""
Unit tests for the intelligent exercise selector.

This module tests the exercise selector that uses natural language understanding
to curate thoughtful, well-rounded routines without hardcoded biases.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, List

from app.core.exercise_selector import ExerciseSelector


class TestExerciseSelector:
    """Test the intelligent exercise selector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.selector = ExerciseSelector()
        
        # Mock candidate clips
        self.mock_clips = [
            {
                'exercise_id': 'ex1',
                'exercise_name': 'Push-up',
                'video_path': '/path/to/pushup.mp4',
                'start_time': 0.0,
                'end_time': 30.0,
                'how_to': 'Start in plank position, lower body, push back up',
                'benefits': 'Builds chest, triceps, and core strength',
                'counteracts': 'Poor posture, weak upper body',
                'fitness_level': 5,
                'intensity': 7,
                'requirement_story': 'Need upper body strength',
                'relevance_score': 0.85
            },
            {
                'exercise_id': 'ex2',
                'exercise_name': 'Squat',
                'video_path': '/path/to/squat.mp4',
                'start_time': 0.0,
                'end_time': 25.0,
                'how_to': 'Stand with feet shoulder-width, lower hips, stand back up',
                'benefits': 'Builds leg strength and mobility',
                'counteracts': 'Weak legs, poor balance',
                'fitness_level': 4,
                'intensity': 6,
                'requirement_story': 'Need lower body strength',
                'relevance_score': 0.78
            },
            {
                'exercise_id': 'ex3',
                'exercise_name': 'Plank',
                'video_path': '/path/to/plank.mp4',
                'start_time': 0.0,
                'end_time': 20.0,
                'how_to': 'Hold body straight from head to heels',
                'benefits': 'Core stability and endurance',
                'counteracts': 'Weak core, poor posture',
                'fitness_level': 3,
                'intensity': 5,
                'requirement_story': 'Need core strength',
                'relevance_score': 0.72
            }
        ]
        
        self.mock_stories = [
            "Need a beginner-friendly upper body workout",
            "Want to improve overall strength and fitness"
        ]
    
    @patch('app.core.exercise_selector.genai')
    def test_prepare_selection_context(self, mock_genai):
        """Test context preparation for LLM."""
        context = self.selector._prepare_selection_context(
            candidate_clips=self.mock_clips,
            requirement_stories=self.mock_stories,
            user_requirements="I need a beginner workout",
            target_duration=300,
            intensity_level="beginner"
        )
        
        # Check that context includes all required information
        assert "USER REQUIREMENTS: I need a beginner workout" in context
        assert "TARGET DURATION: 300 seconds" in context
        assert "INTENSITY LEVEL: beginner" in context
        assert "Push-up" in context
        assert "Squat" in context
        assert "Plank" in context
        assert "Need a beginner-friendly upper body workout" in context
        assert "CONTENT UNIQUENESS" in context
        assert "ROUTINE FLOW" in context
    
    @patch('app.core.exercise_selector.genai')
    @patch('app.core.exercise_selector.os.getenv')
    def test_curate_routine_with_llm_success(self, mock_getenv, mock_genai):
        """Test successful LLM routine curation."""
        # Mock environment variables
        mock_getenv.return_value = "test_api_key"
        
        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.text = '''
        {
          "selected_clips": [
            {
              "clip_number": 1,
              "reasoning": "Good warm-up exercise for upper body",
              "role_in_routine": "warm-up"
            },
            {
              "clip_number": 2,
              "reasoning": "Builds lower body strength",
              "role_in_routine": "strength"
            }
          ],
          "routine_analysis": {
            "total_duration": 55,
            "variety_score": 0.8,
            "progression_flow": "Good flow from upper to lower body",
            "requirement_coverage": "Addresses user needs well",
            "uniqueness_analysis": "Diverse movement patterns"
          }
        }
        '''
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Test the method
        result = asyncio.run(self.selector._curate_routine_with_llm("test context"))
        
        # Verify result
        assert len(result) == 2
        assert result[0]['clip_number'] == 1
        assert result[0]['reasoning'] == "Good warm-up exercise for upper body"
        assert result[1]['clip_number'] == 2
        assert result[1]['reasoning'] == "Builds lower body strength"
    
    @patch('app.core.exercise_selector.genai')
    @patch('app.core.exercise_selector.os.getenv')
    def test_curate_routine_with_llm_fallback(self, mock_getenv, mock_genai):
        """Test LLM curation with fallback when JSON parsing fails."""
        # Mock environment variables
        mock_getenv.return_value = "test_api_key"
        
        # Mock Gemini response with invalid JSON
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Test the method
        result = asyncio.run(self.selector._curate_routine_with_llm("test context"))
        
        # Should return empty list when JSON parsing fails
        assert result == []
    
    def test_validate_and_finalize_selection(self):
        """Test validation and finalization of LLM selection."""
        llm_selection = [
            {'clip_number': 1, 'reasoning': 'Good exercise', 'role_in_routine': 'warm-up'},
            {'clip_number': 2, 'reasoning': 'Another good exercise', 'role_in_routine': 'strength'},
            {'clip_number': 3, 'reasoning': 'Core exercise', 'role_in_routine': 'core'}
        ]
        
        result = self.selector._validate_and_finalize_selection(
            llm_selection=llm_selection,
            candidate_clips=self.mock_clips,
            target_duration=100  # Should fit all 3 clips (30 + 25 + 20 = 75s)
        )
        
        # Should select all 3 clips
        assert len(result) == 3
        assert result[0]['exercise_name'] == 'Push-up'
        assert result[1]['exercise_name'] == 'Squat'
        assert result[2]['exercise_name'] == 'Plank'
    
    def test_validate_and_finalize_selection_duration_limit(self):
        """Test that selection respects duration limits."""
        llm_selection = [
            {'clip_number': 1, 'reasoning': 'Good exercise', 'role_in_routine': 'warm-up'},
            {'clip_number': 2, 'reasoning': 'Another good exercise', 'role_in_routine': 'strength'},
            {'clip_number': 3, 'reasoning': 'Core exercise', 'role_in_routine': 'core'}
        ]
        
        result = self.selector._validate_and_finalize_selection(
            llm_selection=llm_selection,
            candidate_clips=self.mock_clips,
            target_duration=50  # Should only fit first clip (30s) since 30 + 25 = 55s > 50s
        )
        
        # Should select Push-up (30s) + Plank (20s) = 50s total
        assert len(result) == 2
        assert result[0]['exercise_name'] == 'Push-up'
        assert result[1]['exercise_name'] == 'Plank'
    
    def test_validate_and_finalize_selection_invalid_clip_number(self):
        """Test handling of invalid clip numbers."""
        llm_selection = [
            {'clip_number': 1, 'reasoning': 'Good exercise', 'role_in_routine': 'warm-up'},
            {'clip_number': 5, 'reasoning': 'Invalid exercise', 'role_in_routine': 'strength'},  # Invalid
            {'clip_number': 2, 'reasoning': 'Valid exercise', 'role_in_routine': 'core'}
        ]
        
        result = self.selector._validate_and_finalize_selection(
            llm_selection=llm_selection,
            candidate_clips=self.mock_clips,
            target_duration=100
        )
        
        # Should only select valid clips (1 and 2)
        assert len(result) == 2
        assert result[0]['exercise_name'] == 'Push-up'
        assert result[1]['exercise_name'] == 'Squat'
    
    def test_fallback_selection(self):
        """Test fallback selection when LLM fails."""
        result = self.selector._fallback_selection(
            candidate_clips=self.mock_clips,
            target_duration=60  # Should fit first 2 clips (30 + 25 = 55s)
        )
        
        # Should select first 2 clips
        assert len(result) == 2
        assert result[0]['exercise_name'] == 'Push-up'
        assert result[1]['exercise_name'] == 'Squat'
    
    @patch('app.core.exercise_selector.ExerciseSelector._curate_routine_with_llm')
    @patch('app.core.exercise_selector.ExerciseSelector._prepare_selection_context')
    def test_select_intelligent_routine_success(self, mock_prepare_context, mock_curate_llm):
        """Test successful intelligent routine selection."""
        # Mock context preparation
        mock_prepare_context.return_value = "test context"
        
        # Mock LLM curation
        mock_curate_llm.return_value = [
            {'clip_number': 1, 'reasoning': 'Good exercise', 'role_in_routine': 'warm-up'},
            {'clip_number': 2, 'reasoning': 'Another good exercise', 'role_in_routine': 'strength'}
        ]
        
        # Test the method
        result = asyncio.run(self.selector.select_intelligent_routine(
            candidate_clips=self.mock_clips,
            requirement_stories=self.mock_stories,
            user_requirements="I need a beginner workout",
            target_duration=100,
            intensity_level="beginner"
        ))
        
        # Verify result
        assert len(result) == 2
        assert result[0]['exercise_name'] == 'Push-up'
        assert result[1]['exercise_name'] == 'Squat'
        
        # Verify method calls
        mock_prepare_context.assert_called_once()
        mock_curate_llm.assert_called_once_with("test context")
    
    @patch('app.core.exercise_selector.ExerciseSelector._curate_routine_with_llm')
    @patch('app.core.exercise_selector.ExerciseSelector._prepare_selection_context')
    def test_select_intelligent_routine_fallback(self, mock_prepare_context, mock_curate_llm):
        """Test fallback when LLM curation fails."""
        # Mock context preparation
        mock_prepare_context.return_value = "test context"
        
        # Mock LLM curation failure
        mock_curate_llm.side_effect = Exception("LLM failed")
        
        # Test the method
        result = asyncio.run(self.selector.select_intelligent_routine(
            candidate_clips=self.mock_clips,
            requirement_stories=self.mock_stories,
            user_requirements="I need a beginner workout",
            target_duration=100,
            intensity_level="beginner"
        ))
        
        # Should use fallback selection
        assert len(result) == 3  # All clips fit within 100s
        assert result[0]['exercise_name'] == 'Push-up'
        assert result[1]['exercise_name'] == 'Squat'
        assert result[2]['exercise_name'] == 'Plank' 
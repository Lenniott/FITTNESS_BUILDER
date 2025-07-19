"""
Unit tests for workout compilation pipeline.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import os
import tempfile

from app.core.workout_compiler import WorkoutCompiler


class TestWorkoutCompiler:
    """Test the workout compilation pipeline."""
    
    @pytest.fixture
    def compiler(self):
        """Create a workout compiler instance."""
        return WorkoutCompiler()
    
    @pytest.mark.asyncio
    async def test_fallback_requirement_stories(self, compiler):
        """Test fallback requirement story generation when AI fails."""
        
        # Test with various user inputs
        test_cases = [
            {
                "input": "I sit all day and my hips are tight",
                "expected_keywords": ["sit", "hip", "tight"]
            },
            {
                "input": "I want to do handstands but I'm a beginner",
                "expected_keywords": ["handstand", "beginner"]
            },
            {
                "input": "My back hurts from poor posture",
                "expected_keywords": ["back", "posture"]
            }
        ]
        
        for case in test_cases:
            stories = compiler._fallback_requirement_stories(case["input"])
            
            # Should return 3-6 stories
            assert 3 <= len(stories) <= 6
            
            # Should contain relevant keywords
            stories_text = " ".join(stories).lower()
            for keyword in case["expected_keywords"]:
                assert keyword in stories_text
    
    @pytest.mark.asyncio
    async def test_compile_workout_basic_flow(self, compiler):
        """Test basic workout compilation flow."""
        
        # Mock the database operations
        with patch('app.database.compilation_operations.store_compiled_workout') as mock_store:
            mock_store.return_value = "test-workout-id"
            
            # Mock the vector search
            with patch('app.database.vectorization.search_similar_exercises') as mock_search:
                mock_search.return_value = [
                    {
                        'id': 'test-exercise-id',
                        'score': 0.8,
                        'metadata': {
                            'exercise_name': 'Test Exercise',
                            'video_path': '/test/path.mp4',
                            'start_time': 0.0,
                            'end_time': 30.0,
                            'how_to': 'Test instructions',
                            'benefits': 'Test benefits',
                            'counteracts': 'Test problems',
                            'fitness_level': 5,
                            'intensity': 5
                        }
                    }
                ]
                
                # Mock video compilation
                with patch.object(compiler, '_compile_video') as mock_compile:
                    mock_compile.return_value = "/test/workout.mp4"
                    
                    # Test compilation
                    result = await compiler.compile_workout(
                        user_requirements="I need a beginner workout",
                        target_duration=300,  # 5 minutes
                        format="square",
                        intensity_level="beginner"
                    )
                    
                    # Should succeed
                    assert result["success"] is True
                    assert result["workout_id"] == "test-workout-id"
                    assert result["video_path"] == "/test/workout.mp4"
                    assert "requirement_stories" in result
                    assert "clips_used" in result
                    assert "processing_time" in result
    
    @pytest.mark.asyncio
    async def test_compile_workout_error_handling(self, compiler):
        """Test error handling in workout compilation."""
        
        # Mock database operations to raise an error
        with patch('app.database.compilation_operations.store_compiled_workout') as mock_store:
            mock_store.side_effect = Exception("Database error")
            
            # Test compilation with error
            result = await compiler.compile_workout(
                user_requirements="I need a workout",
                target_duration=300,
                format="square",
                intensity_level="beginner"
            )
            
            # Should fail gracefully
            assert result["success"] is False
            assert "error" in result
            assert "processing_time" in result
    
    def test_requirement_story_keywords(self, compiler):
        """Test that requirement stories contain appropriate keywords."""
        
        test_input = "I sit all day, my hips are tight, I want to do handstands"
        stories = compiler._fallback_requirement_stories(test_input)
        
        # Should contain relevant keywords from input
        stories_text = " ".join(stories).lower()
        assert "sit" in stories_text or "mobility" in stories_text
        assert "hip" in stories_text or "flexibility" in stories_text
        assert "handstand" in stories_text or "shoulder" in stories_text
        
        # Should have appropriate number of stories
        assert 3 <= len(stories) <= 6
        
        # Each story should be a descriptive paragraph
        for story in stories:
            assert len(story) > 20  # Should be substantial
            assert not story.isupper()  # Should not be all caps
    
    @pytest.mark.asyncio
    async def test_search_relevant_clips(self, compiler):
        """Test searching for relevant clips."""
        
        # Mock vector search results
        mock_search_results = [
            {
                'id': 'exercise-1',
                'score': 0.9,
                'metadata': {
                    'exercise_name': 'Hip Stretch',
                    'video_path': '/test/hip_stretch.mp4',
                    'start_time': 0.0,
                    'end_time': 30.0,
                    'how_to': 'Stretch your hips',
                    'benefits': 'Improves hip mobility',
                    'counteracts': 'Sitting all day',
                    'fitness_level': 3,
                    'intensity': 2
                }
            },
            {
                'id': 'exercise-2',
                'score': 0.7,
                'metadata': {
                    'exercise_name': 'Shoulder Press',
                    'video_path': '/test/shoulder_press.mp4',
                    'start_time': 0.0,
                    'end_time': 45.0,
                    'how_to': 'Press your shoulders',
                    'benefits': 'Builds shoulder strength',
                    'counteracts': 'Weak shoulders',
                    'fitness_level': 5,
                    'intensity': 6
                }
            }
        ]
        
        with patch('app.database.vectorization.search_similar_exercises') as mock_search:
            mock_search.return_value = mock_search_results
            
            requirement_stories = [
                "Tight hip mobility training for someone who sits all day",
                "Shoulder strength development for handstand progression"
            ]
            
            clips = await compiler._search_relevant_clips(
                requirement_stories=requirement_stories,
                target_duration=300,  # 5 minutes
                intensity_level="beginner"
            )
            
            # Should return clips
            assert len(clips) > 0
            
            # Each clip should have required fields
            for clip in clips:
                assert 'exercise_id' in clip
                assert 'exercise_name' in clip
                assert 'video_path' in clip
                assert 'start_time' in clip
                assert 'end_time' in clip
                assert 'how_to' in clip
                assert 'benefits' in clip
                assert 'counteracts' in clip
                assert 'fitness_level' in clip
                assert 'intensity' in clip
                assert 'requirement_story' in clip
                assert 'relevance_score' in clip
    
    @pytest.mark.asyncio
    async def test_generate_exercise_scripts(self, compiler):
        """Test exercise script generation."""
        
        test_clips = [
            {
                'exercise_name': 'Test Exercise',
                'how_to': 'Basic instructions',
                'benefits': 'Test benefits',
                'counteracts': 'Test problems',
                'fitness_level': 5,
                'intensity': 5
            }
        ]
        
        # Mock AI enhancement
        with patch.object(compiler, '_enhance_exercise_instructions') as mock_enhance:
            mock_enhance.return_value = "Enhanced instructions"
            
            result = await compiler._generate_exercise_scripts(test_clips)
            
            # Should return clips with exercise scripts
            assert len(result) == 1
            assert 'exercise_script' in result[0]
            assert result[0]['exercise_script'] == "Enhanced instructions"
    
    @pytest.mark.asyncio
    async def test_compile_video(self, compiler):
        """Test video compilation with FFmpeg."""
        
        test_clips = [
            {
                'video_path': '/test/clip1.mp4',
                'start_time': 0.0,
                'end_time': 30.0
            },
            {
                'video_path': '/test/clip2.mp4',
                'start_time': 0.0,
                'end_time': 30.0
            }
        ]
        
        # Mock FFmpeg subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")
            
            # Mock file operations
            with patch('pathlib.Path.mkdir'), \
                 patch('builtins.open', create=True), \
                 patch('os.remove'):
                
                result = await compiler._compile_video(
                    clips=test_clips,
                    target_duration=300,
                    format="square"
                )
                
                # Should return a video path
                assert result.endswith('.mp4')
                assert 'workout_' in result
                
                # Should call FFmpeg
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert 'ffmpeg' in call_args[0]
                assert '-f' in call_args
                assert 'concat' in call_args 
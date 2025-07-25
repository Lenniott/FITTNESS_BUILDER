"""
Pydantic models for routine API endpoints.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class RoutineRequest(BaseModel):
    """Request model for routine generation."""
    user_requirements: str = Field(..., description="Natural language workout requirements")
    target_duration: Optional[int] = Field(None, description="Target duration in seconds")
    intensity_level: Optional[str] = Field(None, description="Intensity level (beginner/intermediate/advanced)")
    format: Optional[str] = Field("vertical", description="Format (vertical/square)")

class ExerciseData(BaseModel):
    """Model for exercise data in routine."""
    exercise_id: str
    exercise_name: str
    video_path: str
    start_time: float
    end_time: float
    duration: float
    how_to: str
    benefits: str
    counteracts: str
    fitness_level: int
    intensity: int
    relevance_score: float
    uniqueness_score: Optional[float] = None
    selection_reason: Optional[str] = None
    deletion_metadata: Dict

class RoutineMetadata(BaseModel):
    """Model for routine metadata."""
    total_duration: int
    exercise_count: int
    variety_score: Optional[float] = None
    progression_flow: Optional[str] = None
    ai_selection_notes: Optional[str] = None
    created_at: float

class RoutineData(BaseModel):
    """Model for complete routine data."""
    routine_id: str
    user_requirements: str
    target_duration: int
    intensity_level: str
    format: str
    exercises: List[ExerciseData]
    metadata: RoutineMetadata

class RoutineResponse(BaseModel):
    """Response model for routine generation."""
    success: bool
    routine_id: Optional[str] = None
    routine_data: Optional[RoutineData] = None
    requirement_stories: Optional[List[str]] = None
    exercises_selected: Optional[int] = None
    processing_time: float
    error: Optional[str] = None

class RoutineListResponse(BaseModel):
    """Response model for routine listing."""
    routines: List[RoutineData]
    total_count: int
    limit: int
    offset: int

class DeleteResponse(BaseModel):
    """Response model for deletion operations."""
    success: bool
    message: str
    deleted_count: Optional[int] = None

class RemoveExerciseRequest(BaseModel):
    """Request model for removing exercise from routine."""
    delete_exercise: bool = Field(False, description="Whether to completely delete the exercise") 
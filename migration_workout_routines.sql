-- Migration: Add workout_routines table
-- Run this on existing databases to add new table

CREATE TABLE IF NOT EXISTS workout_routines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_requirements TEXT NOT NULL,
    target_duration INTEGER NOT NULL,
    intensity_level VARCHAR(20) NOT NULL,
    format VARCHAR(20) DEFAULT 'vertical',
    routine_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_workout_routines_intensity_level ON workout_routines(intensity_level);
CREATE INDEX IF NOT EXISTS idx_workout_routines_created_at ON workout_routines(created_at);
CREATE INDEX IF NOT EXISTS idx_workout_routines_user_requirements ON workout_routines USING gin(to_tsvector('english', user_requirements));

-- Create JSONB indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_workout_routines_routine_data ON workout_routines USING gin(routine_data); 
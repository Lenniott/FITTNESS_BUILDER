-- Migration for workout compilation pipeline
-- This script adds the compiled_workouts table

-- Store compiled workout videos
CREATE TABLE IF NOT EXISTS compiled_workouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_requirements TEXT NOT NULL,
    target_duration INTEGER NOT NULL, -- in seconds
    format VARCHAR(10) DEFAULT 'square', -- 'square' or 'vertical'
    intensity_level VARCHAR(20) DEFAULT 'beginner', -- 'beginner', 'intermediate', 'advanced'
    video_path VARCHAR(500) NOT NULL,
    actual_duration INTEGER NOT NULL, -- actual duration in seconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_compiled_workouts_created_at ON compiled_workouts(created_at);

-- Create index on intensity_level for filtering
CREATE INDEX IF NOT EXISTS idx_compiled_workouts_intensity_level ON compiled_workouts(intensity_level);

-- Create index on format for filtering
CREATE INDEX IF NOT EXISTS idx_compiled_workouts_format ON compiled_workouts(format);

-- Grant permissions (if using specific user)
-- GRANT ALL PRIVILEGES ON TABLE compiled_workouts TO fitness_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fitness_user; 
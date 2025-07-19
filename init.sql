-- Initialize fitness database schema
-- This script runs when the PostgreSQL container starts

-- Create the exercises table with all required fields
CREATE TABLE IF NOT EXISTS exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url VARCHAR(500) NOT NULL,
    normalized_url VARCHAR(500) NOT NULL,
    carousel_index INTEGER DEFAULT 1,
    exercise_name VARCHAR(200) NOT NULL,
    video_path VARCHAR(500) NOT NULL,
    start_time DECIMAL(10,3),
    end_time DECIMAL(10,3),
    how_to TEXT,
    benefits TEXT,
    counteracts TEXT,
    fitness_level INTEGER CHECK (fitness_level >= 0 AND fitness_level <= 10),
    rounds_reps VARCHAR(200),
    intensity INTEGER CHECK (intensity >= 0 AND intensity <= 10),
    qdrant_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on url for faster lookups
CREATE INDEX IF NOT EXISTS idx_exercises_url ON exercises(url);

-- Create index on normalized_url and carousel_index for duplicate prevention
CREATE INDEX IF NOT EXISTS idx_exercises_normalized_url ON exercises(normalized_url);
CREATE INDEX IF NOT EXISTS idx_exercises_carousel_index ON exercises(carousel_index);

-- Create unique constraint to prevent duplicate processing
CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_unique_url_index ON exercises(normalized_url, carousel_index);

-- Create index on fitness_level and intensity for filtering
CREATE INDEX IF NOT EXISTS idx_exercises_fitness_level ON exercises(fitness_level);
CREATE INDEX IF NOT EXISTS idx_exercises_intensity ON exercises(intensity);

-- Create index on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_exercises_created_at ON exercises(created_at);

-- Insert some sample data (optional)
-- INSERT INTO exercises (url, exercise_name, video_path, start_time, end_time, how_to, benefits, counteracts, fitness_level, rounds_reps, intensity) VALUES
-- ('https://example.com/video1', 'Sample Exercise', 'storage/clips/sample.mp4', 0.0, 30.0, 'Sample instructions', 'Sample benefits', 'Sample problems', 5, '3 sets of 10', 5);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE exercises TO fitness_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fitness_user; 
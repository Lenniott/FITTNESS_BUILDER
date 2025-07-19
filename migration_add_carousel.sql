-- Migration: Add carousel support fields
-- Run this on existing databases to add new fields

-- Add new columns
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS normalized_url VARCHAR(500);
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS carousel_index INTEGER DEFAULT 1;

-- Update existing records to set normalized_url (remove query parameters)
UPDATE exercises 
SET normalized_url = CASE 
    WHEN url LIKE '%?%' THEN SPLIT_PART(url, '?', 1)
    ELSE url
END
WHERE normalized_url IS NULL;

-- Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_exercises_normalized_url ON exercises(normalized_url);
CREATE INDEX IF NOT EXISTS idx_exercises_carousel_index ON exercises(carousel_index);

-- Create unique constraint to prevent duplicate processing
CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_unique_url_index ON exercises(normalized_url, carousel_index);

-- Make normalized_url NOT NULL after populating it
ALTER TABLE exercises ALTER COLUMN normalized_url SET NOT NULL; 
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- **Simplified Instagram Downloader**: Removed complex carousel handling logic
  - **URL Sanitization**: Automatically removes query parameters like `img_index` from Instagram URLs
  - **Single Download Method**: Uses `python3 -m instaloader` CLI to download all videos from URL
  - **Simplified Processing**: Processor now handles all downloaded videos directly without carousel item folders
  - **Removed Complex Logic**: Eliminated `download_instagram_carousel()` and `download_instagram_single_item()` functions
  - **Direct Video Processing**: All videos from download are processed individually by the processor
  - **Shortcode Extraction**: Properly extracts shortcode from Instagram URLs for CLI usage
  - **Error Handling**: Improved error handling for invalid shortcodes and authentication issues

- **Enhanced Clip Generation Logic**: Added intelligent exercise consolidation and overlap detection
  - **Overlap Detection**: Automatically detects when AI creates multiple overlapping exercises (>50% overlap)
  - **Exercise Consolidation**: Keeps the best exercise (highest confidence or longest duration) when overlaps are detected
  - **Single Cut Handling**: For videos with only one cut, extends the exercise to cover the full video duration
  - **Full Video Coverage**: Ensures single exercises cover at least 80% of the video duration
  - **Duplicate Prevention**: Prevents multiple clips from being generated for the same movement pattern
  - **Improved AI Prompt**: Enhanced AI prompt to explicitly avoid overlapping exercises and prioritize complete movements

### Added
- **Complete Video Processing Pipeline Implementation**: Full implementation of the processor according to the plan
  - **Main Pipeline**: `app/core/processor.py` with complete 9-step video processing workflow
  - **Download Integration**: Uses `app/services/downloaders.py` for video and metadata extraction
  - **Transcription Integration**: Uses `app/services/transcription.py` for audio-to-text conversion
  - **Frame Extraction**: Uses `app/utils/enhanced_keyframe_extraction.py` for keyframe detection
  - **AI Exercise Detection**: Gemini multimodal analysis with all frames sent to LLM
  - **Clip Generation**: FFmpeg-based video clip creation from exercise timestamps
  - **Database Storage**: PostgreSQL integration for exercise metadata storage
  - **Vector Storage**: Qdrant integration for semantic search embeddings
  - **Comprehensive Logging**: Detailed logging throughout the pipeline for debugging
  - **Error Handling**: Robust error handling with fallback mechanisms
  - **Debug Data**: Saves AI prompts, responses, and metadata to temp directory
  - **Frame Bypass**: Uses ALL frames from folder instead of filtered list from extractor
  - **Transcript Quality Analysis**: Intelligently includes/excludes transcript based on quality
  - **Fallback Detection**: Simple keyword-based exercise detection when AI fails
  - **Quality Filtering**: Filters out clips that are too short, too long, or low confidence
  - **Duplicate Prevention**: Checks for already processed URLs to avoid reprocessing
  - **Cleanup**: Automatic cleanup of temporary files after processing

### Fixed
- **Critical Data Integrity Issues**: Fixed processor to properly save all artifacts and prevent orphaned data
  - **Transaction Management**: Implemented proper transaction management to prevent orphaned vector embeddings
  - **Error Recovery**: Added comprehensive error recovery and cleanup mechanisms
  - **File Validation**: Enhanced file validation with FFmpeg probe to detect corrupted files
  - **Rollback Mechanism**: Added rollback for partial failures to prevent orphaned data
  - **Orphaned Data Cleanup**: Added methods to detect and clean up orphaned vector embeddings and files
  - **Data Integrity Validation**: Added validation to ensure database, vector store, and files are in sync
  - **File Creation Order**: Fixed to create files only after successful database storage
  - **Comprehensive Logging**: Enhanced logging with success/failure indicators and detailed error reporting
  - **Cleanup on Failure**: Automatic cleanup of partial files and embeddings when processing fails

### Changed
- **Minimum Exercise Duration**: Reduced minimum exercise duration from 5 seconds to 3.5 seconds
  - Updated AI prompt to detect exercises 3.5+ seconds long instead of 5+ seconds
  - Updated clip generation minimum duration parameter from 5.0 to 3.5 seconds
  - Allows detection of shorter but still meaningful exercise segments
- **Database Schema**: Fixed unique constraint to allow multiple exercises per URL
  - Changed unique constraint from `(normalized_url, carousel_index)` to `(normalized_url, carousel_index, exercise_name)`
  - Now allows storing multiple exercises from the same video (e.g., 3 exercises from one Instagram reel)
  - Fixed issue where only first exercise was stored due to constraint violation

### Added
- **Enhanced Cascade Deletion System**: Comprehensive deletion with database, vector store, file system, and compiled workout cleanup
- **Batch Deletion by Criteria**: Delete multiple exercises based on fitness level, intensity, name patterns, and date ranges
- **Low-Quality Exercise Purge**: Specialized endpoint for removing "bad clips" based on quality thresholds
- **Deletion Preview System**: Preview what would be deleted before committing to deletion
- **Storage Analysis Tools**: Comprehensive storage usage analysis and cleanup recommendations
- **Orphaned File Detection**: Find and clean up files that exist in storage but not referenced in database
- **Temporary File Cleanup**: Automatic cleanup of old temporary processing files
- **Cleanup Utilities Module**: New `app/utils/cleanup_utils.py` with comprehensive cleanup functions
- **Enhanced Database Operations**: Improved deletion functions with cascade cleanup in `app/database/operations.py`
- **Compilation Operations Enhancement**: Added functions for managing compiled workouts in `app/database/compilation_operations.py`
- **Video Compilation Pipeline**: Complete workout generation from natural language requirements
- **Two-Stage AI Workflow**: Requirement story generation + content retrieval and compilation
- **Workout Compilation API**: New endpoints for generating personalized workout videos
- **Database Schema**: `compiled_workouts` table for storing workout compilation results
- **Vector Search Integration**: Leverages existing exercise database for content retrieval
- **FFmpeg Video Compilation**: Stitches selected clips into complete workout videos
- **Exercise Script Generation**: AI-enhanced exercise instructions for each clip
- **Complete `/process` endpoint implementation** following exact specifications
- **Video Processing Pipeline**: Download → Transcribe → Extract Frames → AI Detection → Generate Clips → Store
- **AI Exercise Detection**: Gemini multimodal analysis with comprehensive exercise details
- **Database Integration**: PostgreSQL for exercise storage with full schema
- **Vector Search**: Qdrant integration for semantic exercise search
- **Comprehensive API**: Full REST API with health checks, search, and statistics
- Integration tests for downloader component (`tests/integration/test_downloader_integration.py`)
- Real YouTube video download testing with actual URLs
- URL validation integration tests
- Error handling integration tests

### New Cascade Deletion API Endpoints
- `DELETE /api/v1/exercises/{exercise_id}` - Enhanced single exercise deletion with cascade cleanup
- `DELETE /api/v1/exercises/batch` - Batch deletion by criteria (fitness level, intensity, name patterns, dates)
- `DELETE /api/v1/exercises/purge-low-quality` - Specialized endpoint for removing low-quality exercises
- `GET /api/v1/exercises/deletion-preview` - Preview what would be deleted before committing
- `GET /api/v1/cleanup/analysis` - Comprehensive storage analysis and cleanup recommendations
- `GET /api/v1/cleanup/orphaned-files` - Find files not referenced in database
- `DELETE /api/v1/cleanup/orphaned-files` - Clean up orphaned files (requires confirm=true)
- `DELETE /api/v1/cleanup/temp-files` - Clean up old temporary files (requires confirm=true)
- `GET /api/v1/cleanup/preview` - Preview all cleanup operations without deleting

### Cascade Deletion Features
- **Complete Data Cleanup**: Deletes from database, vector store, file system, and compiled workouts
- **File Path Handling**: Supports multiple path formats (container paths, relative paths, temp paths)
- **Compiled Workout Cleanup**: Automatically removes compiled workouts that reference deleted exercises
- **Vector Store Cleanup**: Removes embeddings from Qdrant when exercises are deleted
- **Error Resilience**: Graceful handling of missing files and database errors
- **Batch Operations**: Efficient deletion of multiple exercises with single database transaction
- **Quality-Based Filtering**: Remove exercises based on fitness level, intensity, and name patterns
- **Date-Based Filtering**: Delete exercises created before/after specific dates
- **Storage Analysis**: Comprehensive analysis of storage usage and cleanup opportunities
- **Orphaned File Detection**: Find files that exist in storage but not referenced in database
- **Temporary File Cleanup**: Remove old temporary processing files

### Implemented Core Components
- **`app/api/main.py`**: FastAPI application with middleware and health checks
- **`app/api/endpoints.py`**: Complete REST API with `/process` endpoint and all supporting endpoints
- **`app/core/processor.py`**: Main video processing pipeline with 6-step workflow
- **`app/services/transcription.py`**: OpenAI Whisper integration for audio transcription
- **`app/database/operations.py`**: PostgreSQL operations with full exercise schema and enhanced cascade deletion
- **`app/database/vectorization.py`**: Qdrant vector database integration
- **`app/database/compilation_operations.py`**: Enhanced compiled workout management with cleanup functions
- **`app/utils/cleanup_utils.py`**: New comprehensive cleanup utilities module
- **`app/api/middleware.py`**: CORS and security middleware

### API Endpoints
- `POST /api/v1/process` - Main video processing endpoint
- `GET /api/v1/exercises` - List exercises with URL filtering
- `GET /api/v1/exercises/{id}` - Get specific exercise
- `POST /api/v1/exercises/search` - Search exercises with filters
- `GET /api/v1/exercises/similar/{id}` - Find similar exercises
- `DELETE /api/v1/exercises/{id}` - Enhanced single exercise deletion with cascade cleanup
- `DELETE /api/v1/exercises/batch` - Batch deletion by criteria
- `DELETE /api/v1/exercises/purge-low-quality` - Remove low-quality exercises
- `GET /api/v1/exercises/deletion-preview` - Preview deletion operations
- `DELETE /api/v1/exercises/all` - Delete ALL exercises, clips, and vector embeddings
- `DELETE /api/v1/exercises/url/{url}` - Delete all exercises and clips for a specific URL
- `GET /api/v1/health/database` - Database health check
- `GET /api/v1/health/vector` - Vector database health check
- `GET /api/v1/stats` - Processing statistics
- `GET /api/v1/cleanup/analysis` - Storage analysis and cleanup recommendations
- `GET /api/v1/cleanup/orphaned-files` - Find orphaned files
- `DELETE /api/v1/cleanup/orphaned-files` - Clean up orphaned files
- `DELETE /api/v1/cleanup/temp-files` - Clean up old temp files
- `GET /api/v1/cleanup/preview` - Preview cleanup operations

### Workout Compilation API Endpoints
- `POST /api/v1/workout/generate` - Generate personalized workout from natural language
- `GET /api/v1/workout/{workout_id}` - Get compiled workout by ID
- `GET /api/v1/workout/{workout_id}/download` - Download compiled workout video
- `GET /api/v1/workouts` - List all compiled workouts
- `DELETE /api/v1/workout/{workout_id}` - Delete compiled workout
- `GET /api/v1/workout/{workout_id}/status` - Get workout generation status

### AI Integration
- **Gemini Multimodal Analysis**: Processes video frames + transcript + metadata
- **Automatic API Fallback**: Seamless fallback from primary to backup Gemini API key
- **Structured Exercise Output**: Complete exercise details (name, instructions, benefits, etc.)
- **Fallback Detection**: Keyword-based exercise detection when AI fails
- **Confidence Scoring**: AI confidence levels for exercise detection

### Database Schema
```sql
-- Exercises table (existing)
CREATE TABLE exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url VARCHAR(500) NOT NULL,
    exercise_name VARCHAR(200) NOT NULL,
    video_path VARCHAR(500) NOT NULL,
    how_to TEXT,
    benefits TEXT,
    counteracts TEXT,
    fitness_level INTEGER CHECK (fitness_level >= 0 AND fitness_level <= 10),
    rounds_reps VARCHAR(200),
    intensity INTEGER CHECK (intensity >= 0 AND intensity <= 10),
    qdrant_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Compiled workouts table (new)
CREATE TABLE compiled_workouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_requirements TEXT NOT NULL,
    target_duration INTEGER NOT NULL, -- in seconds
    format VARCHAR(10) DEFAULT 'square', -- 'square' or 'vertical'
    intensity_level VARCHAR(20) DEFAULT 'beginner', -- 'beginner', 'intermediate', 'advanced'
    video_path VARCHAR(500) NOT NULL,
    actual_duration INTEGER NOT NULL, -- actual duration in seconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Fixed
- **Comprehensive File Validation System**: Added complete file validation pipeline to prevent corrupted files
  - Download corruption detection using multiple methods
  - Video quality validation with OpenCV and FFmpeg
  - Audio content validation and playability testing
  - Automatic cleanup of invalid files during download
  - Detailed validation reporting with errors and warnings

- **Enhanced Transcription Quality**: Added `app/services/enhanced_transcription.py` with comprehensive quality validation
  - Audio quality assessment before transcription
  - Segment duration validation (1-30 seconds)
  - Text length validation (3-500 characters)
  - Segment merging for better timing
  - Text cleaning and normalization
  - Improved subtitle file parsing with validation
  - Better error handling and reporting

- **Enhanced Keyframe Extraction**: Added `app/utils/enhanced_keyframe_extraction.py` with multiple detection methods ✅ **COMPLETED**
  - Movement detection to capture important moments
  - Cut detection to identify scene changes
  - Key moment extraction (start, middle, end)
  - Regular interval extraction (2-second intervals)
  - Smart frame deduplication with method prioritization (key_moment > cut > interval)
  - Dynamic frame extraction - no artificial limits, scales with video duration
  - Improved timing accuracy and coverage
  - **Integration Complete**: Enhanced extraction now used in main processing pipeline
  - **Frame Naming**: Frames now use method suffixes (_key_moment, _cut, _interval)
  - **Deduplication Working**: Intelligent frame saving prevents duplicates within 200ms window
  - **Requirements Compliance**: Fixed to match exact requirements:
    - Extract frames at 4 FPS (not 8 FPS)
    - Use original video frame numbers in naming convention
    - Apply 1 FPS minimum and 8 FPS maximum constraints
    - Proper frame rate constraint implementation
  - **Updated Frame Naming Convention**: Now uses `cut_X_frame_Y_time_Z_diff_W.jpg` format
  - **Smart Cleanup**: Maintains 1 FPS minimum while removing redundant diff_0 frames
  - **Token Optimization**: Reduced frame quality by 50% to save AI processing costs
- Installed ffmpeg dependency for video processing
- Fixed downloader to handle video format merging properly
- Improved error handling for invalid URLs
- Optimized YouTube downloader to skip unnecessary files (thumbnails, verbose JSON)
- Restored subtitle/transcript downloads for fitness video analysis
- Improved transcript handling for Instagram videos: now always uses Whisper for audio transcription, never just the caption.
- Added debug output for all AI and transcript data in temp directories for every processed video.
- Improved error logging and diagnostics for ffmpeg clip generation.
- Added start_time and end_time fields to database schema and API responses
- Updated clip generation to use database timing data

### Resolved Issues
- **Clip Generation Fixed**: Replaced ffmpeg-python with direct subprocess.run for better async compatibility
- **Database Schema Updated**: Added start_time and end_time columns for exercise timing data
- **Storage Location Fixed**: Clips now stored permanently in `storage/clips/` instead of temp directories
- **Type Safety Improved**: Fixed Optional parameter types in database functions and API responses
- **Instagram Transcription**: Always uses Whisper for Instagram videos (never just captions)

### Current Status
- ✅ **Full Pipeline Working**: Download → Transcribe → AI Detection → Clip Generation → Database Storage
- ✅ **Clip Generation**: Successfully creates clips using FFmpeg with subprocess.run
- ✅ **Database Integration**: PostgreSQL stores exercise data with timing information
- ✅ **Vector Search**: Qdrant integration for semantic exercise search
- ✅ **Permanent Storage**: Clips stored in `storage/clips/` with database metadata
- ✅ **API Endpoints**: Complete REST API with health checks, search, and statistics
- ✅ **Docker Deployment**: Production-ready containerization with FFmpeg, connects to external PostgreSQL and Qdrant
- ✅ **Carousel Support**: Automatic processing of Instagram carousel items with duplicate prevention
- ✅ **Data Cleanup**: Comprehensive delete endpoints for database, vector store, and file cleanup
- ✅ **Proper Carousel Implementation**: One URL → detect carousel count → download each item individually → process each video

### Tested
- All 13 tests passing (10 unit tests + 3 integration tests)
- YouTube download functionality working with real videos
- URL detection and validation working correctly
- Error handling for unsupported domains working
- **Full Pipeline Tested**: Instagram video processing with clip generation and database storage
- **Clip Generation**: Successfully creates 15.1s clip from 5.6s-20.7s timing data
- **Database Storage**: Exercise stored with complete metadata and timing information
- **API Endpoints**: All endpoints tested and working correctly
- **Docker Deployment**: Containerized application running successfully in production
- **Carousel Processing**: Instagram carousel detection and multi-item processing
- **Proper Carousel Implementation**: Correctly detects carousel count, downloads each item individually, processes each video without cascade effects

### Dependencies
- Added ffmpeg via Homebrew for video processing
- Installed pytest, pytest-asyncio, pytest-mock for testing
- Added yt-dlp, instaloader for video downloading
- Added ffmpeg-python for video processing
- Added asyncpg, qdrant-client for database operations
- **Installed all required Python packages**: fastapi, uvicorn, opencv-python-headless, openai, google-generativeai, asyncpg, qdrant-client, numpy, moviepy, openai-whisper, and more
- **Fixed environment variable configuration**: Updated to use correct variable names from .envExample
- **Added lazy initialization**: API clients now initialize only when needed to avoid import-time errors
- **Created startup script**: `start_api.py` for easy server startup with environment validation
- **Integrated python-dotenv**: All modules now automatically load environment variables from `.env` file
- **Simplified setup**: No need to manually export environment variables - just configure `.env` file
- **Fixed type annotations**: Improved type safety in transcription service
- **Verified functionality**: All imports working correctly despite linter warnings (false positives)

### Project Cleanup
- **Organized test files**: Moved all test files to proper `tests/` directory structure
- **Removed empty files**: Cleaned up empty documentation and configuration files
- **Updated documentation**: Enhanced README, CHANGELOG, and PROJECT_CONTEXT with latest features
- **Improved project structure**: Clean, organized codebase with proper separation of concerns

### AI Provider Enhancements
- **Gemini API Fallback**: Automatic fallback from primary to backup Gemini API key on failure
- **Robust Error Handling**: Graceful degradation when primary API key hits rate limits or quota
- **Enhanced Logging**: Clear logging of which API key is being used for debugging
- **Environment Configuration**: Added `GEMINI_API_BACKUP_KEY` environment variable support
- **Comprehensive Testing**: Added unit tests for fallback mechanism with 100% test coverage

## [Initial] - 2025-01-18

### Added
- Initial project structure with FastAPI backend
- Downloader component for YouTube, TikTok, and Instagram
- Unit tests for downloader functionality
- Project documentation and context files
### Video Quality & Duration Filtering
- **Minimum Clip Duration**: Added 5-second minimum duration filter for generated clips
- **Maximum Clip Duration**: Added 60-second maximum duration filter to avoid overly long clips
- **Video Quality Validation**: Added checks for video resolution, frame rate, and duration
- **Confidence Score Filtering**: Skip exercises with confidence scores below 0.3
- **Enhanced AI Prompt**: Updated Gemini prompt to be more selective about exercise detection

### Video Quality & Duration Filtering (Latest)
- **Minimum Clip Duration**: Added 5-second minimum duration filter for generated clips
- **Maximum Clip Duration**: Added 60-second maximum duration filter to avoid overly long clips
- **Video Quality Validation**: Added checks for video resolution (320x240 min), frame rate (10 fps min), and duration (10s-600s)
- **Confidence Score Filtering**: Skip exercises with confidence scores below 0.3
- **Enhanced AI Prompt**: Updated Gemini prompt to be more selective about exercise detection
- **Unit Tests**: Added comprehensive tests for clip filtering and video quality validation

### Fixed
- **Keyframe Extraction Naming Convention Mismatch**: Discovered that the enhanced keyframe extractor is being called but frames are using old naming convention (`frame_XXXXXX_method.jpg`) instead of new convention (`cut_X_frame_Y_time_Z_diff_W.jpg`). This causes the AI to receive no frames for analysis. The processor expects new naming convention but receives old format, resulting in 0 frames being processed.
- **Root Cause Identified**: Old frames from previous runs (July 20 16:35) are blocking the enhanced keyframe extractor. The enhanced keyframe extractor IS working correctly and creating frames with proper naming convention, but old frames in temp directory are being used instead.
- **Frame Count Mismatch**: Enhanced keyframe extractor creates 34 frames but processor only finds 14 frames. Added detailed logging to track frame processing and identify why frames are being filtered out.
- **Frame Synchronization Issue**: Enhanced keyframe extractor was deleting frames during cleanup while processor was trying to access them. Added 2-second wait and re-verification to ensure all frame operations complete before processing.
- **Enhanced Keyframe Extractor Async Issues**: Made the enhanced keyframe extractor fully async by converting cleanup and frame rate constraint functions to async operations. This ensures all file operations complete before the processor tries to access frames.
- **Format Specifier Error**: Fixed "Invalid format specifier" error by escaping % characters in database queries. The error was caused by unescaped % characters in URL patterns and exercise name patterns used in SQL LIKE queries.

### July 2024 Pipeline & Frame Extraction Overhaul
- **Enhanced Frame Extraction**: All frames from the extraction folder are used for AI analysis (no filtering, no artificial limits, consistent naming)
- **Processor Logic**:
  - Adds carousel context to the AI prompt (first video in carousel is often an intro/hook, skip if no exercise is present)
  - Prevents multiple clips with start times within 3 seconds of each other
  - Consolidates overlapping exercises (>50% overlap)
  - Extends single exercises to cover the full video duration if needed
  - Uses improved AI prompt with explicit rules for non-overlapping, non-duplicate, and complete movement detection
- **Robustness**: The pipeline is now robust against duplicate, overlapping, or fragmented exercise detection
- **Instagram Carousel Handling**: All videos are downloaded once, and each is processed individually. The system is robust for both single-cut and multi-cut videos, and for carousels with intro/hook videos.

### Fixed
- Robust handling of string/invalid `start_time` and `end_time` in exercise clip generation (`app/core/processor.py`).
- The pipeline now skips and logs exercises with invalid or non-numeric times, preventing crashes from AI output.

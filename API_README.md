# Video Processing API Documentation

## Overview

The Video Processing API is a comprehensive service that extracts exercise clips from workout videos using AI-powered analysis. It follows a 6-step pipeline:

1. **Video Download & Metadata Extraction**
2. **Audio Transcription** 
3. **Keyframe Extraction**
4. **AI Exercise Detection**
5. **Video Clip Generation**
6. **Database Storage**

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.envExample` to `.env` and update with your actual values:

```bash
cp .envExample .env
# Edit .env with your actual API keys and database details
```

### 3. Start the API

```bash
python start_api.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Main Processing Endpoint

#### `POST /api/v1/process`

Process a video URL to extract exercise clips.

**Request:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "background": false
}
```

**Response:**
```json
{
  "success": true,
  "processed_clips": [
    {
      "exercise_id": "uuid",
      "exercise_name": "Push-ups",
      "video_path": "storage/clips/push_ups_001.mp4",
      "segments_count": 3,
      "total_duration": 18.9,
      "segments": [
        {"start_time": 15.2, "end_time": 22.1},
        {"start_time": 45.8, "end_time": 51.3},
        {"start_time": 78.5, "end_time": 85.0}
      ]
    }
  ],
  "total_clips": 2,
  "processing_time": 120.5
}
```

### Exercise Management

#### `GET /api/v1/exercises`
List all exercises, optionally filtered by URL.

#### `GET /api/v1/exercises/{exercise_id}`
Get a specific exercise by ID.

#### `POST /api/v1/exercises/search`
Search exercises with filters.

**Request:**
```json
{
  "query": "push-ups",
  "fitness_level_min": 3,
  "fitness_level_max": 7,
  "intensity_min": 5,
  "intensity_max": 8,
  "limit": 20
}
```

#### `GET /api/v1/exercises/similar/{exercise_id}`
Find similar exercises using vector search.

#### `DELETE /api/v1/exercises/{exercise_id}`
Delete an exercise.

### Health Checks

#### `GET /api/v1/health/database`
Check database connection.

#### `GET /api/v1/health/vector`
Check vector database connection.

#### `GET /api/v1/stats`
Get processing statistics.

## AI Exercise Detection

The system uses Google Gemini for multimodal analysis:

- **Input**: Video frames + transcript + metadata
- **Output**: Structured exercise data with:
  - Exercise name
  - Start/end times
  - Step-by-step instructions
  - Benefits and muscle groups targeted
  - Problems it helps solve
  - Fitness level (0-10)
  - Intensity level (0-10)
  - Specific reps/duration instructions
  - Confidence score

## Database Schema

```sql
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
```

## Testing

### Run Unit Tests
```bash
python -m pytest tests/unit/ -v
```

### Run Integration Tests
```bash
python -m pytest tests/integration/ -v
```

### Test Complete Pipeline
```bash
python test_process_endpoint.py
```

## Supported Platforms

- **YouTube**: Full support with metadata extraction
- **TikTok**: Video download and processing
- **Instagram**: Video download with fallback methods

## File Structure

```
app/
├── api/              # FastAPI endpoints and middleware
├── core/             # Main processing pipeline
├── database/         # PostgreSQL and vector operations
├── services/         # External services (AI, transcription)
└── utils/            # Video utilities and cleanup
```

## Error Handling

The API includes comprehensive error handling:

- **Input Validation**: URL format and domain checking
- **Download Failures**: Graceful fallbacks and retries
- **AI Failures**: Keyword-based fallback detection
- **Database Errors**: Connection pooling and retry logic
- **File Cleanup**: Automatic temporary file cleanup

## Performance Considerations

- **Async Processing**: All I/O operations are asynchronous
- **Connection Pooling**: Database and vector store connections
- **Memory Management**: Streaming video processing
- **Background Tasks**: Optional background processing
- **Progress Tracking**: Real-time processing status

## Security

- **Input Sanitization**: URL and file name validation
- **Environment Variables**: Secure API key management
- **CORS Configuration**: Configurable cross-origin requests
- **Rate Limiting**: Built-in request throttling

## Monitoring

- **Health Checks**: Database and service monitoring
- **Statistics**: Processing metrics and analytics
- **Logging**: Comprehensive error and info logging
- **Metrics**: Performance and usage statistics 
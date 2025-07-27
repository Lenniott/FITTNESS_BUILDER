# Fitness Builder

AI-powered fitness video processing pipeline that extracts exercises, creates clips, and enables semantic search.

## 🚀 Quick Start with Docker

### Prerequisites
- Docker and Docker Compose
- Existing PostgreSQL database
- Existing Qdrant vector database
- OpenAI or Gemini API key

### 1. Environment Setup
```bash
cp env.production.example .env
# Edit .env with your database and API credentials
```

### 2. Build and Deploy
```bash
docker-compose up -d --build
```

### 3. Portainer Deployment
1. **Build the image** using the Dockerfile
2. **Assign network** to your existing PostgreSQL and Qdrant network
3. **Mount volumes** for persistent storage:
   - `fitness_storage` → `/app/storage` (individual clip storage)
   - `fitness_compiled` → `/app/storage/compiled_workouts` (compiled workout videos)
   - `fitness_temp` → `/app/app/temp` (temporary processing)
4. **Set environment variables** from your `.env` file
5. **Expose port** 8000

**Note**: The container expects video clips to be stored in `/app/storage/clips/` inside the container, which maps to your host volume `fitness_storage`.

## 📊 API Contract Documentation

### 🔗 Base URL
```
http://localhost:8000/api/v1
```

### 📋 Data Structure Concepts

#### Exercise Entity
An **exercise** in this system consists of three interconnected components:
1. **Stored Clip File** - Video file in `storage/clips/` directory
2. **PostgreSQL Row** - Metadata stored in `exercises` table
3. **Qdrant Vector** - AI embedding for semantic search

All three components are linked via `qdrant_id` and `database_id` fields.

#### Routine Entity
A **routine** is a complete workout structure containing:
- **Exercises Array** - Ordered list of exercises with UI-ready data
- **Metadata** - Database operations info (database_ids, qdrant_ids, video_paths)
- **User Requirements** - Original prompt and parameters
- **Processing Info** - Creation time, processing duration

---

## 🏋️ ROUTINE MANAGEMENT (CRUD)

### Create Routine
**Generate intelligent workout routine from user prompt**

```http
POST /api/v1/generate-routine
```

**Request Body:**
```json
{
  "user_prompt": "I want to get good at pull ups but i can only do 1 at the moment",
  "target_duration": 900,
  "intensity_level": "moderate",
  "exercises_per_story": 3,
  "initial_limit": 40,
  "score_threshold": 0.3
}
```

**Response:**
```json
{
  "success": true,
  "routine_id": "359072d3-b5f8-40e9-a79a-81283533c3d6",
  "routine": {
    "exercise_ids": ["c8c8d8dd-4223-44e9-88c7-f20695bc1e35", "a2de96ab-3d00-4d6f-9da5-0566a5b47002"],
    "metadata": {
      "total_exercises": 5,
      "user_requirements": "I want to get good at pull ups but i can only do 1 at the moment",
      "target_duration": 900,
      "intensity_level": "moderate"
    }
  },
  "user_requirements": "I want to get good at pull ups but i can only do 1 at the moment",
  "target_duration": 900,
  "intensity_level": "moderate",
  "created_at": "2025-07-26 06:08:17.423912",
  "processing_time": 34.79
}
```

### Read Routine
**Retrieve stored routine by ID**

```http
GET /api/v1/routines/{routine_id}
```

**Response:** Same structure as Create Routine response

### UI Integration Pattern

The routine generation API is designed for efficient UI integration:

1. **Generate Routine** - Returns exercise IDs only
2. **Fetch Exercise Details** - Use bulk endpoint to get full exercise data

**Example UI Flow:**
```typescript
// 1. Generate routine (returns just IDs)
const routine = await generateRoutine(prompt);

// 2. Fetch exercise details (same pattern as getExercises)
const exercises = await getExercisesByIds(routine.exercise_ids);

// 3. Combine for display
const routineWithExercises = {
  ...routine,
  exercises: exercises.map((exercise, index) => ({
    ...exercise,
    order: index + 1
  }))
};
```

**Benefits:**
- **Consistent API pattern** with existing `getExercises`
- **Reusable exercise fetching logic**
- **Smaller routine responses**
- **Better performance** (no data duplication)

---

## 🎥 URL PROCESSING

### Process Video from URL
**Extract exercises from fitness video**

```http
POST /api/v1/process
```

**Request Body:**
```json
{
  "url": "https://www.instagram.com/p/CxYz123ABC/",
  "background": false
}
```

**Supported Platforms:**
- YouTube: `https://www.youtube.com/watch?v=VIDEO_ID`
- Instagram: `https://www.instagram.com/p/POST_ID/`
- TikTok: `https://www.tiktok.com/@user/video/VIDEO_ID`

**Synchronous Response:**
```json
{
  "success": true,
  "processed_clips": [
    {
      "exercise_name": "Push-up",
      "video_path": "storage/clips/push-up_abc123.mp4",
      "start_time": 10.5,
      "end_time": 25.3
    }
  ],
  "total_clips": 1,
  "processing_time": 45.2,
  "temp_dir": "storage/temp/gilgamesh_download_abc123"
}
```

**Asynchronous Response:**
```json
{
  "success": true,
  "processed_clips": [],
  "total_clips": 0,
  "processing_time": 0.0,
  "temp_dir": null,
  "job_id": "e513927a-2f60-4ead-b3e6-fa9597f50066"
}
```

### Check Job Status
**Poll for background processing status**

```http
GET /api/v1/job-status/{job_id}
```

**Response States:**
```json
// In Progress
{
  "status": "in_progress",
  "result": null
}

// Completed
{
  "status": "done",
  "result": {
    "success": true,
    "processed_clips": [...],
    "total_clips": 1,
    "processing_time": 45.2,
    "temp_dir": "storage/temp/gilgamesh_download_abc123"
  }
}

// Failed
{
  "status": "failed",
  "result": {
    "error": "Some error message"
  }
}
```

---

## 💪 EXERCISE MANAGEMENT (CRUD)

### Create Exercise
**Exercises are created automatically during video processing**

### Read Exercises

#### List All Exercises
```http
GET /api/v1/exercises
```

**Query Parameters:**
- `url` (optional): Filter by source URL
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "id": "c8c8d8dd-4223-44e9-88c7-f20695bc1e35",
    "exercise_name": "Push-up",
    "video_path": "storage/clips/push-up_abc123.mp4",
    "start_time": 10.5,
    "end_time": 25.3,
    "how_to": "Start in plank position...",
    "benefits": "Strengthens chest, shoulders, and triceps",
    "counteracts": "Improves upper body pushing strength",
    "fitness_level": 3,
    "rounds_reps": "3 sets of 10-15 reps",
    "intensity": 5,
    "qdrant_id": "77c6856e-e4a2-42a7-b361-bc73808ac812",
    "created_at": "2025-07-26T06:08:17.423912"
  }
]
```

> **Note:** The `qdrant_id` field is always returned as a string (UUID format) in API responses, even if stored as a UUID in the database.

#### Get Specific Exercise
```http
GET /api/v1/exercises/{exercise_id}
```

**Response:** Single exercise object (same structure as above)

#### Get Multiple Exercises by IDs
```http
POST /api/v1/exercises/bulk
```

**Request Body:**
```json
{
  "exercise_ids": ["c8c8d8dd-4223-44e9-88c7-f20695bc1e35", "a2de96ab-3d00-4d6f-9da5-0566a5b47002"]
}
```

**Response:** Array of exercise objects (same structure as individual exercise)

> **UI Integration Pattern:**
> This endpoint is designed to work with the routine generation API. After generating a routine (which returns `exercise_ids`), use this endpoint to fetch the full exercise details for display in the UI.

#### Search Exercises
```http
POST /api/v1/exercises/search
```

**Request Body:**
```json
{
  "query": "push",
  "fitness_level_min": 3,
  "fitness_level_max": 7,
  "intensity_min": 5,
  "intensity_max": 10,
  "limit": 20
}
```

#### Semantic Search
```http
POST /api/v1/exercises/semantic-search
```

**Request Body:**
```json
{
  "query": "I need a beginner workout for my back that helps with posture",
  "limit": 10,
  "score_threshold": 0.7
}
```

#### Find Similar Exercises
```http
GET /api/v1/exercises/similar/{exercise_id}
```

**Query Parameters:**
- `limit` (optional): Number of similar exercises (default: 10, max: 50)

### Update Exercise
**Exercises are immutable - updates require reprocessing the video**

### Delete Exercises

#### Delete by ID
```http
DELETE /api/v1/exercises/{exercise_id}
```

> **Cascade Cleanup:**
> - This endpoint will remove the exercise from PostgreSQL, delete the associated video file from storage, and remove the vector from Qdrant. All three storage layers are cleaned up automatically.

#### Delete by URL
```http
DELETE /api/v1/exercises/url/{url}
```

#### Delete All Exercises
```http
DELETE /api/v1/exercises/all
```

#### Batch Delete by Criteria
```http
DELETE /api/v1/exercises/batch
```

**Query Parameters:**
- `fitness_level_min` (optional): Minimum fitness level (0-10)
- `fitness_level_max` (optional): Maximum fitness level (0-10)
- `intensity_min` (optional): Minimum intensity (0-10)
- `intensity_max` (optional): Maximum intensity (0-10)
- `exercise_name_pattern` (optional): Pattern to match exercise names
- `created_before` (optional): Delete exercises created before this date (ISO format)
- `created_after` (optional): Delete exercises created after this date (ISO format)

#### Purge Low Quality Exercises
```http
DELETE /api/v1/exercises/purge-low-quality
```

**Query Parameters:**
- `fitness_level_threshold` (optional): Delete exercises below this fitness level (default: 3)
- `intensity_threshold` (optional): Delete exercises below this intensity level (default: 3)
- `name_patterns` (optional): Comma-separated patterns to match for deletion

#### Preview Deletion
```http
GET /api/v1/exercises/deletion-preview
```

**Query Parameters:** Same as batch delete, but only shows what would be deleted

---

## 🗑️ Verified Delete Workflow

When you delete an exercise using `DELETE /api/v1/exercises/{exercise_id}`:
- The exercise row is removed from PostgreSQL
- The associated video file is deleted from `storage/clips/`
- The vector is removed from Qdrant
- The API will return `{"detail": "Exercise not found"}` if you try to fetch a deleted exercise
- The file will not be present in the file system
- The vector will not be returned in semantic search results

This ensures **full cleanup** of all exercise data across the system.

---

## 🔧 UTILITY ENDPOINTS

### Health Checks
```http
GET /health
GET /api/v1/health/database
GET /api/v1/health/vector
```

### Statistics
```http
GET /api/v1/stats
```

### Cleanup Operations
```http
GET /api/v1/cleanup/analysis
GET /api/v1/cleanup/orphaned-files
DELETE /api/v1/cleanup/orphaned-files?confirm=true
DELETE /api/v1/cleanup/temp-files?days_old=7&confirm=true
GET /api/v1/cleanup/preview
```

### Generate Clip from Exercise
```http
POST /api/v1/exercises/{exercise_id}/generate-clip
```

---

## 📡 API Usage Examples

### Generate a Pull-up Progression Routine
```bash
curl -X POST http://localhost:8000/api/v1/generate-routine \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "I want to get good at pull ups but i can only do 1 at the moment",
    "target_duration": 900,
    "intensity_level": "moderate"
  }'
```

### Process Instagram Fitness Video
```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/CxYz123ABC/",
    "background": true
  }'
```

### Search for Back Exercises
```bash
curl -X POST http://localhost:8000/api/v1/exercises/semantic-search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I need a beginner workout for my back that helps with posture",
    "limit": 10
  }'
```

### Get Stored Routine
```bash
curl -X GET http://localhost:8000/api/v1/routines/359072d3-b5f8-40e9-a79a-81283533c3d6
```

---

## 🔧 Configuration

### Environment Variables
- `PG_HOST` - PostgreSQL host
- `PG_DBNAME` - Database name
- `PG_USER` - Database user
- `PG_PASSWORD` - Database password
- `QDRANT_URL` - Qdrant server URL
- `QDRANT_API_KEY` - Qdrant API key
- `OPENAI_API_KEY` - OpenAI API key
- `GEMINI_API_KEY` - Gemini API key (primary)
- `GEMINI_API_BACKUP_KEY` - Gemini API key (backup/fallback)

## 🏗️ Architecture

- **FastAPI** - REST API backend
- **PostgreSQL** - Exercise metadata storage
- **Qdrant** - Vector database for semantic search
- **FFmpeg** - Video processing and clip generation
- **OpenAI/Gemini** - AI analysis and transcription (with automatic fallback)
- **Instagram Carousel Support** - Automatic detection and processing of multi-item posts

## 📁 Project Structure

```
app/
├── api/          # FastAPI endpoints
├── core/         # Video processing pipeline
├── database/     # Database operations
├── services/     # External services (AI, storage)
└── utils/        # Utility functions
```

## ⚡ Processing Pipeline

1. **Download**: Video downloaded from URL
2. **Transcribe**: Audio transcribed with Whisper
3. **Extract Frames**: Key frames extracted for AI analysis
4. **AI Detection**: Gemini AI analyzes video + transcript + frames
5. **Generate Clips**: FFmpeg creates individual exercise clips
6. **Store**: Metadata in PostgreSQL, embeddings in Qdrant

## 🚨 Error Handling

- **Rate Limits**: Automatic fallback between Gemini API keys
- **Invalid URLs**: Clear error messages for unsupported platforms
- **Processing Failures**: Detailed error logs in temp directories
- **Network Issues**: Retry logic for downloads and API calls

## 🧪 Testing

```bash
# Test the API
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/fitness-video.mp4"}'

# Test semantic search
curl -X POST http://localhost:8000/api/v1/exercises/semantic-search \
  -H "Content-Type: application/json" \
  -d '{"query": "I need a beginner workout for my back"}'
```

## 🌐 UI API Base URL Configuration (LAN, Tailscale, or Public)

Your UI should NOT hardcode the API base URL. Instead, use an environment variable or config file so you can easily switch between:
- Local LAN (e.g., http://192.168.0.47:8000)
- Tailscale (e.g., http://100.x.x.x:8000)
- Public IP or domain

**Example (React):**
```js
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;
fetch(`${API_BASE_URL}/api/v1/exercises`)
```

**Example (.env):**
```
REACT_APP_API_BASE_URL=http://100.x.x.x:8000
```

**Result:**
- UI works locally, remotely (Tailscale), or publicly by changing one variable
- Video clips and all API endpoints will work as long as the API is reachable

## 📂 Static File Serving

The API now serves all video clips and files from `/app/storage` at the `/storage` URL path. For example:
```
http://<API_HOST>:8000/storage/clips/filename.mp4
```
No changes are needed to Docker volumes or the UI code. Just ensure the UI uses the correct API base URL.
